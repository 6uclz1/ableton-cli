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


def _timing_out_mid_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    request: _CommandRequest,
    calls: list[str],
) -> None:
    """Dispatch that has the client's wait expire while Live is applying it.

    This is the only sequence that can double-apply: the request is already
    ``executing`` when the cancellation lands, so the drain cannot stop it and
    the client is told TIMEOUT for a command that did in fact run.
    """

    def _dispatch(_backend: Any, name: str, _args: dict[str, Any]) -> dict[str, Any]:
        calls.append(name)
        assert _mark_request_timed_out(request) is True
        return {"note_count": 1}

    monkeypatch.setattr(control_surface_module, "dispatch_command", _dispatch)


def _abandoned_request(
    surface: control_surface_module.AbletonCliRemoteSurface,
    *,
    idempotency_key: str | None,
) -> _CommandRequest:
    request = _CommandRequest(
        name="add_notes_to_clip",
        args={"notes": []},
        timeout_ms=1,
        event=threading.Event(),
        idempotency_key=idempotency_key,
    )
    surface._queue.put(request)
    return request


def test_retry_after_timeout_with_the_same_key_does_not_apply_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    calls: list[str] = []
    request = _abandoned_request(surface, idempotency_key="step-key")
    _timing_out_mid_dispatch(monkeypatch, request, calls)

    try:
        surface._drain_requests()
        assert calls == ["add_notes_to_clip"]

        result = surface._execute_command_from_server_thread(
            "add_notes_to_clip",
            {"notes": []},
            {"request_timeout_ms": 1000, "idempotency_key": "step-key"},
        )

        assert calls == ["add_notes_to_clip"]
        assert result == {"note_count": 1, "idempotent_replay": True}
    finally:
        surface.disconnect()


def test_retry_after_timeout_without_a_key_still_applies_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _make_surface(monkeypatch)
    calls: list[str] = []
    request = _abandoned_request(surface, idempotency_key=None)
    _timing_out_mid_dispatch(monkeypatch, request, calls)

    try:
        surface._drain_requests()

        surface._execute_command_from_server_thread(
            "add_notes_to_clip",
            {"notes": []},
            {"request_timeout_ms": 1000},
        )

        # Without a key the Remote Script cannot recognise the resend. This is
        # why `_execute_step` always carries one across a retry.
        assert calls == ["add_notes_to_clip", "add_notes_to_clip"]
    finally:
        surface.disconnect()
