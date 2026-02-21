from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import require_non_negative

device_app = typer.Typer(help="Device commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Device parameter commands", no_args_is_help=True)


@parameter_app.command("set")
def set_device_parameter(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    device: Annotated[int, typer.Argument(help="Device index (0-based)")],
    parameter: Annotated[int, typer.Argument(help="Parameter index (0-based)")],
    value: Annotated[float, typer.Argument(help="Target parameter value")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "device",
            device,
            hint="Use a valid device index from 'ableton-cli track info'.",
        )
        require_non_negative(
            "parameter",
            parameter,
            hint="Use a valid parameter index from 'ableton-cli track info'.",
        )
        return get_client(ctx).set_device_parameter(track, device, parameter, value)

    execute_command(
        ctx,
        command="device parameter set",
        args={
            "track": track,
            "device": device,
            "parameter": parameter,
            "value": value,
        },
        action=_run,
    )


device_app.add_typer(parameter_app, name="parameter")


def register(app: typer.Typer) -> None:
    app.add_typer(device_app, name="device")
