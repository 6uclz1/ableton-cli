from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from ..command_specs import public_command_names
from ..errors import AppError, ErrorCode, ErrorDetailReason, ExitCode, details_with_reason
from .schema import ContractValidationError, validate_value


@dataclass(frozen=True, slots=True)
class CommandContractSpec:
    args: dict[str, Any]
    result: dict[str, Any]
    errors: dict[str, Any]
    side_effect: dict[str, Any]
    remote_command: str | None = None

    def to_public_contract(self) -> dict[str, Any]:
        return {
            "args": deepcopy(self.args),
            "result": deepcopy(self.result),
            "errors": deepcopy(self.errors),
            "side_effect": deepcopy(self.side_effect),
        }


def _ref_schema(*, selector_fields: tuple[str, ...]) -> dict[str, Any]:
    properties: dict[str, Any] = {"mode": {"type": "string"}}
    for field in selector_fields:
        properties[field] = {"type": "string" if field != "index" else "integer"}
    return {
        "type": "object",
        "required": ["mode"],
        "properties": properties,
        "additional_properties": False,
    }


def _track_ref_schema() -> dict[str, Any]:
    return _ref_schema(selector_fields=("index", "name", "query", "stable_ref"))


def _device_ref_schema() -> dict[str, Any]:
    return _ref_schema(selector_fields=("index", "name", "query", "stable_ref"))


def _parameter_ref_schema() -> dict[str, Any]:
    return _ref_schema(selector_fields=("index", "name", "query", "stable_ref", "key"))


def _track_ref_args_schema(*, include_value: dict[str, Any] | None = None) -> dict[str, Any]:
    properties: dict[str, Any] = {"track_ref": _track_ref_schema()}
    required = ["track_ref"]
    if include_value is not None:
        for name, schema in include_value.items():
            properties[name] = schema
            required.append(name)
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additional_properties": False,
    }


def _track_device_args_schema(
    *,
    include_value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "track_ref": _track_ref_schema(),
        "device_ref": _device_ref_schema(),
    }
    required = ["track_ref", "device_ref"]
    if include_value is not None:
        for name, schema in include_value.items():
            properties[name] = schema
            required.append(name)
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additional_properties": False,
    }


def _track_device_parameter_args_schema(
    *,
    include_value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "track_ref": _track_ref_schema(),
        "device_ref": _device_ref_schema(),
        "parameter_ref": _parameter_ref_schema(),
    }
    required = ["track_ref", "device_ref", "parameter_ref"]
    if include_value is not None:
        for name, schema in include_value.items():
            properties[name] = schema
            required.append(name)
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additional_properties": False,
    }


def _parameter_result_schema(*, include_bounds: bool = True) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "index": {"type": "integer"},
        "stable_ref": {"type": "string"},
        "name": {"type": "string"},
        "value": {"type": "number"},
    }
    required = ["index", "stable_ref", "name", "value"]
    if include_bounds:
        properties.update(
            {
                "min": {"type": ["number", "null"]},
                "max": {"type": ["number", "null"]},
                "is_enabled": {"type": "boolean"},
                "is_quantized": {"type": "boolean"},
            }
        )
        required.extend(["min", "max", "is_enabled", "is_quantized"])
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additional_properties": False,
    }


def _device_result_schema(*, include_track_stable_ref: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "index": {"type": "integer"},
        "stable_ref": {"type": "string"},
        "name": {"type": "string"},
        "class_name": {"type": "string"},
        "type": {"type": "string"},
        "parameters": {"type": "array", "items": _parameter_result_schema(include_bounds=False)},
    }
    required = ["index", "stable_ref", "name", "class_name", "type", "parameters"]
    if include_track_stable_ref:
        properties["track_stable_ref"] = {"type": "string"}
        required.append("track_stable_ref")
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additional_properties": False,
    }


def _track_summary_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["index", "stable_ref", "name", "mute", "solo", "arm", "volume"],
        "properties": {
            "index": {"type": "integer"},
            "stable_ref": {"type": "string"},
            "name": {"type": "string"},
            "mute": {"type": "boolean"},
            "solo": {"type": "boolean"},
            "arm": {"type": "boolean"},
            "volume": {"type": "number"},
        },
        "additional_properties": False,
    }


def _track_state_result_schema(*, field_name: str, field_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["track", field_name],
        "properties": {
            "track": {"type": "integer"},
            field_name: field_schema,
        },
        "additional_properties": False,
    }


