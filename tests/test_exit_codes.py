from __future__ import annotations

from ableton_cli.errors import ExitCode, exit_code_from_error_code


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
    assert exit_code_from_error_code("TIMEOUT") == ExitCode.TIMEOUT
    assert exit_code_from_error_code("BATCH_STEP_FAILED") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("REMOTE_BUSY") == ExitCode.EXECUTION_FAILED
    assert exit_code_from_error_code("INTERNAL_ERROR") == ExitCode.INTERNAL_ERROR
    assert exit_code_from_error_code("UNKNOWN") == ExitCode.EXECUTION_FAILED
