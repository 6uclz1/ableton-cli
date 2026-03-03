from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._validation import require_minus_one_or_non_negative, require_non_negative

tracks_app = typer.Typer(help="Track collection commands", no_args_is_help=True)
create_app = typer.Typer(help="Track creation commands", no_args_is_help=True)


TracksCommandSpec = CommandSpec


TRACKS_LIST_SPEC = TracksCommandSpec(
    command_name="tracks list",
    client_method="tracks_list",
)
TRACKS_CREATE_MIDI_SPEC = TracksCommandSpec(
    command_name="tracks create midi",
    client_method="create_midi_track",
)
TRACKS_CREATE_AUDIO_SPEC = TracksCommandSpec(
    command_name="tracks create audio",
    client_method="create_audio_track",
)
TRACKS_DELETE_SPEC = TracksCommandSpec(
    command_name="tracks delete",
    client_method="tracks_delete",
)


def run_client_command(
    ctx: typer.Context,
    *,
    command_name: str,
    args: dict[str, object],
    fn: Callable[[object], dict[str, object]],
) -> None:
    run_client_command_shared(
        ctx,
        command_name=command_name,
        args=args,
        fn=fn,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: TracksCommandSpec,
    args: dict[str, object],
    method_kwargs: dict[str, object] | Callable[[], dict[str, object]] | None = None,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
        method_kwargs=method_kwargs,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


@tracks_app.command("list")
def tracks_list(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=TRACKS_LIST_SPEC,
        args={},
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
    def _method_kwargs() -> dict[str, object]:
        require_minus_one_or_non_negative(
            "index",
            index,
            hint="Use -1 for append or a non-negative insertion index.",
        )
        return {"index": index}

    run_client_command_spec(
        ctx,
        spec=TRACKS_CREATE_MIDI_SPEC,
        args={"index": index},
        method_kwargs=_method_kwargs,
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
    def _method_kwargs() -> dict[str, object]:
        require_minus_one_or_non_negative(
            "index",
            index,
            hint="Use -1 for append or a non-negative insertion index.",
        )
        return {"index": index}

    run_client_command_spec(
        ctx,
        spec=TRACKS_CREATE_AUDIO_SPEC,
        args={"index": index},
        method_kwargs=_method_kwargs,
    )


tracks_app.add_typer(create_app, name="create")


@tracks_app.command("delete")
def delete_track(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        require_non_negative("track", track, hint="Use a valid track index from 'tracks list'.")
        return {"track": track}

    run_client_command_spec(
        ctx,
        spec=TRACKS_DELETE_SPEC,
        args={"track": track},
        method_kwargs=_method_kwargs,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(tracks_app, name="tracks")
