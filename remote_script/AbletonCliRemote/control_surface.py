from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any

from .command_backend import CommandError, dispatch_command
from .live_backend import LiveBackend
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


@dataclass(slots=True)
class _CommandRequest:
    name: str
    args: dict[str, Any]
    timeout_ms: int
    event: threading.Event
    result: dict[str, Any] | None = None
    error: Exception | None = None


class AbletonCliRemoteSurface(_ControlSurface):
    """Ableton Control Surface that exposes a local command server."""

    DEFAULT_COMMAND_WAIT_TIMEOUT_MS = 15000
    MAX_PENDING_COMMANDS = 512

    def __init__(self, c_instance):  # noqa: ANN001
        super().__init__(c_instance)
        self._backend = LiveBackend(self)
        self._queue: queue.Queue[_CommandRequest] = queue.Queue()
        self._command_server = AbletonCommandServer(
            host="127.0.0.1",
            port=8765,
            command_executor=self._execute_command_from_server_thread,
        )
        self._command_server.start()

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
        if not request.event.wait(timeout=timeout_ms / 1000):
            raise CommandExecutionError(
                code="TIMEOUT",
                message="Timed out waiting for Ableton main thread",
                hint="Retry the command while Ableton Live is responsive.",
                details={"request_timeout_ms": timeout_ms},
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

    def _drain_requests(self) -> None:
        while True:
            try:
                request = self._queue.get_nowait()
            except queue.Empty:
                return

            try:
                request.result = dispatch_command(self._backend, request.name, request.args)
            except Exception as exc:  # noqa: BLE001
                request.error = exc
            finally:
                request.event.set()

    def update_display(self) -> None:
        self._drain_requests()
        super().update_display()

    def disconnect(self) -> None:
        self._command_server.stop()
        self._drain_requests()
        super().disconnect()
