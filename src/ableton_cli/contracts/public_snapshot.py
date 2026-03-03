from __future__ import annotations

from typing import Any

from ..client.protocol import REQUIRED_RESPONSE_KEYS, make_request
from ..errors import ErrorCode, ErrorDetailReason, details_with_reason
from ..output import error_payload, success_payload
from .registry import get_registered_contracts

PUBLIC_CONTRACT_SCHEMA_VERSION = 1


def build_public_contract_snapshot() -> dict[str, Any]:
    protocol_request = make_request(
        name="example_command",
        args={"example": True},
        protocol_version=2,
        meta={"request_timeout_ms": 15000},
    ).to_dict()
    protocol_request["request_id"] = "<request-id>"

    return {
        "schema_version": PUBLIC_CONTRACT_SCHEMA_VERSION,
        "json_output_envelope": {
            "success": success_payload(
                command="example command",
                args={"example": True},
                result={"status": "ok"},
            ),
            "error": error_payload(
                command="example command",
                args={"example": True},
                code=ErrorCode.INVALID_ARGUMENT.value,
                message="Example failure",
                hint="Resolve example failure.",
                details=details_with_reason(ErrorDetailReason.NOT_SUPPORTED_BY_LIVE_API),
            ),
        },
        "errors": {
            "codes": sorted(code.value for code in ErrorCode),
            "detail_reasons": sorted(reason.value for reason in ErrorDetailReason),
        },
        "protocol": {
            "request": protocol_request,
            "response_required_keys": sorted(REQUIRED_RESPONSE_KEYS),
            "response_success": {
                "ok": True,
                "request_id": "<request-id>",
                "protocol_version": 2,
                "result": {"status": "ok"},
                "error": None,
            },
            "response_error": {
                "ok": False,
                "request_id": "<request-id>",
                "protocol_version": 2,
                "result": None,
                "error": {
                    "code": ErrorCode.INVALID_ARGUMENT.value,
                    "message": "Example failure",
                    "hint": "Resolve example failure.",
                    "details": details_with_reason(ErrorDetailReason.NOT_SUPPORTED_BY_LIVE_API),
                },
            },
        },
        "command_contracts": get_registered_contracts(),
    }
