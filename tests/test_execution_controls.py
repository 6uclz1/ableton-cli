from __future__ import annotations

import json


def test_require_confirmation_blocks_destructive_command_before_dispatch(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import song

    called = False

    class _ClientStub:
        def song_undo(self):  # noqa: ANN201
            nonlocal called
            called = True
            return {"undone": True}

    monkeypatch.setattr(song, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--require-confirmation", "--output", "json", "song", "undo"],
    )

    assert result.exit_code == 20
    assert called is False
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert payload["error"]["details"]["side_effect"]["kind"] == "destructive"


def test_require_confirmation_allows_destructive_command_with_yes(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import song

    class _ClientStub:
        def song_undo(self):  # noqa: ANN201
            return {"undone": True}

    monkeypatch.setattr(song, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--require-confirmation", "--yes", "--output", "json", "song", "undo"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"undone": True}


def test_plan_outputs_side_effect_metadata_without_dispatch(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import song

    called = False

    class _ClientStub:
        def song_undo(self):  # noqa: ANN201
            nonlocal called
            called = True
            return {"undone": True}

    monkeypatch.setattr(song, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--plan", "--output", "json", "song", "undo"])

    assert result.exit_code == 0
    assert called is False
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "song undo"
    assert payload["result"]["will_dispatch"] is False
    assert payload["result"]["side_effect"]["kind"] == "destructive"
    assert payload["result"]["requires_confirmation"] is True


def test_global_dry_run_outputs_write_plan_without_dispatch(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import transport

    called = False

    class _ClientStub:
        def transport_tempo_set(self, bpm: float):  # noqa: ANN201
            nonlocal called
            called = True
            return {"tempo": bpm}

    monkeypatch.setattr(transport, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--dry-run", "--output", "json", "transport", "tempo", "set", "128"],
    )

    assert result.exit_code == 0
    assert called is False
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["dry_run"] is True
    assert payload["result"]["side_effect"]["kind"] == "write"


def test_plan_applies_to_batch_stream_without_reading_stdin(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    called = False

    class _ClientStub:
        def execute_remote_command(self, name, args):  # noqa: ANN001, ANN201
            nonlocal called
            called = True
            return {"name": name, "args": args}

    monkeypatch.setattr(batch, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--plan", "--output", "json", "batch", "stream"])

    assert result.exit_code == 0
    assert called is False
    payload = json.loads(result.stdout)
    assert payload["command"] == "batch stream"
    assert payload["result"]["side_effect"]["kind"] == "destructive"
