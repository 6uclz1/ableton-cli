from __future__ import annotations

import json
from pathlib import Path

from ableton_cli.errors import AppError, ExitCode


def _ref_index(ref: object) -> int:
    if isinstance(ref, dict):
        return int(ref["index"])
    return int(ref)


def _stable_ref(kind: str, index: int) -> str:
    return f"{kind}:{index}"


class _ClientStub:
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

    def get_session_info(self):  # noqa: ANN201
        return {"tempo": 123.0}

    def session_snapshot(self):  # noqa: ANN201
        return {
            "song_info": {"tempo": 123.0, "is_playing": False},
            "session_info": {"track_count": 2},
            "tracks_list": {
                "tracks": [{"index": 0, "stable_ref": _stable_ref("track", 0), "name": "Track 1"}]
            },
            "scenes_list": {"scenes": [{"index": 0, "name": "Intro"}]},
        }

    def stop_all_clips(self):  # noqa: ANN201
        return {"stopped": True}

    def set_device_parameter(  # noqa: ANN201
        self,
        track_ref,
        device_ref,
        parameter_ref,
        value: float,
    ):
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        parameter_index = _ref_index(parameter_ref)
        return {
            "track": track_index,
            "device": device_index,
            "parameter": parameter_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "parameter_stable_ref": _stable_ref("parameter", parameter_index),
            "value": value,
        }

    def create_midi_track(self, index: int):  # noqa: ANN201
        return {"index": index, "name": "MIDI", "kind": "midi"}

    def create_audio_track(self, index: int):  # noqa: ANN201
        return {"index": index, "name": "Audio", "kind": "audio"}

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
            "cleared_count": 2,
            "added_count": len(notes),
        }

    def clip_duplicate(  # noqa: ANN201
        self,
        track: int,
        src_clip: int,
        dst_clip: int | None = None,
        dst_clips: list[int] | None = None,
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
        grid: str | None,
        slice_count: int | None,
        start_pad: int,
        create_trigger_clip: bool,
        trigger_clip_slot: int | None,
    ):
        resolved_slice_count = (
            slice_count if slice_count is not None else (4 if grid is not None else 0)
        )
        return {
            "source_track": source_track,
            "source_clip": source_clip,
            "source_uri": source_uri,
            "source_path": source_path,
            "target_track": 2 if target_track is None else target_track,
            "grid": grid,
            "slice_count": resolved_slice_count,
            "start_pad": start_pad,
            "assigned_count": resolved_slice_count,
            "create_trigger_clip": create_trigger_clip,
            "trigger_clip_created": create_trigger_clip,
            "trigger_clip_slot": trigger_clip_slot,
        }

    def set_clip_name(self, track: int, clip: int, name: str):  # noqa: ANN201
        return {"track": track, "clip": clip, "name": name}

    def clip_notes_quantize(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        grid: str,
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
            "changed_count": 2,
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
            "changed_count": 2,
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
            "changed_count": 2,
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
            "changed_count": 2,
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
            "target": target,
            "has_groove": True,
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

    def clip_active_get(self, track: int, clip: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "active": True}

    def clip_active_set(self, track: int, clip: int, value: bool):  # noqa: ANN201
        return {"track": track, "clip": clip, "active": value}

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
            "duration_ms": 1.23,
            "items": [],
        }

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

    def get_browser_item(self, uri: str | None, path: str | None):  # noqa: ANN201
        return {"uri": uri, "path": path, "found": True}

    def load_instrument_or_effect(  # noqa: ANN201
        self,
        track: int,
        uri: str | None,
        path: str | None,
        target_track_mode: str = "auto",
        clip_slot: int | None = None,
        preserve_track_name: bool = False,
        notes_mode: str | None = None,
        import_length: bool = False,
        import_groove: bool = False,
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
            "loaded": True,
        }

    def track_mute_get(self, track_ref):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "mute": False}

    def track_mute_set(self, track_ref, value: bool):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "mute": value}

    def track_solo_get(self, track_ref):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "solo": False}

    def track_solo_set(self, track_ref, value: bool):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "solo": value}

    def track_arm_get(self, track_ref):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "arm": False}

    def track_arm_set(self, track_ref, value: bool):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "arm": value}

    def track_panning_get(self, track_ref):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "panning": 0.0}

    def track_panning_set(self, track_ref, value: float):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "panning": value}

    def track_send_get(self, track_ref, send: int):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "send": send, "value": 0.25}

    def track_send_set(self, track_ref, send: int, value: float):  # noqa: ANN001, ANN201
        return {"track": _ref_index(track_ref), "send": send, "value": value}

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

    def track_routing_input_get(self, track_ref):  # noqa: ANN001, ANN201
        return {
            "track": _ref_index(track_ref),
            "current": {"type": "Ext. In", "channel": "1/2"},
            "available": {"types": ["Ext. In"], "channels": ["1/2", "3/4"]},
        }

    def track_routing_input_set(
        self,
        track_ref,
        routing_type: str,
        routing_channel: str,
    ):  # noqa: ANN201
        return {
            "track": _ref_index(track_ref),
            "current": {"type": routing_type, "channel": routing_channel},
            "available": {"types": ["Ext. In"], "channels": ["1/2", "3/4"]},
        }

    def track_routing_output_get(self, track_ref):  # noqa: ANN001, ANN201
        return {
            "track": _ref_index(track_ref),
            "current": {"type": "Master", "channel": "1/2"},
            "available": {"types": ["Master"], "channels": ["1/2", "3/4"]},
        }

    def track_routing_output_set(
        self,
        track_ref,
        routing_type: str,
        routing_channel: str,
    ):  # noqa: ANN201
        return {
            "track": _ref_index(track_ref),
            "current": {"type": routing_type, "channel": routing_channel},
            "available": {"types": ["Master"], "channels": ["1/2", "3/4"]},
        }

    def transport_position_get(self):  # noqa: ANN201
        return {"current_time": 4.0, "beat_position": 4.0}

    def transport_position_set(self, beats: float):  # noqa: ANN201
        return {"current_time": beats, "beat_position": beats}

    def transport_rewind(self):  # noqa: ANN201
        return {"current_time": 0.0, "beat_position": 0.0}

    def scenes_list(self):  # noqa: ANN201
        return {
            "scenes": [
                {"index": 0, "name": "Intro"},
                {"index": 1, "name": "Drop"},
                {"index": 2, "name": "Peak"},
            ]
        }

    def create_scene(self, index: int):  # noqa: ANN201
        return {"index": index, "name": "Scene"}

    def set_scene_name(self, scene: int, name: str):  # noqa: ANN201
        return {"scene": scene, "name": name}

    def fire_scene(self, scene: int):  # noqa: ANN201
        return {"scene": scene, "fired": True}

    def scenes_move(self, from_index: int, to_index: int):  # noqa: ANN201
        return {"from": from_index, "to": to_index, "moved": True}

    def tracks_delete(self, track: int):  # noqa: ANN201
        return {"track": track, "deleted": True}

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
            raise AppError(
                error_code="INVALID_ARGUMENT",
                message="notes are supported only for MIDI tracks",
                hint="Remove --notes-json/--notes-file for audio arrangement clips.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )
        if track == 0 and audio_path is not None:
            raise AppError(
                error_code="INVALID_ARGUMENT",
                message="audio_path must not be provided for MIDI tracks",
                hint="Remove --audio-path for MIDI arrangement clip creation.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )
        if track == 1 and audio_path is None:
            raise AppError(
                error_code="INVALID_ARGUMENT",
                message="audio_path is required for audio tracks",
                hint="Pass --audio-path with an absolute audio file path.",
                exit_code=ExitCode.INVALID_ARGUMENT,
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
        self, track: int, index: int, notes: list[dict[str, object]]
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
            "length_imported": import_length,
            "groove_imported": import_groove,
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

    def arrangement_from_session(self, scenes: list[dict[str, float]]):  # noqa: ANN201
        return {
            "scene_count": len(scenes),
            "created_count": 3,
            "scenes": scenes,
        }

    def execute_batch(self, steps: list[dict[str, object]]):  # noqa: ANN201
        return {
            "step_count": len(steps),
            "results": [{"index": idx, "result": {"ok": True}} for idx, _ in enumerate(steps)],
        }

    def execute_remote_command(self, name: str, args: dict[str, object]):  # noqa: ANN201
        handler = getattr(self, name, None)
        if handler is None:
            return {"name": name, "args": args, "ok": True}
        return handler(**args)

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
                    "track_stable_ref": _stable_ref("track", 0),
                    "stable_ref": _stable_ref("device", 1),
                    "track_name": "Track 1",
                    "device_name": "Wavetable",
                    "class_name": "InstrumentVector",
                    "detected_type": "wavetable",
                }
            ],
        }

    def list_synth_parameters(self, track_ref, device_ref):  # noqa: ANN001, ANN201
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        return {
            "track": track_index,
            "device": device_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "device_name": "Wavetable",
            "class_name": "InstrumentVector",
            "detected_type": "wavetable",
            "parameter_count": 1,
            "parameters": [
                {
                    "index": 0,
                    "stable_ref": _stable_ref("parameter", 0),
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
        track_ref,
        device_ref,
        parameter_ref,
        value: float,
    ):
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        parameter_index = _ref_index(parameter_ref)
        return {
            "track": track_index,
            "device": device_index,
            "parameter": parameter_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "parameter_stable_ref": _stable_ref("parameter", parameter_index),
            "detected_type": "wavetable",
            "before": 0.3,
            "after": value,
            "min": 0.0,
            "max": 1.0,
            "is_enabled": True,
            "is_quantized": False,
        }

    def observe_synth_parameters(self, track_ref, device_ref):  # noqa: ANN001, ANN201
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        return {
            "track": track_index,
            "device": device_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "device_name": "Wavetable",
            "class_name": "InstrumentVector",
            "detected_type": "wavetable",
            "parameter_count": 1,
            "parameters": [
                {
                    "index": 0,
                    "stable_ref": _stable_ref("parameter", 0),
                    "name": "Filter Freq",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "is_enabled": True,
                    "is_quantized": False,
                }
            ],
        }

    def list_standard_synth_keys(self, synth_type: str):  # noqa: ANN201
        return {
            "synth_type": synth_type,
            "key_count": 9,
            "keys": [
                "filter_cutoff",
                "filter_resonance",
                "amp_attack",
                "amp_decay",
                "amp_sustain",
                "amp_release",
                "osc1_position",
                "osc2_position",
                "unison_amount",
            ],
        }

    def set_standard_synth_parameter_safe(  # noqa: ANN201
        self,
        synth_type: str,
        track_ref,
        device_ref,
        parameter_ref,
        key: str,
        value: float,
    ):
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        return {
            "synth_type": synth_type,
            "track": track_index,
            "device": device_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "parameter_stable_ref": _stable_ref("parameter", 0),
            "parameter": 0,
            "detected_type": synth_type,
            "key": key,
            "before": 0.4,
            "after": value,
            "min": 0.0,
            "max": 1.0,
            "is_enabled": True,
            "is_quantized": False,
            "resolved_parameter": 0,
        }

    def observe_standard_synth_state(  # noqa: ANN201
        self,
        synth_type: str,
        track_ref,
        device_ref,
    ):
        return {
            "synth_type": synth_type,
            "track": _ref_index(track_ref),
            "device": _ref_index(device_ref),
            "track_stable_ref": _stable_ref("track", _ref_index(track_ref)),
            "device_stable_ref": _stable_ref("device", _ref_index(device_ref)),
            "key_count": 1,
            "keys": ["filter_cutoff"],
            "state": {"filter_cutoff": 0.5},
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
                    "track_stable_ref": _stable_ref("track", 0),
                    "stable_ref": _stable_ref("device", 2),
                    "track_name": "Track 1",
                    "device_name": "EQ Eight",
                    "class_name": "AudioEffectGroupDevice",
                    "detected_type": "eq8",
                }
            ],
        }

    def list_effect_parameters(self, track_ref, device_ref):  # noqa: ANN001, ANN201
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        return {
            "track": track_index,
            "device": device_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "device_name": "EQ Eight",
            "class_name": "AudioEffectGroupDevice",
            "detected_type": "eq8",
            "parameter_count": 1,
            "parameters": [
                {
                    "index": 0,
                    "stable_ref": _stable_ref("parameter", 0),
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
        track_ref,
        device_ref,
        parameter_ref,
        value: float,
    ):
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        parameter_index = _ref_index(parameter_ref)
        return {
            "track": track_index,
            "device": device_index,
            "parameter": parameter_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "parameter_stable_ref": _stable_ref("parameter", parameter_index),
            "detected_type": "eq8",
            "before": 0.2,
            "after": value,
            "min": 0.0,
            "max": 1.0,
            "is_enabled": True,
            "is_quantized": False,
        }

    def observe_effect_parameters(self, track_ref, device_ref):  # noqa: ANN001, ANN201
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        return {
            "track": track_index,
            "device": device_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "device_name": "EQ Eight",
            "class_name": "AudioEffectGroupDevice",
            "detected_type": "eq8",
            "parameter_count": 1,
            "parameters": [
                {
                    "index": 0,
                    "stable_ref": _stable_ref("parameter", 0),
                    "name": "1 Frequency A",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "is_enabled": True,
                    "is_quantized": False,
                }
            ],
        }

    def list_standard_effect_keys(self, effect_type: str):  # noqa: ANN201
        return {
            "effect_type": effect_type,
            "key_count": 5,
            "keys": [
                "band1_freq",
                "band1_gain",
                "band1_q",
                "low_cut_freq",
                "high_cut_freq",
            ],
        }

    def set_standard_effect_parameter_safe(  # noqa: ANN201
        self,
        effect_type: str,
        track_ref,
        device_ref,
        parameter_ref,
        key: str,
        value: float,
    ):
        track_index = _ref_index(track_ref)
        device_index = _ref_index(device_ref)
        return {
            "effect_type": effect_type,
            "track": track_index,
            "device": device_index,
            "track_stable_ref": _stable_ref("track", track_index),
            "device_stable_ref": _stable_ref("device", device_index),
            "parameter_stable_ref": _stable_ref("parameter", 0),
            "parameter": 0,
            "detected_type": effect_type,
            "key": key,
            "before": 0.1,
            "after": value,
            "min": 0.0,
            "max": 1.0,
            "is_enabled": True,
            "is_quantized": False,
            "resolved_parameter": 0,
        }

    def observe_standard_effect_state(  # noqa: ANN201
        self,
        effect_type: str,
        track_ref,
        device_ref,
    ):
        return {
            "effect_type": effect_type,
            "track": _ref_index(track_ref),
            "device": _ref_index(device_ref),
            "track_stable_ref": _stable_ref("track", _ref_index(track_ref)),
            "device_stable_ref": _stable_ref("device", _ref_index(device_ref)),
            "key_count": 1,
            "keys": ["band1_freq"],
            "state": {"band1_freq": 0.5},
        }


class _WaitReadyClientAlwaysReady:
    def ping(self):  # noqa: ANN201
        return {"protocol_version": 2, "remote_script_version": "0.2.0"}


class _WaitReadyClientEventuallyReady:
    def __init__(self) -> None:
        self._attempt = 0

    def ping(self):  # noqa: ANN201
        self._attempt += 1
        if self._attempt < 3:
            raise AppError(
                error_code="ABLETON_NOT_REACHABLE",
                message="offline",
                hint="start ableton",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            )
        return {"protocol_version": 2, "remote_script_version": "0.2.0"}


class _WaitReadyClientNeverReady:
    def ping(self):  # noqa: ANN201
        raise AppError(
            error_code="ABLETON_NOT_REACHABLE",
            message="offline",
            hint="start ableton",
            exit_code=ExitCode.ABLETON_NOT_CONNECTED,
        )


def test_session_info_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "session", "info"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["tempo"] == 123.0


def test_session_stop_all_clips_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "session", "stop-all-clips"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["stopped"] is True


def test_session_snapshot_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "session", "snapshot"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["song_info"]["tempo"] == 123.0
    assert payload["result"]["scenes_list"]["scenes"][0]["name"] == "Intro"


def test_device_parameter_set_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import device

    monkeypatch.setattr(device, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "device",
            "parameter",
            "set",
            "0.75",
            "--track-index",
            "1",
            "--device-index",
            "2",
            "--parameter-index",
            "3",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "track": 1,
        "device": 2,
        "parameter": 3,
        "track_stable_ref": "track:1",
        "device_stable_ref": "device:2",
        "parameter_stable_ref": "parameter:3",
        "value": 0.75,
    }


def test_tracks_create_commands_accept_index_option(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import tracks

    monkeypatch.setattr(tracks, "get_client", lambda ctx: _ClientStub())

    midi = runner.invoke(
        cli_app,
        ["--output", "json", "tracks", "create", "midi", "--index", "-1"],
    )
    audio = runner.invoke(
        cli_app,
        ["--output", "json", "tracks", "create", "audio", "--index", "2"],
    )

    assert midi.exit_code == 0
    assert audio.exit_code == 0
    midi_payload = json.loads(midi.stdout)
    audio_payload = json.loads(audio.stdout)
    assert midi_payload["result"]["index"] == -1
    assert midi_payload["result"]["kind"] == "midi"
    assert audio_payload["result"]["index"] == 2
    assert audio_payload["result"]["kind"] == "audio"


def test_song_new_save_export_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import song

    monkeypatch.setattr(song, "get_client", lambda ctx: _ClientStub())

    created = runner.invoke(cli_app, ["--output", "json", "song", "new"])
    saved = runner.invoke(
        cli_app,
        ["--output", "json", "song", "save", "--path", "/tmp/demo.als"],
    )
    exported = runner.invoke(
        cli_app,
        ["--output", "json", "song", "export", "audio", "--path", "/tmp/demo.wav"],
    )

    assert created.exit_code == 0
    assert saved.exit_code == 0
    assert exported.exit_code == 0

    created_payload = json.loads(created.stdout)
    saved_payload = json.loads(saved.stdout)
    exported_payload = json.loads(exported.stdout)
    assert created_payload["result"]["created"] is True
    assert saved_payload["result"]["saved"] is True
    assert saved_payload["result"]["path"] == "/tmp/demo.als"
    assert exported_payload["result"]["exported"] is True
    assert exported_payload["result"]["path"] == "/tmp/demo.wav"


def test_song_undo_redo_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import song

    monkeypatch.setattr(song, "get_client", lambda ctx: _ClientStub())

    undone = runner.invoke(cli_app, ["--output", "json", "song", "undo"])
    redone = runner.invoke(cli_app, ["--output", "json", "song", "redo"])

    assert undone.exit_code == 0
    assert redone.exit_code == 0

    undo_payload = json.loads(undone.stdout)
    redo_payload = json.loads(redone.stdout)
    assert undo_payload["result"]["undone"] is True
    assert redo_payload["result"]["redone"] is True


def test_clip_notes_add_parses_json_and_calls_client(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_json = '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'

    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "add", "0", "1", "--notes-json", notes_json],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 0, "clip": 1, "note_count": 1}


def test_clip_notes_add_accepts_notes_file(runner, cli_app, monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_path = tmp_path / "notes.json"
    notes_path.write_text(
        '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]',
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "add",
            "0",
            "1",
            "--notes-file",
            str(notes_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 0, "clip": 1, "note_count": 1}


def test_clip_notes_get_clear_replace_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_json = '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'

    result_get = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "get",
            "0",
            "1",
            "--start-time",
            "0.0",
            "--end-time",
            "1.0",
            "--pitch",
            "60",
        ],
    )
    result_clear = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "clear", "0", "1", "--pitch", "60"],
    )
    result_replace = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "replace",
            "0",
            "1",
            "--notes-json",
            notes_json,
            "--start-time",
            "0.0",
            "--end-time",
            "4.0",
        ],
    )

    assert result_get.exit_code == 0
    assert result_clear.exit_code == 0
    assert result_replace.exit_code == 0

    payload_get = json.loads(result_get.stdout)
    payload_clear = json.loads(result_clear.stdout)
    payload_replace = json.loads(result_replace.stdout)

    assert payload_get["ok"] is True
    assert payload_get["result"]["pitch"] == 60
    assert payload_clear["ok"] is True
    assert payload_clear["result"]["cleared_count"] == 1
    assert payload_replace["ok"] is True
    assert payload_replace["result"]["added_count"] == 1


