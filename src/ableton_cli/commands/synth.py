from __future__ import annotations

from collections.abc import Callable, Sequence
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
from ._validation import (
    invalid_argument,
    require_non_empty_string,
    require_optional_track_index,
)

_SUPPORTED_SYNTH_TYPES = ("wavetable", "drift", "meld")

synth_app = typer.Typer(help="Synth control commands", no_args_is_help=True)
parameters_app = typer.Typer(help="Synth parameter listing commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Synth parameter write commands", no_args_is_help=True)

TrackDeviceValidator = Callable[[RefPayload, RefPayload], tuple[RefPayload, RefPayload]]
TrackDeviceAction = Callable[[object, RefPayload, RefPayload], dict[str, object]]
RefFactory = RefPayload | Callable[[], RefPayload]


def _normalize_synth_type(value: str) -> str:
    parsed = require_non_empty_string("synth_type", value, hint="Pass a non-empty synth type.")
    normalized = parsed.lower()
    if normalized not in _SUPPORTED_SYNTH_TYPES:
        raise invalid_argument(
            message=f"synth_type must be one of {', '.join(_SUPPORTED_SYNTH_TYPES)}",
            hint="Use a supported synth type.",
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
        valid_track = require_optional_track_index(track)
        valid_type = _normalize_synth_type(synth_type) if synth_type is not None else None
        client = get_client(ctx)
        return client.find_synth_devices(track=valid_track, synth_type=valid_type)

    execute_command(
        ctx,
        command="synth find",
        args={"track": track, "synth_type": synth_type},
        action=_run,
    )


@parameters_app.command("list")
def synth_parameters_list(
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
    run_track_device_command(
        ctx,
        command_name="synth parameters list",
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
        fn=lambda client, resolved_track_ref, resolved_device_ref: client.list_synth_parameters(
            track_ref=resolved_track_ref,
            device_ref=resolved_device_ref,
        ),
    )


@parameter_app.command("set")
def synth_parameter_set(
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

    def _run() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref, resolved_parameter_ref = _resolved_refs()
        client = get_client(ctx)
        return client.set_synth_parameter_safe(
            track_ref=resolved_track_ref,
            device_ref=resolved_device_ref,
            parameter_ref=resolved_parameter_ref,
            value=value,
        )

    execute_command(
        ctx,
        command="synth parameter set",
        args={
            "track_ref": None,
            "device_ref": None,
            "parameter_ref": None,
            "value": value,
        },
        resolved_args=lambda: {
            "track_ref": _resolved_refs()[0],
            "device_ref": _resolved_refs()[1],
            "parameter_ref": _resolved_refs()[2],
            "value": value,
        },
        action=_run,
    )


@synth_app.command("observe")
def synth_observe(
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
    run_track_device_command(
        ctx,
        command_name="synth observe",
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
        fn=lambda client, resolved_track_ref, resolved_device_ref: client.observe_synth_parameters(
            track_ref=resolved_track_ref,
            device_ref=resolved_device_ref,
        ),
    )


def _build_standard_synth_app(synth_type: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"{synth_type.title()} synth wrapper commands",
        no_args_is_help=True,
    )

    @standard_app.command("keys")
    def keys(ctx: typer.Context) -> None:
        def _run() -> dict[str, object]:
            client = get_client(ctx)
            return client.list_standard_synth_keys(synth_type)

        execute_command(
            ctx,
            command=f"synth {synth_type} keys",
            args={},
            action=_run,
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

        def _run() -> dict[str, object]:
            resolved_track_ref, resolved_device_ref, resolved_parameter_ref = _resolved_refs()
            client = get_client(ctx)
            return client.set_standard_synth_parameter_safe(
                synth_type=synth_type,
                track_ref=resolved_track_ref,
                device_ref=resolved_device_ref,
                parameter_ref=resolved_parameter_ref,
                key=str(resolved_parameter_ref["key"]),
                value=value,
            )

        execute_command(
            ctx,
            command=f"synth {synth_type} set",
            args={
                "track_ref": None,
                "device_ref": None,
                "parameter_ref": None,
                "value": value,
            },
            resolved_args=lambda: {
                "track_ref": _resolved_refs()[0],
                "device_ref": _resolved_refs()[1],
                "parameter_ref": _resolved_refs()[2],
                "value": value,
            },
            action=_run,
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
        run_track_device_command(
            ctx,
            command_name=f"synth {synth_type} observe",
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
            fn=lambda client, resolved_track_ref, resolved_device_ref: (
                client.observe_standard_synth_state(
                    synth_type=synth_type,
                    track_ref=resolved_track_ref,
                    device_ref=resolved_device_ref,
                )
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
