from __future__ import annotations

import pytest

from ableton_cli.capabilities import required_remote_commands
from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command


def _track_selector(index: int) -> dict[str, object]:
    return {"track_ref": {"mode": "index", "index": index}}


def _device_selector(track: int, device: int) -> dict[str, object]:
    return {
        "track_ref": {"mode": "index", "index": track},
        "device_ref": {"mode": "index", "index": device},
    }


def _parameter_selector(track: int, device: int, parameter: int) -> dict[str, object]:
    return {
        "track_ref": {"mode": "index", "index": track},
        "device_ref": {"mode": "index", "index": device},
        "parameter_ref": {"mode": "index", "index": parameter},
    }


class _BackendStub:
    def ping_info(self):  # noqa: ANN201
        return {
            "pong": True,
            "api_support": {
                "song_new_supported": True,
                "song_save_supported": True,
                "song_export_audio_supported": True,
                "arrangement_record_start_supported": True,
                "arrangement_record_stop_supported": True,
                "arrangement_record_supported": True,
            },
        }

    def get_session_info(self):  # noqa: ANN201
        return {"tempo": 120.0}

    def session_snapshot(self):  # noqa: ANN201
        return {
            "song_info": {"tempo": 120.0},
            "session_info": {"track_count": 0},
            "tracks_list": {"tracks": []},
            "scenes_list": {"scenes": [{"index": 0, "name": "Intro"}]},
        }

    def song_info(self):  # noqa: ANN201
        return {"tempo": 120.0}

    def song_new(self):  # noqa: ANN201
        return {"created": True}

    def song_undo(self):  # noqa: ANN201
        return {"undone": True}

    def song_redo(self):  # noqa: ANN201
        return {"redone": True}

    def song_save(self, path: str):  # noqa: ANN201
        return {"saved": True, "path": path}

    def song_export_audio(self, path: str):  # noqa: ANN201
        return {"exported": True, "path": path}

    def resolve_track_ref(self, track_ref: dict[str, object]) -> int:
        return int(track_ref["index"])

    def resolve_device_ref(self, track: int, device_ref: dict[str, object]) -> int:  # noqa: ARG002
        return int(device_ref["index"])

    def resolve_parameter_ref(
        self,
        track: int,  # noqa: ARG002
        device: int,  # noqa: ARG002
        parameter_ref: dict[str, object],
    ) -> int:
        if parameter_ref["mode"] == "key":
            return 0
        return int(parameter_ref["index"])

    def get_track_info(self, track: int):  # noqa: ANN201
        return {"index": track}

    def tracks_list(self):  # noqa: ANN201
        return {"tracks": []}

    def create_midi_track(self, index: int):  # noqa: ANN201
        return {"index": index, "kind": "midi"}

    def create_audio_track(self, index: int):  # noqa: ANN201
        return {"index": index, "kind": "audio"}

    def set_track_name(self, track: int, name: str):  # noqa: ANN201
        return {"track": track, "name": name}

    def transport_play(self):  # noqa: ANN201
        return {"is_playing": True}

    def transport_stop(self):  # noqa: ANN201
        return {"is_playing": False}

    def transport_toggle(self):  # noqa: ANN201
        return {"is_playing": True}

    def transport_tempo_get(self):  # noqa: ANN201
        return {"tempo": 120.0}

    def transport_tempo_set(self, bpm: float):  # noqa: ANN201
        return {"tempo": bpm}

    def transport_position_get(self):  # noqa: ANN201
        return {"current_time": 4.0, "beat_position": 4.0}

    def transport_position_set(self, beats: float):  # noqa: ANN201
        return {"current_time": beats, "beat_position": beats}

    def transport_rewind(self):  # noqa: ANN201
        return {"current_time": 0.0, "beat_position": 0.0}

    def track_volume_get(self, track: int):  # noqa: ANN201
        return {"track": track, "volume": 0.5}

    def track_volume_set(self, track: int, value: float):  # noqa: ANN201
        return {"track": track, "volume": value}

    def create_clip(self, track: int, clip: int, length: float):  # noqa: ANN201
        return {"track": track, "clip": clip, "length": length}

    def add_notes_to_clip(self, track: int, clip: int, notes: list[dict[str, object]]):  # noqa: ANN201
        return {"track": track, "clip": clip, "note_count": len(notes)}

    def get_clip_notes(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "notes": [],
            "note_count": 0,
        }

    def clear_clip_notes(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": 1,
        }

    def replace_clip_notes(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        notes: list[dict[str, object]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": 1,
            "added_count": len(notes),
        }

    def set_clip_name(self, track: int, clip: int, name: str):  # noqa: ANN201
        return {"track": track, "clip": clip, "name": name}

    def fire_clip(self, track: int, clip: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "fired": True}

    def stop_clip(self, track: int, clip: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "stopped": True}

    def clip_active_get(self, track: int, clip: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "active": True}

    def clip_active_set(self, track: int, clip: int, value: bool):  # noqa: ANN201
        return {"track": track, "clip": clip, "active": value}

    def clip_duplicate(  # noqa: ANN201
        self,
        track: int,
        src_clip: int,
        dst_clip: int | None,
        dst_clips: list[int] | None,
    ):
        if dst_clip is not None:
            return {"track": track, "src_clip": src_clip, "dst_clip": dst_clip, "duplicated": True}
        return {
            "track": track,
            "src_clip": src_clip,
            "dst_clips": dst_clips or [],
            "duplicated": True,
        }

    def clip_cut_to_drum_rack(  # noqa: ANN201
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
    ):
        return {
            "source_track": source_track,
            "source_clip": source_clip,
            "source_uri": source_uri,
            "source_path": source_path,
            "target_track": target_track,
            "grid": grid,
            "slice_count": slice_count,
            "start_pad": start_pad,
            "create_trigger_clip": create_trigger_clip,
            "trigger_clip_slot": trigger_clip_slot,
            "loaded": True,
        }

    def clip_notes_quantize(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        grid: float,
        strength: float,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "grid": grid,
            "strength": strength,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 1,
        }

    def clip_notes_humanize(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        timing: float,
        velocity: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "timing": timing,
            "velocity": velocity,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 1,
        }

    def clip_notes_velocity_scale(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        scale: float,
        offset: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "scale": scale,
            "offset": offset,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 1,
        }

    def clip_notes_transpose(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        semitones: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "semitones": semitones,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 1,
        }

    def clip_groove_get(self, track: int, clip: int):  # noqa: ANN201
        return {
            "track": track,
            "clip": clip,
            "has_groove": True,
            "groove_uri": "groove:hip-hop-boom-bap-16ths-90",
            "groove_path": "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr",
            "groove_name": "Hip Hop Boom Bap 16ths 90 bpm.agr",
            "amount": 0.5,
        }

    def clip_groove_set(self, track: int, clip: int, target: str):  # noqa: ANN201
        return {
            "track": track,
            "clip": clip,
            "has_groove": True,
            "target": target,
            "groove_uri": "groove:hip-hop-boom-bap-16ths-90",
            "groove_path": "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr",
            "groove_name": "Hip Hop Boom Bap 16ths 90 bpm.agr",
            "amount": 0.5,
        }

    def clip_groove_amount_set(self, track: int, clip: int, value: float):  # noqa: ANN201
        return {
            "track": track,
            "clip": clip,
            "has_groove": True,
            "groove_uri": "groove:hip-hop-boom-bap-16ths-90",
            "groove_path": "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr",
            "groove_name": "Hip Hop Boom Bap 16ths 90 bpm.agr",
            "amount": value,
        }

    def clip_groove_clear(self, track: int, clip: int):  # noqa: ANN201
        return {
            "track": track,
            "clip": clip,
            "has_groove": False,
            "groove_uri": None,
            "groove_path": None,
            "groove_name": None,
            "amount": 0.5,
        }

    def load_instrument_or_effect(  # noqa: ANN201
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
    ):
        return {
            "track": track,
            "uri": uri,
            "path": path,
            "target_track_mode": target_track_mode,
            "clip_slot": clip_slot,
            "preserve_track_name": preserve_track_name,
            "notes_mode": notes_mode,
            "import_length": import_length,
            "import_groove": import_groove,
            "loaded": True,
        }

    def get_browser_tree(self, category_type: str):  # noqa: ANN201
        return {"category_type": category_type}

    def get_browser_items_at_path(self, path: str):  # noqa: ANN201
        return {"path": path}

    def get_browser_item(self, uri: str | None, path: str | None):  # noqa: ANN201
        return {"uri": uri, "path": path}

    def get_browser_categories(self, category_type: str):  # noqa: ANN201
        return {"category_type": category_type}

    def get_browser_items(  # noqa: ANN201
        self,
        path: str,
        item_type: str,
        limit: int,
        offset: int,
    ):
        return {
            "path": path,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "returned": 0,
            "total_matches": 0,
            "has_more": False,
            "duration_ms": 0.1,
            "items": [],
        }

    def search_browser_items(  # noqa: ANN201
        self,
        query: str,
        path: str | None,
        item_type: str,
        limit: int,
        offset: int,
        exact: bool,
        case_sensitive: bool,
    ):
        return {
            "query": query,
            "path": path,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "exact": exact,
            "case_sensitive": case_sensitive,
        }

    def load_drum_kit(  # noqa: ANN201
        self,
        track: int,
        rack_uri: str,
        kit_uri: str | None,
        kit_path: str | None,
    ):
        return {
            "track": track,
            "rack_uri": rack_uri,
            "kit_uri": kit_uri,
            "kit_path": kit_path,
        }

    def scenes_list(self):  # noqa: ANN201
        return {"scenes": [{"index": 0, "name": "Intro"}]}

    def create_scene(self, index: int):  # noqa: ANN201
        return {"index": index, "name": "Scene"}

    def set_scene_name(self, scene: int, name: str):  # noqa: ANN201
        return {"scene": scene, "name": name}

    def fire_scene(self, scene: int):  # noqa: ANN201
        return {"scene": scene, "fired": True}

    def scenes_move(self, from_index: int, to_index: int):  # noqa: ANN201
        return {"from": from_index, "to": to_index, "moved": True}

    def stop_all_clips(self):  # noqa: ANN201
        return {"stopped": True}

    def arrangement_record_start(self):  # noqa: ANN201
        return {"recording": True}

    def arrangement_record_stop(self):  # noqa: ANN201
        return {"recording": False}

    def arrangement_clip_create(  # noqa: ANN201
        self,
        track: int,
        start_time: float,
        length: float,
        audio_path: str | None,
        notes: list[dict[str, object]] | None = None,
    ):
        if track == 1 and notes is not None:
            raise CommandError(
                code="INVALID_ARGUMENT",
                message="notes are supported only for MIDI arrangement clips",
            )
        payload = {
            "track": track,
            "start_time": start_time,
            "length": length,
            "arrangement_view_focused": True,
            "created": True,
        }
        if audio_path is None:
            payload["kind"] = "midi"
            if notes is not None:
                payload["notes_added"] = len(notes)
            return payload
        payload["kind"] = "audio"
        payload["audio_path"] = audio_path
        return payload

    def arrangement_clip_list(self, track: int | None):  # noqa: ANN201
        clips = [
            {
                "track": 0,
                "index": 0,
                "name": "Clip A",
                "start_time": 8.0,
                "length": 4.0,
                "is_audio_clip": False,
                "is_midi_clip": True,
            },
            {
                "track": 1,
                "index": 0,
                "name": "Clip B",
                "start_time": 16.0,
                "length": 8.0,
                "is_audio_clip": True,
                "is_midi_clip": False,
            },
        ]
        if track is not None:
            clips = [clip for clip in clips if clip["track"] == track]
        return {"track": track, "clip_count": len(clips), "clips": clips}

    def arrangement_clip_notes_add(  # noqa: ANN201
        self,
        track: int,
        index: int,
        notes: list[dict[str, object]],
    ):
        return {"track": track, "index": index, "note_count": len(notes)}

    def arrangement_clip_notes_get(  # noqa: ANN201
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "index": index,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "notes": [],
            "note_count": 0,
        }

    def arrangement_clip_notes_clear(  # noqa: ANN201
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "index": index,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": 1,
        }

    def arrangement_clip_notes_replace(  # noqa: ANN201
        self,
        track: int,
        index: int,
        notes: list[dict[str, object]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "index": index,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": 1,
            "added_count": len(notes),
        }

    def arrangement_clip_notes_import_browser(  # noqa: ANN201
        self,
        track: int,
        index: int,
        target_uri: str | None,
        target_path: str | None,
        mode: str,
        import_length: bool,
        import_groove: bool,
    ):
        return {
            "track": track,
            "index": index,
            "target_uri": target_uri,
            "target_path": target_path,
            "mode": mode,
            "import_length": import_length,
            "import_groove": import_groove,
            "notes_imported": 2,
        }

    def arrangement_clip_delete(  # noqa: ANN201
        self,
        track: int,
        index: int | None,
        start: float | None,
        end: float | None,
        delete_all: bool,
    ):
        if index is not None:
            return {"track": track, "mode": "index", "deleted_count": 1, "deleted_indexes": [index]}
        if delete_all:
            return {"track": track, "mode": "all", "deleted_count": 2, "deleted_indexes": [0, 1]}
        return {"track": track, "mode": "range", "deleted_count": 1, "deleted_indexes": [1]}

    def arrangement_from_session(self, scenes: list[dict[str, object]]):  # noqa: ANN201
        return {"scene_count": len(scenes), "created_count": 4, "scenes": scenes}

    def track_mute_get(self, track: int):  # noqa: ANN201
        return {"track": track, "mute": False}

    def track_mute_set(self, track: int, value: bool):  # noqa: ANN201
        return {"track": track, "mute": value}

    def track_solo_get(self, track: int):  # noqa: ANN201
        return {"track": track, "solo": False}

    def track_solo_set(self, track: int, value: bool):  # noqa: ANN201
        return {"track": track, "solo": value}

    def track_arm_get(self, track: int):  # noqa: ANN201
        return {"track": track, "arm": False}

    def track_arm_set(self, track: int, value: bool):  # noqa: ANN201
        return {"track": track, "arm": value}

    def track_panning_get(self, track: int):  # noqa: ANN201
        return {"track": track, "panning": 0.0}

    def track_panning_set(self, track: int, value: float):  # noqa: ANN201
        return {"track": track, "panning": value}

    def track_send_get(self, track: int, send: int):  # noqa: ANN201
        return {"track": track, "send": send, "value": 0.2}

    def track_send_set(self, track: int, send: int, value: float):  # noqa: ANN201
        return {"track": track, "send": send, "value": value}

    def return_tracks_list(self):  # noqa: ANN201
        return {"return_tracks": [{"index": 0, "name": "Reverb"}]}

    def return_track_volume_get(self, return_track: int):  # noqa: ANN201
        return {"return_track": return_track, "volume": 0.5}

    def return_track_volume_set(self, return_track: int, value: float):  # noqa: ANN201
        return {"return_track": return_track, "volume": value}

    def return_track_mute_get(self, return_track: int):  # noqa: ANN201
        return {"return_track": return_track, "mute": False}

    def return_track_mute_set(self, return_track: int, value: bool):  # noqa: ANN201
        return {"return_track": return_track, "mute": value}

    def return_track_solo_get(self, return_track: int):  # noqa: ANN201
        return {"return_track": return_track, "solo": True}

    def return_track_solo_set(self, return_track: int, value: bool):  # noqa: ANN201
        return {"return_track": return_track, "solo": value}

    def master_info(self):  # noqa: ANN201
        return {"name": "Master", "volume": 0.9, "panning": 0.0}

    def master_volume_get(self):  # noqa: ANN201
        return {"volume": 0.9}

    def master_panning_get(self):  # noqa: ANN201
        return {"panning": 0.0}

    def master_devices_list(self):  # noqa: ANN201
        return {"devices": [{"index": 0, "name": "Limiter"}]}

    def mixer_crossfader_get(self):  # noqa: ANN201
        return {"value": 0.1}

    def mixer_crossfader_set(self, value: float):  # noqa: ANN201
        return {"value": value}

    def mixer_cue_volume_get(self):  # noqa: ANN201
        return {"value": 0.8}

    def mixer_cue_volume_set(self, value: float):  # noqa: ANN201
        return {"value": value}

    def mixer_cue_routing_get(self):  # noqa: ANN201
        return {"routing": "Master", "available_routings": ["Master", "Ext. Out"]}

    def mixer_cue_routing_set(self, routing: str):  # noqa: ANN201
        return {"routing": routing, "available_routings": ["Master", "Ext. Out"]}

    def track_routing_input_get(self, track: int):  # noqa: ANN201
        return {
            "track": track,
            "current": {"type": "Ext. In", "channel": "1/2"},
            "available": {"types": ["Ext. In"], "channels": ["1/2", "3/4"]},
        }

    def track_routing_input_set(
        self,
        track: int,
        routing_type: str,
        routing_channel: str,
    ):  # noqa: ANN201
        return {
            "track": track,
            "current": {"type": routing_type, "channel": routing_channel},
            "available": {"types": ["Ext. In"], "channels": ["1/2", "3/4"]},
        }

    def track_routing_output_get(self, track: int):  # noqa: ANN201
        return {
            "track": track,
            "current": {"type": "Master", "channel": "1/2"},
            "available": {"types": ["Master"], "channels": ["1/2", "3/4"]},
        }

    def track_routing_output_set(
        self,
        track: int,
        routing_type: str,
        routing_channel: str,
    ):  # noqa: ANN201
        return {
            "track": track,
            "current": {"type": routing_type, "channel": routing_channel},
            "available": {"types": ["Master"], "channels": ["1/2", "3/4"]},
        }

    def tracks_delete(self, track: int):  # noqa: ANN201
        return {"track": track, "deleted": True}

    def set_device_parameter(  # noqa: ANN201
        self, track: int, device: int, parameter: int, value: float
    ):
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "value": value,
        }

    def find_synth_devices(  # noqa: ANN201
        self,
        track: int | None,
        synth_type: str | None,
    ):
        return {
            "track": track,
            "synth_type": synth_type,
            "count": 1,
            "devices": [
                {
                    "track": 0,
                    "device": 1,
                    "detected_type": "wavetable",
                }
            ],
        }

    def list_synth_parameters(  # noqa: ANN201
        self,
        track: int,
        device: int,
    ):
        return {
            "track": track,
            "device": device,
            "detected_type": "wavetable",
            "parameters": [
                {
                    "index": 0,
                    "name": "Filter Freq",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "is_enabled": True,
                    "is_quantized": False,
                }
            ],
        }

    def set_synth_parameter_safe(  # noqa: ANN201
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ):
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "before": 0.4,
            "after": value,
        }

    def observe_synth_parameters(  # noqa: ANN201
        self,
        track: int,
        device: int,
    ):
        return {
            "track": track,
            "device": device,
            "detected_type": "wavetable",
            "parameters": [],
        }

    def list_standard_synth_keys(self, synth_type: str):  # noqa: ANN201
        return {
            "synth_type": synth_type,
            "keys": ["filter_cutoff", "filter_resonance"],
            "key_count": 2,
        }

    def set_standard_synth_parameter_safe(  # noqa: ANN201
        self,
        synth_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ):
        return {
            "synth_type": synth_type,
            "track": track,
            "device": device,
            "key": key,
            "before": 0.3,
            "after": value,
        }

    def observe_standard_synth_state(  # noqa: ANN201
        self,
        synth_type: str,
        track: int,
        device: int,
    ):
        return {
            "synth_type": synth_type,
            "track": track,
            "device": device,
            "state": {"filter_cutoff": 0.4},
        }

    def find_effect_devices(  # noqa: ANN201
        self,
        track: int | None,
        effect_type: str | None,
    ):
        return {
            "track": track,
            "effect_type": effect_type,
            "count": 1,
            "devices": [
                {
                    "track": 0,
                    "device": 2,
                    "detected_type": "eq8",
                }
            ],
        }

    def list_effect_parameters(  # noqa: ANN201
        self,
        track: int,
        device: int,
    ):
        return {
            "track": track,
            "device": device,
            "detected_type": "eq8",
            "parameters": [
                {
                    "index": 0,
                    "name": "1 Frequency A",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "is_enabled": True,
                    "is_quantized": False,
                }
            ],
        }

    def set_effect_parameter_safe(  # noqa: ANN201
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ):
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "before": 0.4,
            "after": value,
        }

    def observe_effect_parameters(  # noqa: ANN201
        self,
        track: int,
        device: int,
    ):
        return {
            "track": track,
            "device": device,
            "detected_type": "eq8",
            "parameters": [],
        }

    def list_standard_effect_keys(self, effect_type: str):  # noqa: ANN201
        return {
            "effect_type": effect_type,
            "keys": ["band1_freq", "band1_gain"],
            "key_count": 2,
        }

    def set_standard_effect_parameter_safe(  # noqa: ANN201
        self,
        effect_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ):
        return {
            "effect_type": effect_type,
            "track": track,
            "device": device,
            "key": key,
            "before": 0.3,
            "after": value,
        }

    def observe_standard_effect_state(  # noqa: ANN201
        self,
        effect_type: str,
        track: int,
        device: int,
    ):
        return {
            "effect_type": effect_type,
            "track": track,
            "device": device,
            "state": {"band1_freq": 0.4},
        }


