from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class ExitCode(IntEnum):
    SUCCESS = 0
    INVALID_ARGUMENT = 2
    CONFIG_INVALID = 3
    ABLETON_NOT_CONNECTED = 10
    REMOTE_SCRIPT_NOT_DETECTED = 11
    TIMEOUT = 12
    PROTOCOL_MISMATCH = 13
    EXECUTION_FAILED = 20
    INTERNAL_ERROR = 99


class ErrorCode(str, Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    CONFIG_INVALID = "CONFIG_INVALID"
    ABLETON_NOT_REACHABLE = "ABLETON_NOT_REACHABLE"
    REMOTE_SCRIPT_NOT_INSTALLED = "REMOTE_SCRIPT_NOT_INSTALLED"
    REMOTE_SCRIPT_INCOMPATIBLE = "REMOTE_SCRIPT_INCOMPATIBLE"
    PROTOCOL_VERSION_MISMATCH = "PROTOCOL_VERSION_MISMATCH"
    PROTOCOL_INVALID_RESPONSE = "PROTOCOL_INVALID_RESPONSE"
    PROTOCOL_REQUEST_ID_MISMATCH = "PROTOCOL_REQUEST_ID_MISMATCH"
    TIMEOUT = "TIMEOUT"
    BATCH_STEP_FAILED = "BATCH_STEP_FAILED"
    REMOTE_BUSY = "REMOTE_BUSY"
    READ_ONLY_VIOLATION = "READ_ONLY_VIOLATION"
    BATCH_PREFLIGHT_FAILED = "BATCH_PREFLIGHT_FAILED"
    BATCH_ASSERT_FAILED = "BATCH_ASSERT_FAILED"
    BATCH_RETRY_EXHAUSTED = "BATCH_RETRY_EXHAUSTED"
    INSTALL_TARGET_NOT_FOUND = "INSTALL_TARGET_NOT_FOUND"
    SKILL_SOURCE_NOT_FOUND = "SKILL_SOURCE_NOT_FOUND"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetailReason(str, Enum):
    NOT_SUPPORTED_BY_LIVE_API = "not_supported_by_live_api"
    CONTRACT_VALIDATION_FAILED = "contract_validation_failed"


def _error_code_value(error_code: ErrorCode | str) -> str:
    return error_code.value if isinstance(error_code, ErrorCode) else error_code


def details_with_reason(
    reason: ErrorDetailReason,
    /,
    **details: Any,
) -> dict[str, Any]:
    return {
        "reason": reason.value,
        **details,
    }


@dataclass(slots=True)
class AppError(Exception):
    error_code: ErrorCode | str
    message: str
    hint: str | None = None
    exit_code: ExitCode = ExitCode.INTERNAL_ERROR
    details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": _error_code_value(self.error_code),
            "message": self.message,
            "hint": self.hint,
            "details": self.details or None,
        }


REMOTE_ERROR_TO_EXIT_CODE: dict[ErrorCode, ExitCode] = {
    ErrorCode.INVALID_ARGUMENT: ExitCode.INVALID_ARGUMENT,
    ErrorCode.CONFIG_INVALID: ExitCode.CONFIG_INVALID,
    ErrorCode.ABLETON_NOT_REACHABLE: ExitCode.ABLETON_NOT_CONNECTED,
    ErrorCode.REMOTE_SCRIPT_NOT_INSTALLED: ExitCode.REMOTE_SCRIPT_NOT_DETECTED,
    ErrorCode.REMOTE_SCRIPT_INCOMPATIBLE: ExitCode.PROTOCOL_MISMATCH,
    ErrorCode.PROTOCOL_VERSION_MISMATCH: ExitCode.PROTOCOL_MISMATCH,
    ErrorCode.PROTOCOL_INVALID_RESPONSE: ExitCode.PROTOCOL_MISMATCH,
    ErrorCode.PROTOCOL_REQUEST_ID_MISMATCH: ExitCode.PROTOCOL_MISMATCH,
    ErrorCode.TIMEOUT: ExitCode.TIMEOUT,
    ErrorCode.BATCH_STEP_FAILED: ExitCode.EXECUTION_FAILED,
    ErrorCode.REMOTE_BUSY: ExitCode.EXECUTION_FAILED,
    ErrorCode.READ_ONLY_VIOLATION: ExitCode.EXECUTION_FAILED,
    ErrorCode.BATCH_PREFLIGHT_FAILED: ExitCode.EXECUTION_FAILED,
    ErrorCode.BATCH_ASSERT_FAILED: ExitCode.EXECUTION_FAILED,
    ErrorCode.BATCH_RETRY_EXHAUSTED: ExitCode.EXECUTION_FAILED,
    ErrorCode.INSTALL_TARGET_NOT_FOUND: ExitCode.EXECUTION_FAILED,
    ErrorCode.SKILL_SOURCE_NOT_FOUND: ExitCode.EXECUTION_FAILED,
    ErrorCode.UNSUPPORTED_OS: ExitCode.EXECUTION_FAILED,
    ErrorCode.INTERNAL_ERROR: ExitCode.INTERNAL_ERROR,
}


def exit_code_from_error_code(error_code: ErrorCode | str) -> ExitCode:
    normalized = _error_code_value(error_code)
    for code, exit_code in REMOTE_ERROR_TO_EXIT_CODE.items():
        if code.value == normalized:
            return exit_code
    return ExitCode.EXECUTION_FAILED


def remote_error_to_app_error(error: dict[str, Any]) -> AppError:
    code = str(error.get("code", ErrorCode.INTERNAL_ERROR.value))
    normalized_code: ErrorCode | str
    try:
        normalized_code = ErrorCode(code)
    except ValueError:
        normalized_code = code
    message = str(error.get("message", "Remote command failed"))
    hint = error.get("hint")
    if hint is not None:
        hint = str(hint)
    details = error.get("details")
    sanitized_details: dict[str, Any] = {}
    if isinstance(details, dict):
        sanitized_details = details
    return AppError(
        error_code=normalized_code,
        message=message,
        hint=hint,
        exit_code=exit_code_from_error_code(normalized_code),
        details={"remote": error, **sanitized_details},
    )
