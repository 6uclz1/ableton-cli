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
