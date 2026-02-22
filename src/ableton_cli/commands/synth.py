from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    invalid_argument,
    require_device_index,
    require_non_empty_string,
    require_parameter_index,
    require_track_index,
)

_SUPPORTED_SYNTH_TYPES = ("wavetable", "drift", "meld")

TrackArgument = Annotated[int, typer.Argument(help="Track index (0-based)")]
DeviceArgument = Annotated[int, typer.Argument(help="Device index (0-based)")]
ParameterArgument = Annotated[int, typer.Argument(help="Parameter index (0-based)")]

synth_app = typer.Typer(help="Synth control commands", no_args_is_help=True)
parameters_app = typer.Typer(help="Synth parameter listing commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Synth parameter write commands", no_args_is_help=True)


def _normalize_synth_type(value: str) -> str:
    parsed = require_non_empty_string("synth_type", value, hint="Pass a non-empty synth type.")
    normalized = parsed.lower()
    if normalized not in _SUPPORTED_SYNTH_TYPES:
        raise invalid_argument(
            message=f"synth_type must be one of {', '.join(_SUPPORTED_SYNTH_TYPES)}",
            hint="Use a supported synth type.",
        )
    return normalized


def _require_optional_track_index(track: int | None) -> int | None:
    if track is None:
        return None
    return require_track_index(track)


def _require_track_and_device_index(track: int, device: int) -> tuple[int, int]:
    return (
        require_track_index(track),
        require_device_index(device),
    )


def _require_synth_parameter_index(parameter: int) -> int:
    return require_parameter_index(
        parameter,
        hint="Use a valid parameter index from 'ableton-cli synth parameters list'.",
    )


def _execute_track_device_command(
    ctx: typer.Context,
    *,
    command: str,
    track: int,
    device: int,
    action: Callable[[int, int], dict[str, object]],
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_device = _require_track_and_device_index(track, device)
        return action(valid_track, valid_device)

    execute_command(
        ctx,
        command=command,
        args={"track": track, "device": device},
        action=_run,
    )


@synth_app.command("find")
def synth_find(
    ctx: typer.Context,
    track: Annotated[
        int | None,
        typer.Option("--track", help="Optional track index filter (0-based)"),
    ] = None,
    synth_type: Annotated[
        str | None,
        typer.Option("--type", help="Optional synth type filter: wavetable|drift|meld"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = _require_optional_track_index(track)
        valid_type = _normalize_synth_type(synth_type) if synth_type is not None else None
        return get_client(ctx).find_synth_devices(track=valid_track, synth_type=valid_type)

    execute_command(
        ctx,
        command="synth find",
        args={"track": track, "synth_type": synth_type},
        action=_run,
    )


@parameters_app.command("list")
def synth_parameters_list(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
) -> None:
    _execute_track_device_command(
        ctx,
        command="synth parameters list",
        track=track,
        device=device,
        action=lambda valid_track, valid_device: get_client(ctx).list_synth_parameters(
            track=valid_track,
            device=valid_device,
        ),
    )


@parameter_app.command("set")
def synth_parameter_set(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
    parameter: ParameterArgument,
    value: Annotated[float, typer.Argument(help="Target parameter value")],
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_device = _require_track_and_device_index(track, device)
        valid_parameter = _require_synth_parameter_index(parameter)
        return get_client(ctx).set_synth_parameter_safe(
            track=valid_track,
            device=valid_device,
            parameter=valid_parameter,
            value=value,
        )

    execute_command(
        ctx,
        command="synth parameter set",
        args={"track": track, "device": device, "parameter": parameter, "value": value},
        action=_run,
    )


@synth_app.command("observe")
def synth_observe(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
) -> None:
    _execute_track_device_command(
        ctx,
        command="synth observe",
        track=track,
        device=device,
        action=lambda valid_track, valid_device: get_client(ctx).observe_synth_parameters(
            track=valid_track,
            device=valid_device,
        ),
    )


def _build_standard_synth_app(synth_type: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"{synth_type.title()} synth wrapper commands",
        no_args_is_help=True,
    )

    @standard_app.command("keys")
    def keys(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command=f"synth {synth_type} keys",
            args={},
            action=lambda: get_client(ctx).list_standard_synth_keys(synth_type),
        )

    @standard_app.command("set")
    def standard_set(
        ctx: typer.Context,
        track: TrackArgument,
        device: DeviceArgument,
        key: Annotated[str, typer.Argument(help="Stable synth key")],
        value: Annotated[float, typer.Argument(help="Target parameter value")],
    ) -> None:
        def _run() -> dict[str, object]:
            valid_track, valid_device = _require_track_and_device_index(track, device)
            valid_key = require_non_empty_string(
                "key",
                key,
                hint="Pass a non-empty stable synth key.",
            )
            return get_client(ctx).set_standard_synth_parameter_safe(
                synth_type=synth_type,
                track=valid_track,
                device=valid_device,
                key=valid_key,
                value=value,
            )

        execute_command(
            ctx,
            command=f"synth {synth_type} set",
            args={"track": track, "device": device, "key": key, "value": value},
            action=_run,
        )

    @standard_app.command("observe")
    def standard_observe(
        ctx: typer.Context,
        track: TrackArgument,
        device: DeviceArgument,
    ) -> None:
        _execute_track_device_command(
            ctx,
            command=f"synth {synth_type} observe",
            track=track,
            device=device,
            action=lambda valid_track, valid_device: get_client(ctx).observe_standard_synth_state(
                synth_type=synth_type,
                track=valid_track,
                device=valid_device,
            ),
        )

    return standard_app


synth_app.add_typer(parameters_app, name="parameters")
synth_app.add_typer(parameter_app, name="parameter")
synth_app.add_typer(_build_standard_synth_app("wavetable"), name="wavetable")
synth_app.add_typer(_build_standard_synth_app("drift"), name="drift")
synth_app.add_typer(_build_standard_synth_app("meld"), name="meld")


def register(app: typer.Typer) -> None:
    app.add_typer(synth_app, name="synth")
