from __future__ import annotations

import json
import socket
import time
from typing import Any

import pytest

from remote_script.AbletonCliRemote.events import (
    EVENT_NAMES,
    EventBroker,
    Subscription,
    UnknownEventError,
)
from remote_script.AbletonCliRemote.live_events import LiveEventSource
from remote_script.AbletonCliRemote.server import AbletonCommandServer


def test_broker_delivers_only_subscribed_events() -> None:
    broker = EventBroker(time_fn=lambda: 1.0)
    subscription = broker.subscribe(["tempo"])

    broker.publish("tempo", {"tempo": 128.0})
    broker.publish("is_playing", {"is_playing": True})

    received = subscription.get(timeout=0)
    assert received is not None
    event, dropped = received
    assert (event.name, event.data, event.ts, dropped) == ("tempo", {"tempo": 128.0}, 1.0, 0)
    assert subscription.get(timeout=0) is None


def test_empty_subscription_means_every_event() -> None:
    broker = EventBroker()
    subscription = broker.subscribe([])
    assert subscription.events == frozenset(EVENT_NAMES)


def test_unknown_event_names_are_rejected() -> None:
    broker = EventBroker()
    with pytest.raises(UnknownEventError):
        broker.subscribe(["tempo", "weather"])
    with pytest.raises(UnknownEventError):
        broker.publish("weather", {})


def test_slow_subscriber_drops_oldest_and_reports_the_count() -> None:
    subscription = Subscription(frozenset({"tempo"}), max_queued=2)
    for index in range(5):
        subscription.offer(_event(index))

    first = subscription.get(timeout=0)
    assert first is not None
    event, dropped = first
    assert dropped == 3
    assert event.data["n"] == 3  # oldest three were dropped

    second = subscription.get(timeout=0)
    assert second is not None
    assert second[1] == 0


def _event(index: int):  # noqa: ANN202
    from remote_script.AbletonCliRemote.events import Event

    return Event(name="tempo", data={"n": index}, ts=float(index))


def test_closed_subscription_stops_receiving() -> None:
    broker = EventBroker()
    subscription = broker.subscribe(["tempo"])
    broker.unsubscribe(subscription)
    broker.publish("tempo", {"tempo": 120.0})
    assert subscription.get(timeout=0) is None
    assert broker.subscription_count == 0


class _Song:
    def __init__(self) -> None:
        self.tempo = 120.0
        self.is_playing = False
        self.current_song_time = 0.0
        self.tracks: list[Any] = []
        self.view = _View()
        self.listeners: dict[str, Any] = {}

    def add_tempo_listener(self, callback) -> None:  # noqa: ANN001
        self.listeners["tempo"] = callback

    def remove_tempo_listener(self, callback) -> None:  # noqa: ANN001
        self.listeners.pop("tempo", None)

    def add_is_playing_listener(self, callback) -> None:  # noqa: ANN001
        self.listeners["is_playing"] = callback

    def remove_is_playing_listener(self, callback) -> None:  # noqa: ANN001
        self.listeners.pop("is_playing", None)

    def add_current_song_time_listener(self, callback) -> None:  # noqa: ANN001
        self.listeners["playing_position"] = callback

    def remove_current_song_time_listener(self, callback) -> None:  # noqa: ANN001
        self.listeners.pop("playing_position", None)


class _View:
    def __init__(self) -> None:
        self.selected_track = None


def test_live_event_source_attaches_only_supported_listeners() -> None:
    song = _Song()
    broker = EventBroker()
    source = LiveEventSource(lambda: song, broker)

    available = source.attach()

    # _View has no add_selected_track_listener, so that event is not offered.
    assert available == ("tempo", "is_playing", "playing_position")
    assert "selected_track" not in available


def test_live_event_source_publishes_current_values() -> None:
    song = _Song()
    broker = EventBroker(time_fn=lambda: 2.0)
    source = LiveEventSource(lambda: song, broker)
    source.attach()
    subscription = broker.subscribe(["tempo"])

    song.tempo = 174.0
    song.listeners["tempo"]()

    received = subscription.get(timeout=0)
    assert received is not None
    assert received[0].data == {"tempo": 174.0}


