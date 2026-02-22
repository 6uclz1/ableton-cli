from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _as_bool,
    _clip_length,
    _clip_notes_filter,
    _insert_index,
    _non_empty_string,
    _notes,
    _track_index,
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
    dst_clip = _track_index("dst_clip", args.get("dst_clip"))
    return backend.clip_duplicate(track, src_clip, dst_clip)


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


def _handle_tracks_delete(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.tracks_delete(track)


TRACKS_CLIPS_HANDLERS: dict[str, Handler] = {
    "create_clip": _handle_create_clip,
    "add_notes_to_clip": _handle_add_notes_to_clip,
    "get_clip_notes": _handle_get_clip_notes,
    "clear_clip_notes": _handle_clear_clip_notes,
    "replace_clip_notes": _handle_replace_clip_notes,
    "set_clip_name": _handle_set_clip_name,
    "fire_clip": _handle_fire_clip,
    "stop_clip": _handle_stop_clip,
    "clip_active_get": _handle_clip_active_get,
    "clip_active_set": _handle_clip_active_set,
    "clip_duplicate": _handle_clip_duplicate,
    "scenes_list": _handle_scenes_list,
    "create_scene": _handle_create_scene,
    "set_scene_name": _handle_set_scene_name,
    "fire_scene": _handle_fire_scene,
    "scenes_move": _handle_scenes_move,
    "stop_all_clips": _handle_stop_all_clips,
    "arrangement_record_start": _handle_arrangement_record_start,
    "arrangement_record_stop": _handle_arrangement_record_stop,
    "tracks_delete": _handle_tracks_delete,
}