def _device_search_result_schema(*, type_field: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["track", type_field, "count", "devices"],
        "properties": {
            "track": {"type": ["integer", "null"]},
            type_field: {"type": ["string", "null"]},
            "count": {"type": "integer"},
            "devices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "track",
                        "device",
                        "track_stable_ref",
                        "stable_ref",
                        "track_name",
                        "device_name",
                        "class_name",
                        "detected_type",
                    ],
                    "properties": {
                        "track": {"type": "integer"},
                        "device": {"type": "integer"},
                        "track_stable_ref": {"type": "string"},
                        "stable_ref": {"type": "string"},
                        "track_name": {"type": "string"},
                        "device_name": {"type": "string"},
                        "class_name": {"type": "string"},
                        "detected_type": {"type": "string"},
                    },
                    "additional_properties": False,
                },
            },
        },
        "additional_properties": False,
    }


def _parameter_listing_result_schema(
    *, detected_type_field: str | None = "detected_type"
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "track": {"type": "integer"},
        "device": {"type": "integer"},
        "track_stable_ref": {"type": "string"},
        "device_stable_ref": {"type": "string"},
        "device_name": {"type": "string"},
        "class_name": {"type": "string"},
        "parameter_count": {"type": "integer"},
        "parameters": {"type": "array", "items": _parameter_result_schema()},
    }
    required = [
        "track",
        "device",
        "track_stable_ref",
        "device_stable_ref",
        "device_name",
        "class_name",
        "parameter_count",
        "parameters",
    ]
    if detected_type_field is not None:
        properties[detected_type_field] = {"type": "string"}
        required.append(detected_type_field)
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additional_properties": False,
    }


def _safe_parameter_set_result_schema(
    *, type_field: str | None = "detected_type"
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "track": {"type": "integer"},
        "device": {"type": "integer"},
        "parameter": {"type": "integer"},
        "track_stable_ref": {"type": "string"},
        "device_stable_ref": {"type": "string"},
        "parameter_stable_ref": {"type": "string"},
        "before": {"type": "number"},
        "after": {"type": "number"},
        "min": {"type": "number"},
        "max": {"type": "number"},
        "is_enabled": {"type": "boolean"},
        "is_quantized": {"type": "boolean"},
    }
    required = [
        "track",
        "device",
        "parameter",
        "track_stable_ref",
        "device_stable_ref",
        "parameter_stable_ref",
        "before",
        "after",
        "min",
        "max",
        "is_enabled",
        "is_quantized",
    ]
    if type_field is not None:
        properties[type_field] = {"type": "string"}
        required.append(type_field)
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additional_properties": False,
    }


def _standard_state_result_schema(*, type_field: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            type_field,
            "track",
            "device",
            "track_stable_ref",
            "device_stable_ref",
            "key_count",
            "keys",
            "state",
        ],
        "properties": {
            type_field: {"type": "string"},
            "track": {"type": "integer"},
            "device": {"type": "integer"},
            "track_stable_ref": {"type": "string"},
            "device_stable_ref": {"type": "string"},
            "key_count": {"type": "integer"},
            "keys": {"type": "array", "items": {"type": "string"}},
            "state": {"type": "object"},
        },
        "additional_properties": False,
    }