def test_playing_position_is_throttled() -> None:
    song = _Song()
    broker = EventBroker()
    clock = iter([0.0, 0.05, 0.2, 0.25])
    source = LiveEventSource(
        lambda: song, broker, time_fn=lambda: next(clock), position_interval_s=0.1
    )
    source.attach()
    subscription = broker.subscribe(["playing_position"])

    for _ in range(4):
        song.listeners["playing_position"]()

    delivered = 0
    while subscription.get(timeout=0) is not None:
        delivered += 1
    assert delivered == 2


def test_detach_removes_listeners() -> None:
    song = _Song()
    source = LiveEventSource(lambda: song, EventBroker())
    source.attach()
    source.detach()
    assert song.listeners == {}
    assert source.available_events() == ()


def test_source_without_a_song_offers_no_events() -> None:
    def _raise() -> Any:
        raise RuntimeError("Live is not running")

    source = LiveEventSource(_raise, EventBroker())
    assert source.attach() == ()


def _start_server(broker: EventBroker) -> tuple[AbletonCommandServer, int]:
    server = AbletonCommandServer(
        host="127.0.0.1",
        port=0,
        command_executor=lambda name, args, meta: {"name": name},
        event_subscriber=lambda args, meta: broker.subscribe(args.get("events", [])),
        event_unsubscriber=broker.unsubscribe,
    )
    server.start()
    port = server._server.server_address[1]  # noqa: SLF001
    return server, port


def _subscribe_request(events: list[str]) -> bytes:
    return (
        json.dumps(
            {
                "type": "subscribe",
                "name": "events",
                "args": {"events": events},
                "meta": {},
                "request_id": "sub-1",
                "protocol_version": 3,
            }
        )
        + "\n"
    ).encode("utf-8")


def test_server_streams_published_events_to_a_subscriber() -> None:
    broker = EventBroker(time_fn=lambda: 3.0)
    server, port = _start_server(broker)
    try:
        with (
            socket.create_connection(("127.0.0.1", port), timeout=5) as sock,
            sock.makefile("rwb") as stream,
        ):
            stream.write(_subscribe_request(["tempo"]))
            stream.flush()

            ack = json.loads(stream.readline().decode("utf-8"))
            assert ack["ok"] is True
            assert ack["result"] == {"subscribed": ["tempo"], "stream": True}

            deadline = time.monotonic() + 5
            while broker.subscription_count == 0 and time.monotonic() < deadline:
                time.sleep(0.01)
            broker.publish("tempo", {"tempo": 90.0})

            line = json.loads(stream.readline().decode("utf-8"))
            assert line == {
                "type": "event",
                "protocol_version": 3,
                "event": "tempo",
                "ts": 3.0,
                "data": {"tempo": 90.0},
                "dropped": 0,
            }
    finally:
        server.stop()


def test_server_rejects_an_unknown_event_name() -> None:
    broker = EventBroker()
    server, port = _start_server(broker)
    try:
        with (
            socket.create_connection(("127.0.0.1", port), timeout=5) as sock,
            sock.makefile("rwb") as stream,
        ):
            stream.write(_subscribe_request(["weather"]))
            stream.flush()
            response = json.loads(stream.readline().decode("utf-8"))
            assert response["ok"] is False
            assert response["error"]["code"] == "INTERNAL_ERROR"
    finally:
        server.stop()


def test_server_without_a_subscriber_refuses_subscriptions() -> None:
    server = AbletonCommandServer(
        host="127.0.0.1",
        port=0,
        command_executor=lambda name, args, meta: {},
    )
    server.start()
    port = server._server.server_address[1]  # noqa: SLF001
    try:
        with (
            socket.create_connection(("127.0.0.1", port), timeout=5) as sock,
            sock.makefile("rwb") as stream,
        ):
            stream.write(_subscribe_request([]))
            stream.flush()
            response = json.loads(stream.readline().decode("utf-8"))
            assert response["ok"] is False
            assert response["error"]["code"] == "INVALID_ARGUMENT"
    finally:
        server.stop()
