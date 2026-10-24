"""The interface ableton-cli offers to plugins.

A plugin is a Python distribution exposing a ``Plugin`` under the
``ableton_cli.plugins`` entry-point group. Its ``register`` callback receives a
``PluginApi``, declares commands with ``PluginApi.command`` and runs them with
``PluginApi.run``, which gives every plugin command the core JSON envelope,
exit codes, ``--plan``/``--dry-run``, ``--read-only`` and
``--require-confirmation`` handling.

Everything exported here is a public contract versioned by
``PLUGIN_API_VERSION``. Plugins must not import any other ``ableton_cli``
module: those may change without notice.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

import typer

from ..command_registry import _DESTRUCTIVE, _READ, _WRITE, CommandDescriptor, SideEffectSpec
from ..errors import AppError, ExitCode, read_only_violation
from ..plugins.model import ENTRY_POINT_GROUP, PLUGIN_API_VERSION, Plugin
from ..runtime import execute_command, get_runtime

__all__ = [
    "DESTRUCTIVE",
    "ENTRY_POINT_GROUP",
    "PLUGIN_API_VERSION",
    "READ",
    "WRITE",
    "ExitCode",
    "Live",
    "Plugin",
    "PluginApi",
    "SideEffectSpec",
]

READ: SideEffectSpec = _READ
WRITE: SideEffectSpec = _WRITE
DESTRUCTIVE: SideEffectSpec = _DESTRUCTIVE

_COMMAND_SEGMENT = re.compile(r"^[a-z][a-z0-9-]*$")
_ERROR_CODE_SUFFIX = re.compile(r"^[A-Z][A-Z0-9_]*$")


class Live:
    """The connection to Ableton Live handed to a plugin command's action.

    ``request`` sends one Remote Script command over the documented TCP JSONL
    protocol (the same names ``batch`` steps use) and returns its ``result``.
    The connection opens on the first request, so actions that never talk to
    Live never need it running.
    """

    def __init__(self, send: Callable[[str, dict[str, Any] | None], dict[str, Any]]) -> None:
        self._send = send

    def request(self, name: str, args: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self._send(name, None if args is None else dict(args))


class PluginApi:
    """Handed to ``Plugin.register``; every command of the plugin goes through it."""

    def __init__(self, plugin_name: str, app: typer.Typer) -> None:
        self.plugin_name = plugin_name
        self._groups: dict[tuple[str, ...], typer.Typer] = {(): app}
        self._descriptors: dict[str, CommandDescriptor] = {}

    @property
    def descriptors(self) -> tuple[CommandDescriptor, ...]:
        return tuple(sorted(self._descriptors.values(), key=lambda item: item.command_name))

    def command(
        self,
        name: str,
        *,
        side_effect: SideEffectSpec,
        help: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Declare ``ableton-cli <plugin> <name>``; ``name`` may hold spaces for subgroups.

        ``side_effect`` is mandatory for the same reason it is in the core
        command table: it decides what ``--read-only`` and
        ``--require-confirmation`` let through.
        """
        path = tuple(name.split())
        if not path or any(_COMMAND_SEGMENT.fullmatch(segment) is None for segment in path):
            raise ValueError(
                f"Invalid command name {name!r}: use lowercase words separated by spaces"
            )
        command_name = " ".join((self.plugin_name, *path))
        if command_name in self._descriptors:
            raise ValueError(f"Command {command_name!r} is declared twice")
        self._descriptors[command_name] = CommandDescriptor(
            command_name=command_name,
            remote_command=None,
            side_effect=side_effect,
        )
        return self._group(path[:-1]).command(path[-1], help=help)

    def run(
        self,
        ctx: typer.Context,
        *,
        args: dict[str, Any],
        action: Callable[[Live], dict[str, Any]],
        human_formatter: Callable[[dict[str, Any]], str] | None = None,
    ) -> None:
        """Run the current command's ``action`` under the core execution rules."""
        command_name = _command_name(ctx)
        descriptor = self._descriptors.get(command_name)
        if descriptor is None:
            raise RuntimeError(f"{command_name!r} was not declared with PluginApi.command")
        runtime = get_runtime(ctx)

        def _action() -> dict[str, Any]:
            if runtime.read_only and descriptor.side_effect.kind != "read":
                raise read_only_violation(command_name)
            return action(
                Live(lambda name, payload: runtime.client().execute_remote_command(name, payload))
            )

        execute_command(
            ctx,
            command=command_name,
            args=args,
            action=_action,
            human_formatter=human_formatter,
            descriptor=descriptor,
        )

    def error(
        self,
        code: str,
        message: str,
        *,
        hint: str | None = None,
        exit_code: ExitCode = ExitCode.EXECUTION_FAILED,
        details: Mapping[str, Any] | None = None,
    ) -> AppError:
        """Build an error to raise from an action; ``code`` is prefixed with the plugin name.

        ``error("GENERATION_FAILED", ...)`` from plugin ``ace-step`` reports
        ``ACE_STEP_GENERATION_FAILED``, so plugin codes can never collide with
        core codes or with each other.
        """
        if _ERROR_CODE_SUFFIX.fullmatch(code) is None:
            raise ValueError(f"Invalid error code {code!r}: use UPPER_SNAKE_CASE")
        if exit_code is ExitCode.SUCCESS:
            raise ValueError("An error cannot exit with ExitCode.SUCCESS")
        prefix = self.plugin_name.upper().replace("-", "_")
        return AppError(
            error_code=f"{prefix}_{code}",
            message=message,
            hint=hint,
            exit_code=exit_code,
            details=dict(details or {}),
        )

    def _group(self, path: tuple[str, ...]) -> typer.Typer:
        group = self._groups.get(path)
        if group is None:
            group = typer.Typer(no_args_is_help=True)
            self._group(path[:-1]).add_typer(group, name=path[-1])
            self._groups[path] = group
        return group


def _command_name(ctx: typer.Context) -> str:
    """``"<plugin> <sub> <command>"``: every context name below the root ``ableton-cli``."""
    names: list[str] = []
    current = ctx
    while current.parent is not None:
        names.append(current.info_name or "")
        current = current.parent
    return " ".join(reversed(names))
