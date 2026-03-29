from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..errors import AppError, ErrorCode, ErrorDetailReason, ExitCode, details_with_reason
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
    "track send get": {
        "args": {
            "type": "object",
            "required": ["track", "send"],
            "properties": {
                "track": {"type": "integer"},
                "send": {"type": "integer"},
            },
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["track", "send", "value"],
            "properties": {
                "track": {"type": "integer"},
                "send": {"type": "integer"},
                "value": {"type": "number"},
            },
            "additional_properties": False,
        },
    },
    "track send set": {
        "args": {
            "type": "object",
            "required": ["track", "send", "value"],
            "properties": {
                "track": {"type": "integer"},
                "send": {"type": "integer"},
                "value": {"type": "number"},
            },
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["track", "send", "value"],
            "properties": {
                "track": {"type": "integer"},
                "send": {"type": "integer"},
                "value": {"type": "number"},
            },
            "additional_properties": False,
        },
    },
    "return-tracks list": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["return_tracks"],
            "properties": {
                "return_tracks": {"type": "array"},
            },
            "additional_properties": False,
        },
    },
    "return-track volume get": {
        "args": {
            "type": "object",
            "required": ["return_track"],
            "properties": {"return_track": {"type": "integer"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["return_track", "volume"],
            "properties": {
                "return_track": {"type": "integer"},
                "volume": {"type": "number"},
            },
            "additional_properties": False,
        },
    },
    "return-track volume set": {
        "args": {
            "type": "object",
            "required": ["return_track", "value"],
            "properties": {
                "return_track": {"type": "integer"},
                "value": {"type": "number"},
            },
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["return_track", "volume"],
            "properties": {
                "return_track": {"type": "integer"},
                "volume": {"type": "number"},
            },
            "additional_properties": False,
        },
    },
    "return-track mute get": {
        "args": {
            "type": "object",
            "required": ["return_track"],
            "properties": {"return_track": {"type": "integer"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["return_track", "mute"],
            "properties": {
                "return_track": {"type": "integer"},
                "mute": {"type": "boolean"},
            },
            "additional_properties": False,
        },
    },
    "return-track mute set": {
        "args": {
            "type": "object",
            "required": ["return_track", "value"],
            "properties": {
                "return_track": {"type": "integer"},
                "value": {"type": "boolean"},
            },
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["return_track", "mute"],
            "properties": {
                "return_track": {"type": "integer"},
                "mute": {"type": "boolean"},
            },
            "additional_properties": False,
        },
    },
    "return-track solo get": {
        "args": {
            "type": "object",
            "required": ["return_track"],
            "properties": {"return_track": {"type": "integer"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["return_track", "solo"],
            "properties": {
                "return_track": {"type": "integer"},
                "solo": {"type": "boolean"},
            },
            "additional_properties": False,
        },
    },
    "return-track solo set": {
        "args": {
            "type": "object",
            "required": ["return_track", "value"],
            "properties": {
                "return_track": {"type": "integer"},
                "value": {"type": "boolean"},
            },
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["return_track", "solo"],
            "properties": {
                "return_track": {"type": "integer"},
                "solo": {"type": "boolean"},
            },
            "additional_properties": False,
        },
    },
    "master info": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["name", "volume", "panning"],
            "properties": {
                "name": {"type": "string"},
                "volume": {"type": "number"},
                "panning": {"type": "number"},
            },
            "additional_properties": False,
        },
    },
    "master volume get": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["volume"],
            "properties": {"volume": {"type": "number"}},
            "additional_properties": False,
        },
    },
    "master panning get": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["panning"],
            "properties": {"panning": {"type": "number"}},
            "additional_properties": False,
        },
    },
    "master devices list": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["devices"],
            "properties": {"devices": {"type": "array"}},
            "additional_properties": False,
        },
    },
    "mixer crossfader get": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "number"}},
            "additional_properties": False,
        },
    },
    "mixer crossfader set": {
        "args": {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "number"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "number"}},
            "additional_properties": False,
        },
    },
    "mixer cue-volume get": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "number"}},
            "additional_properties": False,
        },
    },
    "mixer cue-volume set": {
        "args": {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "number"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "number"}},
            "additional_properties": False,
        },
    },
    "mixer cue-routing get": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["routing", "available_routings"],
            "properties": {
                "routing": {"type": "string"},
                "available_routings": {"type": "array"},
            },
            "additional_properties": False,
        },
    },
    "mixer cue-routing set": {
        "args": {
            "type": "object",
            "required": ["routing"],
            "properties": {"routing": {"type": "string"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["routing", "available_routings"],
            "properties": {
                "routing": {"type": "string"},
                "available_routings": {"type": "array"},
            },
            "additional_properties": False,
        },
    },
    "track routing input get": {
        "args": {
            "type": "object",
            "required": ["track"],
            "properties": {"track": {"type": "integer"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["track", "current", "available"],
            "properties": {
                "track": {"type": "integer"},
                "current": {"type": "object"},
                "available": {"type": "object"},
            },
            "additional_properties": False,
        },
    },
    "track routing input set": {
        "args": {
            "type": "object",
            "required": ["track", "routing_type", "routing_channel"],
            "properties": {
                "track": {"type": "integer"},
                "routing_type": {"type": "string"},
                "routing_channel": {"type": "string"},
            },
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["track", "current", "available"],
            "properties": {
                "track": {"type": "integer"},
                "current": {"type": "object"},
                "available": {"type": "object"},
            },
            "additional_properties": False,
        },
    },
    "track routing output get": {
        "args": {
            "type": "object",
            "required": ["track"],
            "properties": {"track": {"type": "integer"}},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["track", "current", "available"],
            "properties": {
                "track": {"type": "integer"},
                "current": {"type": "object"},
                "available": {"type": "object"},
            },
            "additional_properties": False,
        },
    },
    "track routing output set": {
        "args": {
            "type": "object",
            "required": ["track", "routing_type", "routing_channel"],
            "properties": {
                "track": {"type": "integer"},
                "routing_type": {"type": "string"},
                "routing_channel": {"type": "string"},
            },
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["track", "current", "available"],
            "properties": {
                "track": {"type": "integer"},
                "current": {"type": "object"},
                "available": {"type": "object"},
            },
            "additional_properties": False,
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


def get_registered_contracts() -> dict[str, dict[str, dict[str, Any]]]:
    return deepcopy(_CONTRACTS)


def validate_command_contract(*, command: str, args: dict[str, Any], result: Any) -> None:
    contract = _CONTRACTS.get(command)
    if contract is None:
        return

    try:
        validate_value(contract["args"], args, path="args")
        validate_value(contract["result"], result, path="result")
    except ContractValidationError as exc:
        raise AppError(
            error_code=ErrorCode.PROTOCOL_INVALID_RESPONSE,
            message=f"Contract validation failed for '{command}': {exc.path} {exc.message}",
            hint="Fix the command contract or result payload shape.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
            details={
                "command": command,
                "path": exc.path,
                **details_with_reason(
                    ErrorDetailReason.CONTRACT_VALIDATION_FAILED,
                    validation_message=exc.message,
                ),
            },
        ) from exc
