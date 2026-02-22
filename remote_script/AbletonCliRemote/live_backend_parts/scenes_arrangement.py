from __future__ import annotations

from typing import Any

from ..command_backend_validators import _is_absolute_filesystem_path
from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendScenesArrangementMixin:
    def _focus_arranger_view(self) -> None:
        app = self._application()
        view = getattr(app, "view", None)
        if view is None:
            raise _not_supported_by_live_api(
                message="Application view API is not available in Live API",
                hint="Use a Live version exposing application.view.",
            )
        focus_view = getattr(view, "focus_view", None)
        if not callable(focus_view):
            raise _not_supported_by_live_api(
                message="Application focus_view API is not available in Live API",
                hint="Use a Live version exposing application.view.focus_view.",
            )
        focus_view("Arranger")

    def scenes_list(self) -> dict[str, Any]:
        scenes = []
        for index, scene in enumerate(list(getattr(self._song(), "scenes", []))):
            scenes.append({"index": index, "name": str(getattr(scene, "name", ""))})
        return {"scenes": scenes}

    def create_scene(self, index: int) -> dict[str, Any]:
        song = self._song()
        scenes = list(getattr(song, "scenes", []))
        if index != -1 and index > len(scenes):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint="Use -1 for append or a valid insertion index.",
            )

        target_index = len(scenes) if index == -1 else index
        song.create_scene(target_index)
        created = self._scene_at(target_index)
        return {"index": target_index, "name": str(getattr(created, "name", ""))}

    def set_scene_name(self, scene: int, name: str) -> dict[str, Any]:
        target = self._scene_at(scene)
        target.name = name
        return {"scene": scene, "name": str(target.name)}

    def fire_scene(self, scene: int) -> dict[str, Any]:
        target = self._scene_at(scene)
        target.fire()
        return {"scene": scene, "fired": True}

    def scenes_move(self, from_index: int, to_index: int) -> dict[str, Any]:
        self._scene_at(from_index)
        self._scene_at(to_index)
        move_scene = getattr(self._song(), "move_scene", None)
        if not callable(move_scene):
            raise _not_supported_by_live_api(
                message="Scene move API is not available in Live API",
                hint="Move scenes manually in Ableton Live.",
            )
        move_scene(from_index, to_index)
        return {"from": from_index, "to": to_index, "moved": True}

    def stop_all_clips(self) -> dict[str, Any]:
        song = self._song()
        if not hasattr(song, "stop_all_clips"):
            raise _invalid_argument(
                message="Song does not support stop_all_clips",
                hint="Use a compatible Ableton Live version.",
            )
        song.stop_all_clips()
        return {"stopped": True}

    def arrangement_record_start(self) -> dict[str, Any]:
        song = self._song()
        if hasattr(song, "record_mode"):
            song.record_mode = True
            return {"recording": bool(song.record_mode)}
        start_recording = getattr(song, "start_arrangement_recording", None)
        if callable(start_recording):
            start_recording()
            return {"recording": True}
        raise _not_supported_by_live_api(
            message="Arrangement record start API is not available in Live API",
            hint="Start arrangement recording manually in Ableton Live.",
        )

    def arrangement_record_stop(self) -> dict[str, Any]:
        song = self._song()
        if hasattr(song, "record_mode"):
            song.record_mode = False
            return {"recording": bool(song.record_mode)}
        stop_recording = getattr(song, "stop_arrangement_recording", None)
        if callable(stop_recording):
            stop_recording()
            return {"recording": False}
        raise _not_supported_by_live_api(
            message="Arrangement record stop API is not available in Live API",
            hint="Stop arrangement recording manually in Ableton Live.",
        )

    def arrangement_clip_create(
        self,
        track: int,
        start_time: float,
        length: float,
        audio_path: str | None,
    ) -> dict[str, Any]:
        self._focus_arranger_view()
        target_track = self._track_at(track)
        is_midi_track = bool(getattr(target_track, "has_midi_input", False))
        is_audio_track = bool(getattr(target_track, "has_audio_input", False))
        normalized_start_time = float(start_time)
        normalized_length = float(length)

        if is_midi_track and not is_audio_track:
            if audio_path is not None:
                raise _invalid_argument(
                    message="audio_path must not be provided for MIDI tracks",
                    hint="Remove --audio-path for MIDI arrangement clip creation.",
                )
            create_midi_clip = getattr(target_track, "create_midi_clip", None)
            if not callable(create_midi_clip):
                raise _not_supported_by_live_api(
                    message="Arrangement MIDI clip creation API is not available in Live API",
                    hint="Use a Live version exposing track.create_midi_clip.",
                )
            create_midi_clip(normalized_start_time, normalized_length)
            return {
                "track": track,
                "start_time": normalized_start_time,
                "length": normalized_length,
                "kind": "midi",
                "arrangement_view_focused": True,
                "created": True,
            }

        if is_audio_track and not is_midi_track:
            if audio_path is None:
                raise _invalid_argument(
                    message="audio_path is required for audio tracks",
                    hint="Pass --audio-path with an absolute audio file path.",
                )
            normalized_audio_path = str(audio_path).strip()
            if not _is_absolute_filesystem_path(normalized_audio_path):
                raise _invalid_argument(
                    message=f"audio_path must be an absolute path, got {normalized_audio_path!r}",
                    hint="Pass an absolute filesystem path for --audio-path.",
                )
            create_audio_clip = getattr(target_track, "create_audio_clip", None)
            if not callable(create_audio_clip):
                raise _not_supported_by_live_api(
                    message="Arrangement audio clip creation API is not available in Live API",
                    hint="Use a Live version exposing track.create_audio_clip.",
                )
            create_audio_clip(normalized_audio_path, normalized_start_time)
            return {
                "track": track,
                "start_time": normalized_start_time,
                "length": normalized_length,
                "kind": "audio",
                "audio_path": normalized_audio_path,
                "arrangement_view_focused": True,
                "created": True,
            }

        raise _invalid_argument(
            message=(
                f"track {track} must be exclusively MIDI or audio "
                f"(has_midi_input={is_midi_track}, has_audio_input={is_audio_track})"
            ),
            hint="Use a standard MIDI or audio track for arrangement clip creation.",
        )

    def arrangement_clip_list(self, track: int | None) -> dict[str, Any]:
        if track is None:
            target_tracks = [
                (index, target_track)
                for index, target_track in enumerate(list(self._song().tracks))
            ]
        else:
            target_tracks = [(track, self._track_at(track))]

        clips: list[dict[str, Any]] = []
        for track_index, target_track in target_tracks:
            arrangement_clips = getattr(target_track, "arrangement_clips", None)
            if arrangement_clips is None:
                raise _not_supported_by_live_api(
                    message="Arrangement clip list API is not available in Live API",
                    hint="Use a Live version exposing track.arrangement_clips.",
                )
            for clip_index, clip in enumerate(list(arrangement_clips)):
                clips.append(
                    {
                        "track": track_index,
                        "index": clip_index,
                        "name": str(getattr(clip, "name", "")),
                        "start_time": self._safe_float(getattr(clip, "start_time", None)),
                        "length": self._safe_float(getattr(clip, "length", None)),
                        "is_audio_clip": bool(getattr(clip, "is_audio_clip", False)),
                        "is_midi_clip": bool(getattr(clip, "is_midi_clip", False)),
                    }
                )

        return {
            "track": track,
            "clip_count": len(clips),
            "clips": clips,
        }

    def tracks_delete(self, track: int) -> dict[str, Any]:
        self._track_at(track)
        delete_track = getattr(self._song(), "delete_track", None)
        if not callable(delete_track):
            raise _not_supported_by_live_api(
                message="Track delete API is not available in Live API",
                hint="Delete tracks manually in Ableton Live.",
            )
        delete_track(track)
        return {"track": track, "deleted": True, "track_count": len(list(self._song().tracks))}
