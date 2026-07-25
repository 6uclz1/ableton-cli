from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest

import remote_script.AbletonCliRemote.control_surface as control_surface_module
from remote_script.AbletonCliRemote.remote_config import RemoteConfig
from remote_script.AbletonCliRemote.server import CommandExecutionError


class _CommandServerStub:
    def __init__(
        self,
        host: str,
        port: int,
        command_executor: Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]],
        event_subscriber: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
        event_unsubscriber: Callable[[Any], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.command_executor = command_executor
        self.event_subscriber = event_subscriber
        self.event_unsubscriber = event_unsubscriber
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def _make_surface(
    monkeypatch: pytest.MonkeyPatch,
    *,
    remote_config: RemoteConfig | None = None,
) -> control_surface_module.AbletonCliRemoteSurface:
    monkeypatch.setattr(control_surface_module, "AbletonCommandServer", _CommandServerStub)
    monkeypatch.setattr(
        control_surface_module,
        "load_remote_config",
        lambda: remote_config or RemoteConfig(),
    )
    return control_surface_module.AbletonCliRemoteSurface(object())


def test_surface_starts_command_server_with_configured_host_and_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(
        monkeypatch,
        remote_config=RemoteConfig(host="0.0.0.0", port=9999, auth_token=None),
    )

    try:
        assert surface._command_server.host == "0.0.0.0"
        assert surface._command_server.port == 9999
    finally:
        surface.disconnect()


def test_surface_rejects_command_with_missing_or_wrong_auth_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, args: {"handled": name, "args": args},
    )
    surface = _make_surface(
        monkeypatch,
        remote_config=RemoteConfig(host="127.0.0.1", port=8765, auth_token="expected-token"),
    )

    try:
        with pytest.raises(CommandExecutionError) as missing_token:
            surface._execute_command_from_server_thread(
                "song_info",
                {},
                {"request_timeout_ms": 100},
            )
        assert missing_token.value.code == "UNAUTHORIZED"

        with pytest.raises(CommandExecutionError) as wrong_token:
            surface._execute_command_from_server_thread(
                "song_info",
                {},
                {"request_timeout_ms": 100, "auth_token": "wrong-token"},
            )
        assert wrong_token.value.code == "UNAUTHORIZED"
    finally:
        surface.disconnect()


def test_surface_rejects_non_string_auth_token_without_raising_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, args: {"handled": name, "args": args},
    )
    surface = _make_surface(
        monkeypatch,
        remote_config=RemoteConfig(host="127.0.0.1", port=8765, auth_token="expected-token"),
    )

    try:
        with pytest.raises(CommandExecutionError) as non_string_token:
            surface._execute_command_from_server_thread(
                "song_info",
                {},
                {"request_timeout_ms": 100, "auth_token": 123},
            )
        assert non_string_token.value.code == "UNAUTHORIZED"
    finally:
        surface.disconnect()


def test_surface_allows_command_with_matching_auth_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, args: {"handled": name, "args": args},
    )
    surface = _make_surface(
        monkeypatch,
        remote_config=RemoteConfig(host="127.0.0.1", port=8765, auth_token="expected-token"),
    )

    try:
        result = surface._execute_command_from_server_thread(
            "song_info",
            {},
            {"request_timeout_ms": 100, "auth_token": "expected-token"},
        )
    finally:
        surface.disconnect()

    assert result == {"handled": "song_info", "args": {}}


def test_surface_processes_commands_without_update_display(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, args: {"handled": name, "args": args},
    )
    surface = _make_surface(monkeypatch)

    try:
        result = surface._execute_command_from_server_thread(
            "song_info",
            {"include_devices": True},
            {"request_timeout_ms": 100},
        )
    finally:
        surface.disconnect()

    assert result == {"handled": "song_info", "args": {"include_devices": True}}


