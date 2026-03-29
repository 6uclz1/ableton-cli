from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..refs import (
    DeviceIndexOption,
    DeviceNameOption,
    DeviceQueryOption,
    DeviceStableRefOption,
    ParameterIndexOption,
    ParameterKeyOption,
    ParameterNameOption,
    ParameterQueryOption,
    ParameterStableRefOption,
    SelectedDeviceOption,
    SelectedTrackOption,
    TrackIndexOption,
    TrackNameOption,
    TrackQueryOption,
    TrackStableRefOption,
    build_device_ref,
    build_parameter_ref,
    build_track_ref,
)
from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared

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
    resolved_args: Callable[[], dict[str, object]] | None = None,
) -> None:
    run_client_command_shared(
        ctx,
        command_name=command_name,
        args=args,
        fn=fn,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
        resolved_args=resolved_args,
    )


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: DeviceCommandSpec,
    args: dict[str, object],
    method_kwargs: dict[str, object] | Callable[[], dict[str, object]] | None = None,
    resolved_args: Callable[[], dict[str, object]] | None = None,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
        method_kwargs=method_kwargs,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
        resolved_args=resolved_args,
    )


@parameter_app.command("set")
def set_device_parameter(
    ctx: typer.Context,
    value: Annotated[float, typer.Argument(help="Target parameter value")],
    track_index: TrackIndexOption = None,
    track_name: TrackNameOption = None,
    selected_track: SelectedTrackOption = False,
    track_query: TrackQueryOption = None,
    track_ref: TrackStableRefOption = None,
    device_index: DeviceIndexOption = None,
    device_name: DeviceNameOption = None,
    selected_device: SelectedDeviceOption = False,
    device_query: DeviceQueryOption = None,
    device_ref: DeviceStableRefOption = None,
    parameter_index: ParameterIndexOption = None,
    parameter_name: ParameterNameOption = None,
    parameter_query: ParameterQueryOption = None,
    parameter_key: ParameterKeyOption = None,
    parameter_ref: ParameterStableRefOption = None,
) -> None:
    def _resolved_refs() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        return (
            build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            build_device_ref(
                device_index=device_index,
                device_name=device_name,
                selected_device=selected_device,
                device_query=device_query,
                device_ref=device_ref,
            ),
            build_parameter_ref(
                parameter_index=parameter_index,
                parameter_name=parameter_name,
                parameter_query=parameter_query,
                parameter_key=parameter_key,
                parameter_ref=parameter_ref,
            ),
        )

    def _method_kwargs() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref, resolved_parameter_ref = _resolved_refs()
        return {
            "track_ref": resolved_track_ref,
            "device_ref": resolved_device_ref,
            "parameter_ref": resolved_parameter_ref,
            "value": value,
        }

    run_client_command_spec(
        ctx,
        spec=DEVICE_PARAMETER_SET_SPEC,
        args={
            "track_ref": None,
            "device_ref": None,
            "parameter_ref": None,
            "value": value,
        },
        method_kwargs=_method_kwargs,
        resolved_args=lambda: {
            "track_ref": _resolved_refs()[0],
            "device_ref": _resolved_refs()[1],
            "parameter_ref": _resolved_refs()[2],
            "value": value,
        },
    )


device_app.add_typer(parameter_app, name="parameter")


def register(app: typer.Typer) -> None:
    app.add_typer(device_app, name="device")
