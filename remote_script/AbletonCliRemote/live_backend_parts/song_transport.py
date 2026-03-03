from __future__ import annotations

import time
from typing import Any

from ..command_backend import MAX_BPM, MAX_PANNING, MAX_VOLUME, MIN_BPM, MIN_PANNING, MIN_VOLUME
from .base import _invalid_argument, _not_supported_by_live_api

_TRANSPORT_STATE_TIMEOUT_SECONDS = 1.0
_TRANSPORT_STATE_POLL_INTERVAL_SECONDS = 0.01


class LiveBackendSongSessionMixin:
    def song_info(self) -> dict[str, Any]:
        song = self._song()
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
        app = self._application()
        create_set = getattr(app, "new_live_set", None)
        if not callable(create_set):
            raise _not_supported_by_live_api(
                message="Song creation API is not available in Live API",
                hint="Create a new empty Set manually in Ableton Live.",
            )
        create_set()
        return {"created": True}

    def song_save(self, path: str) -> dict[str, Any]:
        app = self._application()
        save_set = getattr(app, "save_live_set", None)
        if not callable(save_set):
            raise _not_supported_by_live_api(
                message="Song save API is not available in Live API",
                hint="Save the Set manually from Ableton Live.",
            )
        save_set(path)
        return {"saved": True, "path": path}

    def song_export_audio(self, path: str) -> dict[str, Any]:
        app = self._application()
        export_audio = getattr(app, "export_audio", None)
        if not callable(export_audio):
            raise _not_supported_by_live_api(
                message="Song audio export API is not available in Live API",
                hint="Export audio manually from Ableton Live.",
            )
        export_audio(path)
        return {"exported": True, "path": path}

    def get_session_info(self) -> dict[str, Any]:
        song = self._song()
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
            "scenes_list": self.scenes_list(),
        }

    def get_track_info(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
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
        for device_index, device in enumerate(list(target.devices)):
            params = []
            for param_index, param in enumerate(list(getattr(device, "parameters", []))):
                params.append(
                    {
                        "index": param_index,
                        "name": str(getattr(param, "name", f"Parameter {param_index}")),
                        "value": float(getattr(param, "value", 0.0)),
                    }
                )
            devices.append(
                {
                    "index": device_index,
                    "name": str(getattr(device, "name", "")),
                    "class_name": str(getattr(device, "class_name", "")),
                    "type": self._get_device_type(device),
                    "parameters": params,
                }
            )

        return {
            "index": track,
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
        for index, track in enumerate(self._song().tracks):
            tracks.append(
                {
                    "index": index,
                    "name": str(track.name),
                    "mute": bool(track.mute),
                    "solo": bool(track.solo),
                    "arm": bool(getattr(track, "arm", False)),
                    "volume": float(track.mixer_device.volume.value),
                }
            )
        return {"tracks": tracks}

    def create_midi_track(self, index: int) -> dict[str, Any]:
        song = self._song()
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
        song = self._song()
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
        target = self._track_at(track)
        target.name = name
        return {"track": track, "name": str(target.name)}


class LiveBackendTransportMixerMixin:
    def _wait_for_transport_state(self, *, expected: bool | None = None) -> bool:
        deadline = time.monotonic() + _TRANSPORT_STATE_TIMEOUT_SECONDS
        while True:
            is_playing = bool(self._song().is_playing)
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
        song = self._song()
        if self._wait_for_transport_state():
            song.stop_playing()
            expected = False
        else:
            song.start_playing()
            expected = True
        return {"is_playing": self._wait_for_transport_state(expected=expected)}

    def start_playback(self) -> dict[str, Any]:
        song = self._song()
        song.start_playing()
        return {"is_playing": self._wait_for_transport_state(expected=True)}

    def stop_playback(self) -> dict[str, Any]:
        song = self._song()
        song.stop_playing()
        return {"is_playing": self._wait_for_transport_state(expected=False)}

    def transport_tempo_get(self) -> dict[str, Any]:
        return {"tempo": float(self._song().tempo)}

    def transport_tempo_set(self, bpm: float) -> dict[str, Any]:
        if bpm < MIN_BPM or bpm > MAX_BPM:
            raise _invalid_argument(
                message=f"bpm must be between {MIN_BPM} and {MAX_BPM}",
                hint="Use a tempo value like 120.",
            )
        song = self._song()
        song.tempo = float(bpm)
        return {"tempo": float(song.tempo)}

    def transport_position_get(self) -> dict[str, Any]:
        song = self._song()
        if not hasattr(song, "current_song_time"):
            raise _not_supported_by_live_api(
                message="Song position API is not available in Live API",
                hint="Use a Live version exposing song.current_song_time.",
            )
        current_time = float(song.current_song_time)
        return {"current_time": current_time, "beat_position": current_time}

    def transport_position_set(self, beats: float) -> dict[str, Any]:
        song = self._song()
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
        target = self._track_at(track)
        return {"track": track, "volume": float(target.mixer_device.volume.value)}

    def track_volume_set(self, track: int, value: float) -> dict[str, Any]:
        if value < MIN_VOLUME or value > MAX_VOLUME:
            raise _invalid_argument(
                message=f"value must be between {MIN_VOLUME} and {MAX_VOLUME}",
                hint="Use a normalized volume value in [0.0, 1.0].",
            )
        target = self._track_at(track)
        target.mixer_device.volume.value = float(value)
        return {"track": track, "volume": float(target.mixer_device.volume.value)}

    def track_mute_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        return {"track": track, "mute": bool(target.mute)}

    def track_mute_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._track_at(track)
        target.mute = bool(value)
        return {"track": track, "mute": bool(target.mute)}

    def track_solo_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        return {"track": track, "solo": bool(target.solo)}

    def track_solo_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._track_at(track)
        target.solo = bool(value)
        return {"track": track, "solo": bool(target.solo)}

    def track_arm_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        if not hasattr(target, "arm"):
            raise _invalid_argument(
                message="Track does not support arm",
                hint="Use a MIDI or audio track with arm support.",
            )
        return {"track": track, "arm": bool(target.arm)}

    def track_arm_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._track_at(track)
        if not hasattr(target, "arm"):
            raise _invalid_argument(
                message="Track does not support arm",
                hint="Use a MIDI or audio track with arm support.",
            )
        target.arm = bool(value)
        return {"track": track, "arm": bool(target.arm)}

    def track_panning_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        return {"track": track, "panning": float(target.mixer_device.panning.value)}

    def track_panning_set(self, track: int, value: float) -> dict[str, Any]:
        if value < MIN_PANNING or value > MAX_PANNING:
            raise _invalid_argument(
                message=f"value must be between {MIN_PANNING} and {MAX_PANNING}",
                hint="Use a normalized panning value in [-1.0, 1.0].",
            )
        target = self._track_at(track)
        target.mixer_device.panning.value = float(value)
        return {"track": track, "panning": float(target.mixer_device.panning.value)}