def test_dispatch_calls_backend_for_tempo_set() -> None:
    backend = _BackendStub()
    result = dispatch_command(backend, "transport_tempo_set", {"bpm": 128})
    assert result == {"tempo": 128.0}


def test_dispatch_calls_backend_for_song_undo_redo() -> None:
    backend = _BackendStub()

    undone = dispatch_command(backend, "song_undo", {})
    redone = dispatch_command(backend, "song_redo", {})

    assert undone == {"undone": True}
    assert redone == {"redone": True}


def test_dispatch_calls_backend_for_transport_position_commands() -> None:
    backend = _BackendStub()

    gotten = dispatch_command(backend, "transport_position_get", {})
    set_result = dispatch_command(backend, "transport_position_set", {"beats": 24.0})
    rewound = dispatch_command(backend, "transport_rewind", {})

    assert gotten == {"current_time": 4.0, "beat_position": 4.0}
    assert set_result == {"current_time": 24.0, "beat_position": 24.0}
    assert rewound == {"current_time": 0.0, "beat_position": 0.0}


def test_dispatch_ping_includes_supported_commands_and_hash() -> None:
    backend = _BackendStub()
    result = dispatch_command(backend, "ping", {})

    assert result["pong"] is True
    assert result["api_support"]["song_save_supported"] is True
    assert result["api_support"]["song_export_audio_supported"] is True
    assert result["api_support"]["arrangement_record_supported"] is True
    assert "supported_commands" in result
    assert "command_set_hash" in result
    assert isinstance(result["supported_commands"], list)
    assert isinstance(result["command_set_hash"], str)
    assert "get_clip_notes" in result["supported_commands"]
    assert "song_new" in result["supported_commands"]
    assert "arrangement_record_start" in result["supported_commands"]
    assert "arrangement_clip_create" in result["supported_commands"]
    assert "arrangement_clip_list" in result["supported_commands"]
    assert "clip_duplicate" in result["supported_commands"]
    assert "scenes_move" in result["supported_commands"]
    assert "tracks_delete" in result["supported_commands"]


