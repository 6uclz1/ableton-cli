from __future__ import annotations

import json
import socketserver
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .command_backend import PROTOCOL_VERSION


@dataclass(slots=True)
class CommandExecutionError(Exception):
    code: str
    message: str
    hint: str | None = None
    details: dict[str, Any] | None = None


def _ok(request_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "request_id": request_id,
        "protocol_version": PROTOCOL_VERSION,
        "result": result,
        "error": None,
    }


def _error(
    request_id: str,
    code: str,
    message: str,
    hint: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "request_id": request_id,
        "protocol_version": PROTOCOL_VERSION,
        "result": None,
        "error": {
            "code": code,
            "message": message,
            "hint": hint,
            "details": details,
        },
    }


class _CommandTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler: type[socketserver.StreamRequestHandler],
        command_executor: Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.command_executor = command_executor
        super().__init__(server_address, request_handler)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline()
        if not raw:
            return

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_response(
                _error(
                    request_id="unknown",
                    code="PROTOCOL_VERSION_MISMATCH",
                    message="Invalid JSON payload",
                    hint="Send one JSON object per line.",
                )
            )
            return

        request_id = str(payload.get("request_id", "unknown"))

        try:
            if payload.get("type") != "command":
                raise CommandExecutionError(
                    code="INVALID_ARGUMENT",
                    message="type must be 'command'",
                    hint="Use the CLI protocol request shape.",
                )
            protocol_version = payload.get("protocol_version")
            if protocol_version != PROTOCOL_VERSION:
                raise CommandExecutionError(
                    code="PROTOCOL_VERSION_MISMATCH",
                    message=(
                        "Protocol version mismatch "
                        f"(remote={PROTOCOL_VERSION}, request={protocol_version})"
                    ),
                    hint=(
                        "Align protocol_version between CLI and Remote Script "
                        "(--protocol-version or 'ableton-cli config set protocol_version <n>')."
                    ),
                )

            name = str(payload.get("name"))
            args = payload.get("args", {})
            if not isinstance(args, dict):
                raise CommandExecutionError(
                    code="INVALID_ARGUMENT",
                    message="args must be an object",
                    hint="Pass a JSON object for args.",
                )
            meta = payload.get("meta", {})
            if not isinstance(meta, dict):
                raise CommandExecutionError(
                    code="INVALID_ARGUMENT",
                    message="meta must be an object",
                    hint="Pass a JSON object for meta.",
                )

            server = self.server
            if not isinstance(server, _CommandTCPServer):
                raise RuntimeError("Invalid server type")

            result = server.command_executor(name, args, meta)
            response = _ok(request_id=request_id, result=result)
        except CommandExecutionError as exc:
            response = _error(
                request_id=request_id,
                code=exc.code,
                message=exc.message,
                hint=exc.hint,
                details=exc.details,
            )
        except Exception as exc:  # noqa: BLE001
            response = _error(
                request_id=request_id,
                code="INTERNAL_ERROR",
                message=f"Remote internal error: {exc}",
                hint="Check Remote Script logs.",
            )

        self._write_response(response)

    def _write_response(self, payload: dict[str, Any]) -> None:
        self.wfile.write((json.dumps(payload) + "\n").encode("utf-8"))
        self.wfile.flush()


class AbletonCommandServer:
    def __init__(
        self,
        host: str,
        port: int,
        command_executor: Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._host = host
        self._port = port
        self._command_executor = command_executor
        self._server: _CommandTCPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._server = _CommandTCPServer(
            (self._host, self._port),
            _Handler,
            command_executor=self._command_executor,
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="ableton-cli-remote",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return

        self._server.shutdown()
        self._server.server_close()

        if self._thread is not None:
            self._thread.join(timeout=1.0)

        self._server = None
        self._thread = None
