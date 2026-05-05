from __future__ import annotations

import json
import struct
import wave
from pathlib import Path

import pytest

from ableton_cli.audio_analysis.transient import analyze_transients
from ableton_cli.errors import AppError


def _write_impulse_wav(
    path: Path,
    *,
    bpm: float = 120.0,
    beats: float = 4.0,
    impulses: list[tuple[float, float, str]] | None = None,
    sample_rate: int = 44100,
) -> None:
    impulses = impulses or []
    frame_count = int(sample_rate * beats * 60.0 / bpm)
    impulse_map = {
        int(round(beat * 60.0 / bpm * sample_rate)): (amp, channel)
        for beat, amp, channel in impulses
    }
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            amp, channel = impulse_map.get(index, (0.0, "both"))
            value = int(max(-1.0, min(1.0, amp)) * 32767)
            left = value if channel in {"left", "both"} else 0
            right = value if channel in {"right", "both"} else 0
            frames.extend(struct.pack("<hh", left, right))
        wav.writeframes(bytes(frames))


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def test_transient_analysis_detects_impulses_at_known_beats(tmp_path: Path) -> None:
    audio_path = tmp_path / "break.wav"
    _write_impulse_wav(
        audio_path,
        bpm=120.0,
        beats=4.0,
        impulses=[(1.0, 0.9, "both"), (2.5, 0.8, "both")],
    )

    result = analyze_transients(audio_path, bpm=120.0, max_slices=16)

    assert result["path"] == str(audio_path.resolve())
    assert result["analysis_version"] == "builtin_energy_flux_v1"
    assert result["sample_rate"] == 44100
    assert result["channels"] == 2
    assert result["duration_beats"] == pytest.approx(4.0, abs=0.01)
    assert result["warnings"] == []
    assert result["onset_points_beats"] == pytest.approx([1.0, 2.5], abs=0.04)
    assert result["slice_points_beats"] == pytest.approx([0.0, 1.0, 2.5, 4.0], abs=0.04)
    assert result["slice_ranges"][1]["slice_start"] == pytest.approx(1.0, abs=0.04)  # type: ignore[index]
    assert 0.0 <= float(result["confidence"]) <= 1.0


def test_transient_analysis_detects_hard_panned_impulse(tmp_path: Path) -> None:
    audio_path = tmp_path / "panned.wav"
    _write_impulse_wav(
        audio_path,
        bpm=100.0,
        beats=2.0,
        impulses=[(0.75, 0.9, "right")],
    )

    result = analyze_transients(audio_path, bpm=100.0, max_slices=8)

    assert result["onset_points_beats"] == pytest.approx([0.75], abs=0.04)


def test_transient_analysis_merges_near_duplicate_impulses_by_strength(tmp_path: Path) -> None:
    audio_path = tmp_path / "duplicates.wav"
    _write_impulse_wav(
        audio_path,
        bpm=120.0,
        beats=2.0,
        impulses=[(1.0, 0.3, "both"), (1.05, 0.95, "both")],
    )

    result = analyze_transients(audio_path, bpm=120.0, max_slices=8)

    assert result["onset_points_beats"] == pytest.approx([1.05], abs=0.04)


def test_transient_analysis_truncates_to_strongest_slices_in_chronological_order(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "many.wav"
    _write_impulse_wav(
        audio_path,
        bpm=120.0,
        beats=4.0,
        impulses=[
            (0.5, 0.2, "both"),
            (1.0, 0.9, "both"),
            (2.0, 0.7, "both"),
            (3.0, 0.5, "both"),
        ],
    )

    result = analyze_transients(audio_path, bpm=120.0, max_slices=3)

    assert result["onset_points_beats"] == pytest.approx([1.0, 2.0], abs=0.04)
    assert len(result["slice_ranges"]) == 3


def test_transient_analysis_silence_returns_full_range_with_low_confidence(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "silence.wav"
    _write_impulse_wav(audio_path, bpm=120.0, beats=2.0, impulses=[])

    result = analyze_transients(audio_path, bpm=120.0, max_slices=8)

    assert result["onset_points_beats"] == []
    assert result["slice_points_beats"] == [0.0, 2.0]
    assert result["slice_ranges"] == [
        {"index": 0, "slice_start": 0.0, "slice_end": 2.0, "duration_beats": 2.0}
    ]
    assert result["warnings"] == ["LOW_CONFIDENCE"]


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("source.aiff", b"FORM"),
        ("source.flac", b"fLaC"),
        ("source.txt", b"not audio"),
    ],
)
def test_transient_analysis_rejects_non_wav_formats(
    tmp_path: Path,
    filename: str,
    content: bytes,
) -> None:
    audio_path = tmp_path / filename
    audio_path.write_bytes(content)

    with pytest.raises(AppError) as error:
        analyze_transients(audio_path, bpm=120.0, max_slices=8)

    assert error.value.error_code.value == "INVALID_ARGUMENT"


def test_transient_analysis_rejects_compressed_or_non_pcm_wav(tmp_path: Path) -> None:
    audio_path = tmp_path / "float.wav"
    audio_path.write_bytes(
        b"RIFF"
        + (38).to_bytes(4, "little")
        + b"WAVEfmt "
        + (18).to_bytes(4, "little")
        + (3).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + (44100).to_bytes(4, "little")
        + (176400).to_bytes(4, "little")
        + (4).to_bytes(2, "little")
        + (32).to_bytes(2, "little")
        + (0).to_bytes(2, "little")
        + b"data"
        + (0).to_bytes(4, "little")
    )

    with pytest.raises(AppError) as error:
        analyze_transients(audio_path, bpm=120.0, max_slices=8)

    assert error.value.error_code.value == "INVALID_ARGUMENT"


def test_transient_analysis_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AppError) as error:
        analyze_transients(tmp_path / "missing.wav", bpm=120.0, max_slices=8)

    assert error.value.error_code.value == "INVALID_ARGUMENT"


@pytest.mark.parametrize("bpm", [19.99, 1000.0])
def test_transient_analysis_rejects_invalid_bpm(tmp_path: Path, bpm: float) -> None:
    audio_path = tmp_path / "source.wav"
    _write_impulse_wav(audio_path)

    with pytest.raises(AppError) as error:
        analyze_transients(audio_path, bpm=bpm, max_slices=8)

    assert error.value.error_code.value == "INVALID_ARGUMENT"


def test_audio_transient_analyze_command_returns_stable_json_fields(
    runner,
    cli_app,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "break.wav"
    _write_impulse_wav(audio_path, bpm=120.0, beats=2.0, impulses=[(1.0, 0.8, "both")])

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "transient",
            "analyze",
            "--path",
            str(audio_path),
            "--bpm",
            "120",
            "--max-slices",
            "8",
        ],
    )

    assert result.exit_code == 0, result.stdout
    analysis = _payload(result.stdout)["result"]
    assert analysis["path"] == str(audio_path.resolve())  # type: ignore[index]
    assert analysis["bpm"] == 120.0  # type: ignore[index]
    assert analysis["analysis_version"] == "builtin_energy_flux_v1"  # type: ignore[index]
    assert analysis["slice_ranges"][0]["slice_start"] == 0.0  # type: ignore[index]