def test_dispatch_ping_supported_commands_match_required_set() -> None:
    backend = _BackendStub()
    result = dispatch_command(backend, "ping", {})

    assert set(result["supported_commands"]) == required_remote_commands()


def test_dispatch_calls_backend_for_audio_track_creation() -> None:
    backend = _BackendStub()
    result = dispatch_command(backend, "create_audio_track", {"index": 2})
    assert result == {"index": 2, "kind": "audio"}


def test_dispatch_calls_backend_for_device_parameter_set() -> None:
    backend = _BackendStub()
    result = dispatch_command(
        backend,
        "set_device_parameter",
        {**_parameter_selector(1, 0, 3), "value": 0.25},
    )
    assert result == {"track": 1, "device": 0, "parameter": 3, "value": 0.25}


def test_dispatch_calls_backend_for_synth_foundation_commands() -> None:
    backend = _BackendStub()

    found = dispatch_command(
        backend,
        "find_synth_devices",
        {"track": 0, "synth_type": "wavetable"},
    )
    listed = dispatch_command(
        backend,
        "list_synth_parameters",
        _device_selector(0, 1),
    )
    set_result = dispatch_command(
        backend,
        "set_synth_parameter_safe",
        {**_parameter_selector(0, 1, 0), "value": 0.75},
    )
    observed = dispatch_command(
        backend,
        "observe_synth_parameters",
        _device_selector(0, 1),
    )

    assert found["synth_type"] == "wavetable"
    assert found["count"] == 1
    assert listed["parameters"][0]["name"] == "Filter Freq"
    assert set_result["after"] == 0.75
    assert observed["detected_type"] == "wavetable"


