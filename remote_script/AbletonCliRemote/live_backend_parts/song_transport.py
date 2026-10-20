from __future__ import annotations

import time
from typing import Any

from ..command_backend import MAX_BPM, MAX_PANNING, MAX_VOLUME, MIN_BPM, MIN_PANNING, MIN_VOLUME
from .base import _invalid_argument, _not_supported_by_live_api
from .routing import apply_routing, routing_state, string_choices

_TRANSPORT_STATE_TIMEOUT_SECONDS = 1.0
_TRANSPORT_STATE_POLL_INTERVAL_SECONDS = 0.01


class LiveBackendSongSessionMixin:
    def song_info(self) -> dict[str, Any]:
        song = self._ctx._song()
        return {
            "tempo": float(song.tempo),
            "is_playing": bool(song.is_playing),
            "current_time": float(song.current_song_time),
            "beat_position": float(song.current_song_time),
            "signature": {
                "numerator": int(song.signature_numerator),
                "denominator": int(song.signature_denominator),
            },
        }

    def song_new(self) -> dict[str, Any]:
        app = self._ctx._application()
        create_set = getattr(app, "new_live_set", None)
        if not callable(create_set):
            raise _not_supported_by_live_api(
                message="Song creation API is not available in Live API",
                hint="Create a new empty Set manually in Ableton Live.",
            )
        create_set()
        return {"created": True}

    def song_undo(self) -> dict[str, Any]:
        app = self._ctx._application()
        undo = getattr(app, "undo", None)
        if not callable(undo):
            raise _not_supported_by_live_api(
                message="Song undo API is not available in Live API",
                hint="Undo manually from Ableton Live.",
            )
        undo()
        return {"undone": True}

    def song_redo(self) -> dict[str, Any]:
        app = self._ctx._application()
        redo = getattr(app, "redo", None)
        if not callable(redo):
            raise _not_supported_by_live_api(
                message="Song redo API is not available in Live API",
                hint="Redo manually from Ableton Live.",
            )
        redo()
        return {"redone": True}

    def song_save(self, path: str) -> dict[str, Any]:
        app = self._ctx._application()
        save_set = getattr(app, "save_live_set", None)
        if not callable(save_set):
            raise _not_supported_by_live_api(
                message="Song save API is not available in Live API",
                hint="Save the Set manually from Ableton Live.",
            )
        save_set(path)
        return {"saved": True, "path": path}

    def song_export_audio(self, path: str) -> dict[str, Any]:
        app = self._ctx._application()
        export_audio = getattr(app, "export_audio", None)
        if not callable(export_audio):
            raise _not_supported_by_live_api(
                message="Song audio export API is not available in Live API",
                hint="Export audio manually from Ableton Live.",
            )
        export_audio(path)
        return {"exported": True, "path": path}

    def get_session_info(self) -> dict[str, Any]:
        song = self._ctx._song()
        master = song.master_track
        return {
            "tempo": float(song.tempo),
            "signature_numerator": int(song.signature_numerator),
            "signature_denominator": int(song.signature_denominator),
            "track_count": len(song.tracks),
            "return_track_count": len(getattr(song, "return_tracks", [])),
            "master_track": {
                "name": str(getattr(master, "name", "Master")),
                "volume": float(master.mixer_device.volume.value),
                "panning": float(master.mixer_device.panning.value),
            },
        }

    def session_snapshot(self) -> dict[str, Any]:
        return {
            "song_info": self.song_info(),
            "session_info": self.get_session_info(),
            "tracks_list": self.tracks_list(),
            "scenes_list": self._ctx.services.scenes_arrangement.scenes_list(),
        }

    def get_track_info(self, track: int) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        clip_slots = []
        for slot_index, slot in enumerate(list(target.clip_slots)):
            clip_info = None
            if slot.has_clip:
                clip = slot.clip
                clip_info = {
                    "name": str(getattr(clip, "name", "")),
                    "length": float(getattr(clip, "length", 0.0)),
                    "is_playing": bool(getattr(clip, "is_playing", False)),
                    "is_recording": bool(getattr(clip, "is_recording", False)),
                }
            clip_slots.append(
                {
                    "index": slot_index,
                    "has_clip": bool(slot.has_clip),
                    "clip": clip_info,
                }
            )

        devices = []
        devices = self._ctx._serialize_devices(
            list(target.devices),
            track_index=track,
            track_stable_ref=self._ctx._track_stable_ref(target, index=track),
        )

        return {
            "index": track,
            "stable_ref": self._ctx._track_stable_ref(target, index=track),
            "name": str(target.name),
            "is_audio_track": bool(getattr(target, "has_audio_input", False)),
            "is_midi_track": bool(getattr(target, "has_midi_input", False)),
            "mute": bool(target.mute),
            "solo": bool(target.solo),
            "arm": bool(getattr(target, "arm", False)),
            "volume": float(target.mixer_device.volume.value),
            "panning": float(target.mixer_device.panning.value),
            "clip_slots": clip_slots,
            "devices": devices,
        }

    def tracks_list(self) -> dict[str, Any]:
        tracks = []
        for index, track in enumerate(self._ctx._song().tracks):
            tracks.append(
                {
                    "index": index,
                    "stable_ref": self._ctx._track_stable_ref(track, index=index),
                    "name": str(track.name),
                    "mute": bool(track.mute),
                    "solo": bool(track.solo),
                    "arm": bool(getattr(track, "arm", False)),
                    "volume": float(track.mixer_device.volume.value),
                }
            )
        return {"tracks": tracks}

    def create_midi_track(self, index: int) -> dict[str, Any]:
        song = self._ctx._song()
        if index != -1 and index > len(song.tracks):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint="Use -1 for append or a valid insertion index.",
            )
        song.create_midi_track(index)
        target_index = len(song.tracks) - 1 if index == -1 else index
        track = song.tracks[target_index]
        return {"index": target_index, "name": str(track.name), "kind": "midi"}

    def create_audio_track(self, index: int) -> dict[str, Any]:
        song = self._ctx._song()
        if index != -1 and index > len(song.tracks):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint="Use -1 for append or a valid insertion index.",
            )
        song.create_audio_track(index)
        target_index = len(song.tracks) - 1 if index == -1 else index
        track = song.tracks[target_index]
        return {"index": target_index, "name": str(track.name), "kind": "audio"}

    def set_track_name(self, track: int, name: str) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        target.name = name
        return {"track": track, "name": str(target.name)}


