from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    require_absolute_path,
    require_non_negative,
    require_non_negative_float,
    require_positive_float,
)

arrangement_app = typer.Typer(help="Arrangement commands", no_args_is_help=True)
record_app = typer.Typer(help="Arrangement recording commands", no_args_is_help=True)
clip_app = typer.Typer(help="Arrangement clip commands", no_args_is_help=True)


@record_app.command("start")
def arrangement_record_start(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="arrangement record start",
        args={},
        action=lambda: get_client(ctx).arrangement_record_start(),
    )


@record_app.command("stop")
def arrangement_record_stop(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="arrangement record stop",
        args={},
        action=lambda: get_client(ctx).arrangement_record_stop(),
    )


@clip_app.command("create")
def arrangement_clip_create(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    start: Annotated[
        float,
        typer.Option(
            "--start",
            help="Arrangement start time in beats",
        ),
    ],
    length: Annotated[
        float,
        typer.Option(
            "--length",
            help="Arrangement clip length in beats",
        ),
    ],
    audio_path: Annotated[
        str | None,
        typer.Option(
            "--audio-path",
            help="Absolute audio file path for audio tracks",
        ),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative_float(
            "start",
            start,
            hint="Use a non-negative --start value in beats.",
        )
        require_positive_float(
            "length",
            length,
            hint="Use a positive --length value in beats.",
        )
        normalized_audio_path = (
            require_absolute_path(
                "audio_path",
                audio_path,
                hint="Pass an absolute file path for --audio-path.",
            )
            if audio_path is not None
            else None
        )
        return get_client(ctx).arrangement_clip_create(
            track=track,
            start_time=start,
            length=length,
            audio_path=normalized_audio_path,
        )

    execute_command(
        ctx,
        command="arrangement clip create",
        args={
            "track": track,
            "start_time": start,
            "length": length,
            "audio_path": audio_path,
        },
        action=_run,
    )


@clip_app.command("list")
def arrangement_clip_list(
    ctx: typer.Context,
    track: Annotated[
        int | None,
        typer.Option(
            "--track",
            help="Optional track index filter (0-based)",
        ),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        if track is not None:
            require_non_negative(
                "track",
                track,
                hint="Use a valid track index from 'ableton-cli tracks list'.",
            )
        return get_client(ctx).arrangement_clip_list(track=track)

    execute_command(
        ctx,
        command="arrangement clip list",
        args={"track": track},
        action=_run,
    )


arrangement_app.add_typer(record_app, name="record")
arrangement_app.add_typer(clip_app, name="clip")


def register(app: typer.Typer) -> None:
    app.add_typer(arrangement_app, name="arrangement")
