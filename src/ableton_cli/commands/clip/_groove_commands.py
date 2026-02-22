from __future__ import annotations

from typing import Annotated

import typer

from ._shared import (
    execute_clip_command,
    execute_track_clip_command,
    require_float_in_range,
    require_uri_or_path_target,
    resolve_client,
    validate_track_and_clip,
)


def register_groove_commands(
    groove_app: typer.Typer,
    groove_amount_app: typer.Typer,
) -> None:
    groove_app.command("get")(clip_groove_get)
    groove_app.command("set")(clip_groove_set)
    groove_amount_app.command("set")(clip_groove_amount_set)
    groove_app.command("clear")(clip_groove_clear)


def clip_groove_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    execute_track_clip_command(
        ctx,
        command="clip groove get",
        args={"track": track, "clip": clip},
        track_clip=(track, clip),
        action=lambda client, valid_track, valid_clip: client.clip_groove_get(
            valid_track,
            valid_clip,
        ),
    )


def clip_groove_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    target: Annotated[str, typer.Argument(help="Groove target (URI or path to .agr)")],
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        valid_target = require_uri_or_path_target(target)
        return resolve_client(ctx).clip_groove_set(valid_track, valid_clip, valid_target)

    execute_clip_command(
        ctx,
        command="clip groove set",
        args={"track": track, "clip": clip, "target": target},
        action=_run,
    )


def clip_groove_amount_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    value: Annotated[float, typer.Argument(help="Groove amount in [0.0, 1.0]")],
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        valid_value = require_float_in_range(
            name="value",
            value=value,
            minimum=0.0,
            maximum=1.0,
            hint="Use a groove amount in the 0.0-1.0 range.",
        )
        return resolve_client(ctx).clip_groove_amount_set(valid_track, valid_clip, valid_value)

    execute_clip_command(
        ctx,
        command="clip groove amount set",
        args={"track": track, "clip": clip, "value": value},
        action=_run,
    )


def clip_groove_clear(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    execute_track_clip_command(
        ctx,
        command="clip groove clear",
        args={"track": track, "clip": clip},
        track_clip=(track, clip),
        action=lambda client, valid_track, valid_clip: client.clip_groove_clear(
            valid_track,
            valid_clip,
        ),
    )
