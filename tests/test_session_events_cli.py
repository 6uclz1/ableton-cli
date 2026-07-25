from __future__ import annotations

import json
from typing import Any

import pytest

from ableton_cli.client.events import EventStream, parse_event_line
from ableton_cli.commands import session as session_module
from ableton_cli.config import Settings
from ableton_cli.errors import AppError
from remote_script.AbletonCliRemote.events import EventBroker
from remote_script.AbletonCliRemote.server import AbletonCommandServer


class _StreamStub:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events
        self.opened = False
        self.closed = False
        self.kwargs: dict[str, Any] = {}

    def open(self) -> list[str]:
        self.opened = True
        return ["tempo"]

    def events(self, *, count: int | None = None):  # noqa: ANN202
        for index, event in enumerate(self._events):
            if count is not None and index >= count:
                return
            yield event

    def close(self) -> None:
        self.closed = True


def _event(name: str = "tempo") -> dict[str, Any]:
    return {
        "type": "event",
        "protocol_version": 2,
        "event": name,
        "ts": 1.0,
        "data": {"tempo": 128.0},
        "dropped": 0,
    }


def test_session_events_prints_one_json_line_per_event(runner, cli_app, monkeypatch) -> None:
    stub = _StreamStub([_event(), _event("is_playing")])
    monkeypatch.setattr(session_module, "_open_event_stream", lambda ctx, **kwargs: stub)

    result = runner.invoke(cli_app, ["--output", "json", "session", "events", "--count", "2"])

    assert result.exit_code == 0, result.stdout
    lines = [json.loads(line) for line in result.stdout.strip().splitlines()]
    assert [line["event"] for line in lines] == ["tempo", "is_playing"]
    assert stub.opened is True
    assert stub.closed is True


def test_session_events_passes_the_selected_events_through(runner, cli_app, monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _open(ctx, **kwargs):  # noqa: ANN001, ANN202
        captured.update(kwargs)
        return _StreamStub([])

    monkeypatch.setattr(session_module, "_open_event_stream", _open)
    result = runner.invoke(
        cli_app,
        ["--output", "json", "session", "events", "--events", "tempo, is_playing"],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["events"] == ["tempo", "is_playing"]
    assert captured["idle_timeout_ms"] is None


def test_session_events_rejects_unknown_event_names(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app, ["--output", "json", "session", "events", "--events", "weather"]
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_session_events_respects_plan_mode(runner, cli_app, monkeypatch) -> None:
    def _fail(ctx, **kwargs):  # noqa: ANN001, ANN202
        raise AssertionError("plan mode must not open a connection")

    monkeypatch.setattr(session_module, "_open_event_stream", _fail)
    result = runner.invoke(cli_app, ["--output", "json", "--plan", "session", "events"])

    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["command"] == "session events"


def test_parse_event_line_rejects_non_event_payloads() -> None:
    with pytest.raises(AppError):
        parse_event_line({"ok": True})
    with pytest.raises(AppError):
        parse_event_line("nope")
    with pytest.raises(AppError):
        parse_event_line({"type": "event", "event": "tempo"})


def _serve(broker: EventBroker) -> tuple[AbletonCommandServer, int]:
    server = AbletonCommandServer(
        host="127.0.0.1",
        port=0,
        command_executor=lambda name, args, meta: {},
        event_subscriber=lambda args, meta: broker.subscribe(args.get("events", [])),
        event_unsubscriber=broker.unsubscribe,
    )
    server.start()
    return server, server._server.server_address[1]  # noqa: SLF001


def test_event_stream_round_trip_against_the_remote_server() -> None:
    broker = EventBroker(time_fn=lambda: 5.0)
    server, port = _serve(broker)
    settings = Settings(host="127.0.0.1", port=port, timeout_ms=5000)
    try:
        with EventStream(settings, events=["tempo"], idle_timeout_ms=5000) as stream:
            assert stream.subscribed == ["tempo"]
            broker.publish("tempo", {"tempo": 174.0})
            received = next(iter(stream.events(count=1)))
            assert received["event"] == "tempo"
            assert received["data"] == {"tempo": 174.0}
            assert received["dropped"] == 0
    finally:
        server.stop()


def test_event_stream_surfaces_a_remote_subscription_error() -> None:
    broker = EventBroker()
    server, port = _serve(broker)
    settings = Settings(host="127.0.0.1", port=port, timeout_ms=5000)
    try:
        stream = EventStream(settings, events=["weather"])
        with pytest.raises(AppError) as exc_info:
            stream.open()
        assert exc_info.value.error_code
        stream.close()
    finally:
        server.stop()