def test_dispatch_calls_backend_for_standard_synth_commands() -> None:
    backend = _BackendStub()

    keys = dispatch_command(
        backend,
        "list_standard_synth_keys",
        {"synth_type": "wavetable"},
    )
    set_result = dispatch_command(
        backend,
        "set_standard_synth_parameter_safe",
        {
            "synth_type": "wavetable",
            **_device_selector(0, 1),
            "parameter_ref": {"mode": "key", "key": "filter_cutoff"},
            "value": 0.66,
        },
    )
    observed = dispatch_command(
        backend,
        "observe_standard_synth_state",
        {"synth_type": "wavetable", **_device_selector(0, 1)},
    )

    assert keys == {
        "synth_type": "wavetable",
        "keys": ["filter_cutoff", "filter_resonance"],
        "key_count": 2,
    }
    assert set_result["key"] == "filter_cutoff"
    assert set_result["after"] == 0.66
    assert observed["state"]["filter_cutoff"] == 0.4


def test_dispatch_calls_backend_for_effect_foundation_commands() -> None:
    backend = _BackendStub()

    found = dispatch_command(
        backend,
        "find_effect_devices",
        {"track": 0, "effect_type": "eq8"},
    )
    listed = dispatch_command(
        backend,
        "list_effect_parameters",
        _device_selector(0, 2),
    )
    set_result = dispatch_command(
        backend,
        "set_effect_parameter_safe",
        {**_parameter_selector(0, 2, 0), "value": 0.75},
    )
    observed = dispatch_command(
        backend,
        "observe_effect_parameters",
        _device_selector(0, 2),
    )

    assert found["effect_type"] == "eq8"
    assert found["count"] == 1
    assert listed["parameters"][0]["name"] == "1 Frequency A"
    assert set_result["after"] == 0.75
    assert observed["detected_type"] == "eq8"


def test_dispatch_calls_backend_for_standard_effect_commands() -> None:
    backend = _BackendStub()

    keys = dispatch_command(
        backend,
        "list_standard_effect_keys",
        {"effect_type": "eq8"},
    )
    set_result = dispatch_command(
        backend,
        "set_standard_effect_parameter_safe",
        {
            "effect_type": "eq8",
            **_device_selector(0, 2),
            "parameter_ref": {"mode": "key", "key": "band1_freq"},
            "value": 0.66,
        },
    )
    observed = dispatch_command(
        backend,
        "observe_standard_effect_state",
        {"effect_type": "eq8", **_device_selector(0, 2)},
    )

    assert keys == {
        "effect_type": "eq8",
        "keys": ["band1_freq", "band1_gain"],
        "key_count": 2,
    }
    assert set_result["key"] == "band1_freq"
    assert set_result["after"] == 0.66
    assert observed["state"]["band1_freq"] == 0.4


def test_dispatch_calls_backend_for_browser_search() -> None:
    backend = _BackendStub()
    result = dispatch_command(
        backend,
        "search_browser_items",
        {
            "query": "drift",
            "path": "instruments",
            "item_type": "loadable",
            "limit": 20,
            "offset": 5,
            "exact": True,
            "case_sensitive": True,
        },
    )
    assert result == {
        "query": "drift",
        "path": "instruments",
        "item_type": "loadable",
        "limit": 20,
        "offset": 5,
        "exact": True,
        "case_sensitive": True,
    }


def test_dispatch_calls_backend_for_browser_load_with_path() -> None:
    backend = _BackendStub()
    result = dispatch_command(
        backend,
        "load_instrument_or_effect",
        {"track": 2, "path": "instruments/Drift"},
    )
    assert result == {
        "track": 2,
        "uri": None,
        "path": "instruments/Drift",
        "target_track_mode": "auto",
        "clip_slot": None,
        "preserve_track_name": False,
        "notes_mode": None,
        "import_length": False,
        "import_groove": False,
        "loaded": True,
    }


def test_dispatch_calls_backend_for_browser_load_with_existing_mode_and_clip_slot() -> None:
    backend = _BackendStub()
    result = dispatch_command(
        backend,
        "load_instrument_or_effect",
        {
            "track": 1,
            "path": "sounds/Bass Loop.alc",
            "target_track_mode": "existing",
            "clip_slot": 3,
            "preserve_track_name": True,
        },
    )
    assert result == {
        "track": 1,
        "uri": None,
        "path": "sounds/Bass Loop.alc",
        "target_track_mode": "existing",
        "clip_slot": 3,
        "preserve_track_name": True,
        "notes_mode": None,
        "import_length": False,
        "import_groove": False,
        "loaded": True,
    }


