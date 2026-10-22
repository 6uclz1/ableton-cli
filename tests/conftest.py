from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ableton_cli.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_app():
    return app


@pytest.fixture
def fake_ffmpeg(monkeypatch) -> None:
    """Stand in for ffmpeg so loudness and spectrum analysis run on hosts without it.

    Loudness values follow the file's sample peak, so louder files still measure louder;
    every spectrum band reads -20 dBFS. Tests that need real measurements use real_ffmpeg.
    """
    from ableton_cli.audio_analysis.ebur128 import Ebur128Measurement
    from ableton_cli.audio_analysis.io import amplitude_dbfs, read_wav
    from ableton_cli.audio_analysis.spectrum import BANDS

    def measure_loudness(path: str | Path) -> Ebur128Measurement:
        data = read_wav(path)
        peak_dbfs = amplitude_dbfs(
            max(abs(sample) for channel in data.samples for sample in channel)
        )
        return Ebur128Measurement(
            integrated_lufs=round(peak_dbfs - 3.0, 1),
            lra_lu=0.0,
            true_peak_dbtp=round(peak_dbfs, 1),
            momentary_lufs_max=round(peak_dbfs - 3.0, 1),
            short_term_lufs_max=round(peak_dbfs - 3.0, 1),
        )

    def measure_bands(path: str | Path, *, channels: int) -> dict[str, float]:
        return {name: -20.0 for name, _low, _high in BANDS}

    for module in ("loudness", "spectrum"):
        monkeypatch.setattr(
            f"ableton_cli.audio_analysis.{module}.require_ffmpeg_engine",
            lambda engine: engine.strip().lower(),
        )
    monkeypatch.setattr("ableton_cli.audio_analysis.loudness.measure_ebur128", measure_loudness)
    monkeypatch.setattr("ableton_cli.audio_analysis.spectrum.measure_band_levels", measure_bands)


@pytest.fixture
def real_ffmpeg() -> None:
    """Skip a test that measures through the real ffmpeg when the host lacks it."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are required for real audio measurement")
