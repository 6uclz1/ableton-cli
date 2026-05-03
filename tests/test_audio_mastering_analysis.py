from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path


def _write_sine(path: Path, *, freq: float = 440.0, amp: float = 0.5, seconds: float = 1.0) -> None:
    sample_rate = 48000
    frame_count = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            sample = int(amp * 32767 * math.sin(2 * math.pi * freq * index / sample_rate))
            frames.extend(struct.pack("<hh", sample, sample))
        wav.writeframes(bytes(frames))


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def _allow_ffmpeg_engine(monkeypatch) -> None:
    monkeypatch.setattr(
        "ableton_cli.audio_analysis.loudness.require_ffmpeg_engine",
        lambda engine: engine.strip().lower(),
    )


def test_audio_loudness_analyze_reports_peak_rms_and_crest(
    runner,
    cli_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _allow_ffmpeg_engine(monkeypatch)
    audio_path = tmp_path / "tone.wav"
    report_path = tmp_path / "loudness.json"
    _write_sine(audio_path, amp=0.5)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "loudness",
            "analyze",
            "--path",
            str(audio_path),
            "--engine",
            "ffmpeg",
            "--report-out",
            str(report_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = _payload(result.stdout)
    analysis = payload["result"]
    assert analysis["engine"] == "ffmpeg"  # type: ignore[index]
    assert analysis["sample_rate"] == 48000  # type: ignore[index]
    assert analysis["channels"] == 2  # type: ignore[index]
    assert analysis["clipping_sample_count"] == 0  # type: ignore[index]
    assert math.isclose(float(analysis["sample_peak_dbfs"]), -6.02, abs_tol=0.15)  # type: ignore[index]
    assert math.isclose(float(analysis["rms_dbfs"]), -9.03, abs_tol=0.2)  # type: ignore[index]
    assert math.isclose(float(analysis["crest_db"]), 3.01, abs_tol=0.25)  # type: ignore[index]
    assert json.loads(report_path.read_text(encoding="utf-8"))["path"] == str(audio_path)


def test_audio_loudness_analyze_requires_ffmpeg_engine(
    runner,
    cli_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    audio_path = tmp_path / "tone.wav"
    _write_sine(audio_path, amp=0.5)
    monkeypatch.setattr("ableton_cli.audio_analysis.io.shutil.which", lambda _name: None)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "loudness",
            "analyze",
            "--path",
            str(audio_path),
            "--engine",
            "ffmpeg",
        ],
    )

    assert result.exit_code == 3, result.stdout
    payload = _payload(result.stdout)
    error = payload["error"]
    assert error["code"] == "CONFIG_INVALID"  # type: ignore[index]
    assert "ffmpeg engine is not available" in error["message"]  # type: ignore[index]


def test_audio_spectrum_analyze_reports_bands_and_stereo(
    runner,
    cli_app,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "bass.wav"
    _write_sine(audio_path, freq=80.0, amp=0.4)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "spectrum",
            "analyze",
            "--path",
            str(audio_path),
            "--profile",
            "anime-club",
        ],
    )

    assert result.exit_code == 0, result.stdout
    spectrum = _payload(result.stdout)["result"]
    bands = spectrum["bands"]  # type: ignore[index]
    assert bands["bass_60_120_hz"] > bands["presence_2000_6000_hz"]  # type: ignore[index]
    assert spectrum["stereo"]["mono_low_end_risk"] is False  # type: ignore[index]


def test_audio_reference_compare_reports_metric_deltas(
    runner,
    cli_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _allow_ffmpeg_engine(monkeypatch)
    candidate = tmp_path / "candidate.wav"
    reference = tmp_path / "reference.wav"
    _write_sine(candidate, freq=80.0, amp=0.25)
    _write_sine(reference, freq=80.0, amp=0.5)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "reference",
            "compare",
            "--candidate",
            str(candidate),
            "--reference",
            str(reference),
            "--metrics",
            "loudness,spectrum,stereo",
        ],
    )

    assert result.exit_code == 0, result.stdout
    comparison = _payload(result.stdout)["result"]
    assert comparison["delta"]["integrated_lufs"] < 0  # type: ignore[index]
    assert "recommendations" in comparison  # type: ignore[operator]
