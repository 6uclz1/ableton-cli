from __future__ import annotations

import json
import socket
from typing import Any

from ..errors import AppError, ExitCode


class TcpJsonlTransport:
    def __init__(self, host: str, port: int, timeout_ms: int) -> None:
        self.host = host
        self.port = port
        self.timeout_s = timeout_ms / 1000

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized = json.dumps(payload, separators=(",", ":")) + "\n"

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout_s) as sock:
                sock.settimeout(self.timeout_s)
                with sock.makefile("rwb") as file_obj:
                    file_obj.write(serialized.encode("utf-8"))
                    file_obj.flush()
                    raw = file_obj.readline()
        except TimeoutError as exc:
            raise AppError(
                error_code="TIMEOUT",
                message=f"Timed out while communicating with {self.host}:{self.port}",
                hint="Increase --timeout-ms or verify Ableton Remote Script responsiveness.",
                exit_code=ExitCode.TIMEOUT,
            ) from exc
        except ConnectionRefusedError as exc:
            raise AppError(
                error_code="ABLETON_NOT_REACHABLE",
                message=f"Unable to connect to {self.host}:{self.port}",
                hint="Start Ableton Live and enable the Remote Script.",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            ) from exc
        except OSError as exc:
            raise AppError(
                error_code="ABLETON_NOT_REACHABLE",
                message=f"Network error while connecting to {self.host}:{self.port}",
                hint="Check host/port and confirm the Remote Script is running.",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            ) from exc

        if not raw:
            raise AppError(
                error_code="PROTOCOL_VERSION_MISMATCH",
                message="Remote endpoint closed connection without response",
                hint="Ensure the Remote Script returns one JSON line per request.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError(
                error_code="PROTOCOL_VERSION_MISMATCH",
                message="Received malformed JSON from Remote Script",
                hint="Check protocol implementation in Remote Script.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            ) from exc

        if not isinstance(decoded, dict):
            raise AppError(
                error_code="PROTOCOL_VERSION_MISMATCH",
                message="Response must be a JSON object",
                hint="Return object payloads from Remote Script.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )

        return decoded
