from __future__ import annotations


def test_transport_run_client_command_spec_dispatches_method(monkeypatch) -> None:
    from ableton_cli.commands import transport

    captured: dict[str, object] = {}

    class _Client:
        def transport_play(self):  # noqa: ANN201
            return {"playing": True}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(transport, "get_client", _get_client)
    monkeypatch.setattr(transport, "execute_command", _execute_command)

    transport.run_client_command_spec(
        ctx=object(),
        spec=transport.TransportCommandSpec(
            command_name="transport play",
            client_method="transport_play",
        ),
        args={},
    )

    assert captured["command"] == "transport play"
    assert captured["args"] == {}
    assert captured["result"] == {"playing": True}
