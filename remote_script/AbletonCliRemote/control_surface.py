from __future__ import annotations

import hmac
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .command_backend import CommandError, RemoteErrorCode, dispatch_command
from .events import EVENT_NAMES, EventBroker, Subscription, UnknownEventError
from .live_backend import LiveBackend
from .live_events import LiveEventSource
from .remote_config import load_remote_config
from .server import AbletonCommandServer, CommandExecutionError

try:
    from _Framework.ControlSurface import ControlSurface as _ControlSurface  # type: ignore
except Exception:  # pragma: no cover - only used outside Ableton for local checks

    class _ControlSurface:  # type: ignore[too-many-ancestors]
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def disconnect(self) -> None:
            pass

        def update_display(self) -> None:
            pass

        def schedule_message(self, _delay: int, callback: Callable[[], None]) -> None:
            callback()


@dataclass(slots=True)
class _CommandRequest:
    name: str
    args: dict[str, Any]
    timeout_ms: int
    event: threading.Event
    result: dict[str, Any] | None = None
    error: Exception | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    cancelled: bool = False
    executing: bool = False


def _mark_request_timed_out(request: _CommandRequest) -> bool:
    """Cancel a request whose client-side wait timed out.

    Returns ``may_have_executed``: True only when the drain loop had already
    committed to dispatching the request (``executing`` was set) before the
    cancellation was observed, meaning it cannot be stopped.
    """
    with request.lock:
        request.cancelled = True
        return request.executing


