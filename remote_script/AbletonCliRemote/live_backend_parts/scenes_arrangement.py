from __future__ import annotations

from typing import Any

from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendScenesArrangementMixin:
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
