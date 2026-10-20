"""Offline Live Set (``.als``) commands.

These read set files directly and never contact Live or the Remote Script.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..liveset.diff import diff_live_sets
from ..liveset.document import load_live_set
from ..liveset.inspect import inspect_live_set
from ..liveset.lint import lint_live_set, require_no_errors
from ..runtime import execute_command

set_app = typer.Typer(help="Offline Live Set (.als) file commands", no_args_is_help=True)

SetPathOption = Annotated[Path, typer.Option("--path", help="Live Set (.als) path")]


@set_app.command("inspect")
def set_inspect(ctx: typer.Context, path: SetPathOption) -> None:
    execute_command(
        ctx,
        command="set inspect",
        args={"path": str(path)},
        action=lambda: inspect_live_set(load_live_set(path)),
    )


@set_app.command("lint")
def set_lint(ctx: typer.Context, path: SetPathOption) -> None:
    execute_command(
        ctx,
        command="set lint",
        args={"path": str(path)},
        action=lambda: require_no_errors(lint_live_set(load_live_set(path))),
    )


@set_app.command("diff")
def set_diff(
    ctx: typer.Context,
    from_path: Annotated[Path, typer.Option("--from", help="Earlier Live Set (.als) path")],
    to_path: Annotated[Path, typer.Option("--to", help="Later Live Set (.als) path")],
) -> None:
    execute_command(
        ctx,
        command="set diff",
        args={"from": str(from_path), "to": str(to_path)},
        action=lambda: diff_live_sets(load_live_set(from_path), load_live_set(to_path)),
    )


def register(app: typer.Typer) -> None:
    app.add_typer(set_app, name="set")
