from __future__ import annotations

from ableton_cli.errors import ErrorCode, ErrorDetailReason, ExitCode, exit_code_from_error_code


def test_exit_code_values_are_fixed() -> None:
    assert ExitCode.SUCCESS.value == 0
    assert ExitCode.INVALID_ARGUMENT.value == 2
    assert ExitCode.CONFIG_INVALID.value == 3
    assert ExitCode.ABLETON_NOT_CONNECTED.value == 10
    assert ExitCode.REMOTE_SCRIPT_NOT_DETECTED.value == 11
    assert ExitCode.TIMEOUT.value == 12
    assert ExitCode.PROTOCOL_MISMATCH.value == 13
    assert ExitCode.EXECUTION_FAILED.value == 20
    assert ExitCode.INTERNAL_ERROR.value == 99


def test_remote_error_to_exit_code_mapping() -> None:
    assert exit_code_from_error_code("INVALID_ARGUMENT") == ExitCode.INVALID_ARGUMENT
    assert exit_code_from_error_code("CONFIG_INVALID") == ExitCode.CONFIG_INVALID
    assert exit_code_from_error_code("ABLETON_NOT_REACHABLE") == ExitCode.ABLETON_NOT_CONNECTED
    assert (
        exit_code_from_error_code("REMOTE_SCRIPT_NOT_INSTALLED")
        == ExitCode.REMOTE_SCRIPT_NOT_DETECTED
    )
    assert exit_code_from_error_code("REMOTE_SCRIPT_INCOMPATIBLE") == ExitCode.PROTOCOL_MISMATCH
    assert exit_code_from_error_code("PROTOCOL_VERSION_MISMATCH") == ExitCode.PROTOCOL_MISMATCH
    assert exit_code_from_error_code("PROTOCOL_INVALID_RESPONSE") == ExitCode.PROTOCOL_MISMATCH
    assert exit_code_from_error_code("PROTOCOL_REQUEST_ID_MISMATCH") == ExitCode.PROTOCOL_MISMATCH
    assert exit_code_from_error_code("TIMEOUT") == ExitCode.TIMEOUT
    assert exit_code_from_error_code("BATCH_STEP_FAILED") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("REMOTE_BUSY") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("READ_ONLY_VIOLATION") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("BATCH_PREFLIGHT_FAILED") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("BATCH_ASSERT_FAILED") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("BATCH_RETRY_EXHAUSTED") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("INTERNAL_ERROR") == ExitCode.INTERNAL_ERROR
    assert exit_code_from_error_code("UNKNOWN") == ExitCode.EXECUTION_FAILED


def test_error_code_enum_values_are_stable() -> None:
    assert ErrorCode.INVALID_ARGUMENT.value == "INVALID_ARGUMENT"
    assert ErrorCode.CONFIG_INVALID.value == "CONFIG_INVALID"
    assert ErrorCode.ABLETON_NOT_REACHABLE.value == "ABLETON_NOT_REACHABLE"
    assert ErrorCode.REMOTE_SCRIPT_NOT_INSTALLED.value == "REMOTE_SCRIPT_NOT_INSTALLED"
    assert ErrorCode.REMOTE_SCRIPT_INCOMPATIBLE.value == "REMOTE_SCRIPT_INCOMPATIBLE"
    assert ErrorCode.PROTOCOL_VERSION_MISMATCH.value == "PROTOCOL_VERSION_MISMATCH"
    assert ErrorCode.PROTOCOL_INVALID_RESPONSE.value == "PROTOCOL_INVALID_RESPONSE"
    assert ErrorCode.PROTOCOL_REQUEST_ID_MISMATCH.value == "PROTOCOL_REQUEST_ID_MISMATCH"
    assert ErrorCode.TIMEOUT.value == "TIMEOUT"
    assert ErrorCode.BATCH_STEP_FAILED.value == "BATCH_STEP_FAILED"
    assert ErrorCode.REMOTE_BUSY.value == "REMOTE_BUSY"
    assert ErrorCode.READ_ONLY_VIOLATION.value == "READ_ONLY_VIOLATION"
    assert ErrorCode.BATCH_PREFLIGHT_FAILED.value == "BATCH_PREFLIGHT_FAILED"
    assert ErrorCode.BATCH_ASSERT_FAILED.value == "BATCH_ASSERT_FAILED"
    assert ErrorCode.BATCH_RETRY_EXHAUSTED.value == "BATCH_RETRY_EXHAUSTED"
    assert ErrorCode.INSTALL_TARGET_NOT_FOUND.value == "INSTALL_TARGET_NOT_FOUND"
    assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"


def test_error_detail_reason_values_are_stable() -> None:
    assert ErrorDetailReason.NOT_SUPPORTED_BY_LIVE_API.value == "not_supported_by_live_api"
    assert ErrorDetailReason.CONTRACT_VALIDATION_FAILED.value == "contract_validation_failed"