def test_surface_scheduled_drain_keeps_request_order(monkeypatch: pytest.MonkeyPatch) -> None:
    executed: list[str] = []
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, _args: executed.append(name) or {"name": name},
    )
    surface = _make_surface(monkeypatch)
    scheduled_callbacks: list[Callable[[], None]] = []

    def _schedule_message(_delay: int, callback: Callable[[], None]) -> None:
        scheduled_callbacks.append(callback)

    surface.schedule_message = _schedule_message  # type: ignore[method-assign]

    results: list[dict[str, Any]] = []
    errors: list[Exception] = []

    def _worker(name: str) -> None:
        try:
            results.append(
                surface._execute_command_from_server_thread(
                    name,
                    {},
                    {"request_timeout_ms": 300},
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    first = threading.Thread(target=_worker, args=("first",))
    second = threading.Thread(target=_worker, args=("second",))
    first.start()
    second.start()

    time.sleep(0.02)
    assert len(scheduled_callbacks) == 1
    scheduled_callbacks[0]()

    first.join(timeout=1)
    second.join(timeout=1)
    surface.disconnect()

    assert errors == []
    assert executed == ["first", "second"]
    assert sorted(entry["name"] for entry in results) == ["first", "second"]


def test_surface_keeps_remote_busy_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, _args: {"name": name},
    )
    surface = _make_surface(monkeypatch)
    surface.MAX_PENDING_COMMANDS = 0

    try:
        with pytest.raises(CommandExecutionError) as exc_info:
            surface._execute_command_from_server_thread(
                "song_info",
                {},
                {"request_timeout_ms": 100},
            )
    finally:
        surface.disconnect()

    assert exc_info.value.code == "REMOTE_BUSY"


def test_surface_keeps_timeout_when_drain_is_not_scheduled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, _args: {"name": name},
    )
    surface = _make_surface(monkeypatch)
    surface.schedule_message = lambda _delay, _callback: None  # type: ignore[method-assign]

    try:
        with pytest.raises(CommandExecutionError) as exc_info:
            surface._execute_command_from_server_thread(
                "song_info",
                {},
                {"request_timeout_ms": 25},
            )
    finally:
        surface.disconnect()

    assert exc_info.value.code == "TIMEOUT"