def test_clip_notes_replace_accepts_notes_file(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_path = tmp_path / "replace-notes.json"
    notes_path.write_text(
        '[{"pitch":65,"start_time":0.25,"duration":0.5,"velocity":96,"mute":false}]',
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "replace",
            "0",
            "1",
            "--notes-file",
            str(notes_path),
            "--start-time",
            "0.0",
            "--end-time",
            "4.0",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["added_count"] == 1


def test_clip_note_transform_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    quantize = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "quantize",
            "0",
            "1",
            "--grid",
            "1/16",
            "--strength",
            "0.8",
            "--start-time",
            "0.0",
            "--end-time",
            "4.0",
            "--pitch",
            "60",
        ],
    )
    humanize = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "humanize",
            "0",
            "1",
            "--timing",
            "0.1",
            "--velocity",
            "5",
        ],
    )
    velocity_scale = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "velocity-scale",
            "0",
            "1",
            "--scale",
            "1.2",
            "--offset",
            "-3",
        ],
    )
    transpose = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "transpose",
            "0",
            "1",
            "--semitones",
            "7",
        ],
    )

    assert quantize.exit_code == 0
    assert humanize.exit_code == 0
    assert velocity_scale.exit_code == 0
    assert transpose.exit_code == 0

    quantize_payload = json.loads(quantize.stdout)
    humanize_payload = json.loads(humanize.stdout)
    velocity_scale_payload = json.loads(velocity_scale.stdout)
    transpose_payload = json.loads(transpose.stdout)

    assert quantize_payload["result"]["changed_count"] == 2
    assert quantize_payload["result"]["grid"] == "1/16"
    assert humanize_payload["result"]["timing"] == 0.1
    assert humanize_payload["result"]["velocity"] == 5
    assert velocity_scale_payload["result"]["scale"] == 1.2
    assert velocity_scale_payload["result"]["offset"] == -3
    assert transpose_payload["result"]["semitones"] == 7


