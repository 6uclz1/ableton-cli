from __future__ import annotations

import typer

from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared

return_tracks_app = typer.Typer(help="Return track collection commands", no_args_is_help=True)

RETURN_TRACKS_LIST_SPEC = CommandSpec(
    command_name="return-tracks list",
    client_method="return_tracks_list",
)


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: CommandSpec,
    args: dict[str, object],
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
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


def register(app: typer.Typer) -> None:
    app.add_typer(return_tracks_app, name="return-tracks")
