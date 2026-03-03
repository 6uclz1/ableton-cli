from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

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
NOTE_KEYS = frozenset({"pitch", "start_time", "duration", "velocity", "mute"})


class RemoteErrorCode(str, Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    PROTOCOL_VERSION_MISMATCH = "PROTOCOL_VERSION_MISMATCH"
    TIMEOUT = "TIMEOUT"
    REMOTE_BUSY = "REMOTE_BUSY"
    BATCH_STEP_FAILED = "BATCH_STEP_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class RemoteErrorReason(str, Enum):
    NOT_SUPPORTED_BY_LIVE_API = "not_supported_by_live_api"


def details_with_reason(reason: RemoteErrorReason, /, **details: Any) -> dict[str, Any]:
    return {
        "reason": reason.value,
        **details,
    }


@dataclass(slots=True)
class CommandError(Exception):
    code: RemoteErrorCode | str
    message: str
    hint: str | None = None
    details: dict[str, Any] | None = None


class _SongTransportBackend(Protocol):
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

    def transport_position_get(self) -> dict[str, Any]: ...

    def transport_position_set(self, beats: float) -> dict[str, Any]: ...

    def transport_rewind(self) -> dict[str, Any]: ...

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


class _TracksClipsBackend(Protocol):
    def create_clip(self, track: int, clip: int, length: float) -> dict[str, Any]: ...

    def add_notes_to_clip(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
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

    def clip_notes_quantize(
        self,
        track: int,
        clip: int,
        grid: float,
        strength: float,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def clip_notes_humanize(
        self,
        track: int,
        clip: int,
        timing: float,
        velocity: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def clip_notes_velocity_scale(
        self,
        track: int,
        clip: int,
        scale: float,
        offset: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def clip_notes_transpose(
        self,
        track: int,
        clip: int,
        semitones: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def clip_groove_get(self, track: int, clip: int) -> dict[str, Any]: ...

    def clip_groove_set(self, track: int, clip: int, target: str) -> dict[str, Any]: ...

    def clip_groove_amount_set(self, track: int, clip: int, value: float) -> dict[str, Any]: ...

    def clip_groove_clear(self, track: int, clip: int) -> dict[str, Any]: ...

    def set_clip_name(self, track: int, clip: int, name: str) -> dict[str, Any]: ...

    def fire_clip(self, track: int, clip: int) -> dict[str, Any]: ...

    def stop_clip(self, track: int, clip: int) -> dict[str, Any]: ...

    def clip_active_get(self, track: int, clip: int) -> dict[str, Any]: ...

    def clip_active_set(self, track: int, clip: int, value: bool) -> dict[str, Any]: ...

    def clip_duplicate(
        self,
        track: int,
        src_clip: int,
        dst_clip: int | None,
        dst_clips: list[int] | None,
    ) -> dict[str, Any]: ...

    def clip_cut_to_drum_rack(
        self,
        source_track: int | None,
        source_clip: int | None,
        source_uri: str | None,
        source_path: str | None,
        target_track: int | None,
        grid: float | None,
        slice_count: int | None,
        start_pad: int,
        create_trigger_clip: bool,
        trigger_clip_slot: int | None,
    ) -> dict[str, Any]: ...

    def scenes_list(self) -> dict[str, Any]: ...

    def create_scene(self, index: int) -> dict[str, Any]: ...

    def set_scene_name(self, scene: int, name: str) -> dict[str, Any]: ...

    def fire_scene(self, scene: int) -> dict[str, Any]: ...

    def scenes_move(self, from_index: int, to_index: int) -> dict[str, Any]: ...

    def stop_all_clips(self) -> dict[str, Any]: ...

    def arrangement_record_start(self) -> dict[str, Any]: ...

    def arrangement_record_stop(self) -> dict[str, Any]: ...

    def arrangement_clip_create(
        self,
        track: int,
        start_time: float,
        length: float,
        audio_path: str | None,
        notes: list[dict[str, Any]] | None,
    ) -> dict[str, Any]: ...

    def arrangement_clip_list(self, track: int | None) -> dict[str, Any]: ...

    def arrangement_clip_notes_add(
        self,
        track: int,
        index: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    def arrangement_clip_notes_get(
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def arrangement_clip_notes_clear(
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def arrangement_clip_notes_replace(
        self,
        track: int,
        index: int,
        notes: list[dict[str, Any]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]: ...

    def arrangement_clip_notes_import_browser(
        self,
        track: int,
        index: int,
        target_uri: str | None,
        target_path: str | None,
        mode: str,
        import_length: bool,
        import_groove: bool,
    ) -> dict[str, Any]: ...

    def arrangement_clip_delete(
        self,
        track: int,
        index: int | None,
        start: float | None,
        end: float | None,
        delete_all: bool,
    ) -> dict[str, Any]: ...

    def arrangement_from_session(self, scenes: list[dict[str, Any]]) -> dict[str, Any]: ...

    def tracks_delete(self, track: int) -> dict[str, Any]: ...


class _BrowserBackend(Protocol):
    def load_instrument_or_effect(
        self,
        track: int,
        uri: str | None,
        path: str | None,
        target_track_mode: str,
        clip_slot: int | None,
        preserve_track_name: bool,
        notes_mode: str | None,
        import_length: bool,
        import_groove: bool,
    ) -> dict[str, Any]: ...

    def get_browser_tree(self, category_type: str) -> dict[str, Any]: ...

    def get_browser_items_at_path(self, path: str) -> dict[str, Any]: ...

    def get_browser_item(self, uri: str | None, path: str | None) -> dict[str, Any]: ...

    def get_browser_categories(self, category_type: str) -> dict[str, Any]: ...

    def get_browser_items(
        self,
        path: str,
        item_type: str,
        limit: int,
        offset: int,
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


class _DevicesBackend(Protocol):
    def set_device_parameter(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]: ...

    def find_synth_devices(
        self,
        track: int | None,
        synth_type: str | None,
    ) -> dict[str, Any]: ...

    def list_synth_parameters(self, track: int, device: int) -> dict[str, Any]: ...

    def set_synth_parameter_safe(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
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
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
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


class CommandBackend(
    _SongTransportBackend,
    _TracksClipsBackend,
    _BrowserBackend,
    _DevicesBackend,
    Protocol,
):
    pass