def test_clip_groove_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    gotten = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "groove", "get", "0", "1"],
    )
    set_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "groove",
            "set",
            "0",
            "1",
            "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr",
        ],
    )
    amount_result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "groove", "amount", "set", "0", "1", "0.7"],
    )
    cleared = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "groove", "clear", "0", "1"],
    )

    assert gotten.exit_code == 0
    assert set_result.exit_code == 0
    assert amount_result.exit_code == 0
    assert cleared.exit_code == 0

    gotten_payload = json.loads(gotten.stdout)
    set_payload = json.loads(set_result.stdout)
    amount_payload = json.loads(amount_result.stdout)
    cleared_payload = json.loads(cleared.stdout)

    assert gotten_payload["result"]["has_groove"] is True
    assert set_payload["result"]["target"] == "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr"
    assert amount_payload["result"]["amount"] == 0.7
    assert cleared_payload["result"]["has_groove"] is False


def test_browser_item_supports_uri_and_path_target(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    by_uri = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "item", "query:Synths#Operator"],
    )
    by_path = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "item", "instruments/Operator"],
    )

    assert by_uri.exit_code == 0
    assert by_path.exit_code == 0

    uri_payload = json.loads(by_uri.stdout)
    path_payload = json.loads(by_path.stdout)
    assert uri_payload["result"]["uri"] == "query:Synths#Operator"
    assert uri_payload["result"]["path"] is None
    assert path_payload["result"]["path"] == "instruments/Operator"
    assert path_payload["result"]["uri"] is None


