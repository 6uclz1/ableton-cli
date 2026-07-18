from __future__ import annotations

import json
from pathlib import Path


def test_audio_groove_extract_writes_profile_to_out_file(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import _audio_groove_commands

    def _fake_analyze_transients(path, *, bpm, max_slices):  # noqa: ANN001, ANN201, ARG001
        return {
            "onset_points_beats": [0.0, 0.25, 4.0],
            "onset_strengths": [1.0, 0.5, 0.8],
        }

    monkeypatch.setattr(_audio_groove_commands, "analyze_transients", _fake_analyze_transients)

    wav_path = tmp_path / "loop.wav"
    wav_path.write_bytes(b"RIFF....WAVEfmt ")
    out_path = tmp_path / "groove.json"

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "groove",
            "extract",
            "--path",
            str(wav_path),
            "--bpm",
            "120",
            "--grid",
            "1/16",
            "--out",
            str(out_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["grid"] == "1/16"
    assert len(payload["result"]["slots"]) == 16

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written == payload["result"]


def test_audio_groove_extract_bars_filter_limits_transients(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import _audio_groove_commands

    captured: dict[str, object] = {}

    def _fake_extract_groove(transients, *, grid):  # noqa: ANN001, ANN201
        captured["transients"] = transients
        return {"grid": grid, "slots": []}

    def _fake_analyze_transients(path, *, bpm, max_slices):  # noqa: ANN001, ANN201, ARG001
        return {
            "onset_points_beats": [0.0, 2.0, 4.5],
            "onset_strengths": [1.0, 0.5, 0.8],
        }

    monkeypatch.setattr(_audio_groove_commands, "analyze_transients", _fake_analyze_transients)
    monkeypatch.setattr(_audio_groove_commands, "extract_groove", _fake_extract_groove)

    wav_path = tmp_path / "loop.wav"
    wav_path.write_bytes(b"RIFF....WAVEfmt ")

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "groove",
            "extract",
            "--path",
            str(wav_path),
            "--bpm",
            "120",
            "--bars",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["transients"] == [(0.0, 1.0), (2.0, 0.5)]
