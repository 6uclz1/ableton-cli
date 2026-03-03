from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from ..errors import AppError, ErrorCode, ExitCode


@dataclass(slots=True)
class Request:
    type: str
    name: str
    args: dict[str, Any]
    meta: dict[str, Any]
    request_id: str
    protocol_version: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "args": self.args,
            "meta": self.meta,
            "request_id": self.request_id,
            "protocol_version": self.protocol_version,
        }


@dataclass(slots=True)
class Response:
    ok: bool
    request_id: str
    protocol_version: int
    result: dict[str, Any] | None
    error: dict[str, Any] | None


REQUIRED_RESPONSE_KEYS = {"ok", "request_id", "protocol_version"}


def _raise_protocol_error(error_code: ErrorCode, message: str, hint: str) -> None:
    raise AppError(
        error_code=error_code,
        message=message,
        hint=hint,
        exit_code=ExitCode.PROTOCOL_MISMATCH,
    )


def make_request(
    name: str,
    args: dict[str, Any],
    protocol_version: int,
    meta: dict[str, Any] | None = None,
) -> Request:
    return Request(
        type="command",
        name=name,
        args=args,
        meta=meta or {},
        request_id=uuid.uuid4().hex,
        protocol_version=protocol_version,
    )


def parse_response(
    payload: dict[str, Any], expected_request_id: str, expected_protocol: int
) -> Response:
    missing = REQUIRED_RESPONSE_KEYS.difference(payload)
    if missing:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message=f"Invalid response payload, missing keys: {sorted(missing)}",
            hint="Ensure the Remote Script protocol implementation matches the CLI.",
        )

    response_protocol = payload.get("protocol_version")
    if not isinstance(response_protocol, int):
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message="protocol_version must be an integer",
            hint=(
                "Set matching protocol versions on both sides "
                "(--protocol-version or 'ableton-cli config set protocol_version <n>')."
            ),
        )
    if response_protocol != expected_protocol:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_VERSION_MISMATCH,
            message=(
                f"Protocol version mismatch (cli={expected_protocol}, remote={response_protocol})"
            ),
            hint=(
                "Align protocol_version in CLI and Remote Script "
                "(--protocol-version or 'ableton-cli config set protocol_version <n>')."
            ),
        )

    request_id = payload.get("request_id")
    if request_id != expected_request_id:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_REQUEST_ID_MISMATCH,
            message=(f"request_id mismatch (expected={expected_request_id}, actual={request_id})"),
            hint="Check request routing in the Remote Script server.",
        )

    ok = payload.get("ok")
    if not isinstance(ok, bool):
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message="'ok' must be a boolean in response payload",
            hint="Update Remote Script response format.",
        )

    result = payload.get("result")
    if result is not None and not isinstance(result, dict):
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message="'result' must be an object when provided",
            hint="Return JSON object for result payloads.",
        )

    error = payload.get("error")
    if error is not None and not isinstance(error, dict):
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message="'error' must be an object when provided",
            hint="Return structured error payload with code/message.",
        )
    if isinstance(error, dict) and "details" in error and error["details"] is not None:
        if not isinstance(error["details"], dict):
            _raise_protocol_error(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="'error.details' must be an object when provided",
                hint="Return structured error details as a JSON object.",
            )

    return Response(
        ok=ok,
        request_id=request_id,
        protocol_version=response_protocol,
        result=result,
        error=error,
    )
