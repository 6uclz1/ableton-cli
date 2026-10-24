"""Value types shared by the plugin host, the runtime and ``plugin_api``.

This module imports nothing from the runtime so that ``RuntimeContext`` can
carry a ``PluginLoadReport`` without an import cycle through ``plugin_api``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..command_registry import CommandDescriptor
from ..errors import AppError, ErrorCode, ExitCode

#: Bumped whenever ``plugin_api`` changes incompatibly. A plugin declaring any
#: other version is refused at load time rather than half-working.
PLUGIN_API_VERSION = 1
ENTRY_POINT_GROUP = "ableton_cli.plugins"


@dataclass(frozen=True, slots=True)
class Plugin:
    """What a plugin distribution exposes under the ``ableton_cli.plugins`` entry point."""

    name: str
    api_version: int
    #: Called once with an ``ableton_cli.plugin_api.PluginApi`` to declare commands.
    #: (Typed loosely so this module stays free of the runtime-importing API module.)
    register: Callable[[Any], None]
    description: str = ""
    #: Skill directories (each holding a SKILL.md) installed by ``install-skill``.
    skills: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class PluginDistribution:
    name: str
    version: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


class LoadFailure(StrEnum):
    INVALID_NAME = "invalid_name"
    RESERVED_NAME = "reserved_name"
    DUPLICATE_NAME = "duplicate_name"
    IMPORT_FAILED = "import_failed"
    NOT_A_PLUGIN = "not_a_plugin"
    NAME_MISMATCH = "name_mismatch"
    API_VERSION_MISMATCH = "api_version_mismatch"
    INVALID_SKILL = "invalid_skill"
    REGISTER_FAILED = "register_failed"
    NO_COMMANDS = "no_commands"


@dataclass(frozen=True, slots=True)
class LoadedPlugin:
    plugin: Plugin
    distribution: PluginDistribution | None
    commands: tuple[CommandDescriptor, ...]

    @property
    def name(self) -> str:
        return self.plugin.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.plugin.name,
            "state": "loaded",
            "description": self.plugin.description,
            "distribution": _distribution_dict(self.distribution),
            "commands": [
                {
                    "command": descriptor.command_name,
                    "side_effect": descriptor.side_effect.to_contract_metadata(),
                }
                for descriptor in self.commands
            ],
            "skills": [path.name for path in self.plugin.skills],
            "error": None,
        }


@dataclass(frozen=True, slots=True)
class FailedPlugin:
    name: str
    distribution: PluginDistribution | None
    reason: LoadFailure
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_error(self) -> AppError:
        if self.reason is LoadFailure.API_VERSION_MISMATCH:
            hint = (
                f"Update the plugin or ableton-cli so both use plugin API version "
                f"{PLUGIN_API_VERSION}, e.g. 'ableton-cli plugins update {self.name}'."
            )
        else:
            hint = (
                f"Fix or update the plugin ('ableton-cli plugins update {self.name}') "
                f"or remove it ('ableton-cli plugins uninstall {self.name}')."
            )
        return AppError(
            error_code=ErrorCode.PLUGIN_LOAD_FAILED,
            message=f"Plugin '{self.name}' failed to load: {self.message}",
            hint=hint,
            exit_code=ExitCode.EXECUTION_FAILED,
            details={"plugin": self.name, "load_failure": self.reason.value, **self.details},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": "failed",
            "description": None,
            "distribution": _distribution_dict(self.distribution),
            "commands": [],
            "skills": [],
            "error": self.to_error().to_payload(),
        }


@dataclass(frozen=True, slots=True)
class PluginLoadReport:
    """What the host loaded when the app was built; carried on ``RuntimeContext``."""

    enabled: bool
    loaded: tuple[LoadedPlugin, ...] = ()
    failed: tuple[FailedPlugin, ...] = ()
    #: Set when the plugin switch itself is misconfigured; every command fails with it.
    error: AppError | None = None

    def entries(self) -> list[dict[str, Any]]:
        items = [
            *(item.to_dict() for item in self.loaded),
            *(item.to_dict() for item in self.failed),
        ]
        return sorted(items, key=lambda item: item["name"])


def _distribution_dict(distribution: PluginDistribution | None) -> dict[str, str] | None:
    return None if distribution is None else distribution.to_dict()
