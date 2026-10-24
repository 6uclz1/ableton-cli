"""Discover plugins, validate them and mount their commands on the app.

A plugin that fails any check is not mounted. If its name is usable, a stub
takes its place so that calling it fails with ``PLUGIN_LOAD_FAILED`` and the
reason, instead of click's generic "No such command". Core commands never
depend on a plugin loading.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from typing import Any

import typer

from ..command_registry import _READ, CommandDescriptor
from ..errors import AppError, ErrorCode, ExitCode
from ..plugin_api import PluginApi
from ..runtime import execute_command
from .model import (
    ENTRY_POINT_GROUP,
    PLUGIN_API_VERSION,
    FailedPlugin,
    LoadedPlugin,
    LoadFailure,
    Plugin,
    PluginDistribution,
    PluginLoadReport,
)

PLUGINS_SWITCH_ENV = "ABLETON_CLI_PLUGINS"
PLUGIN_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
SKILL_FILE_NAME = "SKILL.md"


@dataclass(frozen=True, slots=True)
class PluginSource:
    """One entry point to load; tests build these directly instead of installing."""

    name: str
    load: Callable[[], object]
    distribution: PluginDistribution | None = None


class _LoadError(Exception):
    def __init__(self, reason: LoadFailure, message: str, **details: Any) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.details = details


def plugins_enabled(env: Mapping[str, str]) -> bool:
    value = env.get(PLUGINS_SWITCH_ENV, "on")
    if value not in ("on", "off"):
        raise AppError(
            error_code=ErrorCode.CONFIG_INVALID,
            message=f"Invalid {PLUGINS_SWITCH_ENV} value: {value!r}",
            hint=f"Set {PLUGINS_SWITCH_ENV} to 'on' or 'off', or unset it.",
            exit_code=ExitCode.CONFIG_INVALID,
        )
    return value == "on"


def discover_plugin_sources() -> tuple[PluginSource, ...]:
    found = sorted(entry_points(group=ENTRY_POINT_GROUP), key=lambda ep: (ep.name, ep.value))
    return tuple(_source_from_entry_point(entry_point) for entry_point in found)


def load_plugins(
    app: typer.Typer,
    *,
    sources: Iterable[PluginSource] | None,
    env: Mapping[str, str],
    reserved_names: Collection[str],
) -> PluginLoadReport:
    """Mount every plugin on ``app`` unless ``ABLETON_CLI_PLUGINS=off``.

    ``sources=None`` means "discover installed entry points".
    """
    try:
        enabled = plugins_enabled(env)
    except AppError as exc:
        return PluginLoadReport(enabled=False, error=exc)
    if not enabled:
        return PluginLoadReport(enabled=False)
    resolved = discover_plugin_sources() if sources is None else tuple(sources)
    return mount_plugins(app, resolved, reserved_names=reserved_names)


def mount_plugins(
    app: typer.Typer,
    sources: Iterable[PluginSource],
    *,
    reserved_names: Collection[str],
) -> PluginLoadReport:
    by_name: dict[str, list[PluginSource]] = {}
    for source in sources:
        by_name.setdefault(source.name, []).append(source)

    loaded: list[LoadedPlugin] = []
    failed: list[FailedPlugin] = []
    for name in sorted(by_name):
        outcome = _mount_one(app, name, by_name[name], reserved_names=reserved_names)
        (loaded if isinstance(outcome, LoadedPlugin) else failed).append(outcome)
    return PluginLoadReport(enabled=True, loaded=tuple(loaded), failed=tuple(failed))


def _mount_one(
    app: typer.Typer,
    name: str,
    candidates: list[PluginSource],
    *,
    reserved_names: Collection[str],
) -> LoadedPlugin | FailedPlugin:
    try:
        if len(candidates) > 1:
            raise _LoadError(
                LoadFailure.DUPLICATE_NAME,
                f"{len(candidates)} installed distributions provide a plugin named {name!r}",
                distributions=[_distribution_label(item) for item in candidates],
            )
        return _load(app, candidates[0], reserved_names=reserved_names)
    except _LoadError as exc:
        failure = FailedPlugin(
            name=name,
            distribution=candidates[0].distribution if len(candidates) == 1 else None,
            reason=exc.reason,
            message=exc.message,
            details=exc.details,
        )
    if failure.reason not in (LoadFailure.INVALID_NAME, LoadFailure.RESERVED_NAME):
        _mount_failure_stub(app, failure)
    return failure


def _load(
    app: typer.Typer, source: PluginSource, *, reserved_names: Collection[str]
) -> LoadedPlugin:
    plugin = _resolve_plugin(source, reserved_names=reserved_names)
    plugin_app = typer.Typer(help=plugin.description or None, no_args_is_help=True)
    api = PluginApi(plugin.name, plugin_app)
    try:
        plugin.register(api)
    except Exception as exc:  # noqa: BLE001 - a broken plugin must not take the CLI down
        raise _LoadError(LoadFailure.REGISTER_FAILED, f"{type(exc).__name__}: {exc}") from exc
    if not api.descriptors:
        raise _LoadError(LoadFailure.NO_COMMANDS, "register() declared no commands")
    app.add_typer(plugin_app, name=plugin.name, help=plugin.description or None)
    return LoadedPlugin(plugin=plugin, distribution=source.distribution, commands=api.descriptors)


def _resolve_plugin(source: PluginSource, *, reserved_names: Collection[str]) -> Plugin:
    """Check the name, import the entry point and check what it returned."""
    name = source.name
    if PLUGIN_NAME_PATTERN.fullmatch(name) is None:
        raise _LoadError(
            LoadFailure.INVALID_NAME,
            f"plugin name {name!r} must match {PLUGIN_NAME_PATTERN.pattern}",
        )
    if name in reserved_names:
        raise _LoadError(LoadFailure.RESERVED_NAME, f"{name!r} is a core ableton-cli command group")
    try:
        plugin = source.load()
    except Exception as exc:  # noqa: BLE001 - any import failure is reported, never raised
        raise _LoadError(LoadFailure.IMPORT_FAILED, f"{type(exc).__name__}: {exc}") from exc
    if not isinstance(plugin, Plugin):
        raise _LoadError(
            LoadFailure.NOT_A_PLUGIN,
            f"entry point resolved to {type(plugin).__name__}, not ableton_cli.plugin_api.Plugin",
        )
    if plugin.name != name:
        raise _LoadError(
            LoadFailure.NAME_MISMATCH,
            f"entry point is named {name!r} but the plugin calls itself {plugin.name!r}",
        )
    if plugin.api_version != PLUGIN_API_VERSION:
        raise _LoadError(
            LoadFailure.API_VERSION_MISMATCH,
            f"plugin targets API version {plugin.api_version}, host provides {PLUGIN_API_VERSION}",
            plugin_api_version=plugin.api_version,
            host_api_version=PLUGIN_API_VERSION,
        )
    _validate_skills(plugin)
    return plugin


def _validate_skills(plugin: Plugin) -> None:
    for skill_dir in plugin.skills:
        path = Path(skill_dir)
        if path.name != plugin.name and not path.name.startswith(f"{plugin.name}-"):
            raise _LoadError(
                LoadFailure.INVALID_SKILL,
                f"skill directory {path.name!r} must be named {plugin.name!r} "
                f"or start with {plugin.name + '-'!r}",
            )
        if not (path / SKILL_FILE_NAME).is_file():
            raise _LoadError(
                LoadFailure.INVALID_SKILL, f"skill directory {path.name!r} has no {SKILL_FILE_NAME}"
            )


def _mount_failure_stub(app: typer.Typer, failure: FailedPlugin) -> None:
    descriptor = CommandDescriptor(
        command_name=failure.name, remote_command=None, side_effect=_READ
    )

    @app.command(
        failure.name,
        help=f"(failed to load) {failure.message}",
        add_help_option=False,
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def _failed_plugin(ctx: typer.Context) -> None:
        def _fail() -> dict[str, Any]:
            raise failure.to_error()

        # resolved_args raises too, so --plan and --dry-run fail the same way.
        execute_command(
            ctx,
            command=failure.name,
            args={"argv": list(ctx.args)},
            action=_fail,
            resolved_args=_fail,
            descriptor=descriptor,
        )


def _source_from_entry_point(entry_point: EntryPoint) -> PluginSource:
    dist = entry_point.dist
    distribution = (
        None
        if dist is None
        else PluginDistribution(name=dist.metadata["Name"], version=dist.version)
    )
    return PluginSource(name=entry_point.name, load=entry_point.load, distribution=distribution)


def _distribution_label(source: PluginSource) -> str | None:
    if source.distribution is None:
        return None
    return f"{source.distribution.name}=={source.distribution.version}"
