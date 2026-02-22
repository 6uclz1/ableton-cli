from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    invalid_argument,
    parse_notes_input,
    require_non_empty_string,
    require_non_negative,
    require_positive_float,
    validate_clip_note_filters,
)

clip_app = typer.Typer(help="Clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Clip note commands", no_args_is_help=True)
name_app = typer.Typer(help="Clip naming commands", no_args_is_help=True)
active_app = typer.Typer(help="Clip active-state commands", no_args_is_help=True)


def _validate_note_filters(
    *,
    start_time: float | None,
    end_time: float | None,
    pitch: int | None,
) -> dict[str, float | int | None]:
    return validate_clip_note_filters(
        start_time=start_time,
        end_time=end_time,
        pitch=pitch,
    )


def _validated_transform_filters(
    *,
    track: int,
    clip: int,
    start_time: float | None,
    end_time: float | None,
    pitch: int | None,
) -> dict[str, float | int | None]:
    require_non_negative(
        "track",
        track,
        hint="Use a valid track index from 'ableton-cli tracks list'.",
    )
    require_non_negative(
        "clip",
        clip,
        hint="Use a valid clip slot index.",
    )
    return _validate_note_filters(start_time=start_time, end_time=end_time, pitch=pitch)


def _require_float_in_range(
    *,
    name: str,
    value: float,
    minimum: float,
    maximum: float,
    hint: str,
) -> float:
    if value < minimum or value > maximum:
        raise invalid_argument(
            message=f"{name} must be between {minimum} and {maximum}, got {value}",
            hint=hint,
        )
    return value


def _require_non_negative_float(*, name: str, value: float, hint: str) -> float:
    if value < 0:
        raise invalid_argument(
            message=f"{name} must be >= 0, got {value}",
            hint=hint,
        )
    return value


def _require_int_in_range(
    *,
    name: str,
    value: int,
    minimum: int,
    maximum: int,
    hint: str,
) -> int:
    if value < minimum or value > maximum:
        raise invalid_argument(
            message=f"{name} must be between {minimum} and {maximum}, got {value}",
            hint=hint,
        )
    return value


