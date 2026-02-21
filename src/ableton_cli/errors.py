from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
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


@dataclass(slots=True)
class AppError(Exception):
    error_code: str
    message: str
    hint: str | None = None
    exit_code: ExitCode = ExitCode.INTERNAL_ERROR
    details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.error_code,
            "message": self.message,
            "hint": self.hint,
            "details": self.details or None,
        }


REMOTE_ERROR_TO_EXIT_CODE: dict[str, ExitCode] = {
    "INVALID_ARGUMENT": ExitCode.INVALID_ARGUMENT,
    "CONFIG_INVALID": ExitCode.CONFIG_INVALID,
    "ABLETON_NOT_REACHABLE": ExitCode.ABLETON_NOT_CONNECTED,
    "REMOTE_SCRIPT_NOT_INSTALLED": ExitCode.REMOTE_SCRIPT_NOT_DETECTED,
    "REMOTE_SCRIPT_INCOMPATIBLE": ExitCode.PROTOCOL_MISMATCH,
    "PROTOCOL_VERSION_MISMATCH": ExitCode.PROTOCOL_MISMATCH,
    "TIMEOUT": ExitCode.TIMEOUT,
    "BATCH_STEP_FAILED": ExitCode.EXECUTION_FAILED,
    "REMOTE_BUSY": ExitCode.EXECUTION_FAILED,
    "INSTALL_TARGET_NOT_FOUND": ExitCode.EXECUTION_FAILED,
    "INTERNAL_ERROR": ExitCode.INTERNAL_ERROR,
}


def exit_code_from_error_code(error_code: str) -> ExitCode:
    return REMOTE_ERROR_TO_EXIT_CODE.get(error_code, ExitCode.EXECUTION_FAILED)


def remote_error_to_app_error(error: dict[str, Any]) -> AppError:
    code = str(error.get("code", "INTERNAL_ERROR"))
    message = str(error.get("message", "Remote command failed"))
    hint = error.get("hint")
    if hint is not None:
        hint = str(hint)
    details = error.get("details")
    sanitized_details: dict[str, Any] = {}
    if isinstance(details, dict):
        sanitized_details = details
    return AppError(
        error_code=code,
        message=message,
        hint=hint,
        exit_code=exit_code_from_error_code(code),
        details={"remote": error, **sanitized_details},
    )
