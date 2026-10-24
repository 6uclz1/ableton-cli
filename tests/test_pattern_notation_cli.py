from __future__ import annotations

import json


class _NotesClientStub:
    def add_notes_to_clip(self, track, clip, notes):  # noqa: ANN001, ANN201
        return {"track": track, "clip": clip, "notes": notes}


def test_clip_notes_add_compiles_pattern_and_calls_client(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _NotesClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "add",
            "0",
            "0",
            "--pattern",
            "c3 ~ [e3 g3] c4*2",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["notes"] == [
        {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100, "mute": False},
        {"pitch": 64, "start_time": 2.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": 67, "start_time": 2.5, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": 72, "start_time": 3.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": 72, "start_time": 3.5, "duration": 0.5, "velocity": 100, "mute": False},
    ]


def test_clip_notes_add_rejects_pattern_and_notes_json_together(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _NotesClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "add",
            "0",
            "0",
            "--pattern",
            "c3",
            "--notes-json",
            "[]",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_add_rejects_malformed_pattern_with_column_in_message(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _NotesClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "add", "0", "0", "--pattern", "c3 h3"],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert "column" in payload["error"]["message"]


def test_arrangement_clip_create_compiles_pattern(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    class _ArrangementClientStub:
        def arrangement_clip_create(self, **kwargs):  # noqa: ANN003, ANN201
            return {"created": True, "note_count": len(kwargs["notes"] or [])}

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ArrangementClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "0",
            "--start",
            "0",
            "--length",
            "4",
            "--pattern",
            "c3 e3 g3 c4",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["result"]["note_count"] == 4


def test_arrangement_clip_create_rejects_pattern_with_audio_path(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import arrangement

    class _ArrangementClientStub:
        def arrangement_clip_create(self, **kwargs):  # noqa: ANN003, ANN201
            return {"created": True}

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ArrangementClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "0",
            "--start",
            "0",
            "--length",
            "4",
            "--audio-path",
            "/tmp/loop.wav",
            "--pattern",
            "c3",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
