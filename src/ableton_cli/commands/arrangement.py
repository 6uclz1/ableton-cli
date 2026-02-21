from __future__ import annotations

import typer

from ..runtime import execute_command, get_client

arrangement_app = typer.Typer(help="Arrangement commands", no_args_is_help=True)
record_app = typer.Typer(help="Arrangement recording commands", no_args_is_help=True)


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


arrangement_app.add_typer(record_app, name="record")


def register(app: typer.Typer) -> None:
    app.add_typer(arrangement_app, name="arrangement")