class AbletonCliRemoteSurface(_ControlSurface):
    """Ableton Control Surface that exposes a local command server."""

    DEFAULT_COMMAND_WAIT_TIMEOUT_MS = 15000
    MAX_PENDING_COMMANDS = 512

    def __init__(self, c_instance):  # noqa: ANN001
        super().__init__(c_instance)
        self._backend = LiveBackend(self)
        self._queue: queue.Queue[_CommandRequest] = queue.Queue()
        self._drain_lock = threading.Lock()
        self._drain_scheduled = False
        remote_config = load_remote_config()
        self._auth_token = remote_config.auth_token
        self._event_broker = EventBroker()
        # Listeners are registered here, on Live's main thread, once —
        # never from a socket thread when a client subscribes.
        self._event_source = LiveEventSource(lambda: self.song(), self._event_broker)
        self._available_events = self._event_source.attach()
        self._command_server = AbletonCommandServer(
            host=remote_config.host,
            port=remote_config.port,
            command_executor=self._execute_command_from_server_thread,
            event_subscriber=self._subscribe_from_server_thread,
            event_unsubscriber=self._event_broker.unsubscribe,
        )
        self._command_server.start()

    @property
    def available_events(self) -> tuple[str, ...]:
        return self._available_events

    def _require_auth(self, meta: dict[str, Any]) -> None:
        provided_auth_token = meta.get("auth_token")
        if self._auth_token is not None and (
            not isinstance(provided_auth_token, str)
            or not hmac.compare_digest(provided_auth_token, self._auth_token)
        ):
            raise CommandExecutionError(
                code=RemoteErrorCode.UNAUTHORIZED.value,
                message="Missing or invalid auth token",
                hint=(
                    "Set the same auth_token in the CLI config and in "
                    "AbletonCliRemote/remote_config.json."
                ),
            )

    def _subscribe_from_server_thread(
        self, args: dict[str, Any], meta: dict[str, Any]
    ) -> Subscription:
        self._require_auth(meta)
        requested = args.get("events", list(self._available_events))
        if not isinstance(requested, list) or not all(isinstance(item, str) for item in requested):
            raise CommandExecutionError(
                code=RemoteErrorCode.INVALID_ARGUMENT.value,
                message="events must be a list of event names",
                hint=f"Use any of: {', '.join(self._available_events) or '(none available)'}.",
            )
        names = requested or list(self._available_events)
        unavailable = [name for name in names if name not in self._available_events]
        if unavailable:
            raise CommandExecutionError(
                code=RemoteErrorCode.INVALID_ARGUMENT.value,
                message=f"events not available in this Live version: {sorted(unavailable)}",
                hint=f"Use any of: {', '.join(self._available_events) or '(none available)'}.",
                details={
                    "available_events": list(self._available_events),
                    "known_events": list(EVENT_NAMES),
                },
            )
        try:
            return self._event_broker.subscribe(names)
        except UnknownEventError as exc:
            raise CommandExecutionError(
                code=RemoteErrorCode.INVALID_ARGUMENT.value,
                message=str(exc),
                hint=f"Use any of: {', '.join(EVENT_NAMES)}.",
            ) from exc

    def _parse_request_timeout_ms(self, meta: dict[str, Any]) -> int:
        raw_timeout = meta.get("request_timeout_ms", self.DEFAULT_COMMAND_WAIT_TIMEOUT_MS)
        try:
            timeout_ms = int(raw_timeout)
        except (TypeError, ValueError) as exc:
            raise CommandExecutionError(
                code="INVALID_ARGUMENT",
                message=f"request_timeout_ms must be an integer, got {raw_timeout!r}",
                hint="Provide a positive integer request_timeout_ms in request meta.",
            ) from exc
        if timeout_ms <= 0:
            raise CommandExecutionError(
                code="INVALID_ARGUMENT",
                message=f"request_timeout_ms must be positive, got {timeout_ms}",
                hint="Provide request_timeout_ms > 0 in request meta.",
            )
        return timeout_ms

    def _execute_command_from_server_thread(
        self, name: str, args: dict[str, Any], meta: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_auth(meta)
        if self._queue.qsize() >= self.MAX_PENDING_COMMANDS:
            raise CommandExecutionError(
                code="REMOTE_BUSY",
                message="Remote command queue is full",
                hint="Reduce command throughput or retry after Live becomes responsive.",
                details={"max_pending_commands": self.MAX_PENDING_COMMANDS},
            )
        timeout_ms = self._parse_request_timeout_ms(meta)
        request = _CommandRequest(
            name=name,
            args=args,
            timeout_ms=timeout_ms,
            event=threading.Event(),
        )
        self._queue.put(request)
        self._schedule_drain()
        if not request.event.wait(timeout=timeout_ms / 1000):
            may_have_executed = _mark_request_timed_out(request)
            raise CommandExecutionError(
                code="TIMEOUT",
                message="Timed out waiting for Ableton main thread",
                hint="Retry the command while Ableton Live is responsive.",
                details={
                    "request_timeout_ms": timeout_ms,
                    "may_have_executed": may_have_executed,
                },
            )

        if request.error is not None:
            if isinstance(request.error, CommandError):
                raise CommandExecutionError(
                    code=request.error.code,
                    message=request.error.message,
                    hint=request.error.hint,
                    details=request.error.details,
                ) from request.error
            raise CommandExecutionError(
                code="INTERNAL_ERROR",
                message=str(request.error),
                hint="Check Ableton Log.txt for details.",
            ) from request.error

        return request.result or {}

    def _schedule_drain(self) -> None:
        with self._drain_lock:
            if self._drain_scheduled:
                return
            self._drain_scheduled = True
        self.schedule_message(0, self._scheduled_drain)

    def _scheduled_drain(self) -> None:
        try:
            self._drain_requests()
        finally:
            with self._drain_lock:
                self._drain_scheduled = False
                needs_reschedule = not self._queue.empty()
        if needs_reschedule:
            self._schedule_drain()

    def _drain_requests(self) -> None:
        while True:
            try:
                request = self._queue.get_nowait()
            except queue.Empty:
                return

            with request.lock:
                if request.cancelled:
                    request.event.set()
                    continue
                request.executing = True

            try:
                request.result = dispatch_command(self._backend, request.name, request.args)
            except Exception as exc:  # noqa: BLE001
                request.error = exc
            finally:
                request.event.set()

    def update_display(self) -> None:
        super().update_display()

    def disconnect(self) -> None:
        self._command_server.stop()
        self._event_source.detach()
        self._event_broker.close()
        self._drain_requests()
        with self._drain_lock:
            self._drain_scheduled = False
        super().disconnect()
