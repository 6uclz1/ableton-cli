from __future__ import annotations


def test_session_run_client_command_spec_passes_method_kwargs(monkeypatch) -> None:
    from ableton_cli.commands import session

    captured: dict[str, object] = {}

    class _Client:
        def stop_all_clips(self):  # noqa: ANN201
            return {"stopped": True}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(session, "get_client", _get_client)
    monkeypatch.setattr(session, "execute_command", _execute_command)

    session.run_client_command_spec(
        ctx=object(),
        spec=session.SessionCommandSpec(
            command_name="session stop-all-clips",
            client_method="stop_all_clips",
        ),
        args={},
    )

    assert captured["command"] == "session stop-all-clips"
    assert captured["args"] == {}
    assert captured["result"] == {"stopped": True}
