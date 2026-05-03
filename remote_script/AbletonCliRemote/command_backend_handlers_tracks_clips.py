from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _absolute_path_or_none,
    _as_bool,
    _as_int,
    _clip_length,
    _clip_notes_filter,
    _clip_quantize_grid,
    _humanize_velocity_amount,
    _insert_index,
    _invalid_argument,
    _non_empty_string,
    _non_negative_float,
    _non_negative_int,
    _notes,
    _optional_track_index,
    _parse_exclusive_string_args,
    _positive_int,
    _track_index,
    _unit_interval,
    _uri_or_path_target,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _handle_create_clip(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    length = _clip_length(args.get("length"))
    return backend.create_clip(track, clip, length)


def _handle_add_notes_to_clip(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    notes = _notes(args.get("notes"))
    return backend.add_notes_to_clip(track, clip, notes)


def _handle_get_clip_notes(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.get_clip_notes(track, clip, start_time, end_time, pitch)


def _handle_clear_clip_notes(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.clear_clip_notes(track, clip, start_time, end_time, pitch)


def _handle_replace_clip_notes(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    notes = _notes(args.get("notes"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.replace_clip_notes(track, clip, notes, start_time, end_time, pitch)


def _handle_clip_notes_quantize(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    grid = _clip_quantize_grid(args.get("grid"))
    strength = _unit_interval("strength", args.get("strength", 1.0))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.clip_notes_quantize(track, clip, grid, strength, start_time, end_time, pitch)


def _handle_clip_notes_humanize(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    timing = _non_negative_float("timing", args.get("timing"))
    velocity = _humanize_velocity_amount(args.get("velocity"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.clip_notes_humanize(track, clip, timing, velocity, start_time, end_time, pitch)


def _handle_clip_notes_velocity_scale(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    scale = _non_negative_float("scale", args.get("scale"))
    offset = _as_int("offset", args.get("offset"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.clip_notes_velocity_scale(
        track,
        clip,
        scale,
        offset,
        start_time,
        end_time,
        pitch,
    )


def _handle_clip_notes_transpose(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    semitones = _as_int("semitones", args.get("semitones"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.clip_notes_transpose(track, clip, semitones, start_time, end_time, pitch)


def _handle_clip_groove_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.clip_groove_get(track, clip)


def _handle_clip_groove_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    target = _uri_or_path_target("target", args.get("target"))
    return backend.clip_groove_set(track, clip, target)


def _handle_clip_groove_amount_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    value = _unit_interval("value", args.get("value"))
    return backend.clip_groove_amount_set(track, clip, value)


def _handle_clip_groove_clear(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.clip_groove_clear(track, clip)


def _handle_clip_props_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.clip_props_get(track, clip)


def _handle_clip_loop_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    start = _non_negative_float("start", args.get("start"))
    end = _non_negative_float("end", args.get("end"))
    if end <= start:
        raise _invalid_argument(
            message=f"end must be greater than start (start={start}, end={end})",
            hint="Use a valid loop range.",
        )
    enabled = _as_bool("enabled", args.get("enabled"))
    return backend.clip_loop_set(track, clip, start, end, enabled)


def _handle_clip_marker_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    start_marker = _non_negative_float("start_marker", args.get("start_marker"))
    end_marker = _non_negative_float("end_marker", args.get("end_marker"))
    return backend.clip_marker_set(track, clip, start_marker, end_marker)


def _handle_clip_warp_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.clip_warp_get(track, clip)


def _handle_clip_warp_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    enabled = _as_bool("enabled", args.get("enabled"))
    mode = args.get("mode")
    parsed_mode = _non_empty_string("mode", mode) if mode is not None else None
    return backend.clip_warp_set(track, clip, enabled, parsed_mode)


def _handle_clip_warp_marker_list(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.clip_warp_marker_list(track, clip)


def _handle_clip_warp_marker_add(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    sample_time = _non_negative_float("sample_time", args.get("sample_time"))
    beat_time = _non_negative_float("beat_time", args.get("beat_time"))
    return backend.clip_warp_marker_add(track, clip, sample_time, beat_time)


def _handle_clip_gain_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    db = float(args.get("db"))
    return backend.clip_gain_set(track, clip, db)


def _handle_clip_transpose_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    semitones = _as_int("semitones", args.get("semitones"))
    return backend.clip_transpose_set(track, clip, semitones)


def _handle_clip_file_replace(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    audio_path = _absolute_path_or_none("audio_path", args.get("audio_path"))
    if audio_path is None:
        raise _invalid_argument(
            message="audio_path is required", hint="Pass an absolute audio_path."
        )
    return backend.clip_file_replace(track, clip, audio_path)


def _handle_set_clip_name(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    name = _non_empty_string("name", args.get("name"))
    return backend.set_clip_name(track, clip, name)


def _handle_fire_clip(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.fire_clip(track, clip)


def _handle_stop_clip(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.stop_clip(track, clip)


def _handle_clip_duplicate(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    src_clip = _track_index("src_clip", args.get("src_clip"))
    dst_clip_raw = args.get("dst_clip")
    dst_clips_raw = args.get("dst_clips")
    if dst_clip_raw is None and dst_clips_raw is None:
        raise _invalid_argument(
            message="Either dst_clip or dst_clips must be provided",
            hint="Provide one destination clip slot or multiple destination clip slots.",
        )
    if dst_clip_raw is not None and dst_clips_raw is not None:
        raise _invalid_argument(
            message="dst_clip and dst_clips are mutually exclusive",
            hint="Provide either dst_clip or dst_clips.",
        )
    if dst_clip_raw is not None:
        dst_clip = _track_index("dst_clip", dst_clip_raw)
        return backend.clip_duplicate(track, src_clip, dst_clip, None)

    if not isinstance(dst_clips_raw, list):
        raise _invalid_argument(
            message="dst_clips must be an array of clip indexes",
            hint="Pass dst_clips as a list of non-negative integers.",
        )
    if not dst_clips_raw:
        raise _invalid_argument(
            message="dst_clips must not be empty",
            hint="Pass at least one destination clip index.",
        )
    parsed_dst_clips: list[int] = []
    seen: set[int] = set()
    for index, value in enumerate(dst_clips_raw):
        parsed_value = _track_index(f"dst_clips[{index}]", value)
        if parsed_value == src_clip:
            raise _invalid_argument(
                message=f"dst_clips[{index}] must differ from src_clip ({src_clip})",
                hint="Use destination clip slots that are not the source clip.",
            )
        if parsed_value in seen:
            raise _invalid_argument(
                message=f"dst_clips[{index}] duplicates clip index {parsed_value}",
                hint="Remove duplicate destination clip indexes.",
            )
        seen.add(parsed_value)
        parsed_dst_clips.append(parsed_value)
    return backend.clip_duplicate(track, src_clip, None, parsed_dst_clips)


def _handle_clip_cut_to_drum_rack(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    source_track_raw = args.get("source_track")
    source_clip_raw = args.get("source_clip")
    source_uri_raw = args.get("source_uri")
    source_path_raw = args.get("source_path")
    has_session_source = source_track_raw is not None or source_clip_raw is not None
    has_browser_source = source_uri_raw is not None or source_path_raw is not None

    source_track: int | None = None
    source_clip: int | None = None
    source_uri: str | None = None
    source_path: str | None = None
    if has_session_source and has_browser_source:
        raise _invalid_argument(
            message="session source and browser source are mutually exclusive",
            hint="Use source_track/source_clip or source_uri/source_path.",
        )
    if has_session_source:
        source_track = _optional_track_index("source_track", source_track_raw)
        source_clip = _optional_track_index("source_clip", source_clip_raw)
        if source_track is None or source_clip is None:
            raise _invalid_argument(
                message="source_track and source_clip must be provided together",
                hint="Provide both source_track and source_clip for session clip source.",
            )
    elif has_browser_source:
        source_uri, source_path = _parse_exclusive_string_args(
            args,
            first_key="source_uri",
            second_key="source_path",
            required_hint="Provide source_uri or source_path.",
        )
    else:
        raise _invalid_argument(
            message="Either session source or browser source must be provided",
            hint="Use source_track/source_clip or source_uri/source_path.",
        )

    grid_raw = args.get("grid")
    slice_count_raw = args.get("slice_count")
    if grid_raw is None and slice_count_raw is None:
        raise _invalid_argument(
            message="Either grid or slice_count must be provided",
            hint="Provide one slicing mode.",
        )
    if grid_raw is not None and slice_count_raw is not None:
        raise _invalid_argument(
            message="grid and slice_count are mutually exclusive",
            hint="Provide either grid or slice_count.",
        )
    grid = _clip_quantize_grid(grid_raw) if grid_raw is not None else None
    slice_count = (
        _positive_int("slice_count", slice_count_raw) if slice_count_raw is not None else None
    )

    target_track = _optional_track_index("target_track", args.get("target_track"))
    start_pad = _non_negative_int("start_pad", args.get("start_pad", 0))
    create_trigger_clip = _as_bool("create_trigger_clip", args.get("create_trigger_clip", False))
    trigger_clip_slot_raw = args.get("trigger_clip_slot")
    if trigger_clip_slot_raw is None:
        trigger_clip_slot = 0 if create_trigger_clip else None
    else:
        trigger_clip_slot = _non_negative_int("trigger_clip_slot", trigger_clip_slot_raw)
        if not create_trigger_clip:
            raise _invalid_argument(
                message="trigger_clip_slot requires create_trigger_clip=true",
                hint="Set create_trigger_clip to true when passing trigger_clip_slot.",
            )

    return backend.clip_cut_to_drum_rack(
        source_track=source_track,
        source_clip=source_clip,
        source_uri=source_uri,
        source_path=source_path,
        target_track=target_track,
        grid=grid,
        slice_count=slice_count,
        start_pad=start_pad,
        create_trigger_clip=create_trigger_clip,
        trigger_clip_slot=trigger_clip_slot,
    )


def _handle_clip_active_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    return backend.clip_active_get(track, clip)


def _handle_clip_active_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    value = _as_bool("value", args.get("value"))
    return backend.clip_active_set(track, clip, value)


def _handle_scenes_list(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.scenes_list()


def _handle_create_scene(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    index = _insert_index("index", args.get("index", -1))
    return backend.create_scene(index)


def _handle_set_scene_name(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    scene = _track_index("scene", args.get("scene"))
    name = _non_empty_string("name", args.get("name"))
    return backend.set_scene_name(scene, name)


def _handle_fire_scene(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    scene = _track_index("scene", args.get("scene"))
    return backend.fire_scene(scene)


def _handle_scenes_move(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    from_index = _track_index("from", args.get("from"))
    to_index = _track_index("to", args.get("to"))
    return backend.scenes_move(from_index, to_index)


def _handle_stop_all_clips(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.stop_all_clips()


def _handle_arrangement_record_start(
    backend: CommandBackend,
    _args: dict[str, Any],
) -> dict[str, Any]:
    return backend.arrangement_record_start()


def _handle_arrangement_record_stop(
    backend: CommandBackend,
    _args: dict[str, Any],
) -> dict[str, Any]:
    return backend.arrangement_record_stop()


def _handle_arrangement_clip_create(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    start_time = _non_negative_float("start_time", args.get("start_time"))
    length = _clip_length(args.get("length"))
    audio_path = _absolute_path_or_none("audio_path", args.get("audio_path"))
    notes_raw = args.get("notes")
    notes = _notes(notes_raw) if notes_raw is not None else None
    return backend.arrangement_clip_create(track, start_time, length, audio_path, notes)


def _handle_arrangement_clip_list(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _optional_track_index("track", args.get("track"))
    return backend.arrangement_clip_list(track)


def _handle_arrangement_clip_notes_add(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    notes = _notes(args.get("notes"))
    return backend.arrangement_clip_notes_add(track, index, notes)


def _handle_arrangement_clip_notes_get(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.arrangement_clip_notes_get(track, index, start_time, end_time, pitch)


def _handle_arrangement_clip_notes_clear(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.arrangement_clip_notes_clear(track, index, start_time, end_time, pitch)


def _handle_arrangement_clip_notes_replace(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    notes = _notes(args.get("notes"))
    start_time, end_time, pitch = _clip_notes_filter(args)
    return backend.arrangement_clip_notes_replace(track, index, notes, start_time, end_time, pitch)


def _handle_arrangement_clip_notes_import_browser(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    target_uri, target_path = _parse_exclusive_string_args(
        args,
        first_key="target_uri",
        second_key="target_path",
        required_hint="Provide target_uri or target_path.",
    )
    mode = _non_empty_string("mode", args.get("mode", "replace")).lower()
    if mode not in {"replace", "append"}:
        raise _invalid_argument(
            message=f"mode must be one of replace/append, got {mode}",
            hint="Use mode replace or append.",
        )
    import_length = _as_bool("import_length", args.get("import_length", False))
    import_groove = _as_bool("import_groove", args.get("import_groove", False))
    return backend.arrangement_clip_notes_import_browser(
        track,
        index,
        target_uri,
        target_path,
        mode,
        import_length,
        import_groove,
    )


def _handle_arrangement_clip_delete(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _optional_track_index("index", args.get("index"))
    start_raw = args.get("start")
    end_raw = args.get("end")
    delete_all = _as_bool("all", args.get("all", False))

    has_range_value = start_raw is not None or end_raw is not None
    if has_range_value and (start_raw is None or end_raw is None):
        raise _invalid_argument(
            message="start and end must be provided together",
            hint="Provide both start and end for range delete mode.",
        )
    mode_count = int(index is not None) + int(has_range_value) + int(delete_all)
    if mode_count != 1:
        raise _invalid_argument(
            message="Exactly one delete mode must be selected: index, range, or all",
            hint="Use one of: index | start+end | all=true.",
        )

    start = _non_negative_float("start", start_raw) if start_raw is not None else None
    end = _non_negative_float("end", end_raw) if end_raw is not None else None
    if start is not None and end is not None and end <= start:
        raise _invalid_argument(
            message=f"end must be greater than start (start={start}, end={end})",
            hint="Use a valid [start, end) range.",
        )
    return backend.arrangement_clip_delete(track, index, start, end, delete_all)


def _handle_arrangement_clip_props_get(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    return backend.arrangement_clip_props_get(track, index)


def _handle_arrangement_clip_loop_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    start = _non_negative_float("start", args.get("start"))
    end = _non_negative_float("end", args.get("end"))
    if end <= start:
        raise _invalid_argument(
            message=f"end must be greater than start (start={start}, end={end})",
            hint="Use a valid loop range.",
        )
    enabled = _as_bool("enabled", args.get("enabled"))
    return backend.arrangement_clip_loop_set(track, index, start, end, enabled)


def _handle_arrangement_clip_marker_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    start_marker = _non_negative_float("start_marker", args.get("start_marker"))
    end_marker = _non_negative_float("end_marker", args.get("end_marker"))
    return backend.arrangement_clip_marker_set(track, index, start_marker, end_marker)


def _handle_arrangement_clip_warp_get(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    return backend.arrangement_clip_warp_get(track, index)


def _handle_arrangement_clip_warp_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    enabled = _as_bool("enabled", args.get("enabled"))
    mode = args.get("mode")
    parsed_mode = _non_empty_string("mode", mode) if mode is not None else None
    return backend.arrangement_clip_warp_set(track, index, enabled, parsed_mode)


def _handle_arrangement_clip_gain_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    db = float(args.get("db"))
    return backend.arrangement_clip_gain_set(track, index, db)


def _handle_arrangement_clip_transpose_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    semitones = _as_int("semitones", args.get("semitones"))
    return backend.arrangement_clip_transpose_set(track, index, semitones)


def _handle_arrangement_clip_file_replace(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    index = _track_index("index", args.get("index"))
    audio_path = _absolute_path_or_none("audio_path", args.get("audio_path"))
    if audio_path is None:
        raise _invalid_argument(
            message="audio_path is required", hint="Pass an absolute audio_path."
        )
    return backend.arrangement_clip_file_replace(track, index, audio_path)


def _arrangement_scene_specs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise _invalid_argument(
            message="scenes must be a non-empty array",
            hint='Pass scenes as [{"scene":0,"duration_beats":24.0}, ...].',
        )
    parsed: list[dict[str, Any]] = []
    for position, item in enumerate(value):
        if not isinstance(item, dict):
            raise _invalid_argument(
                message=f"scenes[{position}] must be an object",
                hint="Each scene entry must include scene and duration_beats.",
            )
        scene = _track_index(f"scenes[{position}].scene", item.get("scene"))
        duration = _non_negative_float(
            f"scenes[{position}].duration_beats",
            item.get("duration_beats"),
        )
        if duration <= 0:
            raise _invalid_argument(
                message=f"scenes[{position}].duration_beats must be > 0",
                hint="Use positive beat durations.",
            )
        parsed.append({"scene": scene, "duration_beats": duration})
    return parsed


def _handle_arrangement_from_session(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    scenes = _arrangement_scene_specs(args.get("scenes"))
    return backend.arrangement_from_session(scenes)


def _handle_tracks_delete(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.tracks_delete(track)


TRACKS_CLIPS_HANDLERS: dict[str, Handler] = {
    "create_clip": _handle_create_clip,
    "add_notes_to_clip": _handle_add_notes_to_clip,
    "get_clip_notes": _handle_get_clip_notes,
    "clear_clip_notes": _handle_clear_clip_notes,
    "replace_clip_notes": _handle_replace_clip_notes,
    "clip_notes_quantize": _handle_clip_notes_quantize,
    "clip_notes_humanize": _handle_clip_notes_humanize,
    "clip_notes_velocity_scale": _handle_clip_notes_velocity_scale,
    "clip_notes_transpose": _handle_clip_notes_transpose,
    "clip_groove_get": _handle_clip_groove_get,
    "clip_groove_set": _handle_clip_groove_set,
    "clip_groove_amount_set": _handle_clip_groove_amount_set,
    "clip_groove_clear": _handle_clip_groove_clear,
    "clip_props_get": _handle_clip_props_get,
    "clip_loop_set": _handle_clip_loop_set,
    "clip_marker_set": _handle_clip_marker_set,
    "clip_warp_get": _handle_clip_warp_get,
    "clip_warp_set": _handle_clip_warp_set,
    "clip_warp_marker_list": _handle_clip_warp_marker_list,
    "clip_warp_marker_add": _handle_clip_warp_marker_add,
    "clip_gain_set": _handle_clip_gain_set,
    "clip_transpose_set": _handle_clip_transpose_set,
    "clip_file_replace": _handle_clip_file_replace,
    "set_clip_name": _handle_set_clip_name,
    "fire_clip": _handle_fire_clip,
    "stop_clip": _handle_stop_clip,
    "clip_active_get": _handle_clip_active_get,
    "clip_active_set": _handle_clip_active_set,
    "clip_duplicate": _handle_clip_duplicate,
    "clip_cut_to_drum_rack": _handle_clip_cut_to_drum_rack,
    "scenes_list": _handle_scenes_list,
    "create_scene": _handle_create_scene,
    "set_scene_name": _handle_set_scene_name,
    "fire_scene": _handle_fire_scene,
    "scenes_move": _handle_scenes_move,
    "stop_all_clips": _handle_stop_all_clips,
    "arrangement_record_start": _handle_arrangement_record_start,
    "arrangement_record_stop": _handle_arrangement_record_stop,
    "arrangement_clip_create": _handle_arrangement_clip_create,
    "arrangement_clip_list": _handle_arrangement_clip_list,
    "arrangement_clip_notes_add": _handle_arrangement_clip_notes_add,
    "arrangement_clip_notes_get": _handle_arrangement_clip_notes_get,
    "arrangement_clip_notes_clear": _handle_arrangement_clip_notes_clear,
    "arrangement_clip_notes_replace": _handle_arrangement_clip_notes_replace,
    "arrangement_clip_notes_import_browser": _handle_arrangement_clip_notes_import_browser,
    "arrangement_clip_delete": _handle_arrangement_clip_delete,
    "arrangement_clip_props_get": _handle_arrangement_clip_props_get,
    "arrangement_clip_loop_set": _handle_arrangement_clip_loop_set,
    "arrangement_clip_marker_set": _handle_arrangement_clip_marker_set,
    "arrangement_clip_warp_get": _handle_arrangement_clip_warp_get,
    "arrangement_clip_warp_set": _handle_arrangement_clip_warp_set,
    "arrangement_clip_gain_set": _handle_arrangement_clip_gain_set,
    "arrangement_clip_transpose_set": _handle_arrangement_clip_transpose_set,
    "arrangement_clip_file_replace": _handle_arrangement_clip_file_replace,
    "arrangement_from_session": _handle_arrangement_from_session,
    "tracks_delete": _handle_tracks_delete,
}
