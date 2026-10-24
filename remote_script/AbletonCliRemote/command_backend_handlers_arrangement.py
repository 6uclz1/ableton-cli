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
    _invalid_argument,
    _non_empty_string,
    _non_negative_float,
    _notes,
    _optional_track_index,
    _parse_exclusive_string_args,
    _track_index,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


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


ARRANGEMENT_HANDLERS: dict[str, Handler] = {
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
}
