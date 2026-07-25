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


REQUIRED_RESPONSE_KEYS = {"ok", "request_id", "protocol_version", "result", "error"}


def _raise_protocol_error(error_code: ErrorCode, message: str, hint: str) -> None:
    raise AppError(
        error_code=error_code,
        message=message,
        hint=hint,
        exit_code=ExitCode.PROTOCOL_MISMATCH,
    )


def _require_response_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message=f"'{key}' must be a non-empty string",
            hint="Update Remote Script response format.",
        )
    return value


#: Upper bound on ``meta.idempotency_key``. Long enough for a uuid4 hex or an
#: opaque caller-supplied token, short enough that one client cannot grow the
#: Remote Script's bounded response cache into a memory problem.
IDEMPOTENCY_KEY_MAX_LENGTH = 128


def _validated_idempotency_key(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message="idempotency_key must be a non-empty string",
            hint="Pass a stable opaque token, or omit idempotency_key entirely.",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )
    if len(value) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=(
                f"idempotency_key must be at most {IDEMPOTENCY_KEY_MAX_LENGTH} "
                f"characters, got {len(value)}"
            ),
            hint="Use a short opaque token such as a uuid4 hex.",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )
    return value


def make_request(
    name: str,
    args: dict[str, Any],
    protocol_version: int,
    meta: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> Request:
    """Build one request envelope.

    ``request_id`` is fresh on every call, so it can never identify a retry.
    ``idempotency_key`` is deliberately *not* generated here: the caller that
    owns the retry loop generates it once and passes the same value to every
    attempt, which is what makes the Remote Script able to deduplicate them.
    """
    request_meta = dict(meta or {})
    if idempotency_key is not None:
        request_meta["idempotency_key"] = _validated_idempotency_key(idempotency_key)
    return Request(
        type="command",
        name=name,
        args=args,
        meta=request_meta,
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
    extra = set(payload).difference(REQUIRED_RESPONSE_KEYS)
    if extra:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message=f"Invalid response payload, unexpected keys: {sorted(extra)}",
            hint="Return only the stable Remote Script response fields.",
        )

    response_protocol = payload.get("protocol_version")
    if type(response_protocol) is not int:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message="protocol_version must be an integer",
            hint=(
                "Set matching protocol versions on both sides "
                "(--protocol-version or 'ableton-cli config set protocol_version <n>')."
            ),
        )
    if response_protocol < 1:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message="protocol_version must be a positive integer",
            hint="Use a positive protocol version on both sides.",
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
    if not isinstance(request_id, str) or not request_id:
        _raise_protocol_error(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message="request_id must be a non-empty string",
            hint="Return the request_id string from the matching request.",
        )
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

    if ok:
        if error is not None:
            _raise_protocol_error(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="'error' must be null for successful responses",
                hint="Set error to null when ok is true.",
            )
        if result is None:
            _raise_protocol_error(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="'result' must be an object for successful responses",
                hint="Return an object result payload when ok is true.",
            )
    else:
        if result is not None:
            _raise_protocol_error(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="'result' must be null for error responses",
                hint="Set result to null when ok is false.",
            )
        if error is None:
            _raise_protocol_error(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="'error' must be an object for error responses",
                hint="Return structured error payload with code/message.",
            )

    if isinstance(error, dict):
        allowed_error_keys = {"code", "message", "hint", "details"}
        extra_error_keys = set(error).difference(allowed_error_keys)
        if extra_error_keys:
            _raise_protocol_error(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message=f"'error' has unexpected keys: {sorted(extra_error_keys)}",
                hint="Return only code/message/hint/details in error payloads.",
            )
        _require_response_string(error, "code")
        _require_response_string(error, "message")
        hint = error.get("hint")
        if hint is not None and not isinstance(hint, str):
            _raise_protocol_error(
                error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
                message="'error.hint' must be a string or null when provided",
                hint="Return a string hint or null.",
            )
        if "details" in error and error["details"] is not None:
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
