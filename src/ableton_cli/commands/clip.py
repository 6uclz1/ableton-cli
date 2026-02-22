from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    invalid_argument,
    parse_notes_input,
    require_non_empty_string,
    require_non_negative,
    require_positive_float,
    resolve_uri_or_path_target,
    validate_clip_note_filters,
)

clip_app = typer.Typer(help="Clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Clip note commands", no_args_is_help=True)
name_app = typer.Typer(help="Clip naming commands", no_args_is_help=True)
active_app = typer.Typer(help="Clip active-state commands", no_args_is_help=True)
groove_app = typer.Typer(help="Clip groove commands", no_args_is_help=True)
groove_amount_app = typer.Typer(help="Clip groove amount commands", no_args_is_help=True)


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


def _require_uri_or_path_target(target: str) -> str:
    parsed = require_non_empty_string(
        "target",
        target,
        hint="Pass a groove target path or URI.",
    )
    if "/" in parsed or ":" in parsed:
        return parsed
    raise invalid_argument(
        message=f"target must include '/' (path) or ':' (uri), got {parsed!r}",
        hint="Use a path like grooves/Hip Hop Boom Bap 16ths 90 bpm.agr or groove URI.",
    )


def _parse_duplicate_destinations(
    *,
    src_clip: int,
    dst_clip: int | None,
    to: str | None,
) -> tuple[int | None, list[int] | None]:
    if dst_clip is None and to is None:
        raise invalid_argument(
            message="Either dst_clip or --to must be provided",
            hint="Provide one destination clip slot or --to 2,4,5.",
        )
    if dst_clip is not None and to is not None:
        raise invalid_argument(
            message="dst_clip and --to are mutually exclusive",
            hint="Use either a single dst_clip argument or --to for multiple destinations.",
        )
    if dst_clip is not None:
        normalized_dst_clip = require_non_negative(
            "dst_clip",
            dst_clip,
            hint="Use a valid destination clip slot index.",
        )
        if normalized_dst_clip == src_clip:
            raise invalid_argument(
                message=f"Destination clip index must differ from src_clip ({src_clip})",
                hint="Use a destination index that is not the source clip.",
            )
        return (normalized_dst_clip, None)

    assert to is not None
    parsed = require_non_empty_string("to", to, hint="Use comma-separated clip slots like 2,4,5.")
    destinations: list[int] = []
    seen: set[int] = set()
    for raw_value in parsed.split(","):
        token = raw_value.strip()
        if not token:
            continue
        try:
            value = int(token)
        except ValueError as exc:
            raise invalid_argument(
                message=f"Invalid destination clip index in --to: {token!r}",
                hint="Use comma-separated non-negative integers like 2,4,5.",
            ) from exc
        _append_destination_index(
            src_clip=src_clip,
            value=value,
            seen=seen,
            destinations=destinations,
            source_label="--to",
        )
    if not destinations:
        raise invalid_argument(
            message="--to must include at least one destination clip index",
            hint="Use comma-separated indexes like --to 2,4,5.",
        )
    return None, destinations


def _append_destination_index(
    *,
    src_clip: int,
    value: int,
    seen: set[int],
    destinations: list[int],
    source_label: str,
) -> None:
    if value < 0:
        raise invalid_argument(
            message=f"Destination clip index must be >= 0, got {value}",
            hint="Use non-negative destination clip indexes.",
        )
    if value == src_clip:
        raise invalid_argument(
            message=f"Destination clip index must differ from src_clip ({src_clip})",
            hint="Use destination indexes that are not the source clip.",
        )
    if value in seen:
        raise invalid_argument(
            message=f"Duplicate destination clip index in {source_label}: {value}",
            hint="Remove duplicated destination indexes.",
        )
    seen.add(value)
    destinations.append(value)


def _parse_scene_token_as_range(token: str) -> tuple[int, int] | None:
    parts = token.split("-", 1)
    if len(parts) != 2:
        return None
    start_text = parts[0].strip()
    end_text = parts[1].strip()
    if not start_text or not end_text:
        return None
    if not start_text.isdigit() or not end_text.isdigit():
        return None
    start = int(start_text)
    end = int(end_text)
    if end < start:
        raise invalid_argument(
            message=f"Scene range must be ascending, got {token!r}",
            hint="Use scene ranges like 2-6.",
        )
    return (start, end)


