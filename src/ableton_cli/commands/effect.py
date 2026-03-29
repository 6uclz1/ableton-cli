from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, cast

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
    RefPayload,
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
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._validation import (
    invalid_argument,
    require_non_empty_string,
    require_optional_track_index,
)

_SUPPORTED_EFFECT_TYPES = (
    "eq8",
    "limiter",
    "compressor",
    "auto_filter",
    "reverb",
    "utility",
)

effect_app = typer.Typer(help="Effect control commands", no_args_is_help=True)
parameters_app = typer.Typer(help="Effect parameter listing commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Effect parameter write commands", no_args_is_help=True)

TrackDeviceValidator = Callable[[RefPayload, RefPayload], tuple[RefPayload, RefPayload]]
TrackDeviceAction = Callable[[object, RefPayload, RefPayload], dict[str, object]]
RefFactory = RefPayload | Callable[[], RefPayload]


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


def _resolve_ref(ref: RefFactory) -> RefPayload:
    if callable(ref):
        return ref()
    return ref


def run_track_device_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: RefFactory,
    device_ref: RefFactory,
    fn: TrackDeviceAction,
    validators: Sequence[TrackDeviceValidator] | None = None,
) -> None:
    active_validators = validators if validators is not None else ()

    def _run() -> dict[str, object]:
        valid_track_ref = _resolve_ref(track_ref)
        valid_device_ref = _resolve_ref(device_ref)
        for validator in active_validators:
            valid_track_ref, valid_device_ref = validator(valid_track_ref, valid_device_ref)
        client = get_client(ctx)
        return fn(client, valid_track_ref, valid_device_ref)

    execute_kwargs: dict[str, object] = {
        "command": command_name,
        "args": {
            "track_ref": None if callable(track_ref) else track_ref,
            "device_ref": None if callable(device_ref) else device_ref,
        },
        "action": _run,
    }
    if callable(track_ref) or callable(device_ref):
        execute_kwargs["resolved_args"] = lambda: {
            "track_ref": _resolve_ref(track_ref),
            "device_ref": _resolve_ref(device_ref),
        }
    execute_command(ctx, **execute_kwargs)


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
    spec: EffectCommandSpec,
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


def run_track_device_command_spec(
    ctx: typer.Context,
    *,
    spec: TrackDeviceCommandSpec,
    track_ref: RefFactory,
    device_ref: RefFactory,
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
        track_ref=track_ref,
        device_ref=device_ref,
        validators=spec.validators,
        fn=lambda client, valid_track_ref, valid_device_ref: cast(
            dict[str, object],
            getattr(client, spec.client_method)(
                **{
                    "track_ref": valid_track_ref,
                    "device_ref": valid_device_ref,
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
    run_track_device_command_spec(
        ctx,
        spec=EFFECT_PARAMETERS_LIST_SPEC,
        track_ref=lambda: build_track_ref(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
        ),
        device_ref=lambda: build_device_ref(
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
    )


@parameter_app.command("set")
def effect_parameter_set(
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
    def _resolved_refs() -> tuple[RefPayload, RefPayload, RefPayload]:
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
        spec=EFFECT_PARAMETER_SET_SPEC,
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


@effect_app.command("observe")
def effect_observe(
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
    run_track_device_command_spec(
        ctx,
        spec=EFFECT_OBSERVE_SPEC,
        track_ref=lambda: build_track_ref(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
        ),
        device_ref=lambda: build_device_ref(
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
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
        parameter_key: ParameterKeyOption = None,
    ) -> None:
        def _resolved_refs() -> tuple[RefPayload, RefPayload, RefPayload]:
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
                    parameter_index=None,
                    parameter_name=None,
                    parameter_query=None,
                    parameter_key=parameter_key,
                    parameter_ref=None,
                ),
            )

        def _method_kwargs() -> dict[str, object]:
            resolved_track_ref, resolved_device_ref, resolved_parameter_ref = _resolved_refs()
            return {
                "effect_type": effect_type,
                "track_ref": resolved_track_ref,
                "device_ref": resolved_device_ref,
                "parameter_ref": resolved_parameter_ref,
                "key": str(resolved_parameter_ref["key"]),
                "value": value,
            }

        run_client_command_spec(
            ctx,
            spec=set_spec,
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

    @standard_app.command("observe")
    def standard_observe(
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
        run_track_device_command_spec(
            ctx,
            spec=observe_spec,
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            device_ref=lambda: build_device_ref(
                device_index=device_index,
                device_name=device_name,
                selected_device=selected_device,
                device_query=device_query,
                device_ref=device_ref,
            ),
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
