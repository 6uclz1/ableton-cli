from __future__ import annotations

from ableton_cli.errors import (
    AppError,
    ErrorCode,
    ErrorDetailReason,
    ExitCode,
    details_with_reason,
)


def test_app_error_payload_uses_string_error_code_for_enum() -> None:
    error = AppError(
        error_code=ErrorCode.TIMEOUT,
        message="timed out",
        hint="retry",
        exit_code=ExitCode.TIMEOUT,
    )

    payload = error.to_payload()

    assert payload["code"] == "TIMEOUT"
    assert payload["message"] == "timed out"
    assert payload["hint"] == "retry"
    assert payload["details"] is None


def test_details_with_reason_normalizes_reason_field() -> None:
    details = details_with_reason(
        ErrorDetailReason.NOT_SUPPORTED_BY_LIVE_API,
        operation="song_save",
    )

    assert details == {
        "reason": "not_supported_by_live_api",
        "operation": "song_save",
    }
