from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared

return_tracks_app = typer.Typer(help="Return track collection commands", no_args_is_help=True)

RETURN_TRACKS_LIST_SPEC = CommandSpec(
    command_name="return-tracks list",
    client_method="return_tracks_list",
)

RETURN_TRACKS_CREATE_SPEC = CommandSpec(
    command_name="return-tracks create",
    client_method="return_track_create",
)
RETURN_TRACKS_DELETE_SPEC = CommandSpec(
    command_name="return-tracks delete",
    client_method="return_track_delete",
)


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: CommandSpec,
    args: dict[str, object],
    method_kwargs: dict[str, object] | None = None,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
        method_kwargs=method_kwargs,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


@return_tracks_app.command("list")
def return_tracks_list(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=RETURN_TRACKS_LIST_SPEC,
        args={},
    )


@return_tracks_app.command("create")
def return_tracks_create(ctx: typer.Context) -> None:
    """Append a new return track."""
    run_client_command_spec(ctx, spec=RETURN_TRACKS_CREATE_SPEC, args={})


@return_tracks_app.command("delete")
def return_tracks_delete(
    ctx: typer.Context,
    return_track: Annotated[int, typer.Argument(help="Return track index (0-based)")],
) -> None:
    """Delete a return track by index."""
    run_client_command_spec(
        ctx,
        spec=RETURN_TRACKS_DELETE_SPEC,
        args={"return_track": return_track},
        method_kwargs={"return_track": return_track},
    )


def register(app: typer.Typer) -> None:
    app.add_typer(return_tracks_app, name="return-tracks")