@clip_app.command("create")
def clip_create(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    length: Annotated[
        float,
        typer.Option("--length", help="Clip length in beats"),
    ] = 4.0,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        require_positive_float("length", length, hint="Use a positive clip length in beats.")
        return get_client(ctx).create_clip(track, clip, length)

    execute_command(
        ctx,
        command="clip create",
        args={"track": track, "clip": clip, "length": length},
        action=_run,
    )


@notes_app.command("add")
def clip_notes_add(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    notes_json: Annotated[
        str | None,
        typer.Option("--notes-json", help="JSON array of note objects"),
    ] = None,
    notes_file: Annotated[
        str | None,
        typer.Option("--notes-file", help="Path to JSON file containing note array"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        return get_client(ctx).add_notes_to_clip(track, clip, notes)

    execute_command(
        ctx,
        command="clip notes add",
        args={"track": track, "clip": clip},
        action=_run,
    )


@notes_app.command("get")
def clip_notes_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        filters = _validate_note_filters(start_time=start_time, end_time=end_time, pitch=pitch)
        return get_client(ctx).get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes get",
        args={
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("clear")
def clip_notes_clear(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        filters = _validate_note_filters(start_time=start_time, end_time=end_time, pitch=pitch)
        return get_client(ctx).clear_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes clear",
        args={
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("replace")
def clip_notes_replace(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    notes_json: Annotated[
        str | None,
        typer.Option("--notes-json", help="JSON array of note objects"),
    ] = None,
    notes_file: Annotated[
        str | None,
        typer.Option("--notes-file", help="Path to JSON file containing note array"),
    ] = None,
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        filters = _validate_note_filters(start_time=start_time, end_time=end_time, pitch=pitch)
        return get_client(ctx).replace_clip_notes(
            track=track,
            clip=clip,
            notes=notes,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes replace",
        args={
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("quantize")
def clip_notes_quantize(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    grid: Annotated[
        str,
        typer.Option("--grid", help="Quantize grid as fraction (for example 1/16) or beats"),
    ] = "1/16",
    strength: Annotated[
        float,
        typer.Option("--strength", help="Quantize strength in [0.0, 1.0]"),
    ] = 1.0,
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = _validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        valid_grid = require_non_empty_string(
            "grid",
            grid,
            hint="Pass a value like '1/16' or a positive beat value.",
        )
        valid_strength = _require_float_in_range(
            name="strength",
            value=strength,
            minimum=0.0,
            maximum=1.0,
            hint="Use --strength in [0.0, 1.0].",
        )
        return get_client(ctx).clip_notes_quantize(
            track=track,
            clip=clip,
            grid=valid_grid,
            strength=valid_strength,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes quantize",
        args={
            "track": track,
            "clip": clip,
            "grid": grid,
            "strength": strength,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("humanize")
def clip_notes_humanize(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    timing: Annotated[
        float,
        typer.Option("--timing", help="Maximum timing shift in beats (>= 0)"),
    ],
    velocity: Annotated[
        int,
        typer.Option("--velocity", help="Maximum velocity shift amount (0-127)"),
    ],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = _validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        valid_timing = _require_non_negative_float(
            name="timing",
            value=timing,
            hint="Use a non-negative --timing value.",
        )
        valid_velocity = _require_int_in_range(
            name="velocity",
            value=velocity,
            minimum=0,
            maximum=127,
            hint="Use --velocity in the 0-127 range.",
        )
        return get_client(ctx).clip_notes_humanize(
            track=track,
            clip=clip,
            timing=valid_timing,
            velocity=valid_velocity,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes humanize",
        args={
            "track": track,
            "clip": clip,
            "timing": timing,
            "velocity": velocity,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("velocity-scale")
def clip_notes_velocity_scale(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    scale: Annotated[
        float,
        typer.Option("--scale", help="Velocity multiplier (>= 0)"),
    ],
    offset: Annotated[
        int,
        typer.Option("--offset", help="Velocity offset (can be negative)"),
    ],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = _validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        valid_scale = _require_non_negative_float(
            name="scale",
            value=scale,
            hint="Use a non-negative --scale value.",
        )
        return get_client(ctx).clip_notes_velocity_scale(
            track=track,
            clip=clip,
            scale=valid_scale,
            offset=offset,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes velocity-scale",
        args={
            "track": track,
            "clip": clip,
            "scale": scale,
            "offset": offset,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("transpose")
def clip_notes_transpose(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    semitones: Annotated[
        int,
        typer.Option("--semitones", help="Semitone offset (can be negative)"),
    ],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = _validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return get_client(ctx).clip_notes_transpose(
            track=track,
            clip=clip,
            semitones=semitones,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes transpose",
        args={
            "track": track,
            "clip": clip,
            "semitones": semitones,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@name_app.command("set")
def clip_name_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    name: Annotated[str, typer.Argument(help="New clip name")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        valid_name = require_non_empty_string("name", name, hint="Pass a non-empty clip name.")
        return get_client(ctx).set_clip_name(track, clip, valid_name)

    execute_command(
        ctx,
        command="clip name set",
        args={"track": track, "clip": clip, "name": name},
        action=_run,
    )


@clip_app.command("fire")
def clip_fire(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).fire_clip(track, clip)

    execute_command(
        ctx,
        command="clip fire",
        args={"track": track, "clip": clip},
        action=_run,
    )


@clip_app.command("stop")
def clip_stop(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).stop_clip(track, clip)

    execute_command(
        ctx,
        command="clip stop",
        args={"track": track, "clip": clip},
        action=_run,
    )


@clip_app.command("duplicate")
def clip_duplicate(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    src_clip: Annotated[int, typer.Argument(help="Source clip slot index (0-based)")],
    dst_clip: Annotated[int, typer.Argument(help="Destination clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "src_clip",
            src_clip,
            hint="Use a valid source clip slot index.",
        )
        require_non_negative(
            "dst_clip",
            dst_clip,
            hint="Use a valid destination clip slot index.",
        )
        return get_client(ctx).clip_duplicate(track, src_clip, dst_clip)

    execute_command(
        ctx,
        command="clip duplicate",
        args={"track": track, "src_clip": src_clip, "dst_clip": dst_clip},
        action=_run,
    )


@active_app.command("get")
def clip_active_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).clip_active_get(track, clip)

    execute_command(
        ctx,
        command="clip active get",
        args={"track": track, "clip": clip},
        action=_run,
    )


@active_app.command("set")
def clip_active_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    value: Annotated[bool, typer.Argument(help="Active value: true|false")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).clip_active_set(track, clip, value)

    execute_command(
        ctx,
        command="clip active set",
        args={"track": track, "clip": clip, "value": value},
        action=_run,
    )


clip_app.add_typer(notes_app, name="notes")
clip_app.add_typer(name_app, name="name")
clip_app.add_typer(active_app, name="active")


def register(app: typer.Typer) -> None:
    app.add_typer(clip_app, name="clip")
