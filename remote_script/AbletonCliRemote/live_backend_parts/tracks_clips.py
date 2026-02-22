from __future__ import annotations

from typing import Any

from ..command_backend import CommandError
from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendTracksClipsMixin:
    def _clip_note_matches_filter(
        self,
        note: dict[str, Any],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> bool:
        note_start = float(note["start_time"])
        note_pitch = int(note["pitch"])
        if start_time is not None and note_start < start_time:
            return False
        if end_time is not None and note_start >= end_time:
            return False
        if pitch is not None and note_pitch != pitch:
            return False
        return True

    def _normalize_clip_note(self, note: Any) -> dict[str, Any]:
        return {
            "note_id": int(note.note_id),
            "pitch": int(note.pitch),
            "start_time": float(note.start_time),
            "duration": float(note.duration),
            "velocity": int(note.velocity),
            "mute": bool(note.mute),
        }

    def _clip_notes_extended(self, clip_obj: Any) -> list[dict[str, Any]]:
        time_span = max(float(getattr(clip_obj, "length", 0.0)), 0.0) + 1.0
        notes_raw = tuple(
            clip_obj.get_notes_extended(
                from_pitch=0,
                pitch_span=128,
                from_time=0.0,
                time_span=time_span,
            )
        )
        return [self._normalize_clip_note(note) for note in notes_raw]

    def _filtered_clip_notes(
        self,
        clip_obj: Any,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> list[dict[str, Any]]:
        return [
            note
            for note in self._clip_notes_extended(clip_obj)
            if self._clip_note_matches_filter(note, start_time, end_time, pitch)
        ]

    def create_clip(self, track: int, clip: int, length: float) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if slot.has_clip:
            raise _invalid_argument(
                message="Clip slot already has a clip",
                hint="Use an empty clip slot.",
            )
        slot.create_clip(float(length))
        if not slot.has_clip:
            raise CommandError(
                code="INTERNAL_ERROR",
                message="Clip creation did not produce a clip",
                hint="Retry and check Ableton logs.",
            )
        clip_obj = slot.clip
        return {
            "track": track,
            "clip": clip,
            "name": str(getattr(clip_obj, "name", "")),
            "length": float(getattr(clip_obj, "length", length)),
        }

    def add_notes_to_clip(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before adding notes.",
            )
        clip_obj = slot.clip
        live_notes = [
            (
                int(note["pitch"]),
                float(note["start_time"]),
                float(note["duration"]),
                int(note["velocity"]),
                bool(note["mute"]),
            )
            for note in notes
        ]
        clip_obj.set_notes(tuple(live_notes))
        return {"track": track, "clip": clip, "note_count": len(live_notes)}

    def get_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before reading notes.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        filtered = self._filtered_clip_notes(clip_obj, start_time, end_time, pitch)
        payload_notes = [
            {
                "pitch": int(note["pitch"]),
                "start_time": float(note["start_time"]),
                "duration": float(note["duration"]),
                "velocity": int(note["velocity"]),
                "mute": bool(note["mute"]),
            }
            for note in filtered
        ]
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "notes": payload_notes,
            "note_count": len(payload_notes),
        }

    def clear_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before clearing notes.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        filtered = self._filtered_clip_notes(clip_obj, start_time, end_time, pitch)
        to_remove = [int(note["note_id"]) for note in filtered]
        if to_remove:
            clip_obj.remove_notes_by_id(to_remove)
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": len(to_remove),
        }

    def replace_clip_notes(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        cleared = self.clear_clip_notes(track, clip, start_time, end_time, pitch)
        added = self.add_notes_to_clip(track, clip, notes)
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": int(cleared["cleared_count"]),
            "added_count": int(added["note_count"]),
        }

    def set_clip_name(self, track: int, clip: int, name: str) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before renaming.",
            )
        clip_obj = slot.clip
        clip_obj.name = name
        return {"track": track, "clip": clip, "name": str(clip_obj.name)}

    def fire_clip(self, track: int, clip: int) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before firing.",
            )
        slot.fire()
        return {"track": track, "clip": clip, "fired": True}

    def stop_clip(self, track: int, clip: int) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before stopping.",
            )
        slot.stop()
        return {"track": track, "clip": clip, "stopped": True}

    def clip_active_get(self, track: int, clip: int) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before reading active state.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        if not hasattr(clip_obj, "muted"):
            raise _not_supported_by_live_api(
                message="Clip active API is not available in Live API",
                hint="Use Ableton Live version exposing clip muted state.",
            )
        return {
            "track": track,
            "clip": clip,
            "active": not bool(clip_obj.muted),
        }

    def clip_active_set(self, track: int, clip: int, value: bool) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before updating active state.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        if not hasattr(clip_obj, "muted"):
            raise _not_supported_by_live_api(
                message="Clip active API is not available in Live API",
                hint="Use Ableton Live version exposing clip muted state.",
            )
        clip_obj.muted = not bool(value)
        return {
            "track": track,
            "clip": clip,
            "active": not bool(clip_obj.muted),
        }

    def clip_duplicate(self, track: int, src_clip: int, dst_clip: int) -> dict[str, Any]:
        source_slot = self._clip_slot_at(track, src_clip)
        if not source_slot.has_clip:
            raise _invalid_argument(
                message="Source clip does not exist",
                hint="Create a clip in the source slot before duplicating.",
            )

        destination_slot = self._clip_slot_at(track, dst_clip)
        if destination_slot.has_clip:
            raise _invalid_argument(
                message="Destination clip slot already has a clip",
                hint="Use an empty destination clip slot.",
            )

        source_clip = source_slot.clip
        assert source_clip is not None
        source_length = float(getattr(source_clip, "length", 0.0))
        if source_length <= 0:
            raise _invalid_argument(
                message="Source clip length must be > 0",
                hint="Duplicate only clips with positive length.",
            )

        destination_slot.create_clip(source_length)
        if not destination_slot.has_clip:
            raise CommandError(
                code="INTERNAL_ERROR",
                message="Clip duplication did not create destination clip",
                hint="Retry and check Ableton logs.",
            )
        destination_clip = destination_slot.clip
        assert destination_clip is not None

        source_notes = self._clip_notes_extended(source_clip)
        live_notes = [
            (
                int(note["pitch"]),
                float(note["start_time"]),
                float(note["duration"]),
                int(note["velocity"]),
                bool(note["mute"]),
            )
            for note in source_notes
        ]
        if live_notes:
            destination_clip.set_notes(tuple(live_notes))
        destination_clip.name = str(getattr(source_clip, "name", ""))

        return {
            "track": track,
            "src_clip": src_clip,
            "dst_clip": dst_clip,
            "duplicated": True,
            "note_count": len(live_notes),
        }
