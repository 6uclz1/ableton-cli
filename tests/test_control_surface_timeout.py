from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest

import remote_script.AbletonCliRemote.control_surface as control_surface_module
from remote_script.AbletonCliRemote.control_surface import (
    _CommandRequest,
    _mark_request_timed_out,
)
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

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


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


def test_timed_out_request_not_executed_by_later_drain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, args: calls.append(name) or {"ok": True},
    )
    surface = _make_surface(monkeypatch)
    # Prevent the (synchronous, in tests) drain from running before the wait
    # below actually times out.
    monkeypatch.setattr(surface, "_schedule_drain", lambda: None)

    try:
        with pytest.raises(CommandExecutionError) as excinfo:
            surface._execute_command_from_server_thread("song_info", {}, {"request_timeout_ms": 1})
        assert excinfo.value.code == "TIMEOUT"
        assert excinfo.value.details["may_have_executed"] is False

        surface._drain_requests()
        assert calls == []
    finally:
        surface.disconnect()


def test_timeout_error_details_include_may_have_executed_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, args: {"ok": True},
    )
    surface = _make_surface(monkeypatch)
    monkeypatch.setattr(surface, "_schedule_drain", lambda: None)

    try:
        with pytest.raises(CommandExecutionError) as excinfo:
            surface._execute_command_from_server_thread("song_info", {}, {"request_timeout_ms": 1})
        assert isinstance(excinfo.value.details["may_have_executed"], bool)
    finally:
        surface._drain_requests()
        surface.disconnect()


def test_may_have_executed_true_when_drain_already_marked_executing() -> None:
    request = _CommandRequest(name="song_info", args={}, timeout_ms=100, event=threading.Event())
    request.executing = True

    may_have_executed = _mark_request_timed_out(request)

    assert may_have_executed is True
    assert request.cancelled is True


def test_may_have_executed_false_when_drain_has_not_started() -> None:
    request = _CommandRequest(name="song_info", args={}, timeout_ms=100, event=threading.Event())

    may_have_executed = _mark_request_timed_out(request)

    assert may_have_executed is False
    assert request.cancelled is True


def test_cancelled_request_is_skipped_by_drain_without_executing_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        control_surface_module,
        "dispatch_command",
        lambda _backend, name, args: calls.append(name) or {"ok": True},
    )
    surface = _make_surface(monkeypatch)

    request = _CommandRequest(name="song_info", args={}, timeout_ms=100, event=threading.Event())
    request.cancelled = True
    surface._queue.put(request)

    surface._drain_requests()

    assert calls == []
    assert request.event.is_set()
    surface.disconnect()