def _extract_scene_index_by_name(
    *,
    scenes_payload: dict[str, object],
    name: str,
) -> int:
    raw_scenes = scenes_payload.get("scenes")
    if not isinstance(raw_scenes, list):
        raise invalid_argument(
            message="scenes list response is invalid",
            hint="Retry after confirming Ableton scenes are available.",
        )
    normalized_name = name.casefold()
    matches: list[int] = []
    for raw_scene in raw_scenes:
        if not isinstance(raw_scene, dict):
            continue
        raw_index = raw_scene.get("index")
        raw_scene_name = raw_scene.get("name")
        if not isinstance(raw_index, int) or raw_index < 0:
            continue
        if not isinstance(raw_scene_name, str):
            continue
        if raw_scene_name.strip().casefold() == normalized_name:
            matches.append(raw_index)

    if not matches:
        raise invalid_argument(
            message=f"Unknown scene name in --scenes: {name!r}",
            hint="Use scene indexes/ranges or existing scene names from 'ableton-cli scenes list'.",
        )
    if len(matches) > 1:
        raise invalid_argument(
            message=f"Scene name is ambiguous in --scenes: {name!r}",
            hint="Use numeric scene indexes for duplicated scene names.",
        )
    return matches[0]


def _parse_place_pattern_destinations(
    *,
    src_clip: int,
    scenes: str,
    load_scenes: Callable[[], dict[str, object]],
) -> list[int]:
    parsed = require_non_empty_string(
        "scenes",
        scenes,
        hint="Use scene selectors like 2,4,6 or 2-6 or Intro,Drop.",
    )
    tokens = [token.strip() for token in parsed.split(",")]
    if any(not token for token in tokens):
        raise invalid_argument(
            message="--scenes contains an empty selector",
            hint="Use comma-separated selectors like 2,4 or Intro,Drop.",
        )

    destinations: list[int] = []
    seen: set[int] = set()
    scenes_payload: dict[str, object] | None = None
    for token in tokens:
        parsed_range = _parse_scene_token_as_range(token)
        if parsed_range is not None:
            start, end = parsed_range
            for value in range(start, end + 1):
                _append_destination_index(
                    src_clip=src_clip,
                    value=value,
                    seen=seen,
                    destinations=destinations,
                    source_label="--scenes",
                )
            continue

        if token.isdigit():
            _append_destination_index(
                src_clip=src_clip,
                value=int(token),
                seen=seen,
                destinations=destinations,
                source_label="--scenes",
            )
            continue

        if scenes_payload is None:
            scenes_payload = load_scenes()
        scene_index = _extract_scene_index_by_name(scenes_payload=scenes_payload, name=token)
        _append_destination_index(
            src_clip=src_clip,
            value=scene_index,
            seen=seen,
            destinations=destinations,
            source_label="--scenes",
        )

    if not destinations:
        raise invalid_argument(
            message="--scenes must include at least one destination",
            hint="Use scene selectors like 2,4 or Intro,Drop.",
        )
    return destinations


def _parse_clip_name_assignments(mapping: str) -> list[tuple[int, str]]:
    parsed = require_non_empty_string(
        "map",
        mapping,
        hint="Use clip:name pairs like 1:Main,2:Var.",
    )
    tokens = [token.strip() for token in parsed.split(",")]
    if any(not token for token in tokens):
        raise invalid_argument(
            message="--map contains an empty assignment",
            hint="Use clip:name pairs like 1:Main,2:Var.",
        )

    assignments: list[tuple[int, str]] = []
    seen: set[int] = set()
    for token in tokens:
        if ":" not in token:
            raise invalid_argument(
                message=f"Invalid clip:name pair in --map: {token!r}",
                hint="Use clip:name pairs like 1:Main,2:Var.",
            )
        clip_token, name_token = token.split(":", 1)
        clip_raw = clip_token.strip()
        try:
            clip = int(clip_raw)
        except ValueError as exc:
            raise invalid_argument(
                message=f"Invalid clip index in --map: {clip_raw!r}",
                hint="Use non-negative clip indexes like 1:Main.",
            ) from exc
        clip = require_non_negative("clip", clip, hint="Use non-negative clip indexes in --map.")
        if clip in seen:
            raise invalid_argument(
                message=f"Duplicate clip index in --map: {clip}",
                hint="Assign each clip index once in --map.",
            )
        seen.add(clip)
        name = require_non_empty_string(
            "name",
            name_token,
            hint="Use non-empty names in --map, e.g. 1:Main.",
        )
        assignments.append((clip, name))

    if not assignments:
        raise invalid_argument(
            message="--map must include at least one clip:name pair",
            hint="Use clip:name pairs like 1:Main,2:Var.",
        )
    return assignments


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


