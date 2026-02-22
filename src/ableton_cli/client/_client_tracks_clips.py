from __future__ import annotations

from typing import Any


class _AbletonClientTracksClipsMixin:
    def get_track_info(self, track: int) -> dict[str, Any]:
        return self._call("get_track_info", {"track": track})

    def tracks_list(self) -> dict[str, Any]:
        return self._call("tracks_list")

    def create_midi_track(self, index: int = -1) -> dict[str, Any]:
        return self._call("create_midi_track", {"index": index})

    def create_audio_track(self, index: int = -1) -> dict[str, Any]:
        return self._call("create_audio_track", {"index": index})

    def set_track_name(self, track: int, name: str) -> dict[str, Any]:
        return self._call("set_track_name", {"track": track, "name": name})

    def track_volume_get(self, track: int) -> dict[str, Any]:
        return self._call("track_volume_get", {"track": track})

    def track_volume_set(self, track: int, value: float) -> dict[str, Any]:
        return self._call("track_volume_set", {"track": track, "value": value})

    def track_mute_get(self, track: int) -> dict[str, Any]:
        return self._call("track_mute_get", {"track": track})

    def track_mute_set(self, track: int, value: bool) -> dict[str, Any]:
        return self._call("track_mute_set", {"track": track, "value": value})

    def track_solo_get(self, track: int) -> dict[str, Any]:
        return self._call("track_solo_get", {"track": track})

    def track_solo_set(self, track: int, value: bool) -> dict[str, Any]:
        return self._call("track_solo_set", {"track": track, "value": value})

    def track_arm_get(self, track: int) -> dict[str, Any]:
        return self._call("track_arm_get", {"track": track})

    def track_arm_set(self, track: int, value: bool) -> dict[str, Any]:
        return self._call("track_arm_set", {"track": track, "value": value})

    def track_panning_get(self, track: int) -> dict[str, Any]:
        return self._call("track_panning_get", {"track": track})

    def track_panning_set(self, track: int, value: float) -> dict[str, Any]:
        return self._call("track_panning_set", {"track": track, "value": value})

    def create_clip(self, track: int, clip: int, length: float) -> dict[str, Any]:
        return self._call("create_clip", {"track": track, "clip": clip, "length": length})

    def add_notes_to_clip(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        args = self._build_clip_note_args(
            track=track,
            clip=clip,
            notes=notes,
            start_time=None,
            end_time=None,
            pitch=None,
        )
        return self._call("add_notes_to_clip", args)

    def get_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args = self._build_clip_note_args(
            track=track,
            clip=clip,
            notes=None,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return self._call("get_clip_notes", args)

    def clear_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args = self._build_clip_note_args(
            track=track,
            clip=clip,
            notes=None,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return self._call("clear_clip_notes", args)

    def replace_clip_notes(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args = self._build_clip_note_args(
            track=track,
            clip=clip,
            notes=notes,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return self._call("replace_clip_notes", args)

    def set_clip_name(self, track: int, clip: int, name: str) -> dict[str, Any]:
        return self._call("set_clip_name", {"track": track, "clip": clip, "name": name})

    def fire_clip(self, track: int, clip: int) -> dict[str, Any]:
        return self._call("fire_clip", {"track": track, "clip": clip})

    def stop_clip(self, track: int, clip: int) -> dict[str, Any]:
        return self._call("stop_clip", {"track": track, "clip": clip})

    def clip_active_get(self, track: int, clip: int) -> dict[str, Any]:
        return self._call("clip_active_get", {"track": track, "clip": clip})

    def clip_active_set(self, track: int, clip: int, value: bool) -> dict[str, Any]:
        return self._call(
            "clip_active_set",
            {"track": track, "clip": clip, "value": value},
        )

    def clip_duplicate(self, track: int, src_clip: int, dst_clip: int) -> dict[str, Any]:
        return self._call(
            "clip_duplicate",
            {"track": track, "src_clip": src_clip, "dst_clip": dst_clip},
        )

    def execute_batch(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        return self._call("execute_batch", {"steps": steps})