def test_dispatch_calls_backend_for_browser_load_with_notes_mode() -> None:
    backend = _BackendStub()
    result = dispatch_command(
        backend,
        "load_instrument_or_effect",
        {
            "track": 1,
            "path": "sounds/Bass Loop.alc",
            "target_track_mode": "existing",
            "clip_slot": 2,
            "notes_mode": "append",
        },
    )
    assert result == {
        "track": 1,
        "uri": None,
        "path": "sounds/Bass Loop.alc",
        "target_track_mode": "existing",
        "clip_slot": 2,
        "preserve_track_name": False,
        "notes_mode": "append",
        "import_length": False,
        "import_groove": False,
        "loaded": True,
    }


def test_dispatch_calls_backend_for_browser_load_with_notes_import_flags() -> None:
    backend = _BackendStub()
    result = dispatch_command(
        backend,
        "load_instrument_or_effect",
        {
            "track": 1,
            "path": "sounds/Bass Loop.alc",
            "target_track_mode": "existing",
            "clip_slot": 2,
            "notes_mode": "replace",
            "import_length": True,
            "import_groove": True,
        },
    )
    assert result == {
        "track": 1,
        "uri": None,
        "path": "sounds/Bass Loop.alc",
        "target_track_mode": "existing",
        "clip_slot": 2,
        "preserve_track_name": False,
        "notes_mode": "replace",
        "import_length": True,
        "import_groove": True,
        "loaded": True,
    }


def test_dispatch_calls_backend_for_add_notes_to_clip() -> None:
    backend = _BackendStub()
    note = {
        "pitch": 60,
        "start_time": 0.0,
        "duration": 0.5,
        "velocity": 100,
        "mute": False,
    }
    result = dispatch_command(
        backend,
        "add_notes_to_clip",
        {"track": 0, "clip": 1, "notes": [note, note]},
    )
    assert result == {"track": 0, "clip": 1, "note_count": 2}


def test_dispatch_calls_backend_for_clip_notes_get_clear_replace() -> None:
    backend = _BackendStub()
    note = {
        "pitch": 60,
        "start_time": 0.0,
        "duration": 0.5,
        "velocity": 100,
        "mute": False,
    }

    got = dispatch_command(
        backend,
        "get_clip_notes",
        {"track": 0, "clip": 1, "start_time": 0.0, "end_time": 4.0, "pitch": 60},
    )
    cleared = dispatch_command(
        backend,
        "clear_clip_notes",
        {"track": 0, "clip": 1, "start_time": 0.0, "end_time": 4.0, "pitch": 60},
    )
    replaced = dispatch_command(
        backend,
        "replace_clip_notes",
        {
            "track": 0,
            "clip": 1,
            "notes": [note],
            "start_time": 0.0,
            "end_time": 4.0,
            "pitch": 60,
        },
    )

    assert got["note_count"] == 0
    assert cleared["cleared_count"] == 1
    assert replaced["added_count"] == 1


def test_dispatch_calls_backend_for_clip_active_get_set() -> None:
    backend = _BackendStub()

    active = dispatch_command(
        backend,
        "clip_active_get",
        {"track": 0, "clip": 1},
    )
    inactive = dispatch_command(
        backend,
        "clip_active_set",
        {"track": 0, "clip": 1, "value": False},
    )

    assert active == {"track": 0, "clip": 1, "active": True}
    assert inactive == {"track": 0, "clip": 1, "active": False}


def test_dispatch_calls_backend_for_clip_cut_to_drum_rack() -> None:
    backend = _BackendStub()

    result = dispatch_command(
        backend,
        "clip_cut_to_drum_rack",
        {
            "source_track": 0,
            "source_clip": 1,
            "target_track": 2,
            "grid": "1/16",
            "start_pad": 4,
            "create_trigger_clip": True,
            "trigger_clip_slot": 3,
        },
    )

    assert result == {
        "source_track": 0,
        "source_clip": 1,
        "source_uri": None,
        "source_path": None,
        "target_track": 2,
        "grid": 0.25,
        "slice_count": None,
        "start_pad": 4,
        "create_trigger_clip": True,
        "trigger_clip_slot": 3,
        "loaded": True,
    }


def test_dispatch_calls_backend_for_load_drum_kit_with_explicit_selection() -> None:
    backend = _BackendStub()
    by_uri = dispatch_command(
        backend,
        "load_drum_kit",
        {"track": 0, "rack_uri": "rack:drums", "kit_uri": "kit:acoustic"},
    )
    by_path = dispatch_command(
        backend,
        "load_drum_kit",
        {
            "track": 0,
            "rack_uri": "rack:drums",
            "kit_path": "drums/Kits/Acoustic Kit",
        },
    )

    assert by_uri == {
        "track": 0,
        "rack_uri": "rack:drums",
        "kit_uri": "kit:acoustic",
        "kit_path": None,
    }
    assert by_path == {
        "track": 0,
        "rack_uri": "rack:drums",
        "kit_uri": None,
        "kit_path": "drums/Kits/Acoustic Kit",
    }


def test_dispatch_calls_backend_for_scene_commands() -> None:
    backend = _BackendStub()

    listed = dispatch_command(backend, "scenes_list", {})
    created = dispatch_command(backend, "create_scene", {"index": 1})
    renamed = dispatch_command(backend, "set_scene_name", {"scene": 1, "name": "Build"})
    fired = dispatch_command(backend, "fire_scene", {"scene": 1})

    assert listed == {"scenes": [{"index": 0, "name": "Intro"}]}
    assert created == {"index": 1, "name": "Scene"}
    assert renamed == {"scene": 1, "name": "Build"}
    assert fired == {"scene": 1, "fired": True}


def test_dispatch_calls_backend_for_session_snapshot() -> None:
    backend = _BackendStub()
    result = dispatch_command(backend, "session_snapshot", {})
    assert result["song_info"]["tempo"] == 120.0
    assert result["scenes_list"]["scenes"][0]["name"] == "Intro"


def test_dispatch_calls_backend_for_stop_all_clips() -> None:
    backend = _BackendStub()
    result = dispatch_command(backend, "stop_all_clips", {})
    assert result == {"stopped": True}


def test_dispatch_calls_backend_for_execute_batch() -> None:
    backend = _BackendStub()
    result = dispatch_command(
        backend,
        "execute_batch",
        {
            "steps": [
                {"name": "transport_tempo_set", "args": {"bpm": 128}},
                {"name": "tracks_list", "args": {}},
            ]
        },
    )

    assert result["step_count"] == 2
    assert result["stopped_at"] is None
    assert len(result["results"]) == 2
    assert result["results"][0]["name"] == "transport_tempo_set"
    assert result["results"][1]["name"] == "tracks_list"


def test_dispatch_execute_batch_stops_on_first_failure() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "execute_batch",
            {
                "steps": [
                    {"name": "tracks_list", "args": {}},
                    {"name": "track_volume_set", "args": {**_track_selector(0), "value": 99.0}},
                    {"name": "transport_play", "args": {}},
                ]
            },
        )

    assert exc_info.value.code == "BATCH_STEP_FAILED"
    assert exc_info.value.details is not None
    assert exc_info.value.details["failed_step_index"] == 1
    assert exc_info.value.details["failed_step_name"] == "track_volume_set"


