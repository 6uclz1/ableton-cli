from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import require_non_empty_string

song_app = typer.Typer(help="Song and session information", no_args_is_help=True)
song_export_app = typer.Typer(help="Song export commands", no_args_is_help=True)


@song_app.command("info")
def song_info(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="song info",
        args={},
        action=lambda: get_client(ctx).song_info(),
    )


@song_app.command("new")
def song_new(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="song new",
        args={},
        action=lambda: get_client(ctx).song_new(),
    )


@song_app.command("save")
def song_save(
    ctx: typer.Context,
    path: Annotated[str, typer.Option("--path", help="Destination .als path")],
) -> None:
    def _run() -> dict[str, object]:
        valid_path = require_non_empty_string(
            "path",
            path,
            hint="Pass a non-empty --path for the destination .als file.",
        )
        return get_client(ctx).song_save(valid_path)

    execute_command(
        ctx,
        command="song save",
        args={"path": path},
        action=_run,
    )


@song_export_app.command("audio")
def song_export_audio(
    ctx: typer.Context,
    path: Annotated[str, typer.Option("--path", help="Destination audio path (for example .wav)")],
) -> None:
    def _run() -> dict[str, object]:
        valid_path = require_non_empty_string(
            "path",
            path,
            hint="Pass a non-empty --path for exported audio.",
        )
        return get_client(ctx).song_export_audio(valid_path)

    execute_command(
        ctx,
        command="song export audio",
        args={"path": path},
        action=_run,
    )


song_app.add_typer(song_export_app, name="export")


def register(app: typer.Typer) -> None:
    app.add_typer(song_app, name="song")
