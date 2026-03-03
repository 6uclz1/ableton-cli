from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Spec:
    command_name: str
    client_method: str


def test_run_client_command_dispatches_execute_command_with_client_action() -> None:
    from ableton_cli.commands._client_command_runner import run_client_command

    captured: dict[str, object] = {}

    class _Client:
        pass

    client = _Client()

    def _get_client(_ctx):  # noqa: ANN202
        captured["get_client_called"] = True
        return client

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    run_client_command(
        ctx=object(),
        command_name="demo command",
        args={"value": 1},
        fn=lambda resolved_client: {"same_client": resolved_client is client},
        get_client_fn=_get_client,
        execute_command_fn=_execute_command,
    )

    assert captured["command"] == "demo command"
    assert captured["args"] == {"value": 1}
    assert captured["get_client_called"] is True
    assert captured["result"] == {"same_client": True}


def test_run_client_command_spec_dispatches_method_with_resolved_kwargs_callable() -> None:
    from ableton_cli.commands._client_command_runner import run_client_command_spec

    captured: dict[str, object] = {}

    class _Client:
        def ping(self, *, value: int):  # noqa: ANN201
            return {"value": value}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    run_client_command_spec(
        ctx=object(),
        spec=_Spec(command_name="demo ping", client_method="ping"),
        args={"value": 3},
        method_kwargs=lambda: {"value": 7},
        get_client_fn=_get_client,
        execute_command_fn=_execute_command,
    )

    assert captured["command"] == "demo ping"
    assert captured["args"] == {"value": 3}
    assert captured["result"] == {"value": 7}


def test_run_client_command_spec_uses_empty_kwargs_when_not_provided() -> None:
    from ableton_cli.commands._client_command_runner import run_client_command_spec

    captured: dict[str, object] = {}

    class _Client:
        def version(self):  # noqa: ANN201
            return {"version": "1.0.0"}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    run_client_command_spec(
        ctx=object(),
        spec=_Spec(command_name="demo version", client_method="version"),
        args={},
        get_client_fn=_get_client,
        execute_command_fn=_execute_command,
    )

    assert captured["command"] == "demo version"
    assert captured["args"] == {}
    assert captured["result"] == {"version": "1.0.0"}
