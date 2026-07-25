from __future__ import annotations

import pytest

from ableton_cli.client.protocol import make_request, parse_response
from ableton_cli.errors import AppError, ExitCode


def test_make_request_contains_required_fields() -> None:
    request = make_request(
        name="ping",
        args={},
        protocol_version=2,
        meta={"request_timeout_ms": 15000},
    )
    data = request.to_dict()
    assert data["type"] == "command"
    assert data["name"] == "ping"
    assert data["args"] == {}
    assert data["meta"] == {"request_timeout_ms": 15000}
    assert data["protocol_version"] == 2
    assert isinstance(data["request_id"], str)
    assert data["request_id"]


def test_parse_response_success_roundtrip() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": request.request_id,
        "protocol_version": 2,
        "result": {"pong": True},
        "error": None,
    }
    response = parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)
    assert response.ok is True
    assert response.result == {"pong": True}


def test_parse_response_protocol_mismatch_raises() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": request.request_id,
        "protocol_version": 1,
        "result": {"pong": True},
        "error": None,
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_VERSION_MISMATCH"
    assert exc_info.value.exit_code == ExitCode.PROTOCOL_MISMATCH


def test_parse_response_missing_keys_raises_invalid_response() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": request.request_id,
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"
    assert exc_info.value.exit_code == ExitCode.PROTOCOL_MISMATCH


def test_parse_response_request_id_mismatch_raises() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": "other-request-id",
        "protocol_version": 2,
        "result": {"pong": True},
        "error": None,
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_REQUEST_ID_MISMATCH"
    assert exc_info.value.exit_code == ExitCode.PROTOCOL_MISMATCH


def test_parse_response_rejects_non_integer_protocol_version() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": request.request_id,
        "protocol_version": "2",
        "result": {"pong": True},
        "error": None,
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"
    assert exc_info.value.exit_code == ExitCode.PROTOCOL_MISMATCH


def test_parse_response_rejects_boolean_protocol_version() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": request.request_id,
        "protocol_version": True,
        "result": {"pong": True},
        "error": None,
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"


def test_parse_response_rejects_extra_response_keys() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": request.request_id,
        "protocol_version": 2,
        "result": {"pong": True},
        "error": None,
        "extra": "not allowed",
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"


def test_parse_response_success_rejects_error_payload() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": True,
        "request_id": request.request_id,
        "protocol_version": 2,
        "result": {"pong": True},
        "error": {"code": "INVALID_ARGUMENT", "message": "bad"},
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"


def test_parse_response_error_requires_code_and_message() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": False,
        "request_id": request.request_id,
        "protocol_version": 2,
        "result": None,
        "error": {"code": "INVALID_ARGUMENT"},
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"


def test_parse_response_rejects_non_object_error_details() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": False,
        "request_id": request.request_id,
        "protocol_version": 2,
        "result": None,
        "error": {"code": "TIMEOUT", "message": "timeout", "details": "not-object"},
    }

    with pytest.raises(AppError) as exc_info:
        parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"


def test_parse_response_accepts_error_details_object() -> None:
    request = make_request(name="ping", args={}, protocol_version=2)
    payload = {
        "ok": False,
        "request_id": request.request_id,
        "protocol_version": 2,
        "result": None,
        "error": {
            "code": "BATCH_STEP_FAILED",
            "message": "failed",
            "details": {"failed_step_index": 1},
        },
    }

    response = parse_response(payload, expected_request_id=request.request_id, expected_protocol=2)
    assert response.ok is False
    assert response.error is not None
    assert response.error["details"] == {"failed_step_index": 1}


def test_make_request_omits_idempotency_key_by_default() -> None:
    request = make_request(name="ping", args={}, protocol_version=3)

    assert "idempotency_key" not in request.meta


def test_make_request_never_generates_its_own_idempotency_key() -> None:
    first = make_request(name="ping", args={}, protocol_version=3, idempotency_key="step-key")
    second = make_request(name="ping", args={}, protocol_version=3, idempotency_key="step-key")

    # The caller owning the retry loop supplies the key, so it is stable across
    # attempts while request_id is not.
    assert first.meta["idempotency_key"] == second.meta["idempotency_key"] == "step-key"
    assert first.request_id != second.request_id


def test_make_request_does_not_mutate_the_caller_meta() -> None:
    meta: dict[str, object] = {"request_timeout_ms": 15000}

    make_request(name="ping", args={}, protocol_version=3, meta=meta, idempotency_key="step-key")

    assert meta == {"request_timeout_ms": 15000}


@pytest.mark.parametrize("value", ["", "x" * 129])
def test_make_request_rejects_an_invalid_idempotency_key(value: str) -> None:
    with pytest.raises(AppError) as exc_info:
        make_request(name="ping", args={}, protocol_version=3, idempotency_key=value)

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert exc_info.value.exit_code == ExitCode.INVALID_ARGUMENT


def test_idempotency_key_bound_matches_the_remote_script() -> None:
    from ableton_cli.client.protocol import IDEMPOTENCY_KEY_MAX_LENGTH
    from remote_script.AbletonCliRemote.server import (
        IDEMPOTENCY_KEY_MAX_LENGTH as REMOTE_MAX_LENGTH,
    )

    assert IDEMPOTENCY_KEY_MAX_LENGTH == REMOTE_MAX_LENGTH
