"""Client side of the event subscription protocol.

``session watch`` polls ``session_snapshot`` on a timer, which can only
notice a change after the fact and burns a round trip per interval. A
subscription instead opens its own connection, sends one
``type: "subscribe"`` request, and reads pushed event lines until the
caller stops.

The stream is a separate connection on purpose: the Remote Script turns a
subscribing connection into an event stream and stops reading requests on
it, so commands never queue behind pushed events.
"""

from __future__ import annotations

import json
import socket
import uuid
from collections.abc import Iterator
from typing import Any

from ..config import Settings
from ..errors import AppError, ErrorCode, ExitCode, remote_error_to_app_error

EVENT_LINE_KEYS = {"type", "protocol_version", "event", "ts", "data", "dropped"}


def _protocol_error(error_code: ErrorCode, message: str, hint: str) -> AppError:
    return AppError(
        error_code=error_code,
        message=message,
        hint=hint,
        exit_code=ExitCode.PROTOCOL_MISMATCH,
    )


def parse_event_line(payload: Any) -> dict[str, Any]:
    """Validate one pushed line, or raise a protocol error."""
    if not isinstance(payload, dict):
        raise _protocol_error(
            ErrorCode.PROTOCOL_INVALID_RESPONSE,
            "Event line must be a JSON object",
            "Update the Remote Script event format.",
        )
    if payload.get("type") != "event":
        raise _protocol_error(
            ErrorCode.PROTOCOL_INVALID_RESPONSE,
            f"Expected an event line, got type={payload.get('type')!r}",
            "A subscribing connection only receives event lines.",
        )
    missing = EVENT_LINE_KEYS.difference(payload)
    if missing:
        raise _protocol_error(
            ErrorCode.PROTOCOL_INVALID_RESPONSE,
            f"Event line is missing keys: {sorted(missing)}",
            "Update the Remote Script event format.",
        )
    return payload


class EventStream:
    """One subscribed connection, yielding pushed events."""

    def __init__(
        self,
        settings: Settings,
        *,
        events: list[str] | None = None,
        idle_timeout_ms: int | None = None,
    ) -> None:
        self._settings = settings
        self._events = list(events or [])
        # The connect/subscribe round trip uses the normal command timeout;
        # waiting for pushed events must not, or an idle session would look
        # like a dropped connection.
        self._idle_timeout_s = None if idle_timeout_ms is None else idle_timeout_ms / 1000
        self._sock: socket.socket | None = None
        self._file: Any = None
        self.subscribed: list[str] = []

    def __enter__(self) -> EventStream:
        self.open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def open(self) -> list[str]:
        """Connect and subscribe; returns the accepted event names."""
        try:
            sock = socket.create_connection(
                (self._settings.host, self._settings.port),
                timeout=self._settings.timeout_ms / 1000,
            )
        except (TimeoutError, OSError) as exc:
            raise AppError(
                error_code=ErrorCode.ABLETON_NOT_REACHABLE,
                message=f"Unable to connect to {self._settings.host}:{self._settings.port}",
                hint="Start Ableton Live and enable the Remote Script.",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            ) from exc
        self._sock = sock
        self._file = sock.makefile("rwb")

        meta: dict[str, Any] = {}
        if self._settings.auth_token is not None:
            meta["auth_token"] = self._settings.auth_token
        request = {
            "type": "subscribe",
            "name": "events",
            "args": {"events": self._events},
            "meta": meta,
            "request_id": uuid.uuid4().hex,
            "protocol_version": self._settings.protocol_version,
        }
        self._write(request)
        response = self._read_line()
        if response is None:
            raise _protocol_error(
                ErrorCode.PROTOCOL_CONNECTION_CLOSED,
                "Remote endpoint closed the subscription without a response",
                "Reinstall the Remote Script with 'ableton-cli install-remote-script --yes'.",
            )
        if not response.get("ok"):
            error = response.get("error")
            if isinstance(error, dict):
                raise remote_error_to_app_error(error)
            raise _protocol_error(
                ErrorCode.PROTOCOL_INVALID_RESPONSE,
                "Subscription failed without a structured error",
                "Update the Remote Script error handling.",
            )
        result = response.get("result") or {}
        self.subscribed = list(result.get("subscribed", []))
        sock.settimeout(self._idle_timeout_s)
        return self.subscribed

    def events(self, *, count: int | None = None) -> Iterator[dict[str, Any]]:
        """Yield pushed events, stopping after ``count`` (or forever)."""
        emitted = 0
        while count is None or emitted < count:
            payload = self._read_line()
            if payload is None:
                return
            yield parse_event_line(payload)
            emitted += 1

    def close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            finally:
                self._file = None
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _write(self, payload: dict[str, Any]) -> None:
        if self._file is None:
            raise RuntimeError("Event stream is not open")
        self._file.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
        self._file.flush()

    def _read_line(self) -> dict[str, Any] | None:
        if self._file is None:
            raise RuntimeError("Event stream is not open")
        try:
            raw = self._file.readline()
        except TimeoutError:
            return None
        except OSError as exc:
            raise AppError(
                error_code=ErrorCode.ABLETON_NOT_REACHABLE,
                message="Network error while reading the event stream",
                hint="Check that Ableton Live is still running.",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            ) from exc
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _protocol_error(
                ErrorCode.PROTOCOL_MALFORMED_JSON,
                "Received malformed JSON on the event stream",
                "Check the Remote Script event serialisation.",
            ) from exc