def test_browser_items_includes_pagination_fields(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "items",
            "drums",
            "--item-type",
            "loadable",
            "--limit",
            "100",
            "--offset",
            "0",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["limit"] == 100
    assert payload["result"]["offset"] == 0
    assert payload["result"]["has_more"] is False


def test_browser_search_includes_duration_ms(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "search", "drift", "--item-type", "loadable"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["duration_ms"] == 1.23


def test_browser_load_supports_uri_and_path_target(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    by_uri = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "load", "0", "query:Synths#Operator"],
    )
    by_path = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "load", "0", "instruments/Operator"],
    )

    assert by_uri.exit_code == 0
    assert by_path.exit_code == 0

    uri_payload = json.loads(by_uri.stdout)
    path_payload = json.loads(by_path.stdout)
    assert uri_payload["result"]["uri"] == "query:Synths#Operator"
    assert uri_payload["result"]["path"] is None
    assert path_payload["result"]["path"] == "instruments/Operator"
    assert path_payload["result"]["uri"] is None


def test_browser_load_treats_uri_with_slash_as_uri(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "0",
            "query:LivePacks#www.ableton.com/272:Drum%20Racks:Fuji%20Kit.adg",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert (
        payload["result"]["uri"]
        == "query:LivePacks#www.ableton.com/272:Drum%20Racks:Fuji%20Kit.adg"
    )
    assert payload["result"]["path"] is None


def test_browser_load_supports_target_track_mode_clip_slot_and_preserve_track_name(
    runner,
    cli_app,
    monkeypatch,
) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "1",
            "sounds/Bass Loop.alc",
            "--target-track-mode",
            "existing",
            "--clip-slot",
            "3",
            "--preserve-track-name",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["track"] == 1
    assert payload["result"]["target_track_mode"] == "existing"
    assert payload["result"]["clip_slot"] == 3
    assert payload["result"]["preserve_track_name"] is True


def test_browser_load_supports_notes_mode(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "1",
            "sounds/Bass Loop.alc",
            "--target-track-mode",
            "existing",
            "--clip-slot",
            "2",
            "--notes-mode",
            "append",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["notes_mode"] == "append"
    assert payload["result"]["clip_slot"] == 2


def test_browser_load_supports_length_and_groove_import_flags(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "1",
            "sounds/Bass Loop.alc",
            "--target-track-mode",
            "existing",
            "--clip-slot",
            "2",
            "--notes-mode",
            "replace",
            "--import-length",
            "--import-groove",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["notes_mode"] == "replace"
    assert payload["result"]["import_length"] is True
    assert payload["result"]["import_groove"] is True


def test_clip_notes_import_browser_supports_length_and_groove_flags(
    runner,
    cli_app,
    monkeypatch,
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "import-browser",
            "1",
            "3",
            "packs/LoFi HipHop by Comakid/MIDI Clips/Drums/Fuji Drumkit groove 01 80 bpm.alc",
            "--mode",
            "append",
            "--import-length",
            "--import-groove",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["track"] == 1
    assert payload["result"]["clip_slot"] == 3
    assert payload["result"]["target_track_mode"] == "existing"
    assert payload["result"]["notes_mode"] == "append"
    assert payload["result"]["import_length"] is True
    assert payload["result"]["import_groove"] is True
    assert payload["result"]["path"].endswith(".alc")
    assert payload["result"]["uri"] is None


def test_browser_load_drum_kit_supports_kit_uri_or_path(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    by_uri = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load-drum-kit",
            "0",
            "rack:drums",
            "--kit-uri",
            "kit:acoustic",
        ],
    )
    by_path = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load-drum-kit",
            "0",
            "rack:drums",
            "--kit-path",
            "drums/Kits/Acoustic Kit",
        ],
    )

    assert by_uri.exit_code == 0
    assert by_path.exit_code == 0
    uri_payload = json.loads(by_uri.stdout)
    path_payload = json.loads(by_path.stdout)
    assert uri_payload["result"]["kit_uri"] == "kit:acoustic"
    assert uri_payload["result"]["kit_path"] is None
    assert path_payload["result"]["kit_path"] == "drums/Kits/Acoustic Kit"
    assert path_payload["result"]["kit_uri"] is None


def test_track_mixer_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import track

    monkeypatch.setattr(track, "get_client", lambda ctx: _ClientStub())

    mute = runner.invoke(
        cli_app,
        ["--output", "json", "track", "mute", "set", "true", "--track-index", "0"],
    )
    solo = runner.invoke(
        cli_app,
        ["--output", "json", "track", "solo", "get", "--track-index", "0"],
    )
    arm = runner.invoke(
        cli_app,
        ["--output", "json", "track", "arm", "set", "false", "--track-index", "0"],
    )
    panning = runner.invoke(
        cli_app,
        ["--output", "json", "track", "panning", "set", "--track-index", "0", "--", "-0.3"],
    )

    assert mute.exit_code == 0
    assert solo.exit_code == 0
    assert arm.exit_code == 0
    assert panning.exit_code == 0

    mute_payload = json.loads(mute.stdout)
    solo_payload = json.loads(solo.stdout)
    arm_payload = json.loads(arm.stdout)
    panning_payload = json.loads(panning.stdout)
    assert mute_payload["result"]["mute"] is True
    assert solo_payload["result"]["solo"] is False
    assert arm_payload["result"]["arm"] is False
    assert panning_payload["result"]["panning"] == -0.3


def test_track_send_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import track

    monkeypatch.setattr(track, "get_client", lambda ctx: _ClientStub())

    get_result = runner.invoke(
        cli_app,
        ["--output", "json", "track", "send", "get", "1", "--track-index", "0"],
    )
    set_result = runner.invoke(
        cli_app,
        ["--output", "json", "track", "send", "set", "1", "0.6", "--track-index", "0"],
    )

    assert get_result.exit_code == 0
    assert set_result.exit_code == 0

    get_payload = json.loads(get_result.stdout)
    set_payload = json.loads(set_result.stdout)
    assert get_payload["result"] == {"track": 0, "send": 1, "value": 0.25}
    assert set_payload["result"] == {"track": 0, "send": 1, "value": 0.6}


def test_return_track_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import return_track, return_tracks

    monkeypatch.setattr(return_tracks, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(return_track, "get_client", lambda ctx: _ClientStub())

    listed = runner.invoke(cli_app, ["--output", "json", "return-tracks", "list"])
    volume = runner.invoke(
        cli_app,
        ["--output", "json", "return-track", "volume", "set", "0", "0.7"],
    )
    mute = runner.invoke(
        cli_app,
        ["--output", "json", "return-track", "mute", "set", "0", "true"],
    )
    solo = runner.invoke(
        cli_app,
        ["--output", "json", "return-track", "solo", "get", "0"],
    )

    assert listed.exit_code == 0
    assert volume.exit_code == 0
    assert mute.exit_code == 0
    assert solo.exit_code == 0

    listed_payload = json.loads(listed.stdout)
    volume_payload = json.loads(volume.stdout)
    mute_payload = json.loads(mute.stdout)
    solo_payload = json.loads(solo.stdout)
    assert listed_payload["result"]["return_tracks"][0]["name"] == "Reverb"
    assert volume_payload["result"] == {"return_track": 0, "volume": 0.7}
    assert mute_payload["result"] == {"return_track": 0, "mute": True}
    assert solo_payload["result"] == {"return_track": 0, "solo": True}


def test_master_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import master

    monkeypatch.setattr(master, "get_client", lambda ctx: _ClientStub())

    info = runner.invoke(cli_app, ["--output", "json", "master", "info"])
    volume = runner.invoke(cli_app, ["--output", "json", "master", "volume", "get"])
    panning = runner.invoke(cli_app, ["--output", "json", "master", "panning", "get"])
    devices = runner.invoke(cli_app, ["--output", "json", "master", "devices", "list"])

    assert info.exit_code == 0
    assert volume.exit_code == 0
    assert panning.exit_code == 0
    assert devices.exit_code == 0

    info_payload = json.loads(info.stdout)
    volume_payload = json.loads(volume.stdout)
    panning_payload = json.loads(panning.stdout)
    devices_payload = json.loads(devices.stdout)
    assert info_payload["result"] == {"name": "Master", "volume": 0.9, "panning": 0.0}
    assert volume_payload["result"] == {"volume": 0.9}
    assert panning_payload["result"] == {"panning": 0.0}
    assert devices_payload["result"] == {"devices": [{"index": 0, "name": "Limiter"}]}


def test_mixer_and_track_routing_commands_output_json_envelope(
    runner,
    cli_app,
    monkeypatch,
) -> None:
    from ableton_cli.commands import mixer, track

    monkeypatch.setattr(mixer, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(track, "get_client", lambda ctx: _ClientStub())

    crossfader = runner.invoke(cli_app, ["--output", "json", "mixer", "crossfader", "set", "0.2"])
    cue_volume = runner.invoke(cli_app, ["--output", "json", "mixer", "cue-volume", "get"])
    cue_routing = runner.invoke(
        cli_app,
        ["--output", "json", "mixer", "cue-routing", "set", "Ext. Out"],
    )
    input_routing = runner.invoke(
        cli_app,
        ["--output", "json", "track", "routing", "input", "get", "--track-index", "0"],
    )
    output_routing = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "track",
            "routing",
            "output",
            "set",
            "--type",
            "Master",
            "--channel",
            "3/4",
            "--track-index",
            "0",
        ],
    )

    assert crossfader.exit_code == 0
    assert cue_volume.exit_code == 0
    assert cue_routing.exit_code == 0
    assert input_routing.exit_code == 0
    assert output_routing.exit_code == 0

    crossfader_payload = json.loads(crossfader.stdout)
    cue_volume_payload = json.loads(cue_volume.stdout)
    cue_routing_payload = json.loads(cue_routing.stdout)
    input_payload = json.loads(input_routing.stdout)
    output_payload = json.loads(output_routing.stdout)
    assert crossfader_payload["result"] == {"value": 0.2}
    assert cue_volume_payload["result"] == {"value": 0.8}
    assert cue_routing_payload["result"]["routing"] == "Ext. Out"
    assert input_payload["result"]["current"] == {"type": "Ext. In", "channel": "1/2"}
    assert output_payload["result"]["current"] == {"type": "Master", "channel": "3/4"}


def test_scenes_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import scenes

    monkeypatch.setattr(scenes, "get_client", lambda ctx: _ClientStub())

    listed = runner.invoke(cli_app, ["--output", "json", "scenes", "list"])
    created = runner.invoke(cli_app, ["--output", "json", "scenes", "create", "--index", "1"])
    renamed = runner.invoke(
        cli_app,
        ["--output", "json", "scenes", "name", "set", "1", "Build"],
    )
    fired = runner.invoke(cli_app, ["--output", "json", "scenes", "fire", "1"])

    assert listed.exit_code == 0
    assert created.exit_code == 0
    assert renamed.exit_code == 0
    assert fired.exit_code == 0

    listed_payload = json.loads(listed.stdout)
    created_payload = json.loads(created.stdout)
    renamed_payload = json.loads(renamed.stdout)
    fired_payload = json.loads(fired.stdout)
    assert listed_payload["result"]["scenes"][0]["name"] == "Intro"
    assert created_payload["result"]["index"] == 1
    assert renamed_payload["result"]["name"] == "Build"
    assert fired_payload["result"]["fired"] is True


def test_clip_duplicate_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    duplicated = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate", "0", "1", "2"],
    )
    assert duplicated.exit_code == 0
    payload = json.loads(duplicated.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 0, "src_clip": 1, "dst_clip": 2, "duplicated": True}


