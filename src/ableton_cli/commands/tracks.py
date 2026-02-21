from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import require_minus_one_or_non_negative, require_non_negative

tracks_app = typer.Typer(help="Track collection commands", no_args_is_help=True)
create_app = typer.Typer(help="Track creation commands", no_args_is_help=True)


@tracks_app.command("list")
def tracks_list(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="tracks list",
        args={},
        action=lambda: get_client(ctx).tracks_list(),
    )


@create_app.command("midi")
def create_midi_track(
    ctx: typer.Context,
    index: Annotated[
        int,
        typer.Option(
            "--index",
            help="Insertion index. Use -1 to append.",
        ),
    ] = -1,
) -> None:
    def _run() -> dict[str, object]:
        require_minus_one_or_non_negative(
            "index",
            index,
            hint="Use -1 for append or a non-negative insertion index.",
        )
        return get_client(ctx).create_midi_track(index)

    execute_command(
        ctx,
        command="tracks create midi",
        args={"index": index},
        action=_run,
    )


@create_app.command("audio")
def create_audio_track(
    ctx: typer.Context,
    index: Annotated[
        int,
        typer.Option(
            "--index",
            help="Insertion index. Use -1 to append.",
        ),
    ] = -1,
) -> None:
    def _run() -> dict[str, object]:
        require_minus_one_or_non_negative(
            "index",
            index,
            hint="Use -1 for append or a non-negative insertion index.",
        )
        return get_client(ctx).create_audio_track(index)

    execute_command(
        ctx,
        command="tracks create audio",
        args={"index": index},
        action=_run,
    )


tracks_app.add_typer(create_app, name="create")


@tracks_app.command("delete")
def delete_track(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative("track", track, hint="Use a valid track index from 'tracks list'.")
        return get_client(ctx).tracks_delete(track)

    execute_command(
        ctx,
        command="tracks delete",
        args={"track": track},
        action=_run,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(tracks_app, name="tracks")
