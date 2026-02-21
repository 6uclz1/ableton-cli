from __future__ import annotations

import typer

from ..runtime import execute_command, get_client

session_app = typer.Typer(help="Session information commands", no_args_is_help=True)


@session_app.command("info")
def session_info(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="session info",
        args={},
        action=lambda: get_client(ctx).get_session_info(),
    )


@session_app.command("snapshot")
def session_snapshot(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="session snapshot",
        args={},
        action=lambda: get_client(ctx).session_snapshot(),
    )


@session_app.command("stop-all-clips")
def session_stop_all_clips(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="session stop-all-clips",
        args={},
        action=lambda: get_client(ctx).stop_all_clips(),
    )


def register(app: typer.Typer) -> None:
    app.add_typer(session_app, name="session")