_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_SCALE_ATTRIBUTES = ("root_note", "scale_name", "scale_mode", "scale_intervals")


class LiveBackendSongScaleMixin:
    """The Set's global scale (Live 12+), which scale-aware devices follow."""

    def _scale_song(self) -> Any:
        song = self._ctx._song()
        if not all(hasattr(song, attribute) for attribute in _SCALE_ATTRIBUTES):
            raise _not_supported_by_live_api(
                message="Song scale API is not available in Live API",
                hint="Use Live 12 or later, which exposes root_note/scale_name/scale_mode.",
            )
        return song

    def song_scale_get(self) -> dict[str, Any]:
        song = self._scale_song()
        root_note = int(song.root_note)
        return {
            "root_note": root_note,
            "root_name": _NOTE_NAMES[root_note % 12],
            "scale_name": str(song.scale_name),
            "scale_mode": bool(song.scale_mode),
            "scale_intervals": [int(interval) for interval in list(song.scale_intervals)],
        }

    def song_scale_set(
        self,
        root_note: int | None,
        scale_name: str | None,
        scale_mode: bool | None,
    ) -> dict[str, Any]:
        song = self._scale_song()
        if root_note is not None and not 0 <= root_note <= 11:
            raise _invalid_argument(
                message=f"root_note out of range: {root_note}",
                hint="Use 0..11 where 0 = C.",
            )
        if scale_name is not None:
            previous_name = str(song.scale_name)
            song.scale_name = scale_name
            if str(song.scale_name) != scale_name:
                # Live answers an unknown name by switching to Major, so undo
                # that before failing rather than leave the Set changed.
                song.scale_name = previous_name
                raise _invalid_argument(
                    message=f"Live did not accept scale name: {scale_name}",
                    hint="Use a name from Live's Scale chooser exactly (e.g. 'Minor', 'Dorian').",
                )
        if root_note is not None:
            song.root_note = int(root_note)
        if scale_mode is not None:
            song.scale_mode = bool(scale_mode)
        return self.song_scale_get()


