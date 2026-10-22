from __future__ import annotations

import math
import struct
import subprocess
import wave
from pathlib import Path

import pytest

from ableton_cli.errors import AppError

SAMPLE_RATE = 48000


def _write_stereo(path: Path, frames: list[float]) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        payload = bytearray()
        for value in frames:
            sample = int(value * 32767)
            payload.extend(struct.pack("<hh", sample, sample))
        wav.writeframes(bytes(payload))


def _sine(*, freq: float, amp: float, seconds: float) -> list[float]:
    return [
        amp * math.sin(2 * math.pi * freq * index / SAMPLE_RATE)
        for index in range(int(SAMPLE_RATE * seconds))
    ]


def test_bands_cover_20_hz_to_18_khz_without_gaps() -> None:
    from ableton_cli.audio_analysis.spectrum import BANDS

    edges = [(low, high) for _name, low, high in BANDS]
    assert edges[0][0] == 20.0
    assert edges[-1][1] == 18000.0
    for (_low, high), (next_low, _high) in zip(edges, edges[1:], strict=False):
        assert high == next_low
    assert "brilliance_6000_10000_hz" in [name for name, _low, _high in BANDS]


def test_measure_band_levels_filters_each_band_over_the_whole_file(tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import BANDS, measure_band_levels

    commands: list[list[str]] = []

    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        stderr = "[Parsed_astats_6 @ 0x1] Overall\n[Parsed_astats_6 @ 0x1] RMS level dB: -21.5\n"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr=stderr)

    audio_path = tmp_path / "mix.wav"
    levels = measure_band_levels(audio_path, channels=2, run=run)

    assert levels == {name: -21.5 for name, _low, _high in BANDS}
    assert len(commands) == len(BANDS)
    for command, (_name, low, high) in zip(commands, BANDS, strict=True):
        assert str(audio_path) in command
        assert "-ss" not in command and "-t" not in command
        graph = command[command.index("-af") + 1]
        assert graph.startswith("pan=mono|c0=0.5*c0+0.5*c1,")
        assert graph.count(f"between(b*sr/(2*(nb-1)),{low:g},{high:g})") == 2


def test_measure_band_levels_reads_silent_band_as_negative_infinity(tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import measure_band_levels

    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        stderr = "[Parsed_astats_4 @ 0x1] RMS level dB: -inf\n"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr=stderr)

    levels = measure_band_levels(tmp_path / "mix.wav", channels=1, run=run)

    assert set(levels.values()) == {float("-inf")}


def test_measure_band_levels_fails_without_rms_reading(tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import measure_band_levels

    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    with pytest.raises(AppError) as exc_info:
        measure_band_levels(tmp_path / "mix.wav", channels=2, run=run)

    assert exc_info.value.error_code == "INTERNAL_ERROR"
    assert exc_info.value.details["band"] == "sub_20_60_hz"


def test_measure_band_levels_fails_when_ffmpeg_exits_nonzero(tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import measure_band_levels

    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="boom\n")

    with pytest.raises(AppError) as exc_info:
        measure_band_levels(tmp_path / "mix.wav", channels=2, run=run)

    assert exc_info.value.error_code == "INTERNAL_ERROR"
    assert exc_info.value.details["returncode"] == 1
    assert exc_info.value.details["stderr_tail"] == ["boom"]


def test_audio_spectrum_analyze_requires_ffmpeg(runner, cli_app, tmp_path: Path, monkeypatch):
    audio_path = tmp_path / "tone.wav"
    _write_stereo(audio_path, _sine(freq=80.0, amp=0.5, seconds=0.5))
    monkeypatch.setattr("ableton_cli.audio_analysis.io.shutil.which", lambda _name: None)

    result = runner.invoke(
        cli_app,
        ["--output", "json", "audio", "spectrum", "analyze", "--path", str(audio_path)],
    )

    assert result.exit_code == 3, result.stdout
    assert '"code": "CONFIG_INVALID"' in result.stdout


def test_analyze_spectrum_puts_a_tone_in_its_band(tmp_path: Path, real_ffmpeg) -> None:
    from ableton_cli.audio_analysis import analyze_spectrum

    audio_path = tmp_path / "tone.wav"
    _write_stereo(audio_path, _sine(freq=7500.0, amp=0.5, seconds=2.0))

    bands = analyze_spectrum(audio_path)["bands"]

    # A 0.5-amplitude sine has an RMS of -9.03 dBFS.
    assert math.isclose(bands["brilliance_6000_10000_hz"], -9.03, abs_tol=0.6)
    for far_band in ("sub_20_60_hz", "bass_60_120_hz", "low_mid_120_400_hz", "mid_400_2000_hz"):
        assert bands[far_band] < -45.0


def test_analyze_spectrum_measures_the_whole_file(tmp_path: Path, real_ffmpeg) -> None:
    from ableton_cli.audio_analysis import analyze_spectrum

    audio_path = tmp_path / "late_tone.wav"
    tone = _sine(freq=80.0, amp=0.5, seconds=4.0)
    _write_stereo(audio_path, [0.0] * len(tone) + tone)

    bands = analyze_spectrum(audio_path)["bands"]

    # The tone fills half the file, so its band reads 3 dB under the tone's RMS.
    assert math.isclose(bands["bass_60_120_hz"], -12.04, abs_tol=0.6)


def _analyze_with_bands(monkeypatch, tmp_path: Path, bands: dict[str, float], profile: str):
    from ableton_cli.audio_analysis import analyze_spectrum

    monkeypatch.setattr(
        "ableton_cli.audio_analysis.spectrum.require_ffmpeg_engine", lambda engine: engine
    )
    monkeypatch.setattr(
        "ableton_cli.audio_analysis.spectrum.measure_band_levels",
        lambda path, *, channels: dict(bands),
    )
    audio_path = tmp_path / "mix.wav"
    _write_stereo(audio_path, _sine(freq=80.0, amp=0.5, seconds=0.1))
    return analyze_spectrum(audio_path, profile=profile)


def test_every_profile_has_a_baseline_for_every_band() -> None:
    from ableton_cli.audio_analysis.spectrum import BANDS, PROFILE_BASELINES

    band_names = {name for name, _low, _high in BANDS}
    for profile, baseline in PROFILE_BASELINES.items():
        assert set(baseline) == band_names, profile


@pytest.mark.parametrize("level_offset_db", [-20.0, 0.0, 15.0])
def test_profile_warnings_judge_balance_not_loudness(
    monkeypatch, tmp_path: Path, level_offset_db: float
) -> None:
    from ableton_cli.audio_analysis.spectrum import PROFILE_BASELINES

    bands = {
        name: value + level_offset_db
        for name, value in PROFILE_BASELINES["anime-club-balanced"].items()
    }

    result = _analyze_with_bands(monkeypatch, tmp_path, bands, "anime-club-balanced")

    assert result["warnings"] == []


def test_profile_warnings_flag_a_band_far_above_its_share(monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import PROFILE_BASELINES

    bands = dict(PROFILE_BASELINES["anime-club-balanced"])
    bands["presence_2000_6000_hz"] += 9.0

    result = _analyze_with_bands(monkeypatch, tmp_path, bands, "anime-club-balanced")

    assert [warning["code"] for warning in result["warnings"]] == ["presence_2000_6000_hz_hot"]


def test_profile_warnings_report_silence_instead_of_judging_balance(
    monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.audio_analysis.spectrum import BANDS

    bands = {name: float("-inf") for name, _low, _high in BANDS}

    result = _analyze_with_bands(monkeypatch, tmp_path, bands, "anime-club")

    assert [warning["code"] for warning in result["warnings"]] == ["silent"]