_DETAILED_CONTRACTS: dict[str, dict[str, dict[str, Any]]] = {
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
            "required": ["track_ref", "send"],
            "properties": {
                "track_ref": _track_ref_schema(),
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
            "required": ["track_ref", "send", "value"],
            "properties": {
                "track_ref": _track_ref_schema(),
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
            "required": ["track_ref"],
            "properties": {"track_ref": _track_ref_schema()},
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
            "required": ["track_ref", "routing_type", "routing_channel"],
            "properties": {
                "track_ref": _track_ref_schema(),
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
            "required": ["track_ref"],
            "properties": {"track_ref": _track_ref_schema()},
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
            "required": ["track_ref", "routing_type", "routing_channel"],
            "properties": {
                "track_ref": _track_ref_schema(),
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

_DETAILED_CONTRACTS.update(
    {
        "tracks list": {
            "result": {
                "type": "object",
                "required": ["tracks"],
                "properties": {
                    "tracks": {"type": "array", "items": _track_summary_schema()},
                },
                "additional_properties": False,
            }
        },
        "track info": {
            "args": _track_ref_args_schema(),
            "result": {
                "type": "object",
                "required": [
                    "index",
                    "stable_ref",
                    "name",
                    "is_audio_track",
                    "is_midi_track",
                    "mute",
                    "solo",
                    "arm",
                    "volume",
                    "panning",
                    "clip_slots",
                    "devices",
                ],
                "properties": {
                    "index": {"type": "integer"},
                    "stable_ref": {"type": "string"},
                    "name": {"type": "string"},
                    "is_audio_track": {"type": "boolean"},
                    "is_midi_track": {"type": "boolean"},
                    "mute": {"type": "boolean"},
                    "solo": {"type": "boolean"},
                    "arm": {"type": "boolean"},
                    "volume": {"type": "number"},
                    "panning": {"type": "number"},
                    "clip_slots": {"type": "array"},
                    "devices": {
                        "type": "array",
                        "items": _device_result_schema(include_track_stable_ref=True),
                    },
                },
                "additional_properties": False,
            },
        },
        "track volume get": {
            "args": _track_ref_args_schema(),
            "result": _track_state_result_schema(
                field_name="volume", field_schema={"type": "number"}
            ),
        },
        "track volume set": {
            "args": _track_ref_args_schema(include_value={"value": {"type": "number"}}),
            "result": _track_state_result_schema(
                field_name="volume", field_schema={"type": "number"}
            ),
        },
        "track name set": {
            "args": _track_ref_args_schema(include_value={"name": {"type": "string"}}),
            "result": _track_state_result_schema(
                field_name="name", field_schema={"type": "string"}
            ),
        },
        "track mute get": {
            "args": _track_ref_args_schema(),
            "result": _track_state_result_schema(
                field_name="mute", field_schema={"type": "boolean"}
            ),
        },
        "track mute set": {
            "args": _track_ref_args_schema(include_value={"value": {"type": "boolean"}}),
            "result": _track_state_result_schema(
                field_name="mute", field_schema={"type": "boolean"}
            ),
        },
        "track solo get": {
            "args": _track_ref_args_schema(),
            "result": _track_state_result_schema(
                field_name="solo", field_schema={"type": "boolean"}
            ),
        },
        "track solo set": {
            "args": _track_ref_args_schema(include_value={"value": {"type": "boolean"}}),
            "result": _track_state_result_schema(
                field_name="solo", field_schema={"type": "boolean"}
            ),
        },
        "track arm get": {
            "args": _track_ref_args_schema(),
            "result": _track_state_result_schema(
                field_name="arm", field_schema={"type": "boolean"}
            ),
        },
        "track arm set": {
            "args": _track_ref_args_schema(include_value={"value": {"type": "boolean"}}),
            "result": _track_state_result_schema(
                field_name="arm", field_schema={"type": "boolean"}
            ),
        },
        "track panning get": {
            "args": _track_ref_args_schema(),
            "result": _track_state_result_schema(
                field_name="panning", field_schema={"type": "number"}
            ),
        },
        "track panning set": {
            "args": _track_ref_args_schema(include_value={"value": {"type": "number"}}),
            "result": _track_state_result_schema(
                field_name="panning", field_schema={"type": "number"}
            ),
        },
        "device parameter set": {
            "args": _track_device_parameter_args_schema(
                include_value={"value": {"type": "number"}}
            ),
            "result": {
                "type": "object",
                "required": [
                    "track",
                    "device",
                    "parameter",
                    "track_stable_ref",
                    "device_stable_ref",
                    "parameter_stable_ref",
                    "value",
                ],
                "properties": {
                    "track": {"type": "integer"},
                    "device": {"type": "integer"},
                    "parameter": {"type": "integer"},
                    "track_stable_ref": {"type": "string"},
                    "device_stable_ref": {"type": "string"},
                    "parameter_stable_ref": {"type": "string"},
                    "value": {"type": "number"},
                },
                "additional_properties": False,
            },
        },
        "synth find": {
            "result": _device_search_result_schema(type_field="synth_type"),
        },
        "synth parameters list": {
            "args": _track_device_args_schema(),
            "result": _parameter_listing_result_schema(),
        },
        "synth parameter set": {
            "args": _track_device_parameter_args_schema(
                include_value={"value": {"type": "number"}}
            ),
            "result": _safe_parameter_set_result_schema(),
        },
        "synth observe": {
            "args": _track_device_args_schema(),
            "result": _parameter_listing_result_schema(),
        },
        "effect find": {
            "result": _device_search_result_schema(type_field="effect_type"),
        },
        "effect parameters list": {
            "args": _track_device_args_schema(),
            "result": _parameter_listing_result_schema(),
        },
        "effect parameter set": {
            "args": _track_device_parameter_args_schema(
                include_value={"value": {"type": "number"}}
            ),
            "result": _safe_parameter_set_result_schema(),
        },
        "effect observe": {
            "args": _track_device_args_schema(),
            "result": _parameter_listing_result_schema(),
        },
    }
)

for synth_type in ("wavetable", "drift", "meld"):
    _DETAILED_CONTRACTS[f"synth {synth_type} set"] = {
        "args": _track_device_parameter_args_schema(include_value={"value": {"type": "number"}}),
        "result": {
            **_safe_parameter_set_result_schema(),
            "required": [
                *_safe_parameter_set_result_schema()["required"],  # type: ignore[index]
                "synth_type",
                "key",
                "resolved_parameter",
            ],
            "properties": {
                **_safe_parameter_set_result_schema()["properties"],  # type: ignore[index]
                "synth_type": {"type": "string"},
                "key": {"type": "string"},
                "resolved_parameter": {"type": "integer"},
            },
        },
    }
    _DETAILED_CONTRACTS[f"synth {synth_type} observe"] = {
        "args": _track_device_args_schema(),
        "result": _standard_state_result_schema(type_field="synth_type"),
    }

for effect_type in ("eq8", "limiter", "compressor", "auto-filter", "reverb", "utility"):
    _DETAILED_CONTRACTS[f"effect {effect_type} set"] = {
        "args": _track_device_parameter_args_schema(include_value={"value": {"type": "number"}}),
        "result": {
            **_safe_parameter_set_result_schema(),
            "required": [
                *_safe_parameter_set_result_schema()["required"],  # type: ignore[index]
                "effect_type",
                "key",
                "resolved_parameter",
            ],
            "properties": {
                **_safe_parameter_set_result_schema()["properties"],  # type: ignore[index]
                "effect_type": {"type": "string"},
                "key": {"type": "string"},
                "resolved_parameter": {"type": "integer"},
            },
        },
    }
    _DETAILED_CONTRACTS[f"effect {effect_type} observe"] = {
        "args": _track_device_args_schema(),
        "result": _standard_state_result_schema(type_field="effect_type"),
    }

_LOCAL_ONLY_COMMANDS = frozenset(
    {
        "batch stream",
        "clip name set-many",
        "clip place-pattern",
        "completion",
        "config init",
        "config set",
        "config show",
        "doctor",
        "install-remote-script",
        "install-skill",
        "session diff",
        "wait-ready",
    }
)

_REMOTE_COMMAND_EXCEPTIONS = {
    "arrangement from-session": "arrangement_from_session",
    "batch run": "execute_batch",
    "browser categories": "get_browser_categories",
    "browser item": "get_browser_item",
    "browser items": "get_browser_items",
    "browser items-at-path": "get_browser_items_at_path",
    "browser load": "load_instrument_or_effect",
    "browser load-drum-kit": "load_drum_kit",
    "browser search": "search_browser_items",
    "browser tree": "get_browser_tree",
    "clip create": "create_clip",
    "clip duplicate-many": "clip_duplicate",
    "clip fire": "fire_clip",
    "clip name set": "set_clip_name",
    "clip notes import-browser": "load_instrument_or_effect",
    "clip stop": "stop_clip",
    "device parameter set": "set_device_parameter",
    "effect find": "find_effect_devices",
    "effect observe": "observe_effect_parameters",
    "effect parameter set": "set_effect_parameter_safe",
    "effect parameters list": "list_effect_parameters",
    "master devices list": "master_devices_list",
    "master info": "master_info",
    "master panning get": "master_panning_get",
    "master volume get": "master_volume_get",
    "return-track mute get": "return_track_mute_get",
    "return-track mute set": "return_track_mute_set",
    "return-track solo get": "return_track_solo_get",
    "return-track solo set": "return_track_solo_set",
    "return-track volume get": "return_track_volume_get",
    "return-track volume set": "return_track_volume_set",
    "return-tracks list": "return_tracks_list",
    "session info": "get_session_info",
    "session stop-all-clips": "stop_all_clips",
    "synth find": "find_synth_devices",
    "synth observe": "observe_synth_parameters",
    "synth parameter set": "set_synth_parameter_safe",
    "synth parameters list": "list_synth_parameters",
    "track info": "get_track_info",
    "tracks create audio": "create_audio_track",
    "tracks create midi": "create_midi_track",
}

_DESTRUCTIVE_COMMANDS = frozenset(
    {
        "arrangement clip delete",
        "arrangement clip notes clear",
        "arrangement clip notes import-browser",
        "arrangement clip notes replace",
        "batch run",
        "batch stream",
        "clip cut-to-drum-rack",
        "clip groove clear",
        "clip notes clear",
        "clip notes import-browser",
        "clip notes replace",
        "config init",
        "config set",
        "install-remote-script",
        "install-skill",
        "song new",
        "song redo",
        "song undo",
        "tracks delete",
    }
)


def _default_errors() -> dict[str, Any]:
    return {"codes": sorted(code.value for code in ErrorCode)}


def _remote_command_name(command_name: str) -> str | None:
    synth_match = re.fullmatch(r"synth (wavetable|drift|meld) (keys|set|observe)", command_name)
    if synth_match:
        suffix = synth_match.group(2)
        if suffix == "keys":
            return "list_standard_synth_keys"
        if suffix == "set":
            return "set_standard_synth_parameter_safe"
        return "observe_standard_synth_state"

    effect_match = re.fullmatch(
        r"effect (eq8|limiter|compressor|auto-filter|reverb|utility) (keys|set|observe)",
        command_name,
    )
    if effect_match:
        suffix = effect_match.group(2)
        if suffix == "keys":
            return "list_standard_effect_keys"
        if suffix == "set":
            return "set_standard_effect_parameter_safe"
        return "observe_standard_effect_state"

    if command_name in _LOCAL_ONLY_COMMANDS:
        return None
    if command_name in _REMOTE_COMMAND_EXCEPTIONS:
        return _REMOTE_COMMAND_EXCEPTIONS[command_name]
    return command_name.replace(" ", "_").replace("-", "_")


def _is_read_command(command_name: str) -> bool:
    if command_name in {
        "completion",
        "config show",
        "doctor",
        "ping",
        "session diff",
        "session info",
        "session snapshot",
        "wait-ready",
    }:
        return True

    read_suffixes = (" get", " info", " list", " find", " observe", " keys")
    if command_name.endswith(read_suffixes):
        return True

    return command_name.startswith(("browser categories", "browser item", "browser items"))


def _side_effect_metadata(command_name: str) -> dict[str, Any]:
    if _is_read_command(command_name):
        return {
            "kind": "read",
            "idempotent": True,
            "requires_confirmation": False,
        }

    kind = "destructive" if command_name in _DESTRUCTIVE_COMMANDS else "write"
    return {
        "kind": kind,
        "idempotent": False,
        "requires_confirmation": kind == "destructive",
    }


def _build_contract_specs() -> dict[str, CommandContractSpec]:
    specs: dict[str, CommandContractSpec] = {}
    for command_name in sorted(public_command_names()):
        detailed = deepcopy(_DETAILED_CONTRACTS.get(command_name, {}))
        specs[command_name] = CommandContractSpec(
            args=detailed.get("args", {"type": "object"}),
            result=detailed.get("result", {"type": "object"}),
            errors=detailed.get("errors", _default_errors()),
            side_effect=detailed.get("side_effect", _side_effect_metadata(command_name)),
            remote_command=_remote_command_name(command_name),
        )
    return specs


_CONTRACTS = _build_contract_specs()


def get_registered_contracts() -> dict[str, dict[str, Any]]:
    return {name: spec.to_public_contract() for name, spec in _CONTRACTS.items()}


def read_only_remote_command_names() -> set[str]:
    return {
        spec.remote_command
        for spec in _CONTRACTS.values()
        if spec.remote_command is not None and spec.side_effect["kind"] == "read"
    }


def validate_command_contract(*, command: str, args: dict[str, Any], result: Any) -> None:
    contract = _CONTRACTS.get(command)
    if contract is None:
        return

    try:
        validate_value(contract.args, args, path="args")
        validate_value(contract.result, result, path="result")
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
