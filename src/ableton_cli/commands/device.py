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
chains_app = typer.Typer(help="Rack chain commands", no_args_is_help=True)
macro_app = typer.Typer(help="Rack macro commands", no_args_is_help=True)
parameters_app = typer.Typer(help="Device parameter listing", no_args_is_help=True)
active_app = typer.Typer(help="Device on/off commands", no_args_is_help=True)
preset_app = typer.Typer(help="Plug-in preset commands", no_args_is_help=True)
sidechain_app = typer.Typer(help="Compressor sidechain routing commands", no_args_is_help=True)


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


DEVICE_CHAINS_LIST_SPEC = DeviceCommandSpec(
    command_name="device chains list",
    client_method="device_chains_list",
)

DEVICE_MACRO_LIST_SPEC = DeviceCommandSpec(
    command_name="device macro list",
    client_method="device_macro_list",
)

DEVICE_MACRO_SET_SPEC = DeviceCommandSpec(
    command_name="device macro set",
    client_method="device_macro_set",
)


def _device_target_refs(
    *,
    track_index: int | None,
    track_name: str | None,
    selected_track: bool,
    track_query: str | None,
    track_ref: str | None,
    device_index: int | None,
    device_name: str | None,
    selected_device: bool,
    device_query: str | None,
    device_ref: str | None,
) -> tuple[dict[str, object], dict[str, object]]:
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
    )


@chains_app.command("list")
def device_chains_list(
    ctx: typer.Context,
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
) -> None:
    def _resolved_refs() -> tuple[dict[str, object], dict[str, object]]:
        return _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )

    def _method_kwargs() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref = _resolved_refs()
        return {"track_ref": resolved_track_ref, "device_ref": resolved_device_ref}

    run_client_command_spec(
        ctx,
        spec=DEVICE_CHAINS_LIST_SPEC,
        args={"track_ref": None, "device_ref": None},
        method_kwargs=_method_kwargs,
        resolved_args=lambda: {
            "track_ref": _resolved_refs()[0],
            "device_ref": _resolved_refs()[1],
        },
    )


@macro_app.command("list")
def device_macro_list(
    ctx: typer.Context,
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
) -> None:
    def _resolved_refs() -> tuple[dict[str, object], dict[str, object]]:
        return _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )

    def _method_kwargs() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref = _resolved_refs()
        return {"track_ref": resolved_track_ref, "device_ref": resolved_device_ref}

    run_client_command_spec(
        ctx,
        spec=DEVICE_MACRO_LIST_SPEC,
        args={"track_ref": None, "device_ref": None},
        method_kwargs=_method_kwargs,
        resolved_args=lambda: {
            "track_ref": _resolved_refs()[0],
            "device_ref": _resolved_refs()[1],
        },
    )


@macro_app.command("set")
def device_macro_set(
    ctx: typer.Context,
    macro_index: Annotated[int, typer.Argument(help="Macro index (0-based)")],
    value: Annotated[float, typer.Argument(help="Target macro value")],
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
) -> None:
    def _resolved_refs() -> tuple[dict[str, object], dict[str, object]]:
        return _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )

    def _method_kwargs() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref = _resolved_refs()
        return {
            "track_ref": resolved_track_ref,
            "device_ref": resolved_device_ref,
            "macro_index": macro_index,
            "value": value,
        }

    run_client_command_spec(
        ctx,
        spec=DEVICE_MACRO_SET_SPEC,
        args={
            "track_ref": None,
            "device_ref": None,
            "macro_index": macro_index,
            "value": value,
        },
        method_kwargs=_method_kwargs,
        resolved_args=lambda: {
            "track_ref": _resolved_refs()[0],
            "device_ref": _resolved_refs()[1],
            "macro_index": macro_index,
            "value": value,
        },
    )


