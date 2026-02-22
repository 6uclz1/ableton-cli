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

_SUPPORTED_EFFECT_TYPES = (
    "eq8",
    "limiter",
    "compressor",
    "auto_filter",
    "reverb",
    "utility",
)

TrackArgument = Annotated[int, typer.Argument(help="Track index (0-based)")]
DeviceArgument = Annotated[int, typer.Argument(help="Device index (0-based)")]
ParameterArgument = Annotated[int, typer.Argument(help="Parameter index (0-based)")]

effect_app = typer.Typer(help="Effect control commands", no_args_is_help=True)
parameters_app = typer.Typer(help="Effect parameter listing commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Effect parameter write commands", no_args_is_help=True)


def _normalize_effect_type(value: str) -> str:
    parsed = require_non_empty_string("effect_type", value, hint="Pass a non-empty effect type.")
    normalized = parsed.lower()
    if normalized not in _SUPPORTED_EFFECT_TYPES:
        raise invalid_argument(
            message=f"effect_type must be one of {', '.join(_SUPPORTED_EFFECT_TYPES)}",
            hint="Use a supported effect type.",
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


def _require_effect_parameter_index(parameter: int) -> int:
    return require_parameter_index(
        parameter,
        hint="Use a valid parameter index from 'ableton-cli effect parameters list'.",
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


@effect_app.command("find")
def effect_find(
    ctx: typer.Context,
    track: Annotated[
        int | None,
        typer.Option("--track", help="Optional track index filter (0-based)"),
    ] = None,
    effect_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Optional effect type filter: eq8|limiter|compressor|auto_filter|reverb|utility",
        ),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = _require_optional_track_index(track)
        valid_type = _normalize_effect_type(effect_type) if effect_type is not None else None
        return get_client(ctx).find_effect_devices(track=valid_track, effect_type=valid_type)

    execute_command(
        ctx,
        command="effect find",
        args={"track": track, "effect_type": effect_type},
        action=_run,
    )


@parameters_app.command("list")
def effect_parameters_list(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
) -> None:
    _execute_track_device_command(
        ctx,
        command="effect parameters list",
        track=track,
        device=device,
        action=lambda valid_track, valid_device: get_client(ctx).list_effect_parameters(
            track=valid_track,
            device=valid_device,
        ),
    )


@parameter_app.command("set")
def effect_parameter_set(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
    parameter: ParameterArgument,
    value: Annotated[float, typer.Argument(help="Target parameter value")],
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_device = _require_track_and_device_index(track, device)
        valid_parameter = _require_effect_parameter_index(parameter)
        return get_client(ctx).set_effect_parameter_safe(
            track=valid_track,
            device=valid_device,
            parameter=valid_parameter,
            value=value,
        )

    execute_command(
        ctx,
        command="effect parameter set",
        args={"track": track, "device": device, "parameter": parameter, "value": value},
        action=_run,
    )


@effect_app.command("observe")
def effect_observe(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
) -> None:
    _execute_track_device_command(
        ctx,
        command="effect observe",
        track=track,
        device=device,
        action=lambda valid_track, valid_device: get_client(ctx).observe_effect_parameters(
            track=valid_track,
            device=valid_device,
        ),
    )


def _build_standard_effect_app(effect_type: str, cli_name: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"{cli_name.title()} effect wrapper commands",
        no_args_is_help=True,
    )

    @standard_app.command("keys")
    def keys(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command=f"effect {cli_name} keys",
            args={},
            action=lambda: get_client(ctx).list_standard_effect_keys(effect_type),
        )

    @standard_app.command("set")
    def standard_set(
        ctx: typer.Context,
        track: TrackArgument,
        device: DeviceArgument,
        key: Annotated[str, typer.Argument(help="Stable effect key")],
        value: Annotated[float, typer.Argument(help="Target parameter value")],
    ) -> None:
        def _run() -> dict[str, object]:
            valid_track, valid_device = _require_track_and_device_index(track, device)
            valid_key = require_non_empty_string(
                "key",
                key,
                hint="Pass a non-empty stable effect key.",
            )
            return get_client(ctx).set_standard_effect_parameter_safe(
                effect_type=effect_type,
                track=valid_track,
                device=valid_device,
                key=valid_key,
                value=value,
            )

        execute_command(
            ctx,
            command=f"effect {cli_name} set",
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
            command=f"effect {cli_name} observe",
            track=track,
            device=device,
            action=lambda valid_track, valid_device: get_client(ctx).observe_standard_effect_state(
                effect_type=effect_type,
                track=valid_track,
                device=valid_device,
            ),
        )

    return standard_app


effect_app.add_typer(parameters_app, name="parameters")
effect_app.add_typer(parameter_app, name="parameter")
effect_app.add_typer(_build_standard_effect_app("eq8", "eq8"), name="eq8")
effect_app.add_typer(_build_standard_effect_app("limiter", "limiter"), name="limiter")
effect_app.add_typer(_build_standard_effect_app("compressor", "compressor"), name="compressor")
effect_app.add_typer(_build_standard_effect_app("auto_filter", "auto-filter"), name="auto-filter")
effect_app.add_typer(_build_standard_effect_app("reverb", "reverb"), name="reverb")
effect_app.add_typer(_build_standard_effect_app("utility", "utility"), name="utility")


def register(app: typer.Typer) -> None:
    app.add_typer(effect_app, name="effect")
