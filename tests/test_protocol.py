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
