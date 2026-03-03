from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, cast

import typer

from ..runtime import execute_command, get_client
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._validation import (
    invalid_argument,
    require_non_empty_string,
    require_optional_track_index,
    require_parameter_index,
    require_track_and_device,
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

TrackDeviceValidator = Callable[[int, int], tuple[int, int]]
TrackDeviceAction = Callable[[object, int, int], dict[str, object]]


@dataclass(frozen=True)
class EffectCommandSpec:
    command_name: str
    client_method: str


@dataclass(frozen=True)
class TrackDeviceCommandSpec:
    command_name: str
    client_method: str
    validators: Sequence[TrackDeviceValidator] | None = None


EFFECT_FIND_SPEC = EffectCommandSpec(
    command_name="effect find",
    client_method="find_effect_devices",
)
EFFECT_PARAMETERS_LIST_SPEC = TrackDeviceCommandSpec(
    command_name="effect parameters list",
    client_method="list_effect_parameters",
)
EFFECT_PARAMETER_SET_SPEC = EffectCommandSpec(
    command_name="effect parameter set",
    client_method="set_effect_parameter_safe",
)
EFFECT_OBSERVE_SPEC = TrackDeviceCommandSpec(
    command_name="effect observe",
    client_method="observe_effect_parameters",
)


def _normalize_effect_type(value: str) -> str:
    parsed = require_non_empty_string("effect_type", value, hint="Pass a non-empty effect type.")
    normalized = parsed.lower()
    if normalized not in _SUPPORTED_EFFECT_TYPES:
        raise invalid_argument(
            message=f"effect_type must be one of {', '.join(_SUPPORTED_EFFECT_TYPES)}",
            hint="Use a supported effect type.",
        )
    return normalized


def _require_effect_parameter_index(parameter: int) -> int:
    return require_parameter_index(
        parameter,
        hint="Use a valid parameter index from 'ableton-cli effect parameters list'.",
    )


def run_track_device_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track: int,
    device: int,
    fn: TrackDeviceAction,
    validators: Sequence[TrackDeviceValidator] | None = None,
) -> None:
    active_validators = validators if validators is not None else (require_track_and_device,)

    def _run() -> dict[str, object]:
        valid_track = track
        valid_device = device
        for validator in active_validators:
            valid_track, valid_device = validator(valid_track, valid_device)
        client = get_client(ctx)
        return fn(client, valid_track, valid_device)

    execute_command(
        ctx,
        command=command_name,
        args={"track": track, "device": device},
        action=_run,
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
    spec: EffectCommandSpec,
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


def run_track_device_command_spec(
    ctx: typer.Context,
    *,
    spec: TrackDeviceCommandSpec,
    track: int,
    device: int,
    method_kwargs: dict[str, object] | Callable[[], dict[str, object]] | None = None,
) -> None:
    def _resolve_method_kwargs() -> dict[str, object]:
        if callable(method_kwargs):
            return method_kwargs()
        if method_kwargs is None:
            return {}
        return method_kwargs

    run_track_device_command(
        ctx,
        command_name=spec.command_name,
        track=track,
        device=device,
        validators=spec.validators,
        fn=lambda client, valid_track, valid_device: cast(
            dict[str, object],
            getattr(client, spec.client_method)(
                **{
                    "track": valid_track,
                    "device": valid_device,
                    **_resolve_method_kwargs(),
                }
            ),
        ),
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
    def _method_kwargs() -> dict[str, object]:
        valid_track = require_optional_track_index(track)
        valid_type = _normalize_effect_type(effect_type) if effect_type is not None else None
        return {"track": valid_track, "effect_type": valid_type}

    run_client_command_spec(
        ctx,
        spec=EFFECT_FIND_SPEC,
        args={"track": track, "effect_type": effect_type},
        method_kwargs=_method_kwargs,
    )


@parameters_app.command("list")
def effect_parameters_list(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
) -> None:
    run_track_device_command_spec(
        ctx,
        spec=EFFECT_PARAMETERS_LIST_SPEC,
        track=track,
        device=device,
    )


@parameter_app.command("set")
def effect_parameter_set(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
    parameter: ParameterArgument,
    value: Annotated[float, typer.Argument(help="Target parameter value")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_track, valid_device = require_track_and_device(track, device)
        valid_parameter = _require_effect_parameter_index(parameter)
        return {
            "track": valid_track,
            "device": valid_device,
            "parameter": valid_parameter,
            "value": value,
        }

    run_client_command_spec(
        ctx,
        spec=EFFECT_PARAMETER_SET_SPEC,
        args={"track": track, "device": device, "parameter": parameter, "value": value},
        method_kwargs=_method_kwargs,
    )


@effect_app.command("observe")
def effect_observe(
    ctx: typer.Context,
    track: TrackArgument,
    device: DeviceArgument,
) -> None:
    run_track_device_command_spec(
        ctx,
        spec=EFFECT_OBSERVE_SPEC,
        track=track,
        device=device,
    )


def _build_standard_effect_app(effect_type: str, cli_name: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"{cli_name.title()} effect wrapper commands",
        no_args_is_help=True,
    )
    keys_spec = EffectCommandSpec(
        command_name=f"effect {cli_name} keys",
        client_method="list_standard_effect_keys",
    )
    set_spec = EffectCommandSpec(
        command_name=f"effect {cli_name} set",
        client_method="set_standard_effect_parameter_safe",
    )
    observe_spec = TrackDeviceCommandSpec(
        command_name=f"effect {cli_name} observe",
        client_method="observe_standard_effect_state",
    )

    @standard_app.command("keys")
    def keys(ctx: typer.Context) -> None:
        run_client_command_spec(
            ctx,
            spec=keys_spec,
            args={},
            method_kwargs={"effect_type": effect_type},
        )

    @standard_app.command("set")
    def standard_set(
        ctx: typer.Context,
        track: TrackArgument,
        device: DeviceArgument,
        key: Annotated[str, typer.Argument(help="Stable effect key")],
        value: Annotated[float, typer.Argument(help="Target parameter value")],
    ) -> None:
        def _method_kwargs() -> dict[str, object]:
            valid_track, valid_device = require_track_and_device(track, device)
            valid_key = require_non_empty_string(
                "key",
                key,
                hint="Pass a non-empty stable effect key.",
            )
            return {
                "effect_type": effect_type,
                "track": valid_track,
                "device": valid_device,
                "key": valid_key,
                "value": value,
            }

        run_client_command_spec(
            ctx,
            spec=set_spec,
            args={"track": track, "device": device, "key": key, "value": value},
            method_kwargs=_method_kwargs,
        )

    @standard_app.command("observe")
    def standard_observe(
        ctx: typer.Context,
        track: TrackArgument,
        device: DeviceArgument,
    ) -> None:
        run_track_device_command_spec(
            ctx,
            spec=observe_spec,
            track=track,
            device=device,
            method_kwargs={"effect_type": effect_type},
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