def test_clip_duplicate_supports_multiple_destinations(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    duplicated = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate", "0", "1", "--to", "2,4,5"],
    )
    assert duplicated.exit_code == 0
    payload = json.loads(duplicated.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "track": 0,
        "src_clip": 1,
        "dst_clips": [2, 4, 5],
        "duplicated": True,
    }


def test_clip_duplicate_many_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    duplicated = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate-many", "0", "1", "--to", "2,4,5"],
    )
    assert duplicated.exit_code == 0
    payload = json.loads(duplicated.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "track": 0,
        "src_clip": 1,
        "dst_clips": [2, 4, 5],
        "duplicated": True,
    }


def test_clip_cut_to_drum_rack_command_supports_session_source(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "cut-to-drum-rack",
            "--source-track",
            "0",
            "--source-clip",
            "1",
            "--slice-count",
            "8",
            "--start-pad",
            "4",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "source_track": 0,
        "source_clip": 1,
        "source_uri": None,
        "source_path": None,
        "target_track": 2,
        "grid": None,
        "slice_count": 8,
        "start_pad": 4,
        "assigned_count": 8,
        "create_trigger_clip": False,
        "trigger_clip_created": False,
        "trigger_clip_slot": None,
    }


def test_clip_cut_to_drum_rack_command_supports_browser_source_and_trigger_clip(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "cut-to-drum-rack",
            "--source",
            "sounds/Bass Loop.wav",
            "--target-track",
            "0",
            "--grid",
            "1/16",
            "--create-trigger-clip",
            "--trigger-clip-slot",
            "3",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "source_track": None,
        "source_clip": None,
        "source_uri": None,
        "source_path": "sounds/Bass Loop.wav",
        "target_track": 0,
        "grid": "1/16",
        "slice_count": 4,
        "start_pad": 0,
        "assigned_count": 4,
        "create_trigger_clip": True,
        "trigger_clip_created": True,
        "trigger_clip_slot": 3,
    }


def test_clip_place_pattern_supports_scene_ranges(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    duplicated = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "place-pattern", "0", "--clip", "1", "--scenes", "2-4,6"],
    )
    assert duplicated.exit_code == 0
    payload = json.loads(duplicated.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "track": 0,
        "src_clip": 1,
        "dst_clips": [2, 3, 4, 6],
        "duplicated": True,
    }


