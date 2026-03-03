from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any, Protocol

from ..errors import AppError, ErrorCode, ExitCode


class JsonTransport(Protocol):
    def send(self, payload: dict[str, Any]) -> dict[str, Any]: ...


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
                error_code=ErrorCode.TIMEOUT,
                message=f"Timed out while communicating with {self.host}:{self.port}",
                hint="Increase --timeout-ms or verify Ableton Remote Script responsiveness.",
                exit_code=ExitCode.TIMEOUT,
            ) from exc
        except ConnectionRefusedError as exc:
            raise AppError(
                error_code=ErrorCode.ABLETON_NOT_REACHABLE,
                message=f"Unable to connect to {self.host}:{self.port}",
                hint="Start Ableton Live and enable the Remote Script.",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            ) from exc
        except OSError as exc:
            raise AppError(
                error_code=ErrorCode.ABLETON_NOT_REACHABLE,
                message=f"Network error while connecting to {self.host}:{self.port}",
                hint="Check host/port and confirm the Remote Script is running.",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            ) from exc

        if not raw:
            raise AppError(
                error_code=ErrorCode.PROTOCOL_VERSION_MISMATCH,
                message="Remote endpoint closed connection without response",
                hint="Ensure the Remote Script returns one JSON line per request.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError(
                error_code=ErrorCode.PROTOCOL_VERSION_MISMATCH,
                message="Received malformed JSON from Remote Script",
                hint="Check protocol implementation in Remote Script.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            ) from exc

        if not isinstance(decoded, dict):
            raise AppError(
                error_code=ErrorCode.PROTOCOL_VERSION_MISMATCH,
                message="Response must be a JSON object",
                hint="Return object payloads from Remote Script.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )

        return decoded


class RecordingTransport:
    def __init__(self, *, inner: JsonTransport, path: str) -> None:
        self.inner = inner
        self.path = Path(path)

    def _append_entry(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.inner.send(payload)
            self._append_entry(
                {
                    "request": payload,
                    "response": response,
                    "error": None,
                }
            )
            return response
        except AppError as exc:
            self._append_entry(
                {
                    "request": payload,
                    "response": None,
                    "error": {
                        "error_code": exc.error_code,
                        "message": exc.message,
                        "hint": exc.hint,
                        "exit_code": int(exc.exit_code.value),
                        "details": exc.details,
                    },
                }
            )
            raise


class ReplayTransport:
    def __init__(self, *, path: str) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise AppError(
                error_code=ErrorCode.INVALID_ARGUMENT,
                message=f"Replay file does not exist: {self.path}",
                hint="Provide an existing JSONL path to --replay.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )

        self._entries_by_key: dict[str, list[dict[str, Any]]] = {}
        replay_lines = self.path.read_text(encoding="utf-8").splitlines()
        for line_number, raw_line in enumerate(replay_lines, start=1):
            if not raw_line.strip():
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise AppError(
                    error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                    message=f"Replay file line {line_number} is not valid JSON",
                    hint="Fix JSONL formatting in replay file.",
                    exit_code=ExitCode.PROTOCOL_MISMATCH,
                ) from exc

            if not isinstance(entry, dict):
                raise AppError(
                    error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                    message=f"Replay file line {line_number} must be an object",
                    hint="Use object-per-line JSONL format.",
                    exit_code=ExitCode.PROTOCOL_MISMATCH,
                )
            request = entry.get("request")
            if not isinstance(request, dict):
                raise AppError(
                    error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                    message=f"Replay file line {line_number}.request must be an object",
                    hint="Each replay entry requires a request object.",
                    exit_code=ExitCode.PROTOCOL_MISMATCH,
                )
            key = self._request_key(request)
            self._entries_by_key.setdefault(key, []).append(entry)

    @staticmethod
    def _request_key(request: dict[str, Any]) -> str:
        name = request.get("name")
        args = request.get("args", {})
        if not isinstance(name, str) or not name:
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay request.name must be a non-empty string",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        if not isinstance(args, dict):
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay request.args must be an object",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        normalized = {"name": name, "args": args}
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _raise_replay_error(payload: Any) -> None:
        if not isinstance(payload, dict):
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay error payload must be an object",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )

        code_value = payload.get("error_code", payload.get("code"))
        if not isinstance(code_value, str) or not code_value:
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay error payload is missing error_code",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        message = payload.get("message")
        if not isinstance(message, str) or not message:
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay error payload is missing message",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        hint = payload.get("hint")
        if hint is not None and not isinstance(hint, str):
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay error payload hint must be a string or null",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        raw_exit_code = payload.get("exit_code")
        try:
            exit_code = ExitCode(int(raw_exit_code))
        except (TypeError, ValueError) as exc:
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay error payload exit_code is invalid",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            ) from exc
        details = payload.get("details", {})
        if details is not None and not isinstance(details, dict):
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay error payload details must be an object or null",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        raise AppError(
            error_code=code_value,
            message=message,
            hint=hint,
            exit_code=exit_code,
            details={} if details is None else details,
        )

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = self._request_key(payload)
        bucket = self._entries_by_key.get(key)
        if not bucket:
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay fixture does not contain a matching request",
                hint="Record fixtures with --record for the exact name+args sequence.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
                details={"name": payload.get("name"), "args": payload.get("args")},
            )

        entry = bucket.pop(0)
        replay_error = entry.get("error")
        if replay_error is not None:
            self._raise_replay_error(replay_error)

        response = entry.get("response")
        if not isinstance(response, dict):
            raise AppError(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="Replay entry response must be an object",
                hint="Record new replay fixtures with --record.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        replayed_response = dict(response)
        if "request_id" in payload:
            replayed_response["request_id"] = payload["request_id"]
        return replayed_response
