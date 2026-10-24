"""Contracts of the ``plugins`` command group."""

from __future__ import annotations

from typing import Any

_STRING = {"type": "string"}
_OPTIONAL_STRING = {"oneOf": [{"type": "string"}, {"type": "null"}]}
_SHA = {"type": "string", "minLength": 40}


def _one_of_strings(*values: str) -> dict[str, Any]:
    return {"oneOf": [{"type": "string", "const": value} for value in values]}


_MANIFEST_ENTRY = {
    "type": "object",
    "required": ["name", "source", "requested_ref", "rev", "distribution", "version"],
    "properties": {
        "name": _STRING,
        "source": _STRING,
        "requested_ref": _OPTIONAL_STRING,
        "rev": _SHA,
        "distribution": _STRING,
        "version": _STRING,
    },
    "additional_properties": False,
}

_PLUGIN_ENTRY = {
    "type": "object",
    "required": [
        "name",
        "state",
        "managed",
        "source",
        "installed_rev",
        "in_sync",
        "distribution",
        "commands",
        "skills",
        "error",
    ],
    "properties": {
        "name": _STRING,
        "state": _one_of_strings("loaded", "failed", "not_installed", "disabled"),
        "managed": {"type": "boolean"},
        "commands": {"type": "array"},
        "skills": {"type": "array", "items": _STRING},
    },
}


def _pinned_args(*leading: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": [*leading, "ref", "source", "rev"],
        "properties": {
            **{name: _STRING for name in leading},
            "ref": _OPTIONAL_STRING,
            "source": _STRING,
            "rev": _SHA,
        },
        "additional_properties": False,
    }


PLUGIN_CONTRACTS: dict[str, dict[str, dict[str, Any]]] = {
    "plugins list": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["enabled", "api_version", "manifest_path", "plugins"],
            "properties": {
                "enabled": {"type": "boolean"},
                "api_version": {"type": "integer", "minimum": 1},
                "manifest_path": _STRING,
                "plugins": {"type": "array", "items": _PLUGIN_ENTRY},
            },
        },
    },
    "plugins info": {
        "args": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": _STRING},
            "additional_properties": False,
        },
        "result": _PLUGIN_ENTRY,
    },
    "plugins install": {
        "args": _pinned_args("url"),
        "result": {
            "type": "object",
            "required": ["action", "plugin"],
            "properties": {"action": _one_of_strings("installed"), "plugin": _MANIFEST_ENTRY},
        },
    },
    "plugins update": {
        "args": _pinned_args("name"),
        "result": {
            "type": "object",
            "required": ["action", "plugin", "previous_rev"],
            "properties": {
                "action": _one_of_strings("updated", "unchanged"),
                "plugin": _MANIFEST_ENTRY,
                "previous_rev": _SHA,
            },
        },
    },
    "plugins uninstall": {
        "args": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": _STRING},
            "additional_properties": False,
        },
        "result": {
            "type": "object",
            "required": ["action", "plugin"],
            "properties": {
                "action": _one_of_strings("uninstalled", "removed_from_manifest"),
                "plugin": _MANIFEST_ENTRY,
            },
        },
    },
    "plugins sync": {
        "args": {"type": "object", "additional_properties": False},
        "result": {
            "type": "object",
            "required": ["plugins"],
            "properties": {
                "plugins": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "action", "rev"],
                        "properties": {
                            "name": _STRING,
                            "action": _one_of_strings("installed", "unchanged"),
                            "rev": _SHA,
                        },
                        "additional_properties": False,
                    },
                },
            },
        },
    },
}
