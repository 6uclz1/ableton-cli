from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..command_backend import (
    NOTE_PITCH_MAX,
    NOTE_PITCH_MIN,
    NOTE_VELOCITY_MAX,
    NOTE_VELOCITY_MIN,
)
from ..live_api import midi_note_specification_class
from .base import _invalid_argument, _not_supported_by_live_api

_NOTE_EXTENDED_FIELD_NAMES = ("probability", "velocity_deviation", "release_velocity")
_NOTE_UPDATABLE_FIELD_NAMES = (
    "pitch",
    "start_time",
    "duration",
    "velocity",
    "mute",
    *_NOTE_EXTENDED_FIELD_NAMES,
)


class LiveBackendClipNotesMixin:
    """Session clip note read/write/transform commands.

    Split out of ``LiveBackendTracksClipsMixin`` to keep both classes well
    under the quality harness god-class-risk threshold (see
    ``docs/quality-harness-phase2.md``). Note-related helpers used by
    arrangement clips (``scenes_arrangement.py``) and by drum-rack cutting
    (``tracks_clips_cut_to_drum_rack.py``) also live here and are shared via
    the ``LiveBackend`` mixin composition.
    """

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
            "probability": float(note.probability),
            "velocity_deviation": float(note.velocity_deviation),
            "release_velocity": int(note.release_velocity),
        }

    def _note_specification(self, note: dict[str, Any]) -> Any:
        factory = getattr(self, "_note_spec_factory", None) or midi_note_specification_class()
        kwargs: dict[str, Any] = {
            "pitch": int(note["pitch"]),
            "start_time": float(note["start_time"]),
            "duration": float(note["duration"]),
            "velocity": int(note["velocity"]),
            "mute": bool(note.get("mute", False)),
        }
        for optional in _NOTE_EXTENDED_FIELD_NAMES:
            if optional in note:
                kwargs[optional] = note[optional]
        return factory(**kwargs)

    def _clip_note_objects(self, clip_obj: Any) -> list[Any]:
        time_span = max(float(getattr(clip_obj, "length", 0.0)), 0.0) + 1.0
        return list(
            clip_obj.get_notes_extended(
                from_pitch=0,
                pitch_span=128,
                from_time=0.0,
                time_span=time_span,
            )
        )

    def _clip_notes_extended(self, clip_obj: Any) -> list[dict[str, Any]]:
        return [self._normalize_clip_note(note) for note in self._clip_note_objects(clip_obj)]

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

    def _filtered_clip_note_objects(
        self,
        clip_obj: Any,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> list[Any]:
        return [
            note_obj
            for note_obj in self._clip_note_objects(clip_obj)
            if self._clip_note_matches_filter(
                self._normalize_clip_note(note_obj), start_time, end_time, pitch
            )
        ]

    @staticmethod
    def _clamp_int(value: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(maximum, value))

    def _clip_note_tuple(self, note: dict[str, Any]) -> tuple[int, float, float, int, bool]:
        return (
            int(note["pitch"]),
            float(note["start_time"]),
            float(note["duration"]),
            int(note["velocity"]),
            bool(note["mute"]),
        )

    def _normalized_note_payload(self, note: dict[str, Any]) -> dict[str, Any]:
        return {
            "pitch": self._clamp_int(int(note["pitch"]), NOTE_PITCH_MIN, NOTE_PITCH_MAX),
            "start_time": max(0.0, float(note["start_time"])),
            "duration": max(float(note["duration"]), 0.000001),
            "velocity": self._clamp_int(
                int(note["velocity"]),
                NOTE_VELOCITY_MIN,
                NOTE_VELOCITY_MAX,
            ),
            "mute": bool(note["mute"]),
        }

    def _transform_filtered_clip_notes(
        self,
        *,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
        transform: Callable[[dict[str, Any], int], dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before transforming notes.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        apply_note_modifications = getattr(clip_obj, "apply_note_modifications", None)
        if not callable(apply_note_modifications):
            raise _not_supported_by_live_api(
                message="Clip extended note modification API is not available in Live API",
                hint="Use a Live version exposing clip.apply_note_modifications (Live 12+).",
            )
        filtered_objects = self._filtered_clip_note_objects(clip_obj, start_time, end_time, pitch)
        modified: list[Any] = []

        for index, note_obj in enumerate(filtered_objects):
            before = self._normalize_clip_note(note_obj)
            transformed = self._normalized_note_payload(transform(dict(before), index))
            if self._clip_note_tuple(before) == self._clip_note_tuple(transformed):
                continue
            note_obj.pitch = transformed["pitch"]
            note_obj.start_time = transformed["start_time"]
            note_obj.duration = transformed["duration"]
            note_obj.velocity = transformed["velocity"]
            note_obj.mute = transformed["mute"]
            modified.append(note_obj)

        if modified:
            apply_note_modifications(tuple(modified))

        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            **(metadata or {}),
            "changed_count": len(modified),
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
        add_new_notes = getattr(clip_obj, "add_new_notes", None)
        if not callable(add_new_notes):
            raise _not_supported_by_live_api(
                message="Clip extended note write API is not available in Live API",
                hint="Use a Live version exposing clip.add_new_notes (Live 12+).",
            )
        specs = tuple(self._note_specification(note) for note in notes)
        add_new_notes(specs)
        return {"track": track, "clip": clip, "note_count": len(specs)}

    def update_clip_notes(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before updating notes.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        apply_note_modifications = getattr(clip_obj, "apply_note_modifications", None)
        if not callable(apply_note_modifications):
            raise _not_supported_by_live_api(
                message="Clip extended note modification API is not available in Live API",
                hint="Use a Live version exposing clip.apply_note_modifications (Live 12+).",
            )
        by_id = {int(note_obj.note_id): note_obj for note_obj in self._clip_note_objects(clip_obj)}
        missing_note_ids: list[int] = []
        modified: list[Any] = []
        for update in notes:
            note_id = int(update["note_id"])
            target = by_id.get(note_id)
            if target is None:
                missing_note_ids.append(note_id)
                continue
            for field_name in _NOTE_UPDATABLE_FIELD_NAMES:
                if field_name in update:
                    setattr(target, field_name, update[field_name])
            modified.append(target)
        if missing_note_ids:
            raise _invalid_argument(
                message=f"Unknown note_id(s): {sorted(missing_note_ids)}",
                hint="Use note_id values from 'clip notes get'.",
                details={"missing_note_ids": sorted(missing_note_ids)},
            )
        if modified:
            apply_note_modifications(tuple(modified))
        return {"track": track, "clip": clip, "updated_count": len(modified)}

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
                "note_id": int(note["note_id"]),
                "pitch": int(note["pitch"]),
                "start_time": float(note["start_time"]),
                "duration": float(note["duration"]),
                "velocity": int(note["velocity"]),
                "mute": bool(note["mute"]),
                "probability": float(note["probability"]),
                "velocity_deviation": float(note["velocity_deviation"]),
                "release_velocity": int(note["release_velocity"]),
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

    def clip_notes_quantize(
        self,
        track: int,
        clip: int,
        grid: float,
        strength: float,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        def _quantize(note: dict[str, Any], _index: int) -> dict[str, Any]:
            original_start = float(note["start_time"])
            snapped_start = round(round(original_start / grid) * grid, 6)
            note["start_time"] = round(
                original_start + ((snapped_start - original_start) * strength),
                6,
            )
            return note

        return self._transform_filtered_clip_notes(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
            transform=_quantize,
            metadata={"grid": grid, "strength": strength},
        )

    def clip_notes_humanize(
        self,
        track: int,
        clip: int,
        timing: float,
        velocity: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        def _humanize(note: dict[str, Any], index: int) -> dict[str, Any]:
            direction = 1 if index % 2 == 0 else -1
            note["start_time"] = round(float(note["start_time"]) + (timing * direction), 6)
            note["velocity"] = int(note["velocity"]) + (velocity * direction)
            return note

        return self._transform_filtered_clip_notes(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
            transform=_humanize,
            metadata={"timing": timing, "velocity": velocity},
        )

    def clip_notes_velocity_scale(
        self,
        track: int,
        clip: int,
        scale: float,
        offset: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        def _velocity_scale(note: dict[str, Any], _index: int) -> dict[str, Any]:
            note["velocity"] = int(round(float(note["velocity"]) * scale + offset))
            return note

        return self._transform_filtered_clip_notes(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
            transform=_velocity_scale,
            metadata={"scale": scale, "offset": offset},
        )

    def clip_notes_transpose(
        self,
        track: int,
        clip: int,
        semitones: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        def _transpose(note: dict[str, Any], _index: int) -> dict[str, Any]:
            note["pitch"] = int(note["pitch"]) + semitones
            return note

        return self._transform_filtered_clip_notes(
            track=track,
            clip=clip,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
            transform=_transpose,
            metadata={"semitones": semitones},
        )
