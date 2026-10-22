from __future__ import annotations

import json
import math
import struct
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


def _stem(tmp_path: Path, name: str) -> Path:
    path = tmp_path / f"{name}.wav"
    _write_stereo(path, _sine(freq=80.0, amp=0.1, seconds=0.1))
    return path


def _fake_levels(monkeypatch, levels_by_stem: dict[str, dict[str, float]]) -> None:
    """Measure each stem as the levels given for its file stem; unlisted bands are silent."""

    def measure(path, *, channels, bands):  # noqa: ANN001, ANN202
        levels = levels_by_stem[Path(path).stem]
        return {name: levels.get(name, float("-inf")) for name, _low, _high in bands}

    monkeypatch.setattr(
        "ableton_cli.audio_analysis.spectrum.require_ffmpeg_engine", lambda engine: engine
    )
    monkeypatch.setattr("ableton_cli.audio_analysis.spectrum.measure_band_levels", measure)


def test_third_octave_bands_are_contiguous_iso_bands() -> None:
    from ableton_cli.audio_analysis.spectrum import THIRD_OCTAVE_BANDS

    names = [name for name, _low, _high in THIRD_OCTAVE_BANDS]
    assert len(THIRD_OCTAVE_BANDS) == 29
    assert names[0] == "25_hz"
    assert names[names.index("1000_hz") - 1] == "800_hz"
    assert "31.5_hz" in names
    assert names[-1] == "16000_hz"
    for (_n, _low, high), (_next, next_low, _h) in zip(
        THIRD_OCTAVE_BANDS, THIRD_OCTAVE_BANDS[1:], strict=False
    ):
        assert high == next_low
    _name, low, high = THIRD_OCTAVE_BANDS[names.index("1000_hz")]
    assert math.isclose(low, 890.9, abs_tol=0.1)
    assert math.isclose(high, 1122.5, abs_tol=0.1)


def test_spectrum_shares_splits_each_band_by_stem_energy(monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import spectrum_shares

    _fake_levels(
        monkeypatch,
        {
            "kick": {"sub_20_60_hz": -20.0, "bass_60_120_hz": -20.0},
            "bass": {"sub_20_60_hz": -26.0206, "bass_60_120_hz": -20.0},
        },
    )

    result = spectrum_shares([("Kick", _stem(tmp_path, "kick")), ("Bass", _stem(tmp_path, "bass"))])

    assert result["resolution"] == "bands"
    assert result["bands"][0] == {"name": "sub_20_60_hz", "low_hz": 20.0, "high_hz": 60.0}
    assert [stem["label"] for stem in result["stems"]] == ["Kick", "Bass"]
    assert result["stems"][0]["levels"]["sub_20_60_hz"] == -20.0
    assert result["shares_pct"]["sub_20_60_hz"] == {"Kick": 80.0, "Bass": 20.0}
    assert result["shares_pct"]["bass_60_120_hz"] == {"Kick": 50.0, "Bass": 50.0}
    assert result["dominant"]["sub_20_60_hz"] == "Kick"
    assert math.isclose(result["band_totals_dbfs"]["bass_60_120_hz"], -16.99, abs_tol=0.01)
    assert "focus" not in result


def test_spectrum_shares_leave_silent_bands_unowned(monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import spectrum_shares

    _fake_levels(monkeypatch, {"a": {"sub_20_60_hz": -20.0}, "b": {}})

    result = spectrum_shares([("A", _stem(tmp_path, "a")), ("B", _stem(tmp_path, "b"))])

    assert result["shares_pct"]["air_10000_18000_hz"] == {"A": 0.0, "B": 0.0}
    assert result["dominant"]["air_10000_18000_hz"] is None
    assert result["band_totals_dbfs"]["air_10000_18000_hz"] == float("-inf")


def test_spectrum_shares_focus_reports_margin_over_loudest_other_stem(
    monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.audio_analysis.spectrum import spectrum_shares

    _fake_levels(
        monkeypatch,
        {
            "lead": {"mid_400_2000_hz": -30.0, "presence_2000_6000_hz": -30.0},
            "pluck": {"mid_400_2000_hz": -27.0, "presence_2000_6000_hz": -38.0},
            "perc": {"mid_400_2000_hz": -35.0, "presence_2000_6000_hz": -34.0},
        },
    )
    stems = [(label, _stem(tmp_path, label.lower())) for label in ("Lead", "Pluck", "Perc")]

    result = spectrum_shares(stems, focus="Lead")

    assert result["focus"]["label"] == "Lead"
    assert result["focus"]["margin_db"]["mid_400_2000_hz"] == -3.0
    assert result["focus"]["margin_db"]["presence_2000_6000_hz"] == 4.0
    assert result["focus"]["margin_db"]["air_10000_18000_hz"] is None


def test_spectrum_shares_third_octave_measures_third_octave_bands(
    monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.audio_analysis.spectrum import spectrum_shares

    _fake_levels(monkeypatch, {"a": {"1000_hz": -20.0}})

    result = spectrum_shares([("A", _stem(tmp_path, "a"))], resolution="third-octave")

    assert result["resolution"] == "third-octave"
    assert len(result["bands"]) == 29
    assert result["shares_pct"]["1000_hz"] == {"A": 100.0}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"stems": []}, "at least one stem"),
        ({"focus": "Missing"}, "focus label"),
        ({"resolution": "octave"}, "resolution"),
    ],
)
def test_spectrum_shares_rejects_invalid_requests(
    monkeypatch, tmp_path: Path, kwargs: dict[str, object], message: str
) -> None:
    from ableton_cli.audio_analysis.spectrum import spectrum_shares

    _fake_levels(monkeypatch, {"a": {}})
    request: dict[str, object] = {"stems": [("A", _stem(tmp_path, "a"))], **kwargs}

    with pytest.raises(AppError) as exc_info:
        spectrum_shares(**request)  # type: ignore[arg-type]

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert message in exc_info.value.message