def _run_device_target_command(
    ctx: typer.Context,
    *,
    spec: DeviceCommandSpec,
    refs: Callable[[], tuple[dict[str, object], dict[str, object]]],
    extra: dict[str, object] | None = None,
) -> None:
    """Run a command addressed by track+device selectors plus plain arguments."""
    extra_args = dict(extra or {})

    def _resolved() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref = refs()
        return {"track_ref": resolved_track_ref, "device_ref": resolved_device_ref, **extra_args}

    run_client_command_spec(
        ctx,
        spec=spec,
        args={"track_ref": None, "device_ref": None, **extra_args},
        method_kwargs=_resolved,
        resolved_args=_resolved,
    )


def _run_device_parameter_command(
    ctx: typer.Context,
    *,
    spec: DeviceCommandSpec,
    refs: Callable[[], tuple[dict[str, object], dict[str, object]]],
    parameter_ref: Callable[[], dict[str, object]],
    extra: dict[str, object],
) -> None:
    """Run a command addressed by track+device+parameter selectors."""

    def _resolved() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref = refs()
        return {
            "track_ref": resolved_track_ref,
            "device_ref": resolved_device_ref,
            "parameter_ref": parameter_ref(),
            **extra,
        }

    run_client_command_spec(
        ctx,
        spec=spec,
        args={"track_ref": None, "device_ref": None, "parameter_ref": None, **extra},
        method_kwargs=_resolved,
        resolved_args=_resolved,
    )


DEVICE_PARAMETERS_LIST_SPEC = DeviceCommandSpec(
    command_name="device parameters list", client_method="device_parameters_list"
)
DEVICE_PARAMETER_SELECT_SPEC = DeviceCommandSpec(
    command_name="device parameter select", client_method="device_parameter_select"
)
DEVICE_PARAMETER_SET_DISPLAY_SPEC = DeviceCommandSpec(
    command_name="device parameter set-display", client_method="device_parameter_display_set"
)
DEVICE_ACTIVE_GET_SPEC = DeviceCommandSpec(
    command_name="device active get", client_method="device_active_get"
)
DEVICE_ACTIVE_SET_SPEC = DeviceCommandSpec(
    command_name="device active set", client_method="device_active_set"
)
DEVICE_PRESET_LIST_SPEC = DeviceCommandSpec(
    command_name="device preset list", client_method="device_preset_list"
)
DEVICE_PRESET_SET_SPEC = DeviceCommandSpec(
    command_name="device preset set", client_method="device_preset_set"
)
DEVICE_SIDECHAIN_GET_SPEC = DeviceCommandSpec(
    command_name="device sidechain get", client_method="device_sidechain_get"
)
DEVICE_SIDECHAIN_SET_SPEC = DeviceCommandSpec(
    command_name="device sidechain set", client_method="device_sidechain_set"
)
DEVICE_INSERT_SPEC = DeviceCommandSpec(command_name="device insert", client_method="device_insert")
DEVICE_DELETE_SPEC = DeviceCommandSpec(command_name="device delete", client_method="device_delete")
DEVICE_MOVE_SPEC = DeviceCommandSpec(command_name="device move", client_method="device_move")


@parameters_app.command("list")
def device_parameters_list(
    ctx: typer.Context,
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
) -> None:
    """List every parameter of any device, with display strings and choice items."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_PARAMETERS_LIST_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
    )


@parameter_app.command("select")
def device_parameter_select(
    ctx: typer.Context,
    item: Annotated[str, typer.Argument(help="Item name from value_items")],
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
    """Set a choice parameter (e.g. Compressor Model) by its item name."""
    _run_device_parameter_command(
        ctx,
        spec=DEVICE_PARAMETER_SELECT_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
        parameter_ref=lambda: build_parameter_ref(
            parameter_index=parameter_index,
            parameter_name=parameter_name,
            parameter_query=parameter_query,
            parameter_key=parameter_key,
            parameter_ref=parameter_ref,
        ),
        extra={"item": item},
    )


@parameter_app.command("set-display")
def device_parameter_set_display(
    ctx: typer.Context,
    value: Annotated[float, typer.Argument(help="Value in display units")],
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
    """Set a parameter in the units Live displays (dB, Hz, ms, %)."""
    _run_device_parameter_command(
        ctx,
        spec=DEVICE_PARAMETER_SET_DISPLAY_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
        parameter_ref=lambda: build_parameter_ref(
            parameter_index=parameter_index,
            parameter_name=parameter_name,
            parameter_query=parameter_query,
            parameter_key=parameter_key,
            parameter_ref=parameter_ref,
        ),
        extra={"value": value},
    )


@active_app.command("get")
def device_active_get(
    ctx: typer.Context,
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
) -> None:
    """Read whether a device is switched on."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_ACTIVE_GET_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
    )