class LiveBackendTransportMixerMixin:
    def _track_routing_payload(self, track_index: int, direction: str) -> dict[str, Any]:
        track = self._ctx._track_at(track_index)
        return {"track": track_index, **routing_state(track, direction, subject="track")}

    def _set_track_routing(
        self,
        *,
        track_index: int,
        direction: str,
        routing_type: str,
        routing_channel: str | None,
    ) -> dict[str, Any]:
        track = self._ctx._track_at(track_index)
        apply_routing(
            track,
            direction,
            subject="track",
            routing_type=routing_type,
            routing_channel=routing_channel,
        )
        return self._track_routing_payload(track_index, direction)

    def _require_cue_routing_support(self) -> tuple[Any, list[str]]:
        song = self._ctx._song()
        if not hasattr(song, "cue_routing") or not hasattr(song, "available_cue_routings"):
            raise _not_supported_by_live_api(
                message="Cue routing API is not available in Live API",
                hint="Use a Live version exposing cue routing properties.",
            )
        available = string_choices(list(song.available_cue_routings))
        return song, available

    def _wait_for_transport_state(self, *, expected: bool | None = None) -> bool:
        deadline = time.monotonic() + _TRANSPORT_STATE_TIMEOUT_SECONDS
        while True:
            is_playing = bool(self._ctx._song().is_playing)
            if expected is None or is_playing is expected:
                return is_playing
            if time.monotonic() >= deadline:
                return is_playing
            time.sleep(_TRANSPORT_STATE_POLL_INTERVAL_SECONDS)

    def transport_play(self) -> dict[str, Any]:
        return self.start_playback()

    def transport_stop(self) -> dict[str, Any]:
        return self.stop_playback()

    def transport_toggle(self) -> dict[str, Any]:
        song = self._ctx._song()
        if self._wait_for_transport_state():
            song.stop_playing()
            expected = False
        else:
            song.start_playing()
            expected = True
        return {"is_playing": self._wait_for_transport_state(expected=expected)}

    def start_playback(self) -> dict[str, Any]:
        song = self._ctx._song()
        song.start_playing()
        return {"is_playing": self._wait_for_transport_state(expected=True)}

    def stop_playback(self) -> dict[str, Any]:
        song = self._ctx._song()
        song.stop_playing()
        return {"is_playing": self._wait_for_transport_state(expected=False)}

    def transport_tempo_get(self) -> dict[str, Any]:
        return {"tempo": float(self._ctx._song().tempo)}

    def transport_tempo_set(self, bpm: float) -> dict[str, Any]:
        if bpm < MIN_BPM or bpm > MAX_BPM:
            raise _invalid_argument(
                message=f"bpm must be between {MIN_BPM} and {MAX_BPM}",
                hint="Use a tempo value like 120.",
            )
        song = self._ctx._song()
        song.tempo = float(bpm)
        return {"tempo": float(song.tempo)}

    def transport_position_get(self) -> dict[str, Any]:
        song = self._ctx._song()
        if not hasattr(song, "current_song_time"):
            raise _not_supported_by_live_api(
                message="Song position API is not available in Live API",
                hint="Use a Live version exposing song.current_song_time.",
            )
        current_time = float(song.current_song_time)
        return {"current_time": current_time, "beat_position": current_time}

    def transport_position_set(self, beats: float) -> dict[str, Any]:
        song = self._ctx._song()
        if not hasattr(song, "current_song_time"):
            raise _not_supported_by_live_api(
                message="Song position API is not available in Live API",
                hint="Use a Live version exposing song.current_song_time.",
            )
        song.current_song_time = float(beats)
        current_time = float(song.current_song_time)
        return {"current_time": current_time, "beat_position": current_time}

    def transport_rewind(self) -> dict[str, Any]:
        return self.transport_position_set(0.0)

    def set_tempo(self, tempo: float) -> dict[str, Any]:
        return self.transport_tempo_set(tempo)

    def track_volume_get(self, track: int) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        return {"track": track, "volume": float(target.mixer_device.volume.value)}

    def track_volume_set(self, track: int, value: float) -> dict[str, Any]:
        if value < MIN_VOLUME or value > MAX_VOLUME:
            raise _invalid_argument(
                message=f"value must be between {MIN_VOLUME} and {MAX_VOLUME}",
                hint="Use a normalized volume value in [0.0, 1.0].",
            )
        target = self._ctx._track_at(track)
        target.mixer_device.volume.value = float(value)
        return {"track": track, "volume": float(target.mixer_device.volume.value)}

    def track_mute_get(self, track: int) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        return {"track": track, "mute": bool(target.mute)}

    def track_mute_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        target.mute = bool(value)
        return {"track": track, "mute": bool(target.mute)}

    def track_solo_get(self, track: int) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        return {"track": track, "solo": bool(target.solo)}

    def track_solo_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        target.solo = bool(value)
        return {"track": track, "solo": bool(target.solo)}

    def track_arm_get(self, track: int) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        if not hasattr(target, "arm"):
            raise _invalid_argument(
                message="Track does not support arm",
                hint="Use a MIDI or audio track with arm support.",
            )
        return {"track": track, "arm": bool(target.arm)}

    def track_arm_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        if not hasattr(target, "arm"):
            raise _invalid_argument(
                message="Track does not support arm",
                hint="Use a MIDI or audio track with arm support.",
            )
        target.arm = bool(value)
        return {"track": track, "arm": bool(target.arm)}

    def track_panning_get(self, track: int) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        return {"track": track, "panning": float(target.mixer_device.panning.value)}

    def track_panning_set(self, track: int, value: float) -> dict[str, Any]:
        if value < MIN_PANNING or value > MAX_PANNING:
            raise _invalid_argument(
                message=f"value must be between {MIN_PANNING} and {MAX_PANNING}",
                hint="Use a normalized panning value in [-1.0, 1.0].",
            )
        target = self._ctx._track_at(track)
        target.mixer_device.panning.value = float(value)
        return {"track": track, "panning": float(target.mixer_device.panning.value)}

    def track_send_get(self, track: int, send: int) -> dict[str, Any]:
        target = self._ctx._track_at(track)
        sends = list(getattr(target.mixer_device, "sends", []))
        if send < 0 or send >= len(sends):
            raise _invalid_argument(
                message=f"send out of range: {send}",
                hint="Use a valid 0-based send index.",
            )
        return {"track": track, "send": send, "value": float(sends[send].value)}

    def track_send_set(self, track: int, send: int, value: float) -> dict[str, Any]:
        if value < MIN_VOLUME or value > MAX_VOLUME:
            raise _invalid_argument(
                message=f"value must be between {MIN_VOLUME} and {MAX_VOLUME}",
                hint="Use a normalized volume value in [0.0, 1.0].",
            )
        target = self._ctx._track_at(track)
        sends = list(getattr(target.mixer_device, "sends", []))
        if send < 0 or send >= len(sends):
            raise _invalid_argument(
                message=f"send out of range: {send}",
                hint="Use a valid 0-based send index.",
            )
        sends[send].value = float(value)
        return {"track": track, "send": send, "value": float(sends[send].value)}

    def return_tracks_list(self) -> dict[str, Any]:
        tracks = []
        for index, track in enumerate(getattr(self._ctx._song(), "return_tracks", [])):
            tracks.append(
                {
                    "index": index,
                    "name": str(getattr(track, "name", f"Return {index}")),
                    "mute": bool(getattr(track, "mute", False)),
                    "solo": bool(getattr(track, "solo", False)),
                    "volume": float(track.mixer_device.volume.value),
                }
            )
        return {"return_tracks": tracks}

    def _song_callable(self, name: str, *, message: str, hint: str) -> Any:
        method = getattr(self._ctx._song(), name, None)
        if not callable(method):
            raise _not_supported_by_live_api(message=message, hint=hint)
        return method

    def return_track_create(self) -> dict[str, Any]:
        create = self._song_callable(
            "create_return_track",
            message="Song.create_return_track is not available in Live API",
            hint="Add the return track manually in Ableton Live.",
        )
        create()
        tracks = list(self._ctx._song().return_tracks)
        index = len(tracks) - 1
        return {
            "return_track": index,
            "name": str(getattr(tracks[index], "name", f"Return {index}")),
            "return_track_count": len(tracks),
        }

    def return_track_delete(self, return_track: int) -> dict[str, Any]:
        target = self._ctx._return_track_at(return_track)
        delete = self._song_callable(
            "delete_return_track",
            message="Song.delete_return_track is not available in Live API",
            hint="Delete the return track manually in Ableton Live.",
        )
        name = str(getattr(target, "name", f"Return {return_track}"))
        delete(return_track)
        return {
            "return_track": return_track,
            "name": name,
            "return_track_count": len(list(self._ctx._song().return_tracks)),
        }

    def return_track_volume_get(self, return_track: int) -> dict[str, Any]:
        target = self._ctx._return_track_at(return_track)
        return {"return_track": return_track, "volume": float(target.mixer_device.volume.value)}

    def return_track_volume_set(self, return_track: int, value: float) -> dict[str, Any]:
        if value < MIN_VOLUME or value > MAX_VOLUME:
            raise _invalid_argument(
                message=f"value must be between {MIN_VOLUME} and {MAX_VOLUME}",
                hint="Use a normalized volume value in [0.0, 1.0].",
            )
        target = self._ctx._return_track_at(return_track)
        target.mixer_device.volume.value = float(value)
        return {"return_track": return_track, "volume": float(target.mixer_device.volume.value)}

    def return_track_mute_get(self, return_track: int) -> dict[str, Any]:
        target = self._ctx._return_track_at(return_track)
        return {"return_track": return_track, "mute": bool(target.mute)}

    def return_track_mute_set(self, return_track: int, value: bool) -> dict[str, Any]:
        target = self._ctx._return_track_at(return_track)
        target.mute = bool(value)
        return {"return_track": return_track, "mute": bool(target.mute)}

    def return_track_solo_get(self, return_track: int) -> dict[str, Any]:
        target = self._ctx._return_track_at(return_track)
        return {"return_track": return_track, "solo": bool(target.solo)}

    def return_track_solo_set(self, return_track: int, value: bool) -> dict[str, Any]:
        target = self._ctx._return_track_at(return_track)
        target.solo = bool(value)
        return {"return_track": return_track, "solo": bool(target.solo)}

    def _meter_reading(self, target: Any) -> dict[str, Any]:
        """One reading of a track's output meters (Live's 0.0-1.0 meter scale)."""
        reading: dict[str, Any] = {}
        for channel in ("left", "right", "level"):
            value = getattr(target, f"output_meter_{channel}", None)
            if not isinstance(value, (int, float)):
                raise _not_supported_by_live_api(
                    message=f"Track output_meter_{channel} is not available in Live API",
                    hint="Use a Live version exposing track output meters.",
                )
            reading[channel] = float(value)
        reading["is_playing"] = bool(self._ctx._song().is_playing)
        return reading

    def track_meter_get(self, track: int) -> dict[str, Any]:
        return {"track": track, **self._meter_reading(self._ctx._track_at(track))}

    def return_track_meter_get(self, return_track: int) -> dict[str, Any]:
        target = self._ctx._return_track_at(return_track)
        return {"return_track": return_track, **self._meter_reading(target)}

    def master_meter_get(self) -> dict[str, Any]:
        return self._meter_reading(self._ctx._song().master_track)

    def master_info(self) -> dict[str, Any]:
        target = self._ctx._song().master_track
        return {
            "name": str(getattr(target, "name", "Master")),
            "volume": float(target.mixer_device.volume.value),
            "panning": float(target.mixer_device.panning.value),
        }

    def master_volume_get(self) -> dict[str, Any]:
        target = self._ctx._song().master_track
        return {"volume": float(target.mixer_device.volume.value)}

    def master_volume_set(self, value: float) -> dict[str, Any]:
        target = self._ctx._song().master_track
        target.mixer_device.volume.value = float(value)
        return {"volume": float(target.mixer_device.volume.value)}

    def master_panning_get(self) -> dict[str, Any]:
        target = self._ctx._song().master_track
        return {"panning": float(target.mixer_device.panning.value)}

    def master_panning_set(self, value: float) -> dict[str, Any]:
        target = self._ctx._song().master_track
        target.mixer_device.panning.value = float(value)
        return {"panning": float(target.mixer_device.panning.value)}

    def master_devices_list(self) -> dict[str, Any]:
        target = self._ctx._song().master_track
        return {"devices": self._ctx._serialize_devices(list(getattr(target, "devices", [])))}

    def mixer_crossfader_get(self) -> dict[str, Any]:
        mixer = self._ctx._song().master_track.mixer_device
        if not hasattr(mixer, "crossfader"):
            raise _not_supported_by_live_api(
                message="Crossfader API is not available in Live API",
                hint="Use a Live version exposing mixer crossfader properties.",
            )
        return {"value": float(mixer.crossfader.value)}

    def mixer_crossfader_set(self, value: float) -> dict[str, Any]:
        mixer = self._ctx._song().master_track.mixer_device
        if not hasattr(mixer, "crossfader"):
            raise _not_supported_by_live_api(
                message="Crossfader API is not available in Live API",
                hint="Use a Live version exposing mixer crossfader properties.",
            )
        mixer.crossfader.value = float(value)
        return {"value": float(mixer.crossfader.value)}

    def mixer_cue_volume_get(self) -> dict[str, Any]:
        mixer = self._ctx._song().master_track.mixer_device
        if not hasattr(mixer, "cue_volume"):
            raise _not_supported_by_live_api(
                message="Cue volume API is not available in Live API",
                hint="Use a Live version exposing cue volume properties.",
            )
        return {"value": float(mixer.cue_volume.value)}

    def mixer_cue_volume_set(self, value: float) -> dict[str, Any]:
        mixer = self._ctx._song().master_track.mixer_device
        if not hasattr(mixer, "cue_volume"):
            raise _not_supported_by_live_api(
                message="Cue volume API is not available in Live API",
                hint="Use a Live version exposing cue volume properties.",
            )
        mixer.cue_volume.value = float(value)
        return {"value": float(mixer.cue_volume.value)}

    def mixer_cue_routing_get(self) -> dict[str, Any]:
        song, available = self._require_cue_routing_support()
        return {
            "routing": str(song.cue_routing),
            "available_routings": available,
        }

    def mixer_cue_routing_set(self, routing: str) -> dict[str, Any]:
        song, available = self._require_cue_routing_support()
        if routing not in available:
            raise _invalid_argument(
                message=f"Unsupported cue routing: {routing}",
                hint="Use one of the exact routing names reported by mixer cue-routing get.",
            )
        song.cue_routing = routing
        return {
            "routing": str(song.cue_routing),
            "available_routings": available,
        }

    def track_routing_input_get(self, track: int) -> dict[str, Any]:
        return self._track_routing_payload(track, "input")

    def track_routing_input_set(
        self,
        track: int,
        routing_type: str,
        routing_channel: str | None,
    ) -> dict[str, Any]:
        return self._set_track_routing(
            track_index=track,
            direction="input",
            routing_type=routing_type,
            routing_channel=routing_channel,
        )

    def track_routing_output_get(self, track: int) -> dict[str, Any]:
        return self._track_routing_payload(track, "output")

    def track_routing_output_set(
        self,
        track: int,
        routing_type: str,
        routing_channel: str | None,
    ) -> dict[str, Any]:
        return self._set_track_routing(
            track_index=track,
            direction="output",
            routing_type=routing_type,
            routing_channel=routing_channel,
        )