def test_clip_place_pattern_supports_scene_names(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    duplicated = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "place-pattern",
            "0",
            "--clip",
            "1",
            "--scenes",
            "Intro,Peak",
        ],
    )
    assert duplicated.exit_code == 0
    payload = json.loads(duplicated.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "track": 0,
        "src_clip": 1,
        "dst_clips": [0, 2],
        "duplicated": True,
    }


def test_clip_name_set_many_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    renamed = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "name", "set-many", "0", "--map", "1:Main,2:Var,5:Peak"],
    )
    assert renamed.exit_code == 0
    payload = json.loads(renamed.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {
        "track": 0,
        "updated_count": 3,
        "updated": [
            {"track": 0, "clip": 1, "name": "Main"},
            {"track": 0, "clip": 2, "name": "Var"},
            {"track": 0, "clip": 5, "name": "Peak"},
        ],
    }


def test_clip_active_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    active_get = runner.invoke(cli_app, ["--output", "json", "clip", "active", "get", "0", "1"])
    active_set = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "active", "set", "0", "1", "false"],
    )

    assert active_get.exit_code == 0
    assert active_set.exit_code == 0
    payload_get = json.loads(active_get.stdout)
    payload_set = json.loads(active_set.stdout)
    assert payload_get["result"] == {"track": 0, "clip": 1, "active": True}
    assert payload_set["result"] == {"track": 0, "clip": 1, "active": False}


def test_scenes_move_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import scenes

    monkeypatch.setattr(scenes, "get_client", lambda ctx: _ClientStub())

    moved = runner.invoke(
        cli_app,
        ["--output", "json", "scenes", "move", "3", "1"],
    )
    assert moved.exit_code == 0
    payload = json.loads(moved.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"from": 3, "to": 1, "moved": True}


def test_tracks_delete_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import tracks

    monkeypatch.setattr(tracks, "get_client", lambda ctx: _ClientStub())

    deleted = runner.invoke(cli_app, ["--output", "json", "tracks", "delete", "1"])
    assert deleted.exit_code == 0
    payload = json.loads(deleted.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 1, "deleted": True}


def test_transport_position_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import transport

    monkeypatch.setattr(transport, "get_client", lambda ctx: _ClientStub())

    gotten = runner.invoke(cli_app, ["--output", "json", "transport", "position", "get"])
    set_result = runner.invoke(
        cli_app,
        ["--output", "json", "transport", "position", "set", "32"],
    )
    rewind = runner.invoke(cli_app, ["--output", "json", "transport", "rewind"])

    assert gotten.exit_code == 0
    assert set_result.exit_code == 0
    assert rewind.exit_code == 0
    gotten_payload = json.loads(gotten.stdout)
    set_payload = json.loads(set_result.stdout)
    rewind_payload = json.loads(rewind.stdout)
    assert gotten_payload["ok"] is True
    assert set_payload["ok"] is True
    assert rewind_payload["ok"] is True
    assert gotten_payload["result"] == {"current_time": 4.0, "beat_position": 4.0}
    assert set_payload["result"] == {"current_time": 32.0, "beat_position": 32.0}
    assert rewind_payload["result"] == {"current_time": 0.0, "beat_position": 0.0}


def test_arrangement_record_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    started = runner.invoke(cli_app, ["--output", "json", "arrangement", "record", "start"])
    stopped = runner.invoke(cli_app, ["--output", "json", "arrangement", "record", "stop"])

    assert started.exit_code == 0
    assert stopped.exit_code == 0
    started_payload = json.loads(started.stdout)
    stopped_payload = json.loads(stopped.stdout)
    assert started_payload["result"]["recording"] is True
    assert stopped_payload["result"]["recording"] is False


def test_arrangement_clip_create_command_outputs_json_envelope(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    midi_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "0",
            "--start",
            "8",
            "--length",
            "4",
        ],
    )
    audio_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "1",
            "--start",
            "16",
            "--length",
            "8",
            "--audio-path",
            "/tmp/loop.wav",
        ],
    )

    assert midi_result.exit_code == 0
    assert audio_result.exit_code == 0

    midi_payload = json.loads(midi_result.stdout)
    audio_payload = json.loads(audio_result.stdout)
    assert midi_payload["ok"] is True
    assert audio_payload["ok"] is True
    assert midi_payload["result"] == {
        "track": 0,
        "start_time": 8.0,
        "length": 4.0,
        "kind": "midi",
        "arrangement_view_focused": True,
        "created": True,
    }
    assert audio_payload["result"] == {
        "track": 1,
        "start_time": 16.0,
        "length": 8.0,
        "kind": "audio",
        "audio_path": "/tmp/loop.wav",
        "arrangement_view_focused": True,
        "created": True,
    }


def test_arrangement_clip_create_accepts_notes_options(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "0",
            "--start",
            "8",
            "--length",
            "4",
            "--notes-json",
            '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]',
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["notes_added"] == 1


def test_arrangement_clip_create_accepts_windows_absolute_audio_path(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "1",
            "--start",
            "16",
            "--length",
            "8",
            "--audio-path",
            "C:/tmp/loop.wav",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["audio_path"] == "C:/tmp/loop.wav"


def test_arrangement_clip_create_rejects_track_kind_audio_path_mismatch(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    midi_with_audio_path = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "0",
            "--start",
            "0",
            "--length",
            "4",
            "--audio-path",
            "/tmp/loop.wav",
        ],
    )
    audio_without_audio_path = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "create",
            "1",
            "--start",
            "0",
            "--length",
            "4",
        ],
    )

    assert midi_with_audio_path.exit_code == 2
    assert audio_without_audio_path.exit_code == 2
    assert json.loads(midi_with_audio_path.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(audio_without_audio_path.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_arrangement_clip_list_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    all_tracks = runner.invoke(
        cli_app,
        ["--output", "json", "arrangement", "clip", "list"],
    )
    filtered = runner.invoke(
        cli_app,
        ["--output", "json", "arrangement", "clip", "list", "--track", "1"],
    )

    assert all_tracks.exit_code == 0
    assert filtered.exit_code == 0
    all_payload = json.loads(all_tracks.stdout)
    filtered_payload = json.loads(filtered.stdout)
    assert all_payload["ok"] is True
    assert filtered_payload["ok"] is True
    assert all_payload["result"] == {
        "track": None,
        "clip_count": 2,
        "clips": [
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
        ],
    }
    assert filtered_payload["result"] == {
        "track": 1,
        "clip_count": 1,
        "clips": [
            {
                "track": 1,
                "index": 0,
                "name": "Clip B",
                "start_time": 16.0,
                "length": 8.0,
                "is_audio_clip": True,
                "is_midi_clip": False,
            }
        ],
    }


def test_arrangement_clip_notes_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    add_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "notes",
            "add",
            "0",
            "1",
            "--notes-json",
            '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]',
        ],
    )
    get_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "notes",
            "get",
            "0",
            "1",
            "--start-time",
            "0",
            "--end-time",
            "4",
            "--pitch",
            "60",
        ],
    )
    clear_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "notes",
            "clear",
            "0",
            "1",
            "--pitch",
            "60",
        ],
    )
    replace_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "notes",
            "replace",
            "0",
            "1",
            "--notes-json",
            '[{"pitch":62,"start_time":1.0,"duration":0.5,"velocity":100,"mute":false}]',
            "--start-time",
            "0",
            "--end-time",
            "4",
        ],
    )
    import_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "notes",
            "import-browser",
            "0",
            "1",
            "sounds/Bass Loop.alc",
            "--mode",
            "append",
            "--import-length",
            "--import-groove",
        ],
    )

    assert add_result.exit_code == 0
    assert get_result.exit_code == 0
    assert clear_result.exit_code == 0
    assert replace_result.exit_code == 0
    assert import_result.exit_code == 0

    assert json.loads(add_result.stdout)["result"] == {"track": 0, "index": 1, "note_count": 1}
    assert json.loads(get_result.stdout)["result"]["note_count"] == 0
    assert json.loads(clear_result.stdout)["result"]["cleared_count"] == 1
    assert json.loads(replace_result.stdout)["result"]["added_count"] == 1
    imported = json.loads(import_result.stdout)["result"]
    assert imported["mode"] == "append"
    assert imported["import_length"] is True
    assert imported["import_groove"] is True


