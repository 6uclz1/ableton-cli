from __future__ import annotations

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
def fake_ffmpeg_loudness(monkeypatch) -> None:
    """Stand in for ffmpeg so loudness analysis runs on hosts without it.

    The fake derives every EBU R128 value from the file's sample peak, so louder
    files still measure louder; tests that need real BS.1770 numbers run ffmpeg.
    """
    from ableton_cli.audio_analysis.ebur128 import Ebur128Measurement
    from ableton_cli.audio_analysis.io import amplitude_dbfs, read_wav

    def measure(path: str | Path) -> Ebur128Measurement:
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

    monkeypatch.setattr(
        "ableton_cli.audio_analysis.loudness.require_ffmpeg_engine",
        lambda engine: engine.strip().lower(),
    )
    monkeypatch.setattr("ableton_cli.audio_analysis.loudness.measure_ebur128", measure)