class _FakeClock:
    """Deterministic stand-in for the ``time`` module used by the drain loop."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


def _install_drain_harness(
    monkeypatch: pytest.MonkeyPatch,
    surface: control_surface_module.AbletonCliRemoteSurface,
    *,
    seconds_per_command: float,
) -> tuple[_FakeClock, list[str], list[Callable[[], None]]]:
    clock = _FakeClock()
    executed: list[str] = []

    def _dispatch(_backend: Any, name: str, _args: dict[str, Any]) -> dict[str, Any]:
        executed.append(name)
        clock.now += seconds_per_command
        return {"name": name}

    monkeypatch.setattr(control_surface_module, "time", clock)
    monkeypatch.setattr(control_surface_module, "dispatch_command", _dispatch)

    scheduled: list[Callable[[], None]] = []
    surface.schedule_message = lambda _delay, callback: scheduled.append(  # type: ignore[method-assign]
        callback
    )
    return clock, executed, scheduled


def _enqueue(
    surface: control_surface_module.AbletonCliRemoteSurface, name: str
) -> control_surface_module._CommandRequest:
    request = control_surface_module._CommandRequest(
        name=name,
        args={},
        timeout_ms=1000,
        event=threading.Event(),
    )
    surface._queue.put(request)
    return request


def test_scheduled_drain_stops_at_the_main_thread_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    monkeypatch.setattr(control_surface_module, "DRAIN_BUDGET_S", 0.005)
    _clock, executed, scheduled = _install_drain_harness(
        monkeypatch, surface, seconds_per_command=0.004
    )
    for index in range(5):
        _enqueue(surface, f"command-{index}")

    surface._scheduled_drain()

    assert executed == ["command-0", "command-1"]
    assert not surface._queue.empty()


def test_budget_overflow_is_rescheduled_until_every_request_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    monkeypatch.setattr(control_surface_module, "DRAIN_BUDGET_S", 0.005)
    clock, executed, scheduled = _install_drain_harness(
        monkeypatch, surface, seconds_per_command=0.004
    )
    requests = [_enqueue(surface, f"command-{index}") for index in range(5)]

    surface._scheduled_drain()
    while scheduled:
        callback = scheduled.pop(0)
        clock.now = 0.0
        callback()

    assert executed == [f"command-{index}" for index in range(5)]
    assert all(request.event.is_set() for request in requests)
    assert surface._queue.empty()


def test_budget_overflow_resets_the_drain_scheduled_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    monkeypatch.setattr(control_surface_module, "DRAIN_BUDGET_S", 0.005)
    clock, _executed, scheduled = _install_drain_harness(
        monkeypatch, surface, seconds_per_command=0.004
    )
    for index in range(5):
        _enqueue(surface, f"command-{index}")

    surface._scheduled_drain()

    # The flag was released and immediately re-taken by the pending reschedule.
    assert len(scheduled) == 1
    assert surface._drain_scheduled is True

    while scheduled:
        callback = scheduled.pop(0)
        clock.now = 0.0
        callback()

    assert surface._drain_scheduled is False


def test_exhausted_budget_still_dispatches_one_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    monkeypatch.setattr(control_surface_module, "DRAIN_BUDGET_S", 0.0)
    _clock, executed, _scheduled = _install_drain_harness(
        monkeypatch, surface, seconds_per_command=0.004
    )
    for index in range(3):
        _enqueue(surface, f"command-{index}")

    surface._scheduled_drain()

    assert executed == ["command-0"]


def test_disconnect_drains_the_queue_regardless_of_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    monkeypatch.setattr(control_surface_module, "DRAIN_BUDGET_S", 0.0)
    _clock, executed, _scheduled = _install_drain_harness(
        monkeypatch, surface, seconds_per_command=0.004
    )
    for index in range(5):
        _enqueue(surface, f"command-{index}")

    surface.disconnect()

    assert executed == [f"command-{index}" for index in range(5)]
    assert surface._queue.empty()


def _enqueue_keyed(
    surface: control_surface_module.AbletonCliRemoteSurface,
    name: str,
    key: str | None,
) -> control_surface_module._CommandRequest:
    request = control_surface_module._CommandRequest(
        name=name,
        args={},
        timeout_ms=1000,
        event=threading.Event(),
        idempotency_key=key,
    )
    surface._queue.put(request)
    return request


def _count_dispatches(monkeypatch: pytest.MonkeyPatch, result: dict[str, Any]) -> list[str]:
    dispatched: list[str] = []

    def _dispatch(_backend: Any, name: str, _args: dict[str, Any]) -> dict[str, Any]:
        dispatched.append(name)
        return dict(result)

    monkeypatch.setattr(control_surface_module, "dispatch_command", _dispatch)
    return dispatched


def test_repeating_an_idempotency_key_replays_instead_of_dispatching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    dispatched = _count_dispatches(monkeypatch, {"tempo": 120.0})

    first = _enqueue_keyed(surface, "song_info", "key-1")
    surface._drain_requests()
    second = _enqueue_keyed(surface, "song_info", "key-1")
    surface._drain_requests()

    assert dispatched == ["song_info"]
    assert first.result == {"tempo": 120.0}
    assert second.result == {"tempo": 120.0, "idempotent_replay": True}


def test_requests_without_a_key_are_always_dispatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    dispatched = _count_dispatches(monkeypatch, {"tempo": 120.0})

    _enqueue_keyed(surface, "song_info", None)
    _enqueue_keyed(surface, "song_info", None)
    surface._drain_requests()

    assert dispatched == ["song_info", "song_info"]


def test_a_failed_command_is_replayed_as_the_same_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from remote_script.AbletonCliRemote.command_backend import CommandError

    surface = _make_surface(monkeypatch)
    dispatched: list[str] = []

    def _dispatch(_backend: Any, name: str, _args: dict[str, Any]) -> dict[str, Any]:
        dispatched.append(name)
        raise CommandError(code="INVALID_ARGUMENT", message="bad track", hint="fix it")

    monkeypatch.setattr(control_surface_module, "dispatch_command", _dispatch)

    _enqueue_keyed(surface, "track_volume_set", "key-1")
    surface._drain_requests()
    second = _enqueue_keyed(surface, "track_volume_set", "key-1")
    surface._drain_requests()

    assert dispatched == ["track_volume_set"]
    assert isinstance(second.error, CommandError)
    assert second.error.code == "INVALID_ARGUMENT"
    assert second.error.message == "bad track"
    assert second.error.details == {"idempotent_replay": True}


def test_cancelled_requests_leave_nothing_to_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    surface = _make_surface(monkeypatch)
    dispatched = _count_dispatches(monkeypatch, {"tempo": 120.0})

    cancelled = _enqueue_keyed(surface, "song_info", "key-1")
    cancelled.cancelled = True
    surface._drain_requests()
    assert dispatched == []

    retry = _enqueue_keyed(surface, "song_info", "key-1")
    surface._drain_requests()

    assert dispatched == ["song_info"]
    assert retry.result == {"tempo": 120.0}


def test_response_cache_evicts_the_oldest_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    surface = _make_surface(monkeypatch)
    monkeypatch.setattr(control_surface_module, "IDEMPOTENCY_CACHE_SIZE", 3)
    dispatched = _count_dispatches(monkeypatch, {"tempo": 120.0})

    for index in range(4):
        _enqueue_keyed(surface, "song_info", f"key-{index}")
    surface._drain_requests()
    assert len(dispatched) == 4
    assert list(surface._response_cache) == ["key-1", "key-2", "key-3"]

    # key-0 fell out of the cache, so its retry has to run again.
    evicted_retry = _enqueue_keyed(surface, "song_info", "key-0")
    # key-3 is still cached, so its retry is replayed.
    cached_retry = _enqueue_keyed(surface, "song_info", "key-3")
    surface._drain_requests()

    assert len(dispatched) == 5
    assert evicted_retry.result == {"tempo": 120.0}
    assert cached_retry.result == {"tempo": 120.0, "idempotent_replay": True}
