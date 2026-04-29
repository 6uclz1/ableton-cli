from __future__ import annotations

import hashlib
from typing import Any

from .command_specs import read_only_remote_command_names, remote_command_names
from .errors import AppError, ErrorCode, ExitCode


def required_remote_commands() -> set[str]:
    return remote_command_names()


def read_only_remote_commands() -> set[str]:
    return read_only_remote_command_names()


def compute_command_set_hash(commands: list[str] | set[str]) -> str:
    normalized = sorted(set(commands))
    digest = hashlib.sha256()
    digest.update("\n".join(normalized).encode("utf-8"))
    return digest.hexdigest()


def parse_supported_commands(ping_payload: dict[str, Any]) -> set[str]:
    raw_commands = ping_payload.get("supported_commands")
    if not isinstance(raw_commands, list):
        raise AppError(
            error_code=ErrorCode.REMOTE_SCRIPT_INCOMPATIBLE,
            message="Remote Script ping payload is missing supported_commands",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    commands: set[str] = set()
    for index, value in enumerate(raw_commands):
        if not isinstance(value, str) or not value.strip():
            raise AppError(
                error_code=ErrorCode.REMOTE_SCRIPT_INCOMPATIBLE,
                message=f"supported_commands[{index}] must be a non-empty string",
                hint="Reinstall Remote Script and restart Ableton Live.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        commands.add(value)

    if not commands:
        raise AppError(
            error_code=ErrorCode.REMOTE_SCRIPT_INCOMPATIBLE,
            message="Remote Script reported no supported commands",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    remote_hash = ping_payload.get("command_set_hash")
    if not isinstance(remote_hash, str) or not remote_hash.strip():
        raise AppError(
            error_code=ErrorCode.REMOTE_SCRIPT_INCOMPATIBLE,
            message="Remote Script ping payload is missing command_set_hash",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )
    expected_hash = compute_command_set_hash(commands)
    if remote_hash != expected_hash:
        raise AppError(
            error_code=ErrorCode.REMOTE_SCRIPT_INCOMPATIBLE,
            message="Remote Script command_set_hash does not match supported_commands",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    return commands


def missing_required_commands(supported_commands: set[str]) -> list[str]:
    return sorted(required_remote_commands().difference(supported_commands))