@active_app.command("set")
def device_active_set(
    ctx: typer.Context,
    value: Annotated[bool, typer.Argument(help="Active value: true|false")],
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
) -> None:
    """Switch a device on or off."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_ACTIVE_SET_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
        extra={"value": value},
    )


@preset_app.command("list")
def device_preset_list(
    ctx: typer.Context,
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
) -> None:
    """List a plug-in device's presets."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_PRESET_LIST_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
    )


@preset_app.command("set")
def device_preset_set(
    ctx: typer.Context,
    preset_index: Annotated[int, typer.Argument(help="Preset index (0-based)")],
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
) -> None:
    """Select a plug-in device preset by index."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_PRESET_SET_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
        extra={"preset_index": preset_index},
    )


@sidechain_app.command("get")
def device_sidechain_get(
    ctx: typer.Context,
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
) -> None:
    """Read a Compressor's sidechain source and the available sources."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_SIDECHAIN_GET_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
    )


@sidechain_app.command("set")
def device_sidechain_set(
    ctx: typer.Context,
    routing_type: Annotated[
        str, typer.Option("--type", help="Sidechain source type (from 'device sidechain get')")
    ],
    routing_channel: Annotated[
        str | None,
        typer.Option("--channel", help="Sidechain source channel; omit for Live's default"),
    ] = None,
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
) -> None:
    """Route a Compressor's sidechain input from a source."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_SIDECHAIN_SET_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
        extra={"routing_type": routing_type, "routing_channel": routing_channel},
    )


@device_app.command("delete")
def device_delete(
    ctx: typer.Context,
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
) -> None:
    """Delete a top-level device from a track."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_DELETE_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
    )


@device_app.command("move")
def device_move(
    ctx: typer.Context,
    to_index: Annotated[int, typer.Option("--to-index", help="Destination index")],
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
) -> None:
    """Move a top-level device to another position on its track."""
    _run_device_target_command(
        ctx,
        spec=DEVICE_MOVE_SPEC,
        refs=lambda: _device_target_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
        extra={"to_index": to_index},
    )


@device_app.command("insert")
def device_insert(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Native Live device name, e.g. Compressor")],
    index: Annotated[
        int, typer.Option("--index", help="Insertion index; -1 appends (Live 12.3+)")
    ] = -1,
    track_index: TrackIndexOption = None,
    track_name: TrackNameOption = None,
    selected_track: SelectedTrackOption = False,
    track_query: TrackQueryOption = None,
    track_ref: TrackStableRefOption = None,
) -> None:
    """Insert a native Live device onto a track by name (Live 12.3+)."""

    def _resolved() -> dict[str, object]:
        return {
            "track_ref": build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            "device_name": name,
            "index": index,
        }

    run_client_command_spec(
        ctx,
        spec=DEVICE_INSERT_SPEC,
        args={"track_ref": None, "device_name": name, "index": index},
        method_kwargs=_resolved,
        resolved_args=_resolved,
    )


device_app.add_typer(parameter_app, name="parameter")
device_app.add_typer(chains_app, name="chains")
device_app.add_typer(macro_app, name="macro")
device_app.add_typer(parameters_app, name="parameters")
device_app.add_typer(active_app, name="active")
device_app.add_typer(preset_app, name="preset")
device_app.add_typer(sidechain_app, name="sidechain")


def register(app: typer.Typer) -> None:
    app.add_typer(device_app, name="device")
