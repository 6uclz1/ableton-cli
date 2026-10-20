"""Contracts for the offline ``set`` command group."""

from __future__ import annotations

from typing import Any


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "additional_properties": False,
    }


def _array(items: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": items}


_STRING = {"type": "string"}
_INTEGER = {"type": "integer"}
_NULLABLE_INTEGER = {"type": ["integer", "null"]}
_NUMBER = {"type": "number"}
_BOOLEAN = {"type": "boolean"}

_PATH_ARGS = _object({"path": _STRING})
_VERSION = _object({"major": _STRING, "minor": _STRING, "creator": _STRING})
_DEVICE = _object({"class": _STRING, "name": {"type": ["string", "null"]}})
_TRACK_BASE = {
    "index": _INTEGER,
    "id": _INTEGER,
    "name": _STRING,
    "color": _INTEGER,
    "devices": _array(_DEVICE),
}

_NULLABLE_STRING = {"type": ["string", "null"]}

LIVESET_CONTRACTS: dict[str, dict[str, dict[str, Any]]] = {
    "set automation write": {
        "args": _object(
            {
                "path": _STRING,
                "out": _STRING,
                "target": _STRING,
                "track_index": _NULLABLE_INTEGER,
                "track_name": _NULLABLE_STRING,
                "return_track_index": _NULLABLE_INTEGER,
                "main": _BOOLEAN,
            }
        ),
        "result": _object(
            {
                "path": _STRING,
                "out": _STRING,
                "scope": _object(
                    {"kind": _STRING, "index": _NULLABLE_INTEGER, "name": _NULLABLE_STRING}
                ),
                "target": _STRING,
                "parameter": _STRING,
                "point_count": _INTEGER,
                "replaced_point_count": _INTEGER,
            }
        ),
    },
    "set inspect": {
        "args": _PATH_ARGS,
        "result": _object(
            {
                "path": _STRING,
                "version": _VERSION,
                "song": _object(
                    {
                        "tempo": _NUMBER,
                        "tempo_automated": _BOOLEAN,
                        "time_signature": _object({"numerator": _INTEGER, "denominator": _INTEGER}),
                        "scale": _object(
                            {"root_note": _INTEGER, "name_index": _INTEGER, "in_key": _BOOLEAN}
                        ),
                    }
                ),
                "tracks": _array(
                    _object(
                        {
                            **_TRACK_BASE,
                            "type": _STRING,
                            "group_id": _NULLABLE_INTEGER,
                            "session_clip_count": _INTEGER,
                            "arrangement_clip_count": _INTEGER,
                        }
                    )
                ),
                "return_tracks": _array(_object(_TRACK_BASE)),
                "scenes": _array(_object({"index": _INTEGER, "name": _STRING})),
                "locators": _array(_object({"id": _INTEGER, "time": _NUMBER, "name": _STRING})),
                "plugins": _array(_object({"format": _STRING, "name": _STRING, "count": _INTEGER})),
            }
        ),
    },
    "set lint": {
        "args": _PATH_ARGS,
        "result": _object(
            {
                "path": _STRING,
                "version": _VERSION,
                "error_count": _INTEGER,
                "warning_count": _INTEGER,
                "findings": _array(
                    _object(
                        {
                            "severity": _STRING,
                            "code": _STRING,
                            "message": _STRING,
                            "details": {"type": "object"},
                        }
                    )
                ),
                "media": _object(
                    {
                        "checked_count": _INTEGER,
                        "unchecked_count": _INTEGER,
                        "unchecked_by_relative_path_type": {"type": "object"},
                    }
                ),
            }
        ),
    },
    "set diff": {
        "args": _object({"from": _STRING, "to": _STRING}),
        "result": _object(
            {
                "from_path": _STRING,
                "to_path": _STRING,
                "added": {"type": "object"},
                "removed": {"type": "object"},
                "changed": {"type": "object"},
            }
        ),
    },
}
