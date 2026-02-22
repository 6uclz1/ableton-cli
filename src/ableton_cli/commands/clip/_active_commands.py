from __future__ import annotations

from typing import Annotated

import typer

from ._shared import (
    execute_clip_command,
    execute_track_clip_command,
    resolve_client,
    validate_track_and_clip,
)


def register_active_commands(active_app: typer.Typer) -> None:
    active_app.command("get")(clip_active_get)
    active_app.command("set")(clip_active_set)


def clip_active_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    execute_track_clip_command(
        ctx,
        command="clip active get",
        args={"track": track, "clip": clip},
        track_clip=(track, clip),
        action=lambda client, valid_track, valid_clip: client.clip_active_get(
            valid_track,
            valid_clip,
        ),
    )


def clip_active_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    value: Annotated[bool, typer.Argument(help="Active value: true|false")],
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        return resolve_client(ctx).clip_active_set(valid_track, valid_clip, value)

    execute_clip_command(
        ctx,
        command="clip active set",
        args={"track": track, "clip": clip, "value": value},
        action=_run,
    )
