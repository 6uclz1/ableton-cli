from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from ..errors import AppError, ExitCode


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
        raise AppError(
            error_code="PROTOCOL_VERSION_MISMATCH",
            message=f"Invalid response payload, missing keys: {sorted(missing)}",
            hint="Ensure the Remote Script protocol implementation matches the CLI.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    response_protocol = payload.get("protocol_version")
    if not isinstance(response_protocol, int):
        raise AppError(
            error_code="PROTOCOL_VERSION_MISMATCH",
            message="protocol_version must be an integer",
            hint=(
                "Set matching protocol versions on both sides "
                "(--protocol-version or 'ableton-cli config set protocol_version <n>')."
            ),
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )
    if response_protocol != expected_protocol:
        raise AppError(
            error_code="PROTOCOL_VERSION_MISMATCH",
            message=(
                f"Protocol version mismatch (cli={expected_protocol}, remote={response_protocol})"
            ),
            hint=(
                "Align protocol_version in CLI and Remote Script "
                "(--protocol-version or 'ableton-cli config set protocol_version <n>')."
            ),
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    request_id = payload.get("request_id")
    if request_id != expected_request_id:
        raise AppError(
            error_code="PROTOCOL_VERSION_MISMATCH",
            message=(f"request_id mismatch (expected={expected_request_id}, actual={request_id})"),
            hint="Check request routing in the Remote Script server.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    ok = payload.get("ok")
    if not isinstance(ok, bool):
        raise AppError(
            error_code="PROTOCOL_VERSION_MISMATCH",
            message="'ok' must be a boolean in response payload",
            hint="Update Remote Script response format.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    result = payload.get("result")
    if result is not None and not isinstance(result, dict):
        raise AppError(
            error_code="PROTOCOL_VERSION_MISMATCH",
            message="'result' must be an object when provided",
            hint="Return JSON object for result payloads.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    error = payload.get("error")
    if error is not None and not isinstance(error, dict):
        raise AppError(
            error_code="PROTOCOL_VERSION_MISMATCH",
            message="'error' must be an object when provided",
            hint="Return structured error payload with code/message.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )
    if isinstance(error, dict) and "details" in error and error["details"] is not None:
        if not isinstance(error["details"], dict):
            raise AppError(
                error_code="PROTOCOL_VERSION_MISMATCH",
                message="'error.details' must be an object when provided",
                hint="Return structured error details as a JSON object.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )

    return Response(
        ok=ok,
        request_id=request_id,
        protocol_version=response_protocol,
        result=result,
        error=error,
    )