def test_arrangement_clip_delete_command_supports_index_range_all(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    by_index = runner.invoke(
        cli_app,
        ["--output", "json", "arrangement", "clip", "delete", "0", "1"],
    )
    by_range = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "delete",
            "0",
            "--start",
            "8",
            "--end",
            "16",
        ],
    )
    by_all = runner.invoke(
        cli_app,
        ["--output", "json", "arrangement", "clip", "delete", "0", "--all"],
    )

    assert by_index.exit_code == 0
    assert by_range.exit_code == 0
    assert by_all.exit_code == 0
    assert json.loads(by_index.stdout)["result"]["mode"] == "index"
    assert json.loads(by_range.stdout)["result"]["mode"] == "range"
    assert json.loads(by_all.stdout)["result"]["mode"] == "all"


def test_arrangement_from_session_command_outputs_json_envelope(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "arrangement", "from-session", "--scenes", "0:24,1:48"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["scene_count"] == 2
    assert payload["result"]["scenes"] == [
        {"scene": 0, "duration_beats": 24.0},
        {"scene": 1, "duration_beats": 48.0},
    ]


def test_new_commands_validate_arguments_with_exit_code_2(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip, scenes, song, tracks

    monkeypatch.setattr(song, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(scenes, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(tracks, "get_client", lambda ctx: _ClientStub())

    song_save = runner.invoke(cli_app, ["--output", "json", "song", "save", "--path", "   "])
    song_export = runner.invoke(
        cli_app,
        ["--output", "json", "song", "export", "audio", "--path", " "],
    )
    clip_duplicate = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate", "0", "1", "--", "-1"],
    )
    scenes_move = runner.invoke(cli_app, ["--output", "json", "scenes", "move", "--", "-1", "0"])
    tracks_delete = runner.invoke(cli_app, ["--output", "json", "tracks", "delete", "--", "-1"])

    assert song_save.exit_code == 2
    assert song_export.exit_code == 2
    assert clip_duplicate.exit_code == 2
    assert scenes_move.exit_code == 2
    assert tracks_delete.exit_code == 2

    assert json.loads(song_save.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(song_export.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(clip_duplicate.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(scenes_move.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(tracks_delete.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_batch_run_outputs_json_envelope(runner, cli_app, monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.commands import batch

    monkeypatch.setattr(batch, "get_client", lambda ctx: _ClientStub())

    steps_path = tmp_path / "steps.json"
    steps_path.write_text(
        json.dumps(
            {
                "steps": [
                    {"name": "transport_tempo_set", "args": {"bpm": 128}},
                    {"name": "tracks_list", "args": {}},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        ["--output", "json", "batch", "run", "--steps-file", str(steps_path)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["step_count"] == 2


def test_batch_run_accepts_steps_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    monkeypatch.setattr(batch, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--steps-json",
            json.dumps({"steps": [{"name": "tracks_list", "args": {}}]}),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["step_count"] == 1


def test_batch_run_accepts_steps_stdin(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    monkeypatch.setattr(batch, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "batch", "run", "--steps-stdin"],
        input=json.dumps({"steps": [{"name": "tracks_list", "args": {}}]}),
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["step_count"] == 1


def test_wait_ready_succeeds_when_ping_is_ready(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    monkeypatch.setattr(setup, "get_client", lambda ctx: _WaitReadyClientAlwaysReady())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "wait-ready", "--max-wait-ms", "100", "--interval-ms", "1"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["ready"] is True


def test_wait_ready_retries_until_ready(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    client = _WaitReadyClientEventuallyReady()
    monkeypatch.setattr(setup, "get_client", lambda ctx: client)

    result = runner.invoke(
        cli_app,
        ["--output", "json", "wait-ready", "--max-wait-ms", "100", "--interval-ms", "1"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["attempts"] == 3


def test_wait_ready_times_out_when_ping_never_recovers(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    monkeypatch.setattr(setup, "get_client", lambda ctx: _WaitReadyClientNeverReady())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "wait-ready", "--max-wait-ms", "1", "--interval-ms", "1"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "TIMEOUT"


def test_synth_foundation_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import synth

    monkeypatch.setattr(synth, "get_client", lambda ctx: _ClientStub())

    found = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "find", "--track", "0", "--type", "wavetable"],
    )
    listed = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "synth",
            "parameters",
            "list",
            "--track-index",
            "0",
            "--device-index",
            "1",
        ],
    )
    set_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "synth",
            "parameter",
            "set",
            "0.77",
            "--track-index",
            "0",
            "--device-index",
            "1",
            "--parameter-index",
            "0",
        ],
    )
    observed = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "observe", "--track-index", "0", "--device-index", "1"],
    )

    assert found.exit_code == 0
    assert listed.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    found_payload = json.loads(found.stdout)
    listed_payload = json.loads(listed.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert found_payload["result"]["synth_type"] == "wavetable"
    assert listed_payload["result"]["parameters"][0]["name"] == "Filter Freq"
    assert set_payload["result"]["after"] == 0.77
    assert observed_payload["result"]["detected_type"] == "wavetable"


def test_synth_standard_wrapper_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import synth

    monkeypatch.setattr(synth, "get_client", lambda ctx: _ClientStub())

    keys = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "wavetable", "keys"],
    )
    set_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "synth",
            "wavetable",
            "set",
            "0.62",
            "--track-index",
            "0",
            "--device-index",
            "1",
            "--parameter-key",
            "filter_cutoff",
        ],
    )
    observed = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "synth",
            "wavetable",
            "observe",
            "--track-index",
            "0",
            "--device-index",
            "1",
        ],
    )

    assert keys.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    keys_payload = json.loads(keys.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert keys_payload["result"]["key_count"] == 9
    assert set_payload["result"]["key"] == "filter_cutoff"
    assert set_payload["result"]["after"] == 0.62
    assert observed_payload["result"]["state"]["filter_cutoff"] == 0.5


def test_effect_foundation_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import effect

    monkeypatch.setattr(effect, "get_client", lambda ctx: _ClientStub())

    found = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "find", "--track", "0", "--type", "eq8"],
    )
    listed = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "effect",
            "parameters",
            "list",
            "--track-index",
            "0",
            "--device-index",
            "2",
        ],
    )
    set_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "effect",
            "parameter",
            "set",
            "0.77",
            "--track-index",
            "0",
            "--device-index",
            "2",
            "--parameter-index",
            "0",
        ],
    )
    observed = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "observe", "--track-index", "0", "--device-index", "2"],
    )

    assert found.exit_code == 0
    assert listed.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    found_payload = json.loads(found.stdout)
    listed_payload = json.loads(listed.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert found_payload["result"]["effect_type"] == "eq8"
    assert listed_payload["result"]["parameters"][0]["name"] == "1 Frequency A"
    assert set_payload["result"]["after"] == 0.77
    assert observed_payload["result"]["detected_type"] == "eq8"


def test_effect_standard_wrapper_commands_output_json_envelope(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import effect

    monkeypatch.setattr(effect, "get_client", lambda ctx: _ClientStub())

    keys = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "eq8", "keys"],
    )
    set_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "effect",
            "eq8",
            "set",
            "0.62",
            "--track-index",
            "0",
            "--device-index",
            "2",
            "--parameter-key",
            "band1_freq",
        ],
    )
    observed = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "effect",
            "eq8",
            "observe",
            "--track-index",
            "0",
            "--device-index",
            "2",
        ],
    )

    assert keys.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    keys_payload = json.loads(keys.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert keys_payload["result"]["key_count"] == 5
    assert set_payload["result"]["key"] == "band1_freq"
    assert set_payload["result"]["after"] == 0.62
    assert observed_payload["result"]["state"]["band1_freq"] == 0.5


class _BatchStreamClientStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute_remote_command(self, name: str, args: dict[str, object]):  # noqa: ANN201
        self.calls.append((name, args))
        return {"ok": True, "name": name}


def test_batch_stream_processes_multiple_lines_and_reuses_client(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import batch

    client = _BatchStreamClientStub()
    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return client

    monkeypatch.setattr(batch, "get_client", _get_client)

    payload = "\n".join(
        [
            json.dumps({"id": "first", "steps": [{"name": "tracks_list", "args": {}}]}),
            json.dumps({"id": "second", "steps": [{"name": "song_info", "args": {}}]}),
        ]
    )
    result = runner.invoke(cli_app, ["batch", "stream"], input=f"{payload}\n")

    assert result.exit_code == 0
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert get_client_calls["count"] == 1
    assert [item["id"] for item in responses] == ["first", "second"]
    assert [item["ok"] for item in responses] == [True, True]
    assert client.calls == [
        ("tracks_list", {}),
        ("song_info", {}),
    ]


def test_batch_stream_emits_structured_line_errors_and_continues(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import batch

    client = _BatchStreamClientStub()
    monkeypatch.setattr(batch, "get_client", lambda _ctx: client)

    payload = "\n".join(
        [
            json.dumps({"id": "ok-1", "steps": [{"name": "tracks_list", "args": {}}]}),
            "{",
            json.dumps({"id": "bad-steps", "steps": "not-array"}),
            json.dumps({"id": "ok-2", "steps": [{"name": "song_info", "args": {}}]}),
        ]
    )
    result = runner.invoke(cli_app, ["batch", "stream"], input=f"{payload}\n")

    assert result.exit_code == 0
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(responses) == 4

    assert responses[0]["id"] == "ok-1"
    assert responses[0]["ok"] is True

    assert responses[1]["id"] is None
    assert responses[1]["ok"] is False
    assert responses[1]["error"]["code"] == "INVALID_ARGUMENT"

    assert responses[2]["id"] == "bad-steps"
    assert responses[2]["ok"] is False
    assert responses[2]["error"]["code"] == "INVALID_ARGUMENT"

    assert responses[3]["id"] == "ok-2"
    assert responses[3]["ok"] is True
    assert len(client.calls) == 2


def _timeout_error() -> AppError:
    return AppError(
        error_code="TIMEOUT",
        message="timed out",
        hint="retry",
        exit_code=ExitCode.TIMEOUT,
    )


class _BatchAdvancedClientStub:
    def __init__(self) -> None:
        from ableton_cli.capabilities import compute_command_set_hash

        self.calls: list[tuple[str, dict[str, object]]] = []
        self._responses: dict[str, list[dict[str, object] | AppError]] = {}
        supported = ["ping", "tracks_list", "song_info", "track_volume_set"]
        self._ping_payload = {
            "protocol_version": 2,
            "supported_commands": supported,
            "command_set_hash": compute_command_set_hash(supported),
            "remote_script_version": "0.0.0",
            "api_support": {},
        }

    def set_responses(self, name: str, items: list[dict[str, object] | AppError]) -> None:
        self._responses[name] = list(items)

    def ping(self):  # noqa: ANN201
        return dict(self._ping_payload)

    def execute_remote_command(self, name: str, args: dict[str, object]):  # noqa: ANN201
        self.calls.append((name, args))
        queue = self._responses.get(name)
        if queue:
            item = queue.pop(0)
            if isinstance(item, AppError):
                raise item
            return item
        return {"ok": True, "name": name}


def test_batch_run_retries_only_configured_errors(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    client = _BatchAdvancedClientStub()
    client.set_responses("tracks_list", [_timeout_error(), {"tracks": []}])
    monkeypatch.setattr(batch, "get_client", lambda _ctx: client)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--steps-json",
            json.dumps(
                {
                    "steps": [
                        {
                            "name": "tracks_list",
                            "args": {},
                            "retry": {"max_attempts": 3, "backoff_ms": 0, "on": ["TIMEOUT"]},
                        }
                    ]
                }
            ),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["results"][0]["attempts"] == 2


def test_batch_run_fails_when_retry_is_exhausted(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    client = _BatchAdvancedClientStub()
    client.set_responses("tracks_list", [_timeout_error(), _timeout_error(), _timeout_error()])
    monkeypatch.setattr(batch, "get_client", lambda _ctx: client)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--steps-json",
            json.dumps(
                {
                    "steps": [
                        {
                            "name": "tracks_list",
                            "args": {},
                            "retry": {"max_attempts": 3, "backoff_ms": 0, "on": ["TIMEOUT"]},
                        }
                    ]
                }
            ),
        ],
    )

    assert result.exit_code == 20
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BATCH_RETRY_EXHAUSTED"


def test_batch_run_fails_when_assert_condition_does_not_match(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    client = _BatchAdvancedClientStub()
    client.set_responses("song_info", [{"tempo": 90.0}])
    client.set_responses("tracks_list", [{"tracks": []}])
    monkeypatch.setattr(batch, "get_client", lambda _ctx: client)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--steps-json",
            json.dumps(
                {
                    "steps": [
                        {"name": "song_info", "args": {}},
                        {
                            "name": "tracks_list",
                            "args": {},
                            "assert": {
                                "source": "previous",
                                "path": "tempo",
                                "op": "gte",
                                "value": 120.0,
                            },
                        },
                    ]
                }
            ),
        ],
    )

    assert result.exit_code == 20
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BATCH_ASSERT_FAILED"


def test_batch_run_preflight_blocks_on_protocol_mismatch(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    client = _BatchAdvancedClientStub()
    monkeypatch.setattr(batch, "get_client", lambda _ctx: client)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--steps-json",
            json.dumps(
                {
                    "preflight": {"protocol_version": 99},
                    "steps": [{"name": "tracks_list", "args": {}}],
                }
            ),
        ],
    )

    assert result.exit_code == 20
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BATCH_PREFLIGHT_FAILED"


def test_batch_stream_continues_after_assert_failure(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    client = _BatchAdvancedClientStub()
    client.set_responses("song_info", [{"tempo": 80.0}, {"tempo": 130.0}])
    monkeypatch.setattr(batch, "get_client", lambda _ctx: client)

    payload = "\n".join(
        [
            json.dumps(
                {
                    "id": "fail-assert",
                    "steps": [
                        {"name": "song_info", "args": {}},
                        {
                            "name": "tracks_list",
                            "args": {},
                            "assert": {
                                "source": "previous",
                                "path": "tempo",
                                "op": "gte",
                                "value": 100.0,
                            },
                        },
                    ],
                }
            ),
            json.dumps({"id": "ok", "steps": [{"name": "song_info", "args": {}}]}),
        ]
    )

    result = runner.invoke(cli_app, ["batch", "stream"], input=f"{payload}\n")

    assert result.exit_code == 0
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(responses) == 2
    assert responses[0]["id"] == "fail-assert"
    assert responses[0]["ok"] is False
    assert responses[0]["error"]["code"] == "BATCH_ASSERT_FAILED"
    assert responses[1]["id"] == "ok"
    assert responses[1]["ok"] is True
