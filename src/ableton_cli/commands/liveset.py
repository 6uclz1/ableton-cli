"""Offline Live Set (``.als``) commands.

These read set files directly and never contact Live or the Remote Script.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from ..errors import read_only_violation
from ..liveset.diff import diff_live_sets
from ..liveset.document import load_live_set
from ..liveset.inspect import inspect_live_set
from ..liveset.lint import lint_live_set, require_no_errors
from ..liveset.ops.automation import AutomationScope, write_automation
from ..liveset.save import require_new_output, save_live_set
from ..runtime import execute_command, get_runtime
from ._validation import invalid_argument, parse_envelope_points_json

set_app = typer.Typer(help="Offline Live Set (.als) file commands", no_args_is_help=True)
automation_app = typer.Typer(help="Arrangement automation lanes", no_args_is_help=True)
set_app.add_typer(automation_app, name="automation")

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


def _automation_scope(
    track_index: int | None, track_name: str | None, return_track_index: int | None, main: bool
) -> AutomationScope:
    chosen = [
        option
        for option, given in (
            ("--track-index", track_index is not None),
            ("--track-name", track_name is not None),
            ("--return-track-index", return_track_index is not None),
            ("--main", main),
        )
        if given
    ]
    if len(chosen) != 1:
        raise invalid_argument(
            message=f"Pass exactly one track selector, got {chosen or 'none'}",
            hint="Use one of --track-index, --track-name, --return-track-index or --main.",
        )
    if main:
        return AutomationScope("main")
    if return_track_index is not None:
        return AutomationScope("return", index=return_track_index)
    return AutomationScope("track", index=track_index, name=track_name)


@automation_app.command("write")
def set_automation_write(
    ctx: typer.Context,
    path: SetPathOption,
    out: Annotated[Path, typer.Option("--out", help="New Live Set (.als) path to write")],
    target: Annotated[
        str,
        typer.Option(
            "--target",
            help="mixer.volume | mixer.pan | mixer.tempo | send.<index> | device.<index>.<Tag>",
        ),
    ],
    points_json: Annotated[
        str, typer.Option("--points-json", help='JSON array of {"time","value"} breakpoints')
    ],
    track_index: Annotated[
        int | None, typer.Option("--track-index", min=0, help="Regular track index")
    ] = None,
    track_name: Annotated[str | None, typer.Option("--track-name", help="Track name")] = None,
    return_track_index: Annotated[
        int | None, typer.Option("--return-track-index", min=0, help="Return track index")
    ] = None,
    main: Annotated[bool, typer.Option("--main", help="Target the main track")] = False,
) -> None:
    command = "set automation write"

    def _run() -> dict[str, Any]:
        if get_runtime(ctx).read_only:
            raise read_only_violation(command)
        scope = _automation_scope(track_index, track_name, return_track_index, main)
        points = parse_envelope_points_json(points_json)
        require_new_output(path, out)
        document = load_live_set(path)
        summary = write_automation(document, scope, target, points)
        save_live_set(document, out)
        return {"path": str(path), "out": str(out), **summary}

    execute_command(
        ctx,
        command=command,
        args={
            "path": str(path),
            "out": str(out),
            "target": target,
            "track_index": track_index,
            "track_name": track_name,
            "return_track_index": return_track_index,
            "main": main,
        },
        action=_run,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(set_app, name="set")