def test_dispatch_calls_backend_for_track_mixer_commands() -> None:
    backend = _BackendStub()

    mute = dispatch_command(backend, "track_mute_set", {**_track_selector(0), "value": True})
    solo = dispatch_command(backend, "track_solo_get", _track_selector(0))
    arm = dispatch_command(backend, "track_arm_set", {**_track_selector(0), "value": False})
    panning = dispatch_command(backend, "track_panning_set", {**_track_selector(0), "value": -0.25})
    send_get = dispatch_command(backend, "track_send_get", {**_track_selector(0), "send": 1})
    send_set = dispatch_command(
        backend,
        "track_send_set",
        {**_track_selector(0), "send": 1, "value": 0.8},
    )

    assert mute == {"track": 0, "mute": True}
    assert solo == {"track": 0, "solo": False}
    assert arm == {"track": 0, "arm": False}
    assert panning == {"track": 0, "panning": -0.25}
    assert send_get == {"track": 0, "send": 1, "value": 0.2}
    assert send_set == {"track": 0, "send": 1, "value": 0.8}


def test_dispatch_calls_backend_for_return_track_commands() -> None:
    backend = _BackendStub()

    listed = dispatch_command(backend, "return_tracks_list", {})
    volume = dispatch_command(backend, "return_track_volume_set", {"return_track": 0, "value": 0.6})
    mute = dispatch_command(backend, "return_track_mute_set", {"return_track": 0, "value": True})
    solo = dispatch_command(backend, "return_track_solo_get", {"return_track": 0})

    assert listed == {"return_tracks": [{"index": 0, "name": "Reverb"}]}
    assert volume == {"return_track": 0, "volume": 0.6}
    assert mute == {"return_track": 0, "mute": True}
    assert solo == {"return_track": 0, "solo": True}


def test_dispatch_calls_backend_for_master_commands() -> None:
    backend = _BackendStub()

    info = dispatch_command(backend, "master_info", {})
    volume = dispatch_command(backend, "master_volume_get", {})
    panning = dispatch_command(backend, "master_panning_get", {})
    devices = dispatch_command(backend, "master_devices_list", {})

    assert info == {"name": "Master", "volume": 0.9, "panning": 0.0}
    assert volume == {"volume": 0.9}
    assert panning == {"panning": 0.0}
    assert devices == {"devices": [{"index": 0, "name": "Limiter"}]}


def test_dispatch_calls_backend_for_mixer_and_routing_commands() -> None:
    backend = _BackendStub()

    crossfader = dispatch_command(backend, "mixer_crossfader_set", {"value": 0.4})
    cue_volume = dispatch_command(backend, "mixer_cue_volume_get", {})
    cue_routing = dispatch_command(backend, "mixer_cue_routing_set", {"routing": "Ext. Out"})
    input_routing = dispatch_command(backend, "track_routing_input_get", _track_selector(0))
    output_routing = dispatch_command(
        backend,
        "track_routing_output_set",
        {**_track_selector(0), "routing_type": "Master", "routing_channel": "3/4"},
    )

    assert crossfader == {"value": 0.4}
    assert cue_volume == {"value": 0.8}
    assert cue_routing["routing"] == "Ext. Out"
    assert input_routing["current"] == {"type": "Ext. In", "channel": "1/2"}
    assert output_routing["current"] == {"type": "Master", "channel": "3/4"}


def test_dispatch_calls_backend_for_new_todo_commands() -> None:
    backend = _BackendStub()

    song_new = dispatch_command(backend, "song_new", {})
    song_save = dispatch_command(backend, "song_save", {"path": "/tmp/song.als"})
    song_export = dispatch_command(backend, "song_export_audio", {"path": "/tmp/song.wav"})
    record_start = dispatch_command(backend, "arrangement_record_start", {})
    record_stop = dispatch_command(backend, "arrangement_record_stop", {})
    arrangement_clip = dispatch_command(
        backend,
        "arrangement_clip_create",
        {"track": 0, "start_time": 8.0, "length": 4.0},
    )
    arrangement_clip_audio = dispatch_command(
        backend,
        "arrangement_clip_create",
        {"track": 1, "start_time": 16.0, "length": 8.0, "audio_path": "C:/tmp/loop.wav"},
    )
    arrangement_clip_with_notes = dispatch_command(
        backend,
        "arrangement_clip_create",
        {
            "track": 0,
            "start_time": 24.0,
            "length": 4.0,
            "notes": [
                {
                    "pitch": 60,
                    "start_time": 0.0,
                    "duration": 0.5,
                    "velocity": 100,
                    "mute": False,
                }
            ],
        },
    )
    arrangement_clip_list = dispatch_command(
        backend,
        "arrangement_clip_list",
        {},
    )
    arrangement_clip_list_track = dispatch_command(
        backend,
        "arrangement_clip_list",
        {"track": 1},
    )
    duplicate = dispatch_command(
        backend,
        "clip_duplicate",
        {"track": 1, "src_clip": 2, "dst_clip": 3},
    )
    scenes_move = dispatch_command(backend, "scenes_move", {"from": 3, "to": 1})
    tracks_delete = dispatch_command(backend, "tracks_delete", {"track": 0})

    assert song_new == {"created": True}
    assert song_save == {"saved": True, "path": "/tmp/song.als"}
    assert song_export == {"exported": True, "path": "/tmp/song.wav"}
    assert record_start == {"recording": True}
    assert record_stop == {"recording": False}
    assert arrangement_clip == {
        "track": 0,
        "start_time": 8.0,
        "length": 4.0,
        "kind": "midi",
        "arrangement_view_focused": True,
        "created": True,
    }
    assert arrangement_clip_audio == {
        "track": 1,
        "start_time": 16.0,
        "length": 8.0,
        "kind": "audio",
        "audio_path": "C:/tmp/loop.wav",
        "arrangement_view_focused": True,
        "created": True,
    }
    assert arrangement_clip_with_notes["notes_added"] == 1
    assert arrangement_clip_list["track"] is None
    assert arrangement_clip_list["clip_count"] == 2
    assert arrangement_clip_list_track["track"] == 1
    assert arrangement_clip_list_track["clip_count"] == 1
    assert duplicate == {"track": 1, "src_clip": 2, "dst_clip": 3, "duplicated": True}
    assert scenes_move == {"from": 3, "to": 1, "moved": True}
    assert tracks_delete == {"track": 0, "deleted": True}


def test_dispatch_calls_backend_for_clip_duplicate_many() -> None:
    backend = _BackendStub()

    duplicate_many = dispatch_command(
        backend,
        "clip_duplicate",
        {"track": 1, "src_clip": 2, "dst_clips": [3, 4, 5]},
    )

    assert duplicate_many == {
        "track": 1,
        "src_clip": 2,
        "dst_clips": [3, 4, 5],
        "duplicated": True,
    }


