"""``plugins.toml``: the plugins this user installed with ``ableton-cli plugins``.

The manifest is the source of truth for managed plugins. The Python
environment can drift from it (``uv sync`` or reinstalling ableton-cli removes
packages it did not install); ``plugins sync`` makes the environment match it
again. Plugins installed by other means are never written here.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import default_config_path
from ..errors import AppError, ErrorCode, ExitCode

PLUGIN_MANIFEST_ENV = "ABLETON_CLI_PLUGIN_MANIFEST"
MANIFEST_FILE_NAME = "plugins.toml"

_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_KEYS = ("source", "rev", "distribution", "version")
_OPTIONAL_KEYS = ("requested_ref",)
_HEADER = "# Managed by 'ableton-cli plugins'. Change it with those commands, not by hand.\n"


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    name: str
    #: Canonical ``https://github.com/<owner>/<repo>``.
    source: str
    #: The ref the user asked for (branch or tag), or ``None`` for the default branch.
    requested_ref: str | None
    #: The commit it resolved to; installs are always pinned to this.
    rev: str
    distribution: str
    version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "requested_ref": self.requested_ref,
            "rev": self.rev,
            "distribution": self.distribution,
            "version": self.version,
        }


def plugin_manifest_path(env: Mapping[str, str] = os.environ) -> Path:
    override = env.get(PLUGIN_MANIFEST_ENV)
    if override:
        return Path(override)
    return default_config_path().parent / MANIFEST_FILE_NAME


def read_manifest(path: Path) -> dict[str, ManifestEntry]:
    if not path.exists():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise _invalid(path, f"cannot be read: {exc}") from exc

    unknown_roots = sorted(set(raw) - {"plugins"})
    if unknown_roots:
        raise _invalid(path, f"unknown top-level keys {unknown_roots}")
    plugins = raw.get("plugins", {})
    if not isinstance(plugins, dict):
        raise _invalid(path, "'plugins' must be a table")
    return {name: _entry(path, name, table) for name, table in sorted(plugins.items())}


def write_manifest(path: Path, entries: Mapping[str, ManifestEntry]) -> None:
    lines = [_HEADER]
    for name in sorted(entries):
        lines.append(f"\n[plugins.{name}]\n")
        lines.extend(_entry_lines(entries[name]))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text("".join(lines), encoding="utf-8", newline="\n")
    temporary.replace(path)


def _entry_lines(entry: ManifestEntry) -> list[str]:
    # JSON string escapes are valid TOML basic-string escapes.
    return [
        f"{key} = {json.dumps(value)}\n"
        for key, value in entry.to_dict().items()
        if key != "name" and value is not None
    ]


def _entry(path: Path, name: str, table: object) -> ManifestEntry:
    if not isinstance(table, dict):
        raise _invalid(path, f"[plugins.{name}] must be a table")
    _check_keys(path, name, table)
    values = {key: table.get(key) for key in (*_REQUIRED_KEYS, *_OPTIONAL_KEYS)}
    for key, value in values.items():
        if not (isinstance(value, str) or (value is None and key in _OPTIONAL_KEYS)):
            raise _invalid(path, f"[plugins.{name}].{key} must be a string")
    if _SHA_PATTERN.fullmatch(values["rev"]) is None:
        raise _invalid(path, f"[plugins.{name}].rev must be a full 40-character commit SHA")
    return ManifestEntry(name=name, **values)


def _check_keys(path: Path, name: str, table: dict[str, object]) -> None:
    unknown = sorted(set(table) - set(_REQUIRED_KEYS) - set(_OPTIONAL_KEYS))
    missing = [key for key in _REQUIRED_KEYS if key not in table]
    if unknown or missing:
        raise _invalid(path, f"[plugins.{name}] has unknown keys {unknown}, missing {missing}")


def _invalid(path: Path, problem: str) -> AppError:
    return AppError(
        error_code=ErrorCode.CONFIG_INVALID,
        message=f"Plugin manifest {path} {problem}",
        hint=(
            "Restore the file, or delete it and reinstall plugins with "
            "'ableton-cli plugins install'."
        ),
        exit_code=ExitCode.CONFIG_INVALID,
    )
