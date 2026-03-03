from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._validation import require_non_negative

device_app = typer.Typer(help="Device commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Device parameter commands", no_args_is_help=True)


DeviceCommandSpec = CommandSpec


DEVICE_PARAMETER_SET_SPEC = DeviceCommandSpec(
    command_name="device parameter set",
    client_method="set_device_parameter",
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
    spec: DeviceCommandSpec,
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


@parameter_app.command("set")
def set_device_parameter(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    device: Annotated[int, typer.Argument(help="Device index (0-based)")],
    parameter: Annotated[int, typer.Argument(help="Parameter index (0-based)")],
    value: Annotated[float, typer.Argument(help="Target parameter value")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
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
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "value": value,
        }

    run_client_command_spec(
        ctx,
        spec=DEVICE_PARAMETER_SET_SPEC,
        args={
            "track": track,
            "device": device,
            "parameter": parameter,
            "value": value,
        },
        method_kwargs=_method_kwargs,
    )


device_app.add_typer(parameter_app, name="parameter")


def register(app: typer.Typer) -> None:
    app.add_typer(device_app, name="device")
