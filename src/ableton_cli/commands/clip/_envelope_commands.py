from __future__ import annotations

from typing import Annotated, Any

import typer

from ...envelope_shapes import generate_shape_points
from ...refs import (
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
    build_device_ref,
    build_parameter_ref,
)
from .._params import ClipArgument, TrackArgument
from .._validation import invalid_argument, parse_envelope_points_json
from ._shared import execute_clip_command, resolve_client, validate_track_and_clip

_ENVELOPE_SHAPES = ("ramp", "exp", "scurve", "lfo-sine", "lfo-square")


def register_envelope_commands(envelope_app: typer.Typer) -> None:
    envelope_app.command("set")(clip_envelope_set)
    envelope_app.command("shape")(clip_envelope_shape)
    envelope_app.command("clear")(clip_envelope_clear)


def _device_ref_options(
    *,
    device_index: int | None,
    device_name: str | None,
    selected_device: bool,
    device_query: str | None,
    device_ref: str | None,
) -> RefPayload:
    return build_device_ref(
        device_index=device_index,
        device_name=device_name,
        selected_device=selected_device,
        device_query=device_query,
        device_ref=device_ref,
    )


def _parameter_ref_options(
    *,
    parameter_index: int | None,
    parameter_name: str | None,
    parameter_query: str | None,
    parameter_key: str | None,
    parameter_ref: str | None,
) -> RefPayload:
    return build_parameter_ref(
        parameter_index=parameter_index,
        parameter_name=parameter_name,
        parameter_query=parameter_query,
        parameter_key=parameter_key,
        parameter_ref=parameter_ref,
    )


def clip_envelope_set(
    ctx: typer.Context,
    track: TrackArgument,
    clip: ClipArgument,
    points_json: Annotated[
        str, typer.Option("--points-json", help='JSON array of {"time","value"} breakpoints')
    ],
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
    mode: Annotated[
        str, typer.Option("--mode", help="replace clears the existing envelope first")
    ] = "replace",
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        points = parse_envelope_points_json(points_json)
        resolved_device_ref = _device_ref_options(
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )
        resolved_parameter_ref = _parameter_ref_options(
            parameter_index=parameter_index,
            parameter_name=parameter_name,
            parameter_query=parameter_query,
            parameter_key=parameter_key,
            parameter_ref=parameter_ref,
        )
        if mode != "replace":
            raise invalid_argument(
                message=f"mode must be 'replace', got {mode!r}",
                hint="Only mode=replace is currently supported.",
            )
        return resolve_client(ctx).clip_envelope_set(
            valid_track,
            valid_clip,
            resolved_device_ref,
            resolved_parameter_ref,
            points,
            mode,
        )

    execute_clip_command(
        ctx,
        command="clip envelope set",
        args={"track": track, "clip": clip, "mode": mode},
        action=_run,
    )


def clip_envelope_shape(
    ctx: typer.Context,
    track: TrackArgument,
    clip: ClipArgument,
    shape: Annotated[str, typer.Option("--shape", help=f"One of {', '.join(_ENVELOPE_SHAPES)}")],
    from_value: Annotated[float, typer.Option("--from", help="Starting value")],
    to_value: Annotated[float, typer.Option("--to", help="Ending/target value")],
    start: Annotated[float, typer.Option("--start", help="Start time in beats")] = 0.0,
    length: Annotated[float, typer.Option("--length", help="Curve length in beats")] = 4.0,
    resolution: Annotated[
        int, typer.Option("--resolution", help="Number of breakpoints to generate")
    ] = 16,
    rate: Annotated[
        float, typer.Option("--rate", help="LFO cycles per beat of length (lfo-* shapes only)")
    ] = 1.0,
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
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        if shape not in _ENVELOPE_SHAPES:
            raise invalid_argument(
                message=f"shape must be one of {_ENVELOPE_SHAPES}, got {shape!r}",
                hint="Use --shape ramp|exp|scurve|lfo-sine|lfo-square.",
            )
        try:
            points: list[dict[str, Any]] = generate_shape_points(
                shape,
                from_value=from_value,
                to_value=to_value,
                start=start,
                length=length,
                resolution=resolution,
                rate=rate,
            )
        except ValueError as exc:
            raise invalid_argument(
                message=str(exc),
                hint="Use --resolution >= 1 and --length > 0.",
            ) from exc
        resolved_device_ref = _device_ref_options(
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )
        resolved_parameter_ref = _parameter_ref_options(
            parameter_index=parameter_index,
            parameter_name=parameter_name,
            parameter_query=parameter_query,
            parameter_key=parameter_key,
            parameter_ref=parameter_ref,
        )
        return resolve_client(ctx).clip_envelope_set(
            valid_track,
            valid_clip,
            resolved_device_ref,
            resolved_parameter_ref,
            points,
            "replace",
        )

    execute_clip_command(
        ctx,
        command="clip envelope shape",
        args={
            "track": track,
            "clip": clip,
            "shape": shape,
            "from": from_value,
            "to": to_value,
            "start": start,
            "length": length,
            "resolution": resolution,
            "rate": rate,
        },
        action=_run,
    )


def clip_envelope_clear(
    ctx: typer.Context,
    track: TrackArgument,
    clip: ClipArgument,
    all_envelopes: Annotated[
        bool, typer.Option("--all", help="Clear every envelope on the clip")
    ] = False,
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
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        client = resolve_client(ctx)
        if all_envelopes:
            return client.clip_envelope_clear(valid_track, valid_clip, clear_all=True)
        resolved_device_ref = _device_ref_options(
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )
        resolved_parameter_ref = _parameter_ref_options(
            parameter_index=parameter_index,
            parameter_name=parameter_name,
            parameter_query=parameter_query,
            parameter_key=parameter_key,
            parameter_ref=parameter_ref,
        )
        return client.clip_envelope_clear(
            valid_track,
            valid_clip,
            resolved_device_ref,
            resolved_parameter_ref,
            clear_all=False,
        )

    execute_clip_command(
        ctx,
        command="clip envelope clear",
        args={"track": track, "clip": clip, "all": all_envelopes},
        action=_run,
    )