def test_dispatch_calls_backend_for_arrangement_notes_delete_and_from_session() -> None:
    backend = _BackendStub()

    added = dispatch_command(
        backend,
        "arrangement_clip_notes_add",
        {
            "track": 0,
            "index": 1,
            "notes": [
                {
                    "pitch": 60,
                    "start_time": 0.0,
                    "duration": 0.5,
                    "velocity": 100,
                    "mute": False,
                }
            ],
        },
    )
    gotten = dispatch_command(
        backend,
        "arrangement_clip_notes_get",
        {"track": 0, "index": 1, "start_time": 0.0, "end_time": 4.0, "pitch": 60},
    )
    cleared = dispatch_command(
        backend,
        "arrangement_clip_notes_clear",
        {"track": 0, "index": 1, "pitch": 60},
    )
    replaced = dispatch_command(
        backend,
        "arrangement_clip_notes_replace",
        {
            "track": 0,
            "index": 1,
            "notes": [
                {
                    "pitch": 62,
                    "start_time": 1.0,
                    "duration": 0.5,
                    "velocity": 90,
                    "mute": False,
                }
            ],
            "start_time": 0.0,
            "end_time": 8.0,
        },
    )
    imported = dispatch_command(
        backend,
        "arrangement_clip_notes_import_browser",
        {
            "track": 0,
            "index": 1,
            "target_path": "sounds/Bass Loop.alc",
            "mode": "append",
            "import_length": True,
            "import_groove": False,
        },
    )
    deleted_index = dispatch_command(
        backend,
        "arrangement_clip_delete",
        {"track": 0, "index": 1},
    )
    deleted_range = dispatch_command(
        backend,
        "arrangement_clip_delete",
        {"track": 0, "start": 8.0, "end": 16.0},
    )
    deleted_all = dispatch_command(
        backend,
        "arrangement_clip_delete",
        {"track": 0, "all": True},
    )
    from_session = dispatch_command(
        backend,
        "arrangement_from_session",
        {"scenes": [{"scene": 0, "duration_beats": 24.0}, {"scene": 1, "duration_beats": 48.0}]},
    )

    assert added["note_count"] == 1
    assert gotten["note_count"] == 0
    assert cleared["cleared_count"] == 1
    assert replaced["added_count"] == 1
    assert imported["mode"] == "append"
    assert deleted_index["mode"] == "index"
    assert deleted_range["mode"] == "range"
    assert deleted_all["mode"] == "all"
    assert from_session["scene_count"] == 2


def test_dispatch_calls_backend_for_clip_note_transform_commands() -> None:
    backend = _BackendStub()

    quantized = dispatch_command(
        backend,
        "clip_notes_quantize",
        {
            "track": 0,
            "clip": 1,
            "grid": "1/16",
            "strength": 0.75,
            "start_time": 0.0,
            "end_time": 4.0,
            "pitch": 60,
        },
    )
    humanized = dispatch_command(
        backend,
        "clip_notes_humanize",
        {
            "track": 0,
            "clip": 1,
            "timing": 0.1,
            "velocity": 5,
        },
    )
    velocity_scaled = dispatch_command(
        backend,
        "clip_notes_velocity_scale",
        {
            "track": 0,
            "clip": 1,
            "scale": 1.2,
            "offset": -3,
        },
    )
    transposed = dispatch_command(
        backend,
        "clip_notes_transpose",
        {
            "track": 0,
            "clip": 1,
            "semitones": 7,
        },
    )

    assert quantized["grid"] == 0.25
    assert quantized["strength"] == 0.75
    assert quantized["changed_count"] == 1
    assert humanized["timing"] == 0.1
    assert humanized["velocity"] == 5
    assert velocity_scaled["scale"] == 1.2
    assert velocity_scaled["offset"] == -3
    assert transposed["semitones"] == 7


def test_dispatch_calls_backend_for_clip_groove_commands() -> None:
    backend = _BackendStub()

    gotten = dispatch_command(backend, "clip_groove_get", {"track": 0, "clip": 1})
    set_result = dispatch_command(
        backend,
        "clip_groove_set",
        {"track": 0, "clip": 1, "target": "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr"},
    )
    amount_result = dispatch_command(
        backend,
        "clip_groove_amount_set",
        {"track": 0, "clip": 1, "value": 0.7},
    )
    cleared = dispatch_command(backend, "clip_groove_clear", {"track": 0, "clip": 1})

    assert gotten["has_groove"] is True
    assert set_result["has_groove"] is True
    assert set_result["target"] == "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr"
    assert amount_result["amount"] == 0.7
    assert cleared["has_groove"] is False


