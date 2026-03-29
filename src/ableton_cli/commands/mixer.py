from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._track_shared import PanningValueArgument, VolumeValueArgument
from ._validation import require_non_empty_string

MIXER_ROUTING_HINT = "Use one of the exact routing names returned by mixer cue-routing get."

mixer_app = typer.Typer(help="Mixer and cue commands", no_args_is_help=True)
crossfader_app = typer.Typer(help="Crossfader commands", no_args_is_help=True)
cue_volume_app = typer.Typer(help="Cue volume commands", no_args_is_help=True)
cue_routing_app = typer.Typer(help="Cue routing commands", no_args_is_help=True)


def _run_read_command(ctx: typer.Context, *, command_name: str, fn_name: str) -> None:
    execute_command(
        ctx,
        command=command_name,
        args={},
        action=lambda: getattr(get_client(ctx), fn_name)(),
    )


def _run_value_command(
    ctx: typer.Context,
    *,
    command_name: str,
    args: dict[str, object],
    fn,
) -> None:
    execute_command(
        ctx,
        command=command_name,
        args=args,
        action=lambda: fn(get_client(ctx)),
    )


@crossfader_app.command("get")
def mixer_crossfader_get(ctx: typer.Context) -> None:
    _run_read_command(ctx, command_name="mixer crossfader get", fn_name="mixer_crossfader_get")


@crossfader_app.command("set")
def mixer_crossfader_set(
    ctx: typer.Context,
    value: PanningValueArgument,
) -> None:
    _run_value_command(
        ctx,
        command_name="mixer crossfader set",
        args={"value": value},
        fn=lambda client: client.mixer_crossfader_set(value),
    )


@cue_volume_app.command("get")
def mixer_cue_volume_get(ctx: typer.Context) -> None:
    _run_read_command(ctx, command_name="mixer cue-volume get", fn_name="mixer_cue_volume_get")


@cue_volume_app.command("set")
def mixer_cue_volume_set(
    ctx: typer.Context,
    value: VolumeValueArgument,
) -> None:
    _run_value_command(
        ctx,
        command_name="mixer cue-volume set",
        args={"value": value},
        fn=lambda client: client.mixer_cue_volume_set(value),
    )


@cue_routing_app.command("get")
def mixer_cue_routing_get(ctx: typer.Context) -> None:
    _run_read_command(ctx, command_name="mixer cue-routing get", fn_name="mixer_cue_routing_get")


@cue_routing_app.command("set")
def mixer_cue_routing_set(
    ctx: typer.Context,
    routing: Annotated[str, typer.Argument(help="Cue routing name")],
) -> None:
    valid_routing = require_non_empty_string("routing", routing, hint=MIXER_ROUTING_HINT)
    _run_value_command(
        ctx,
        command_name="mixer cue-routing set",
        args={"routing": valid_routing},
        fn=lambda client: client.mixer_cue_routing_set(valid_routing),
    )


mixer_app.add_typer(crossfader_app, name="crossfader")
mixer_app.add_typer(cue_volume_app, name="cue-volume")
mixer_app.add_typer(cue_routing_app, name="cue-routing")


def register(app: typer.Typer) -> None:
    app.add_typer(mixer_app, name="mixer")