def test_spectrum_shares_rejects_duplicate_labels(monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.spectrum import spectrum_shares

    _fake_levels(monkeypatch, {"a": {}})
    path = _stem(tmp_path, "a")

    with pytest.raises(AppError) as exc_info:
        spectrum_shares([("A", path), ("A", path)])

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert "duplicate stem label: A" in exc_info.value.message


def test_audio_spectrum_shares_cli_parses_stems_and_writes_report(
    runner, cli_app, tmp_path: Path, monkeypatch
) -> None:
    _fake_levels(monkeypatch, {"kick": {"sub_20_60_hz": -20.0}, "sub": {"sub_20_60_hz": -20.0}})
    report = tmp_path / "shares.json"

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "spectrum",
            "shares",
            "--stem",
            f"Kick={_stem(tmp_path, 'kick')}",
            "--stem",
            f"Sub={_stem(tmp_path, 'sub')}",
            "--focus",
            "Sub",
            "--report-out",
            str(report),
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["args"]["stems"] == [
        {"label": "Kick", "path": str(tmp_path / "kick.wav")},
        {"label": "Sub", "path": str(tmp_path / "sub.wav")},
    ]
    assert payload["result"]["shares_pct"]["sub_20_60_hz"] == {"Kick": 50.0, "Sub": 50.0}
    assert payload["result"]["focus"]["margin_db"]["sub_20_60_hz"] == 0.0
    assert json.loads(report.read_text(encoding="utf-8"))["resolution"] == "bands"


@pytest.mark.parametrize("stem", ["no-separator.wav", "=missing-label.wav", "Label="])
def test_audio_spectrum_shares_cli_rejects_malformed_stem(
    runner, cli_app, tmp_path: Path, stem: str
) -> None:
    result = runner.invoke(
        cli_app, ["--output", "json", "audio", "spectrum", "shares", "--stem", stem]
    )

    assert result.exit_code == 2, result.stdout
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_audio_spectrum_shares_cli_rejects_missing_file(runner, cli_app, tmp_path: Path) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "audio", "spectrum", "shares", "--stem", f"A={tmp_path / 'x.wav'}"],
    )

    assert result.exit_code == 2, result.stdout
    assert "audio file not found" in json.loads(result.stdout)["error"]["message"]


def test_spectrum_shares_measure_real_stems(tmp_path: Path, real_ffmpeg) -> None:
    from ableton_cli.audio_analysis.spectrum import spectrum_shares

    loud = tmp_path / "loud.wav"
    quiet = tmp_path / "quiet.wav"
    _write_stereo(loud, _sine(freq=80.0, amp=0.5, seconds=2.0))
    _write_stereo(quiet, _sine(freq=80.0, amp=0.25, seconds=2.0))

    result = spectrum_shares([("Loud", loud), ("Quiet", quiet)], focus="Quiet")

    # Half the amplitude is a quarter of the power: an 80/20 split of the band.
    assert result["shares_pct"]["bass_60_120_hz"] == {"Loud": 80.0, "Quiet": 20.0}
    assert math.isclose(result["focus"]["margin_db"]["bass_60_120_hz"], -6.02, abs_tol=0.1)