@notes_app.command("import-browser")
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
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid destination clip slot index.",
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
        return get_client(ctx).load_instrument_or_effect(
            track=track,
            uri=valid_uri,
            path=valid_path,
            target_track_mode="existing",
            clip_slot=clip,
            notes_mode=valid_mode,
            preserve_track_name=False,
            import_length=import_length,
            import_groove=import_groove,
        )

    execute_command(
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


@groove_app.command("get")
def clip_groove_get(
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
        return get_client(ctx).clip_groove_get(track, clip)

    execute_command(
        ctx,
        command="clip groove get",
        args={"track": track, "clip": clip},
        action=_run,
    )


@groove_app.command("set")
def clip_groove_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    target: Annotated[str, typer.Argument(help="Groove target (URI or path to .agr)")],
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
        valid_target = _require_uri_or_path_target(target)
        return get_client(ctx).clip_groove_set(track, clip, valid_target)

    execute_command(
        ctx,
        command="clip groove set",
        args={"track": track, "clip": clip, "target": target},
        action=_run,
    )


@groove_amount_app.command("set")
def clip_groove_amount_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    value: Annotated[float, typer.Argument(help="Groove amount in [0.0, 1.0]")],
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
        valid_value = _require_float_in_range(
            name="value",
            value=value,
            minimum=0.0,
            maximum=1.0,
            hint="Use a groove amount in the 0.0-1.0 range.",
        )
        return get_client(ctx).clip_groove_amount_set(track, clip, valid_value)

    execute_command(
        ctx,
        command="clip groove amount set",
        args={"track": track, "clip": clip, "value": value},
        action=_run,
    )


@groove_app.command("clear")
def clip_groove_clear(
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
        return get_client(ctx).clip_groove_clear(track, clip)

    execute_command(
        ctx,
        command="clip groove clear",
        args={"track": track, "clip": clip},
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


@name_app.command("set-many")
def clip_name_set_many(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    map_: Annotated[
        str,
        typer.Option("--map", help="Comma-separated clip:name pairs (e.g. 1:Main,2:Var)"),
    ],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        assignments = _parse_clip_name_assignments(map_)
        client = get_client(ctx)
        updated = [
            client.set_clip_name(track=track, clip=clip_index, name=clip_name)
            for clip_index, clip_name in assignments
        ]
        return {
            "track": track,
            "updated_count": len(updated),
            "updated": updated,
        }

    execute_command(
        ctx,
        command="clip name set-many",
        args={"track": track, "map": map_},
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
    dst_clip: Annotated[
        int | None,
        typer.Argument(help="Destination clip slot index (0-based)"),
    ] = None,
    to: Annotated[
        str | None,
        typer.Option("--to", help="Comma-separated destination clip slot indexes (0-based)"),
    ] = None,
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
        single_dst_clip, many_dst_clips = _parse_duplicate_destinations(
            src_clip=src_clip,
            dst_clip=dst_clip,
            to=to,
        )
        return get_client(ctx).clip_duplicate(
            track=track,
            src_clip=src_clip,
            dst_clip=single_dst_clip,
            dst_clips=many_dst_clips,
        )

    execute_command(
        ctx,
        command="clip duplicate",
        args={"track": track, "src_clip": src_clip, "dst_clip": dst_clip, "to": to},
        action=_run,
    )


@clip_app.command("duplicate-many")
def clip_duplicate_many(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    src_clip: Annotated[int, typer.Argument(help="Source clip slot index (0-based)")],
    to: Annotated[
        str,
        typer.Option("--to", help="Comma-separated destination clip slot indexes (0-based)"),
    ],
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
        _single_dst_clip, many_dst_clips = _parse_duplicate_destinations(
            src_clip=src_clip,
            dst_clip=None,
            to=to,
        )
        assert many_dst_clips is not None
        return get_client(ctx).clip_duplicate(
            track=track,
            src_clip=src_clip,
            dst_clips=many_dst_clips,
        )

    execute_command(
        ctx,
        command="clip duplicate-many",
        args={"track": track, "src_clip": src_clip, "to": to},
        action=_run,
    )


@clip_app.command("place-pattern")
def clip_place_pattern(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[
        int,
        typer.Option("--clip", help="Source clip slot index to place (0-based)"),
    ],
    scenes: Annotated[
        str,
        typer.Option(
            "--scenes",
            help=(
                "Scene selectors: comma-separated indexes/ranges/names "
                "(e.g. 2,4,6 or 2-6 or Intro,Drop)"
            ),
        ),
    ],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        src_clip = require_non_negative(
            "clip",
            clip,
            hint="Use a valid source clip slot index.",
        )
        client = get_client(ctx)
        dst_clips = _parse_place_pattern_destinations(
            src_clip=src_clip,
            scenes=scenes,
            load_scenes=client.scenes_list,
        )
        return client.clip_duplicate(
            track=track,
            src_clip=src_clip,
            dst_clips=dst_clips,
        )

    execute_command(
        ctx,
        command="clip place-pattern",
        args={"track": track, "clip": clip, "scenes": scenes},
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
groove_app.add_typer(groove_amount_app, name="amount")
clip_app.add_typer(groove_app, name="groove")


def register(app: typer.Typer) -> None:
    app.add_typer(clip_app, name="clip")
