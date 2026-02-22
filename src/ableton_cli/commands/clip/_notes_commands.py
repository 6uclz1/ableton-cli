from __future__ import annotations

from typing import Annotated

import typer

from .._validation import (
    invalid_argument,
    parse_notes_input,
    require_non_empty_string,
    require_non_negative_float,
    resolve_uri_or_path_target,
)
from ._shared import (
    execute_clip_command,
    require_float_in_range,
    require_int_in_range,
    resolve_client,
    validate_track_and_clip,
    validated_transform_filters,
)


def register_notes_commands(notes_app: typer.Typer) -> None:
    notes_app.command("add")(clip_notes_add)
    notes_app.command("get")(clip_notes_get)
    notes_app.command("clear")(clip_notes_clear)
    notes_app.command("replace")(clip_notes_replace)
    notes_app.command("import-browser")(clip_notes_import_browser)
    notes_app.command("quantize")(clip_notes_quantize)
    notes_app.command("humanize")(clip_notes_humanize)
    notes_app.command("velocity-scale")(clip_notes_velocity_scale)
    notes_app.command("transpose")(clip_notes_transpose)


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
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        return resolve_client(ctx).add_notes_to_clip(valid_track, valid_clip, notes)

    execute_clip_command(
        ctx,
        command="clip notes add",
        args={"track": track, "clip": clip},
        action=_run,
    )


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
        filters = validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return resolve_client(ctx).get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
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
        filters = validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return resolve_client(ctx).clear_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
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
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        filters = validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return resolve_client(ctx).replace_clip_notes(
            track=track,
            clip=clip,
            notes=notes,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
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


def clip_notes_import_browser(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Destination clip slot index (0-based)")],
    target: Annotated[str, typer.Argument(help="Browser target (URI or path to .alc)")],
    mode: Annotated[
        str,
        typer.Option("--mode", help="Note import mode: replace|append"),
    ] = "replace",
    import_length: Annotated[
        bool,
        typer.Option(
            "--import-length/--no-import-length",
            help="Copy source clip length into the destination clip",
        ),
    ] = False,
    import_groove: Annotated[
        bool,
        typer.Option(
            "--import-groove/--no-import-groove",
            help="Copy source clip groove settings into the destination clip",
        ),
    ] = False,
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(
            track=track,
            clip=clip,
            clip_hint="Use a valid destination clip slot index.",
        )
        valid_mode = require_non_empty_string(
            "mode",
            mode,
            hint="Use --mode replace or append.",
        ).lower()
        if valid_mode not in {"replace", "append"}:
            raise invalid_argument(
                message=f"mode must be one of replace/append, got {mode}",
                hint="Use --mode replace or append.",
            )
        valid_uri, valid_path = resolve_uri_or_path_target(
            target=target,
            hint="Use a browser path or URI for a .alc MIDI clip item.",
        )
        return resolve_client(ctx).load_instrument_or_effect(
            track=valid_track,
            uri=valid_uri,
            path=valid_path,
            target_track_mode="existing",
            clip_slot=valid_clip,
            notes_mode=valid_mode,
            preserve_track_name=False,
            import_length=import_length,
            import_groove=import_groove,
        )

    execute_clip_command(
        ctx,
        command="clip notes import-browser",
        args={
            "track": track,
            "clip": clip,
            "target": target,
            "mode": mode,
            "import_length": import_length,
            "import_groove": import_groove,
        },
        action=_run,
    )


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
        filters = validated_transform_filters(
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
        valid_strength = require_float_in_range(
            name="strength",
            value=strength,
            minimum=0.0,
            maximum=1.0,
            hint="Use --strength in [0.0, 1.0].",
        )
        return resolve_client(ctx).clip_notes_quantize(
            track=track,
            clip=clip,
            grid=valid_grid,
            strength=valid_strength,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
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
        filters = validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        valid_timing = require_non_negative_float(
            "timing",
            timing,
            hint="Use a non-negative --timing value.",
        )
        valid_velocity = require_int_in_range(
            name="velocity",
            value=velocity,
            minimum=0,
            maximum=127,
            hint="Use --velocity in the 0-127 range.",
        )
        return resolve_client(ctx).clip_notes_humanize(
            track=track,
            clip=clip,
            timing=valid_timing,
            velocity=valid_velocity,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
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
        filters = validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        valid_scale = require_non_negative_float(
            "scale",
            scale,
            hint="Use a non-negative --scale value.",
        )
        return resolve_client(ctx).clip_notes_velocity_scale(
            track=track,
            clip=clip,
            scale=valid_scale,
            offset=offset,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
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
        filters = validated_transform_filters(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return resolve_client(ctx).clip_notes_transpose(
            track=track,
            clip=clip,
            semitones=semitones,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
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
