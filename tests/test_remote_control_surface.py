from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest

import remote_script.AbletonCliRemote.control_surface as control_surface_module
from remote_script.AbletonCliRemote.server import CommandExecutionError


class _CommandServerStub:
    def __init__(
        self,
        host: str,
        port: int,
        command_executor: Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.host = host
        self.port = port
        self.command_executor = command_executor
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def _make_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> control_surface_module.AbletonCliRemoteSurface:
    monkeypatch.setattr(control_surface_module, "AbletonCommandServer", _CommandServerStub)
    return control_surface_module.AbletonCliRemoteSurface(object())


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
