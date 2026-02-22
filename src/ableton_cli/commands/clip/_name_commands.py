from __future__ import annotations

from typing import Annotated

import typer

from .._validation import require_non_empty_string
from ._parsers import parse_clip_name_assignments
from ._shared import execute_clip_command, resolve_client, validate_track, validate_track_and_clip


def register_name_commands(name_app: typer.Typer) -> None:
    name_app.command("set")(clip_name_set)
    name_app.command("set-many")(clip_name_set_many)


def clip_name_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    name: Annotated[str, typer.Argument(help="New clip name")],
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        valid_name = require_non_empty_string("name", name, hint="Pass a non-empty clip name.")
        return resolve_client(ctx).set_clip_name(valid_track, valid_clip, valid_name)

    execute_clip_command(
        ctx,
        command="clip name set",
        args={"track": track, "clip": clip, "name": name},
        action=_run,
    )


def clip_name_set_many(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    map_: Annotated[
        str,
        typer.Option("--map", help="Comma-separated clip:name pairs (e.g. 1:Main,2:Var)"),
    ],
) -> None:
    def _run() -> dict[str, object]:
        valid_track = validate_track(track)
        assignments = parse_clip_name_assignments(map_)
        client = resolve_client(ctx)
        updated = [
            client.set_clip_name(track=valid_track, clip=clip_index, name=clip_name)
            for clip_index, clip_name in assignments
        ]
        return {
            "track": valid_track,
            "updated_count": len(updated),
            "updated": updated,
        }

    execute_clip_command(
        ctx,
        command="clip name set-many",
        args={"track": track, "map": map_},
        action=_run,
    )