def test_dispatch_validates_new_todo_command_arguments() -> None:
    backend = _BackendStub()

    with pytest.raises(CommandError) as song_save_exc:
        dispatch_command(backend, "song_save", {"path": ""})
    with pytest.raises(CommandError) as song_export_exc:
        dispatch_command(backend, "song_export_audio", {"path": ""})
    with pytest.raises(CommandError) as clip_duplicate_exc:
        dispatch_command(
            backend,
            "clip_duplicate",
            {"track": 0, "src_clip": 1, "dst_clip": -1},
        )
    with pytest.raises(CommandError) as clip_duplicate_conflict_exc:
        dispatch_command(
            backend,
            "clip_duplicate",
            {"track": 0, "src_clip": 1, "dst_clip": 2, "dst_clips": [3]},
        )
    with pytest.raises(CommandError) as clip_duplicate_missing_dst_exc:
        dispatch_command(
            backend,
            "clip_duplicate",
            {"track": 0, "src_clip": 1},
        )
    with pytest.raises(CommandError) as clip_active_set_exc:
        dispatch_command(
            backend,
            "clip_active_set",
            {"track": 0, "clip": 1, "value": "false"},
        )
    with pytest.raises(CommandError) as scenes_move_exc:
        dispatch_command(backend, "scenes_move", {"from": -1, "to": 0})
    with pytest.raises(CommandError) as tracks_delete_exc:
        dispatch_command(backend, "tracks_delete", {"track": -1})
    with pytest.raises(CommandError) as arrangement_clip_start_exc:
        dispatch_command(
            backend,
            "arrangement_clip_create",
            {"track": 0, "start_time": -1, "length": 4.0},
        )
    with pytest.raises(CommandError) as arrangement_clip_audio_path_exc:
        dispatch_command(
            backend,
            "arrangement_clip_create",
            {"track": 1, "start_time": 0, "length": 4.0, "audio_path": "loops/amen.wav"},
        )
    with pytest.raises(CommandError) as arrangement_clip_list_track_exc:
        dispatch_command(
            backend,
            "arrangement_clip_list",
            {"track": -1},
        )
    with pytest.raises(CommandError) as transport_position_set_exc:
        dispatch_command(
            backend,
            "transport_position_set",
            {"beats": -0.5},
        )
    with pytest.raises(CommandError) as arrangement_clip_notes_pitch_exc:
        dispatch_command(
            backend,
            "arrangement_clip_notes_get",
            {"track": 0, "index": 0, "pitch": 200},
        )
    with pytest.raises(CommandError) as arrangement_clip_delete_missing_mode_exc:
        dispatch_command(
            backend,
            "arrangement_clip_delete",
            {"track": 0},
        )
    with pytest.raises(CommandError) as arrangement_clip_delete_multiple_modes_exc:
        dispatch_command(
            backend,
            "arrangement_clip_delete",
            {"track": 0, "index": 0, "all": True},
        )
    with pytest.raises(CommandError) as arrangement_clip_delete_bad_range_exc:
        dispatch_command(
            backend,
            "arrangement_clip_delete",
            {"track": 0, "start": 8.0},
        )
    with pytest.raises(CommandError) as arrangement_from_session_invalid_exc:
        dispatch_command(
            backend,
            "arrangement_from_session",
            {"scenes": [{"scene": 0, "duration_beats": 0.0}]},
        )

    assert song_save_exc.value.code == "INVALID_ARGUMENT"
    assert song_export_exc.value.code == "INVALID_ARGUMENT"
    assert clip_duplicate_exc.value.code == "INVALID_ARGUMENT"
    assert clip_duplicate_conflict_exc.value.code == "INVALID_ARGUMENT"
    assert clip_duplicate_missing_dst_exc.value.code == "INVALID_ARGUMENT"
    assert clip_active_set_exc.value.code == "INVALID_ARGUMENT"
    assert scenes_move_exc.value.code == "INVALID_ARGUMENT"
    assert tracks_delete_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_clip_start_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_clip_audio_path_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_clip_list_track_exc.value.code == "INVALID_ARGUMENT"
    assert transport_position_set_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_clip_notes_pitch_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_clip_delete_missing_mode_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_clip_delete_multiple_modes_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_clip_delete_bad_range_exc.value.code == "INVALID_ARGUMENT"
    assert arrangement_from_session_invalid_exc.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_invalid_clip_note_transform_arguments() -> None:
    backend = _BackendStub()

    with pytest.raises(CommandError) as invalid_grid:
        dispatch_command(
            backend,
            "clip_notes_quantize",
            {"track": 0, "clip": 0, "grid": "0/16", "strength": 1.0},
        )
    with pytest.raises(CommandError) as invalid_strength:
        dispatch_command(
            backend,
            "clip_notes_quantize",
            {"track": 0, "clip": 0, "grid": "1/16", "strength": 2.0},
        )
    with pytest.raises(CommandError) as invalid_humanize_velocity:
        dispatch_command(
            backend,
            "clip_notes_humanize",
            {"track": 0, "clip": 0, "timing": 0.1, "velocity": 128},
        )
    with pytest.raises(CommandError) as invalid_scale:
        dispatch_command(
            backend,
            "clip_notes_velocity_scale",
            {"track": 0, "clip": 0, "scale": -0.1, "offset": 0},
        )

    assert invalid_grid.value.code == "INVALID_ARGUMENT"
    assert invalid_strength.value.code == "INVALID_ARGUMENT"
    assert invalid_humanize_velocity.value.code == "INVALID_ARGUMENT"
    assert invalid_scale.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_invalid_clip_groove_arguments() -> None:
    backend = _BackendStub()

    with pytest.raises(CommandError) as invalid_target:
        dispatch_command(backend, "clip_groove_set", {"track": 0, "clip": 0, "target": "hiphop"})
    with pytest.raises(CommandError) as invalid_amount:
        dispatch_command(backend, "clip_groove_amount_set", {"track": 0, "clip": 0, "value": 1.5})

    assert invalid_target.value.code == "INVALID_ARGUMENT"
    assert invalid_amount.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_unknown_command() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "unknown", {})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_invalid_volume() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "track_volume_set", {**_track_selector(0), "value": 1.5})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_create_audio_track_index_below_minus_one() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "create_audio_track", {"index": -2})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_set_device_parameter_negative_device() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "set_device_parameter",
            {
                "track_ref": {"mode": "index", "index": 0},
                "device_ref": {"mode": "index", "index": -1},
                "parameter_ref": {"mode": "index", "index": 0},
                "value": 0.1,
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_find_synth_devices_unknown_type() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "find_synth_devices",
            {"synth_type": "operator"},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_set_standard_synth_parameter_empty_key() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "set_standard_synth_parameter_safe",
            {
                "synth_type": "wavetable",
                **_device_selector(0, 1),
                "parameter_ref": {"mode": "key", "key": "   "},
                "value": 0.5,
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_find_effect_devices_unknown_type() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "find_effect_devices",
            {"effect_type": "phaser"},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_set_standard_effect_parameter_empty_key() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "set_standard_effect_parameter_safe",
            {
                "effect_type": "eq8",
                **_device_selector(0, 2),
                "parameter_ref": {"mode": "key", "key": "   "},
                "value": 0.5,
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_invalid_note_velocity() -> None:
    backend = _BackendStub()
    note = {
        "pitch": 60,
        "start_time": 0.0,
        "duration": 0.25,
        "velocity": 200,
        "mute": False,
    }
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "add_notes_to_clip",
            {"track": 0, "clip": 0, "notes": [note]},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_load_without_uri_or_path() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "load_instrument_or_effect", {"track": 0})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_load_with_uri_and_path() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "load_instrument_or_effect",
            {"track": 0, "uri": "query:Synths#Drift", "path": "instruments/Drift"},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_load_with_invalid_target_track_mode() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "load_instrument_or_effect",
            {
                "track": 0,
                "path": "instruments/Drift",
                "target_track_mode": "legacy",
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_load_with_negative_clip_slot() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "load_instrument_or_effect",
            {
                "track": 0,
                "path": "instruments/Drift",
                "clip_slot": -1,
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_load_with_invalid_notes_mode() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "load_instrument_or_effect",
            {
                "track": 0,
                "path": "sounds/Bass Loop.alc",
                "target_track_mode": "existing",
                "clip_slot": 1,
                "notes_mode": "merge",
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_load_with_non_boolean_import_flags() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "load_instrument_or_effect",
            {
                "track": 0,
                "path": "sounds/Bass Loop.alc",
                "target_track_mode": "existing",
                "clip_slot": 1,
                "notes_mode": "replace",
                "import_length": "true",
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_search_invalid_limit() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "search_browser_items", {"query": "drift", "limit": 0})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_search_negative_offset() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "search_browser_items", {"query": "drift", "offset": -1})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_browser_search_invalid_item_type() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "search_browser_items",
            {"query": "drift", "item_type": "unknown"},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_clip_note_filter_invalid_range() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "get_clip_notes",
            {"track": 0, "clip": 0, "start_time": 2.0, "end_time": 2.0},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_clip_note_filter_invalid_pitch() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "clear_clip_notes",
            {"track": 0, "clip": 0, "pitch": 200},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_load_drum_kit_ambiguous_selection() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info_none:
        dispatch_command(
            backend,
            "load_drum_kit",
            {"track": 0, "rack_uri": "rack:drums"},
        )
    with pytest.raises(CommandError) as exc_info_both:
        dispatch_command(
            backend,
            "load_drum_kit",
            {
                "track": 0,
                "rack_uri": "rack:drums",
                "kit_uri": "kit:acoustic",
                "kit_path": "drums/Kits/Acoustic Kit",
            },
        )

    assert exc_info_none.value.code == "INVALID_ARGUMENT"
    assert exc_info_both.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_clip_cut_to_drum_rack_ambiguous_source() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "clip_cut_to_drum_rack",
            {
                "source_track": 0,
                "source_clip": 1,
                "source_path": "sounds/Bass Loop.wav",
                "slice_count": 8,
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_clip_cut_to_drum_rack_missing_slice_mode() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "clip_cut_to_drum_rack",
            {
                "source_track": 0,
                "source_clip": 1,
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_clip_cut_to_drum_rack_trigger_slot_without_flag() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "clip_cut_to_drum_rack",
            {
                "source_track": 0,
                "source_clip": 1,
                "slice_count": 8,
                "trigger_clip_slot": 3,
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_rejects_track_panning_out_of_range() -> None:
    backend = _BackendStub()
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "track_panning_set",
            {**_track_selector(0), "value": 1.1},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"
