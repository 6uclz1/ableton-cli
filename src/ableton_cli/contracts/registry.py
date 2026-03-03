from __future__ import annotations

from typing import Any

from ..errors import AppError, ExitCode
from .schema import ContractValidationError, validate_value

_CONTRACTS: dict[str, dict[str, dict[str, Any]]] = {
    "ping": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["host", "port", "rtt_ms"],
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer"},
                "protocol_version": {"type": ["integer", "null"]},
                "remote_script_version": {"type": ["string", "null"]},
                "supported_commands": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "command_set_hash": {"type": ["string", "null"]},
                "api_support": {"type": ["object", "null"]},
                "rtt_ms": {"type": "number"},
            },
        },
    },
    "doctor": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["summary", "checks"],
            "properties": {
                "summary": {
                    "type": "object",
                    "required": ["pass", "warn", "fail"],
                    "properties": {
                        "pass": {"type": "integer"},
                        "warn": {"type": "integer"},
                        "fail": {"type": "integer"},
                    },
                },
                "checks": {"type": "array"},
            },
        },
    },
    "song info": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "properties": {
                "tempo": {"type": "number"},
            },
        },
    },
    "tracks list": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["tracks"],
            "properties": {
                "tracks": {"type": "array"},
            },
        },
    },
    "session diff": {
        "args": {
            "type": "object",
            "required": ["from", "to"],
            "properties": {
                "from": {"type": "string"},
                "to": {"type": "string"},
            },
        },
        "result": {
            "type": "object",
            "required": ["from_path", "to_path", "added", "removed", "changed"],
            "properties": {
                "from_path": {"type": "string"},
                "to_path": {"type": "string"},
                "added": {"type": "object"},
                "removed": {"type": "object"},
                "changed": {"type": "object"},
            },
        },
    },
}


def validate_command_contract(*, command: str, args: dict[str, Any], result: Any) -> None:
    contract = _CONTRACTS.get(command)
    if contract is None:
        return

    try:
        validate_value(contract["args"], args, path="args")
        validate_value(contract["result"], result, path="result")
    except ContractValidationError as exc:
        raise AppError(
            error_code="PROTOCOL_INVALID_RESPONSE",
            message=f"Contract validation failed for '{command}': {exc.path} {exc.message}",
            hint="Fix the command contract or result payload shape.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
            details={
                "command": command,
                "path": exc.path,
                "reason": exc.message,
            },
        ) from exc
