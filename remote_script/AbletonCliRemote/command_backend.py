from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .effect_specs import SUPPORTED_EFFECT_TYPES
from .synth_specs import SUPPORTED_SYNTH_TYPES

PROTOCOL_VERSION = 2
REMOTE_SCRIPT_VERSION = "0.4.0"
MIN_BPM = 20.0
MAX_BPM = 999.0
MIN_VOLUME = 0.0
MAX_VOLUME = 1.0
MIN_PANNING = -1.0
MAX_PANNING = 1.0
NOTE_PITCH_MIN = 0
NOTE_PITCH_MAX = 127
NOTE_VELOCITY_MIN = 1
NOTE_VELOCITY_MAX = 127
_NOTE_KEYS = {"pitch", "start_time", "duration", "velocity", "mute"}


@dataclass(slots=True)
class CommandError(Exception):
    code: str
    message: str
    hint: str | None = None
    details: dict[str, Any] | None = None


class CommandBackend(Protocol):
    def ping_info(self) -> dict[str, Any]: ...

    def song_info(self) -> dict[str, Any]: ...

    def song_new(self) -> dict[str, Any]: ...

    def song_save(self, path: str) -> dict[str, Any]: ...

    def song_export_audio(self, path: str) -> dict[str, Any]: ...

    def get_session_info(self) -> dict[str, Any]: ...

    def session_snapshot(self) -> dict[str, Any]: ...

    def get_track_info(self, track: int) -> dict[str, Any]: ...

    def tracks_list(self) -> dict[str, Any]: ...

    def create_midi_track(self, index: int) -> dict[str, Any]: ...

    def create_audio_track(self, index: int) -> dict[str, Any]: ...

    def set_track_name(self, track: int, name: str) -> dict[str, Any]: ...

    def transport_play(self) -> dict[str, Any]: ...

    def transport_stop(self) -> dict[str, Any]: ...

    def transport_toggle(self) -> dict[str, Any]: ...

    def start_playback(self) -> dict[str, Any]: ...

    def stop_playback(self) -> dict[str, Any]: ...

    def transport_tempo_get(self) -> dict[str, Any]: ...

    def transport_tempo_set(self, bpm: float) -> dict[str, Any]: ...

    def set_tempo(self, tempo: float) -> dict[str, Any]: ...

    def track_volume_get(self, track: int) -> dict[str, Any]: ...

    def track_volume_set(self, track: int, value: float) -> dict[str, Any]: ...

    def track_mute_get(self, track: int) -> dict[str, Any]: ...

    def track_mute_set(self, track: int, value: bool) -> dict[str, Any]: ...

    def track_solo_get(self, track: int) -> dict[str, Any]: ...

    def track_solo_set(self, track: int, value: bool) -> dict[str, Any]: ...

    def track_arm_get(self, track: int) -> dict[str, Any]: ...

    def track_arm_set(self, track: int, value: bool) -> dict[str, Any]: ...

    def track_panning_get(self, track: int) -> dict[str, Any]: ...

    def track_panning_set(self, track: int, value: float) -> dict[str, Any]: ...

    def create_clip(self, track: int, clip: int, length: float) -> dict[str, Any]: ...

    def add_notes_to_clip(
        self, track: int, clip: int, notes: list[dict[str, Any]]
    ) -> dict[str, Any]: ...

    def get_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def clear_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def replace_clip_notes(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def set_clip_name(self, track: int, clip: int, name: str) -> dict[str, Any]: ...

    def fire_clip(self, track: int, clip: int) -> dict[str, Any]: ...

    def stop_clip(self, track: int, clip: int) -> dict[str, Any]: ...

    def clip_duplicate(self, track: int, src_clip: int, dst_clip: int) -> dict[str, Any]: ...

    def load_instrument_or_effect(
        self, track: int, uri: str | None, path: str | None
    ) -> dict[str, Any]: ...

    def get_browser_tree(self, category_type: str) -> dict[str, Any]: ...

    def get_browser_items_at_path(self, path: str) -> dict[str, Any]: ...

    def get_browser_item(self, uri: str | None, path: str | None) -> dict[str, Any]: ...

    def get_browser_categories(self, category_type: str) -> dict[str, Any]: ...

    def get_browser_items(
        self, path: str, item_type: str, limit: int, offset: int
    ) -> dict[str, Any]: ...

    def search_browser_items(
        self,
        query: str,
        path: str | None,
        item_type: str,
        limit: int,
        offset: int,
        exact: bool,
        case_sensitive: bool,
    ) -> dict[str, Any]: ...

    def load_drum_kit(
        self,
        track: int,
        rack_uri: str,
        kit_uri: str | None,
        kit_path: str | None,
    ) -> dict[str, Any]: ...

    def scenes_list(self) -> dict[str, Any]: ...

    def create_scene(self, index: int) -> dict[str, Any]: ...

    def set_scene_name(self, scene: int, name: str) -> dict[str, Any]: ...

    def fire_scene(self, scene: int) -> dict[str, Any]: ...

    def scenes_move(self, from_index: int, to_index: int) -> dict[str, Any]: ...

    def stop_all_clips(self) -> dict[str, Any]: ...

    def arrangement_record_start(self) -> dict[str, Any]: ...

    def arrangement_record_stop(self) -> dict[str, Any]: ...

    def tracks_delete(self, track: int) -> dict[str, Any]: ...

    def set_device_parameter(
        self, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]: ...

    def find_synth_devices(
        self,
        track: int | None,
        synth_type: str | None,
    ) -> dict[str, Any]: ...

    def list_synth_parameters(self, track: int, device: int) -> dict[str, Any]: ...

    def set_synth_parameter_safe(
        self, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]: ...

    def observe_synth_parameters(self, track: int, device: int) -> dict[str, Any]: ...

    def list_standard_synth_keys(self, synth_type: str) -> dict[str, Any]: ...

    def set_standard_synth_parameter_safe(
        self,
        synth_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]: ...

    def observe_standard_synth_state(
        self,
        synth_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]: ...

    def find_effect_devices(
        self,
        track: int | None,
        effect_type: str | None,
    ) -> dict[str, Any]: ...

    def list_effect_parameters(self, track: int, device: int) -> dict[str, Any]: ...

    def set_effect_parameter_safe(
        self, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]: ...

    def observe_effect_parameters(self, track: int, device: int) -> dict[str, Any]: ...

    def list_standard_effect_keys(self, effect_type: str) -> dict[str, Any]: ...

    def set_standard_effect_parameter_safe(
        self,
        effect_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]: ...

    def observe_standard_effect_state(
        self,
        effect_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]: ...


def _invalid_argument(message: str, hint: str) -> CommandError:
    return CommandError(code="INVALID_ARGUMENT", message=message, hint=hint)


def _as_int(name: str, value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise _invalid_argument(
            message=f"{name} must be an integer",
            hint=f"Pass a valid integer for '{name}'.",
        ) from exc


def _as_float(name: str, value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise _invalid_argument(
            message=f"{name} must be a number",
            hint=f"Pass a valid numeric value for '{name}'.",
        ) from exc


def _as_str(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise _invalid_argument(
            message=f"{name} must be a string",
            hint=f"Pass a valid string for '{name}'.",
        )
    return value


def _non_empty_string(name: str, value: Any) -> str:
    parsed = _as_str(name, value).strip()
    if not parsed:
        raise _invalid_argument(
            message=f"{name} must not be empty",
            hint=f"Pass a non-empty value for '{name}'.",
        )
    return parsed


def _track_index(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed < 0:
        raise _invalid_argument(
            message=f"{name} must be >= 0",
            hint="Use a valid index from listing commands.",
        )
    return parsed


def _optional_track_index(name: str, value: Any) -> int | None:
    if value is None:
        return None
    return _track_index(name, value)


def _insert_index(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed < -1:
        raise _invalid_argument(
            message=f"{name} must be >= -1",
            hint="Use -1 for append or a non-negative insertion index.",
        )
    return parsed


def _tempo(value: Any) -> float:
    parsed = _as_float("bpm", value)
    if parsed < MIN_BPM or parsed > MAX_BPM:
        raise _invalid_argument(
            message=f"bpm must be between {MIN_BPM} and {MAX_BPM}",
            hint="Use a tempo value like 120.",
        )
    return parsed


def _volume(value: Any) -> float:
    parsed = _as_float("value", value)
    if parsed < MIN_VOLUME or parsed > MAX_VOLUME:
        raise _invalid_argument(
            message=f"value must be between {MIN_VOLUME} and {MAX_VOLUME}",
            hint="Use a normalized volume value in [0.0, 1.0].",
        )
    return parsed


def _panning(value: Any) -> float:
    parsed = _as_float("value", value)
    if parsed < MIN_PANNING or parsed > MAX_PANNING:
        raise _invalid_argument(
            message=f"value must be between {MIN_PANNING} and {MAX_PANNING}",
            hint="Use a normalized panning value in [-1.0, 1.0].",
        )
    return parsed


def _clip_length(value: Any) -> float:
    length = _as_float("length", value)
    if length <= 0:
        raise _invalid_argument(
            message="length must be > 0",
            hint="Use a positive clip length in beats.",
        )
    return length


def _positive_int(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed <= 0:
        raise _invalid_argument(
            message=f"{name} must be > 0",
            hint=f"Pass a positive integer for '{name}'.",
        )
    return parsed


def _non_negative_int(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed < 0:
        raise _invalid_argument(
            message=f"{name} must be >= 0",
            hint=f"Pass a non-negative integer for '{name}'.",
        )
    return parsed


def _as_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise _invalid_argument(
            message=f"{name} must be a boolean",
            hint=f"Pass true or false for '{name}'.",
        )
    return value


def _optional_float(name: str, value: Any) -> float | None:
    if value is None:
        return None
    return _as_float(name, value)


def _optional_int(name: str, value: Any) -> int | None:
    if value is None:
        return None
    return _as_int(name, value)


def _clip_notes_filter(args: dict[str, Any]) -> tuple[float | None, float | None, int | None]:
    start_time = _optional_float("start_time", args.get("start_time"))
    end_time = _optional_float("end_time", args.get("end_time"))
    pitch = _optional_int("pitch", args.get("pitch"))

    if start_time is not None and start_time < 0:
        raise _invalid_argument(
            message=f"start_time must be >= 0, got {start_time}",
            hint="Use a non-negative start_time.",
        )
    if end_time is not None and end_time <= 0:
        raise _invalid_argument(
            message=f"end_time must be > 0, got {end_time}",
            hint="Use a positive end_time.",
        )
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise _invalid_argument(
            message=(
                f"end_time must be greater than start_time (start={start_time}, end={end_time})"
            ),
            hint="Use a valid [start_time, end_time) range.",
        )
    if pitch is not None and (pitch < NOTE_PITCH_MIN or pitch > NOTE_PITCH_MAX):
        raise _invalid_argument(
            message=f"pitch must be between {NOTE_PITCH_MIN} and {NOTE_PITCH_MAX}",
            hint="Use a valid MIDI pitch.",
        )

    return start_time, end_time, pitch


def _synth_type(value: Any) -> str:
    parsed = _non_empty_string("synth_type", value).lower()
    if parsed not in SUPPORTED_SYNTH_TYPES:
        raise _invalid_argument(
            message=f"synth_type must be one of {', '.join(SUPPORTED_SYNTH_TYPES)}",
            hint="Use a supported synth type.",
        )
    return parsed


def _effect_type(value: Any) -> str:
    parsed = _non_empty_string("effect_type", value).lower()
    if parsed not in SUPPORTED_EFFECT_TYPES:
        raise _invalid_argument(
            message=f"effect_type must be one of {', '.join(SUPPORTED_EFFECT_TYPES)}",
            hint="Use a supported effect type.",
        )
    return parsed


def _notes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise _invalid_argument(
            message="notes must be an array",
            hint="Pass notes as a JSON array of note objects.",
        )

    parsed_notes: list[dict[str, Any]] = []
    for index, note in enumerate(value):
        if not isinstance(note, dict):
            raise _invalid_argument(
                message=f"notes[{index}] must be an object",
                hint="Each note must include pitch/start_time/duration/velocity/mute.",
            )

        keys = set(note.keys())
        if keys != _NOTE_KEYS:
            raise _invalid_argument(
                message=f"notes[{index}] must include exactly {sorted(_NOTE_KEYS)}",
                hint="Provide all required note fields and no extra keys.",
            )

        pitch = _as_int("pitch", note["pitch"])
        if pitch < NOTE_PITCH_MIN or pitch > NOTE_PITCH_MAX:
            raise _invalid_argument(
                message=f"pitch must be between {NOTE_PITCH_MIN} and {NOTE_PITCH_MAX}",
                hint="Use a valid MIDI pitch.",
            )

        start_time = _as_float("start_time", note["start_time"])
        if start_time < 0:
            raise _invalid_argument(
                message="start_time must be >= 0",
                hint="Use a non-negative note start time.",
            )

        duration = _as_float("duration", note["duration"])
        if duration <= 0:
            raise _invalid_argument(
                message="duration must be > 0",
                hint="Use a positive note duration.",
            )

        velocity = _as_int("velocity", note["velocity"])
        if velocity < NOTE_VELOCITY_MIN or velocity > NOTE_VELOCITY_MAX:
            raise _invalid_argument(
                message=(f"velocity must be between {NOTE_VELOCITY_MIN} and {NOTE_VELOCITY_MAX}"),
                hint="Use a valid MIDI velocity.",
            )

        mute = note["mute"]
        if not isinstance(mute, bool):
            raise _invalid_argument(
                message="mute must be a boolean",
                hint="Set mute to true or false.",
            )

        parsed_notes.append(
            {
                "pitch": pitch,
                "start_time": start_time,
                "duration": duration,
                "velocity": velocity,
                "mute": mute,
            }
        )

    return parsed_notes


def _supported_command_names() -> list[str]:
    return sorted(_HANDLERS.keys())


def _command_set_hash(commands: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update("\n".join(commands).encode("utf-8"))
    return digest.hexdigest()


def _handle_ping(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    result = dict(backend.ping_info())
    supported_commands = _supported_command_names()
    result["supported_commands"] = supported_commands
    result["command_set_hash"] = _command_set_hash(supported_commands)
    return result


def _handle_song_info(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.song_info()


def _handle_song_new(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.song_new()


def _handle_song_save(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    return backend.song_save(path)


def _handle_song_export_audio(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    return backend.song_export_audio(path)


def _handle_get_session_info(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.get_session_info()


def _handle_session_snapshot(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.session_snapshot()


def _handle_get_track_info(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.get_track_info(track)


def _handle_tracks_list(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.tracks_list()


def _handle_create_midi_track(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    index = _insert_index("index", args.get("index", -1))
    return backend.create_midi_track(index)


def _handle_create_audio_track(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    index = _insert_index("index", args.get("index", -1))
    return backend.create_audio_track(index)


def _handle_set_track_name(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    name = _non_empty_string("name", args.get("name"))
    return backend.set_track_name(track, name)


def _handle_transport_play(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_play()


def _handle_transport_stop(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_stop()


def _handle_transport_toggle(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_toggle()


def _handle_start_playback(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.start_playback()


def _handle_stop_playback(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.stop_playback()


def _handle_transport_tempo_get(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_tempo_get()


def _handle_transport_tempo_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_tempo_set(_tempo(args.get("bpm")))


def _handle_set_tempo(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.set_tempo(_tempo(args.get("tempo")))


def _handle_track_volume_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_volume_get(track)


def _handle_track_volume_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_volume_set(track, _volume(args.get("value")))


def _handle_track_mute_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_mute_get(track)


def _handle_track_mute_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    value = _as_bool("value", args.get("value"))
    return backend.track_mute_set(track, value)


def _handle_track_solo_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_solo_get(track)


def _handle_track_solo_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    value = _as_bool("value", args.get("value"))
    return backend.track_solo_set(track, value)


def _handle_track_arm_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_arm_get(track)


def _handle_track_arm_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    value = _as_bool("value", args.get("value"))
    return backend.track_arm_set(track, value)


def _handle_track_panning_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_panning_get(track)


def _handle_track_panning_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    value = _panning(args.get("value"))
    return backend.track_panning_set(track, value)


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


def _handle_load_instrument_or_effect(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    uri_raw = args.get("uri")
    path_raw = args.get("path")
    if uri_raw is None and path_raw is None:
        raise _invalid_argument(
            message="Exactly one of uri or path must be provided",
            hint="Provide --uri or --path.",
        )
    if uri_raw is not None and path_raw is not None:
        raise _invalid_argument(
            message="uri and path are mutually exclusive",
            hint="Provide only one of uri or path.",
        )
    uri = _non_empty_string("uri", uri_raw) if uri_raw is not None else None
    path = _non_empty_string("path", path_raw) if path_raw is not None else None
    return backend.load_instrument_or_effect(track, uri, path)


def _handle_get_browser_tree(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    category_type = _non_empty_string("category_type", args.get("category_type", "all"))
    return backend.get_browser_tree(category_type)


def _handle_get_browser_items_at_path(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    return backend.get_browser_items_at_path(path)


def _handle_get_browser_item(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    uri_raw = args.get("uri")
    path_raw = args.get("path")
    if uri_raw is None and path_raw is None:
        raise _invalid_argument(
            message="Exactly one of uri or path must be provided",
            hint="Provide --uri or --path.",
        )
    if uri_raw is not None and path_raw is not None:
        raise _invalid_argument(
            message="uri and path are mutually exclusive",
            hint="Provide only one of uri or path.",
        )
    uri = _non_empty_string("uri", uri_raw) if uri_raw is not None else None
    path = _non_empty_string("path", path_raw) if path_raw is not None else None
    return backend.get_browser_item(uri=uri, path=path)


def _handle_get_browser_categories(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    category_type = _non_empty_string("category_type", args.get("category_type", "all"))
    return backend.get_browser_categories(category_type)


def _handle_get_browser_items(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    item_type = _non_empty_string("item_type", args.get("item_type", "all"))
    if item_type not in {"all", "folder", "device", "loadable"}:
        raise _invalid_argument(
            message=f"item_type must be one of all/folder/device/loadable, got {item_type}",
            hint="Use a supported item type.",
        )
    limit = _positive_int("limit", args.get("limit", 100))
    offset = _non_negative_int("offset", args.get("offset", 0))
    return backend.get_browser_items(path, item_type, limit, offset)


def _handle_search_browser_items(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    query = _non_empty_string("query", args.get("query"))
    path_raw = args.get("path")
    path = _non_empty_string("path", path_raw) if path_raw is not None else None

    item_type = _non_empty_string("item_type", args.get("item_type", "loadable"))
    if item_type not in {"all", "folder", "device", "loadable"}:
        raise _invalid_argument(
            message=f"item_type must be one of all/folder/device/loadable, got {item_type}",
            hint="Use a supported item type.",
        )

    limit = _positive_int("limit", args.get("limit", 50))
    offset = _non_negative_int("offset", args.get("offset", 0))
    exact = _as_bool("exact", args.get("exact", False))
    case_sensitive = _as_bool("case_sensitive", args.get("case_sensitive", False))

    return backend.search_browser_items(
        query=query,
        path=path,
        item_type=item_type,
        limit=limit,
        offset=offset,
        exact=exact,
        case_sensitive=case_sensitive,
    )


def _handle_load_drum_kit(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    rack_uri = _non_empty_string("rack_uri", args.get("rack_uri"))
    kit_uri_raw = args.get("kit_uri")
    kit_path_raw = args.get("kit_path")
    if kit_uri_raw is None and kit_path_raw is None:
        raise _invalid_argument(
            message="Exactly one of kit_uri or kit_path must be provided",
            hint="Provide kit_uri or kit_path.",
        )
    if kit_uri_raw is not None and kit_path_raw is not None:
        raise _invalid_argument(
            message="kit_uri and kit_path are mutually exclusive",
            hint="Provide only one of kit_uri or kit_path.",
        )
    kit_uri = _non_empty_string("kit_uri", kit_uri_raw) if kit_uri_raw is not None else None
    kit_path = _non_empty_string("kit_path", kit_path_raw) if kit_path_raw is not None else None
    return backend.load_drum_kit(track, rack_uri, kit_uri, kit_path)


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
    backend: CommandBackend, _args: dict[str, Any]
) -> dict[str, Any]:
    return backend.arrangement_record_start()


def _handle_arrangement_record_stop(
    backend: CommandBackend, _args: dict[str, Any]
) -> dict[str, Any]:
    return backend.arrangement_record_stop()


def _handle_tracks_delete(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.tracks_delete(track)


def _handle_set_device_parameter(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    parameter = _track_index("parameter", args.get("parameter"))
    value = _as_float("value", args.get("value"))
    return backend.set_device_parameter(track, device, parameter, value)


def _handle_find_synth_devices(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _optional_track_index("track", args.get("track"))
    synth_type_raw = args.get("synth_type")
    synth_type = _synth_type(synth_type_raw) if synth_type_raw is not None else None
    return backend.find_synth_devices(track, synth_type)


def _handle_list_synth_parameters(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.list_synth_parameters(track, device)


def _handle_set_synth_parameter_safe(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    parameter = _track_index("parameter", args.get("parameter"))
    value = _as_float("value", args.get("value"))
    return backend.set_synth_parameter_safe(track, device, parameter, value)


def _handle_observe_synth_parameters(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_synth_parameters(track, device)


def _handle_list_standard_synth_keys(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    synth_type = _synth_type(args.get("synth_type"))
    return backend.list_standard_synth_keys(synth_type)


def _handle_set_standard_synth_parameter_safe(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    synth_type = _synth_type(args.get("synth_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    key = _non_empty_string("key", args.get("key"))
    value = _as_float("value", args.get("value"))
    return backend.set_standard_synth_parameter_safe(
        synth_type=synth_type,
        track=track,
        device=device,
        key=key,
        value=value,
    )


def _handle_observe_standard_synth_state(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    synth_type = _synth_type(args.get("synth_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_standard_synth_state(
        synth_type=synth_type,
        track=track,
        device=device,
    )


def _handle_find_effect_devices(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _optional_track_index("track", args.get("track"))
    effect_type_raw = args.get("effect_type")
    effect_type = _effect_type(effect_type_raw) if effect_type_raw is not None else None
    return backend.find_effect_devices(track, effect_type)


def _handle_list_effect_parameters(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.list_effect_parameters(track, device)


def _handle_set_effect_parameter_safe(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    parameter = _track_index("parameter", args.get("parameter"))
    value = _as_float("value", args.get("value"))
    return backend.set_effect_parameter_safe(track, device, parameter, value)


def _handle_observe_effect_parameters(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_effect_parameters(track, device)


def _handle_list_standard_effect_keys(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    return backend.list_standard_effect_keys(effect_type)


def _handle_set_standard_effect_parameter_safe(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    key = _non_empty_string("key", args.get("key"))
    value = _as_float("value", args.get("value"))
    return backend.set_standard_effect_parameter_safe(
        effect_type=effect_type,
        track=track,
        device=device,
        key=key,
        value=value,
    )


def _handle_observe_standard_effect_state(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_standard_effect_state(
        effect_type=effect_type,
        track=track,
        device=device,
    )


def _parse_batch_steps(args: dict[str, Any]) -> list[dict[str, Any]]:
    raw_steps = args.get("steps")
    if not isinstance(raw_steps, list):
        raise _invalid_argument(
            message="steps must be an array",
            hint="Pass a JSON array of step objects.",
        )
    if not raw_steps:
        raise _invalid_argument(
            message="steps must not be empty",
            hint="Provide at least one step.",
        )

    steps: list[dict[str, Any]] = []
    for index, item in enumerate(raw_steps):
        if not isinstance(item, dict):
            raise _invalid_argument(
                message=f"steps[{index}] must be an object",
                hint="Each step must include name and optional args.",
            )
        name = _non_empty_string("name", item.get("name"))
        raw_args = item.get("args", {})
        if not isinstance(raw_args, dict):
            raise _invalid_argument(
                message=f"steps[{index}].args must be an object",
                hint="Pass args as a JSON object.",
            )
        if name == "execute_batch":
            raise _invalid_argument(
                message="steps[].name cannot be execute_batch",
                hint="Nested batch execution is not supported.",
            )
        steps.append({"name": name, "args": raw_args})
    return steps


def _handle_execute_batch(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    steps = _parse_batch_steps(args)
    results: list[dict[str, Any]] = []

    for index, step in enumerate(steps):
        step_name = str(step["name"])
        step_args = dict(step["args"])
        try:
            step_result = dispatch_command(backend, step_name, step_args)
            results.append(
                {
                    "index": index,
                    "name": step_name,
                    "result": step_result,
                }
            )
        except CommandError as exc:
            raise CommandError(
                code="BATCH_STEP_FAILED",
                message=f"Batch step failed at index {index}: {step_name}",
                hint="Inspect error.details for failed step context.",
                details={
                    "failed_step_index": index,
                    "failed_step_name": step_name,
                    "failed_error": {
                        "code": exc.code,
                        "message": exc.message,
                        "hint": exc.hint,
                        "details": exc.details,
                    },
                    "results": results,
                },
            ) from exc

    return {
        "step_count": len(steps),
        "stopped_at": None,
        "results": results,
    }


_HANDLERS: dict[str, Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]] = {
    "ping": _handle_ping,
    "song_info": _handle_song_info,
    "song_new": _handle_song_new,
    "song_save": _handle_song_save,
    "song_export_audio": _handle_song_export_audio,
    "get_session_info": _handle_get_session_info,
    "session_snapshot": _handle_session_snapshot,
    "get_track_info": _handle_get_track_info,
    "tracks_list": _handle_tracks_list,
    "create_midi_track": _handle_create_midi_track,
    "create_audio_track": _handle_create_audio_track,
    "set_track_name": _handle_set_track_name,
    "transport_play": _handle_transport_play,
    "transport_stop": _handle_transport_stop,
    "transport_toggle": _handle_transport_toggle,
    "start_playback": _handle_start_playback,
    "stop_playback": _handle_stop_playback,
    "transport_tempo_get": _handle_transport_tempo_get,
    "transport_tempo_set": _handle_transport_tempo_set,
    "set_tempo": _handle_set_tempo,
    "track_volume_get": _handle_track_volume_get,
    "track_volume_set": _handle_track_volume_set,
    "track_mute_get": _handle_track_mute_get,
    "track_mute_set": _handle_track_mute_set,
    "track_solo_get": _handle_track_solo_get,
    "track_solo_set": _handle_track_solo_set,
    "track_arm_get": _handle_track_arm_get,
    "track_arm_set": _handle_track_arm_set,
    "track_panning_get": _handle_track_panning_get,
    "track_panning_set": _handle_track_panning_set,
    "create_clip": _handle_create_clip,
    "add_notes_to_clip": _handle_add_notes_to_clip,
    "get_clip_notes": _handle_get_clip_notes,
    "clear_clip_notes": _handle_clear_clip_notes,
    "replace_clip_notes": _handle_replace_clip_notes,
    "set_clip_name": _handle_set_clip_name,
    "fire_clip": _handle_fire_clip,
    "stop_clip": _handle_stop_clip,
    "clip_duplicate": _handle_clip_duplicate,
    "load_instrument_or_effect": _handle_load_instrument_or_effect,
    "get_browser_tree": _handle_get_browser_tree,
    "get_browser_items_at_path": _handle_get_browser_items_at_path,
    "get_browser_item": _handle_get_browser_item,
    "get_browser_categories": _handle_get_browser_categories,
    "get_browser_items": _handle_get_browser_items,
    "search_browser_items": _handle_search_browser_items,
    "load_drum_kit": _handle_load_drum_kit,
    "scenes_list": _handle_scenes_list,
    "create_scene": _handle_create_scene,
    "set_scene_name": _handle_set_scene_name,
    "fire_scene": _handle_fire_scene,
    "scenes_move": _handle_scenes_move,
    "stop_all_clips": _handle_stop_all_clips,
    "arrangement_record_start": _handle_arrangement_record_start,
    "arrangement_record_stop": _handle_arrangement_record_stop,
    "tracks_delete": _handle_tracks_delete,
    "set_device_parameter": _handle_set_device_parameter,
    "find_synth_devices": _handle_find_synth_devices,
    "list_synth_parameters": _handle_list_synth_parameters,
    "set_synth_parameter_safe": _handle_set_synth_parameter_safe,
    "observe_synth_parameters": _handle_observe_synth_parameters,
    "list_standard_synth_keys": _handle_list_standard_synth_keys,
    "set_standard_synth_parameter_safe": _handle_set_standard_synth_parameter_safe,
    "observe_standard_synth_state": _handle_observe_standard_synth_state,
    "find_effect_devices": _handle_find_effect_devices,
    "list_effect_parameters": _handle_list_effect_parameters,
    "set_effect_parameter_safe": _handle_set_effect_parameter_safe,
    "observe_effect_parameters": _handle_observe_effect_parameters,
    "list_standard_effect_keys": _handle_list_standard_effect_keys,
    "set_standard_effect_parameter_safe": _handle_set_standard_effect_parameter_safe,
    "observe_standard_effect_state": _handle_observe_standard_effect_state,
    "execute_batch": _handle_execute_batch,
}


def dispatch_command(backend: CommandBackend, name: str, args: dict[str, Any]) -> dict[str, Any]:
    handler = _HANDLERS.get(name)
    if handler is None:
        raise CommandError(
            code="INVALID_ARGUMENT",
            message=f"Unknown command: {name}",
            hint="Use a supported command name.",
        )
    return handler(backend, args)
