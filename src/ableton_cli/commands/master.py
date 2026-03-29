from __future__ import annotations

import typer

from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared

master_app = typer.Typer(help="Master track commands", no_args_is_help=True)
volume_app = typer.Typer(help="Master volume commands", no_args_is_help=True)
panning_app = typer.Typer(help="Master panning commands", no_args_is_help=True)
devices_app = typer.Typer(help="Master device commands", no_args_is_help=True)

MASTER_INFO_SPEC = CommandSpec(command_name="master info", client_method="master_info")
MASTER_VOLUME_GET_SPEC = CommandSpec(
    command_name="master volume get",
    client_method="master_volume_get",
)
MASTER_PANNING_GET_SPEC = CommandSpec(
    command_name="master panning get",
    client_method="master_panning_get",
)
MASTER_DEVICES_LIST_SPEC = CommandSpec(
    command_name="master devices list",
    client_method="master_devices_list",
)


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: CommandSpec,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args={},
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


@master_app.command("info")
def master_info(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_INFO_SPEC)


@volume_app.command("get")
def master_volume_get(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_VOLUME_GET_SPEC)


@panning_app.command("get")
def master_panning_get(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_PANNING_GET_SPEC)


@devices_app.command("list")
def master_devices_list(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_DEVICES_LIST_SPEC)


master_app.add_typer(volume_app, name="volume")
master_app.add_typer(panning_app, name="panning")
master_app.add_typer(devices_app, name="devices")


def register(app: typer.Typer) -> None:
    app.add_typer(master_app, name="master")
