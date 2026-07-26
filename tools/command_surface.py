"""Characterization snapshot of the CLI surface (Typer/click option shapes).

``tests/snapshots/public_contract_snapshot.json`` captures the *contract*
(args/result/errors/side_effect) of every public command, but it says nothing
about how those commands are spelled on the command line. A refactor that
renamed ``--track-index`` to ``--track_index``, reordered two positional
arguments, or changed an option default would leave that snapshot untouched.

This module captures the missing half: for every command and group in the real
``ableton_cli.cli.app``, the parameter shapes and the rendered ``--help``.

It lives in ``tools/`` rather than ``src/`` because it must import
``ableton_cli.commands`` to walk the app, and it is test/tooling scaffolding
rather than product code.
"""

from __future__ import annotations

import contextlib
import io
from typing import Any

import click
from typer.main import get_command

SNAPSHOT_VERSION = 1

# Rendered help is only stable if rich is told exactly how wide the terminal is
# and that it is not talking to one. Without this the snapshot depends on
# COLUMNS/TERM in whatever shell happens to run the tests.
_RENDER_WIDTH = 100


def _json_safe(value: Any) -> Any:
    """Render a click default/envvar in a form that survives JSON round-trips."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    # Callable defaults and sentinels have no stable literal form; repr() at
    # least changes when the object changes.
    return repr(value)


def _param_type_record(param_type: click.ParamType) -> dict[str, Any]:
    record: dict[str, Any] = {
        "class": type(param_type).__name__,
        "name": param_type.name,
    }
    choices = getattr(param_type, "choices", None)
    if choices is not None:
        record["choices"] = [str(choice) for choice in choices]
    for attr in ("min", "max"):
        bound = getattr(param_type, attr, None)
        if bound is not None:
            record[attr] = _json_safe(bound)
    return record


def _param_record(param: click.Parameter) -> dict[str, Any]:
    record: dict[str, Any] = {
        "kind": param.param_type_name,
        "name": param.name,
        "opts": list(param.opts),
        "secondary_opts": list(param.secondary_opts),
        "type": _param_type_record(param.type),
        "required": bool(param.required),
        "default": _json_safe(param.default),
        "nargs": param.nargs,
        "multiple": bool(param.multiple),
        "metavar": param.metavar,
        "envvar": _json_safe(param.envvar),
        "expose_value": bool(param.expose_value),
    }
    if isinstance(param, click.Option):
        record.update(
            {
                "help": param.help,
                "is_flag": bool(param.is_flag),
                "flag_value": _json_safe(param.flag_value),
                "count": bool(param.count),
                "hidden": bool(param.hidden),
                "show_default": _json_safe(param.show_default),
                "prompt": _json_safe(param.prompt),
            }
        )
    else:
        # TyperArgument carries a help string that plain click.Argument lacks.
        record["help"] = getattr(param, "help", None)
    return record


def _render_help(command: click.Command, path: tuple[str, ...]) -> list[str]:
    """Capture ``--help`` exactly as a user would see it.

    Typer renders help through rich, which *prints* to stdout from inside
    ``get_help()`` instead of returning it, so stdout has to be captured too.
    """
    import rich.console
    import typer.rich_utils as rich_utils

    saved = (rich_utils.MAX_WIDTH, rich_utils.FORCE_TERMINAL, rich_utils.COLOR_SYSTEM)
    rich_utils.MAX_WIDTH = _RENDER_WIDTH
    rich_utils.FORCE_TERMINAL = False
    rich_utils.COLOR_SYSTEM = None
    # rich swaps the rounded panel box for a square one when it thinks it is on
    # a legacy Windows console, which would make this snapshot disagree between
    # macOS and Windows CI. Typer builds its Console without passing
    # legacy_windows, so pinning the detector is the only injection point.
    saved_detect = rich.console.detect_legacy_windows
    rich.console.detect_legacy_windows = lambda: False
    buffer = io.StringIO()
    try:
        ctx = click.Context(
            command,
            info_name=path[-1] if path else "ableton-cli",
            terminal_width=_RENDER_WIDTH,
            max_content_width=_RENDER_WIDTH,
        )
        with contextlib.redirect_stdout(buffer):
            returned = command.get_help(ctx)
    finally:
        rich_utils.MAX_WIDTH, rich_utils.FORCE_TERMINAL, rich_utils.COLOR_SYSTEM = saved
        rich.console.detect_legacy_windows = saved_detect

    text = buffer.getvalue() or returned
    return [line.rstrip() for line in text.rstrip().splitlines()]


def _command_record(command: click.Command, path: tuple[str, ...]) -> dict[str, Any]:
    return {
        "path": list(path),
        "kind": "group" if isinstance(command, click.Group) else "command",
        "help": command.help,
        "short_help": command.short_help,
        "hidden": bool(command.hidden),
        "deprecated": _json_safe(command.deprecated),
        "no_args_is_help": bool(getattr(command, "no_args_is_help", False)),
        "params": [_param_record(param) for param in command.params],
        "help_text": _render_help(command, path),
    }


def _walk(
    command: click.Command,
    path: tuple[str, ...],
    into: dict[str, dict[str, Any]],
) -> None:
    key = " ".join(path)
    if key in into:
        raise AssertionError(f"duplicate command path in CLI surface: {key!r}")
    record = _command_record(command, path)
    if isinstance(command, click.Group):
        # Declaration order is part of the surface: it is the order --help lists.
        record["subcommands"] = list(command.commands)
    into[key] = record
    if isinstance(command, click.Group):
        for name, child in command.commands.items():
            _walk(child, (*path, name), into)


def build_command_surface_snapshot() -> dict[str, Any]:
    """Walk the real CLI app and describe every command's command-line shape."""
    from ableton_cli.cli import app

    root = get_command(app)
    commands: dict[str, dict[str, Any]] = {}
    _walk(root, (), commands)
    root_record = commands.pop("")
    return {
        "version": SNAPSHOT_VERSION,
        "root": root_record,
        "commands": {key: commands[key] for key in sorted(commands)},
    }
