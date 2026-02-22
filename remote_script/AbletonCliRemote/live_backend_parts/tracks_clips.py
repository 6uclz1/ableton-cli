from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..command_backend import (
    NOTE_PITCH_MAX,
    NOTE_PITCH_MIN,
    NOTE_VELOCITY_MAX,
    NOTE_VELOCITY_MIN,
    CommandError,
)
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
        filtered = self._filtered_clip_notes(clip_obj, start_time, end_time, pitch)
        changed_note_ids: list[int] = []
        replacement_notes: list[tuple[int, float, float, int, bool]] = []

        for index, note in enumerate(filtered):
            transformed = self._normalized_note_payload(transform(dict(note), index))
            if self._clip_note_tuple(note) == self._clip_note_tuple(transformed):
                continue
            changed_note_ids.append(int(note["note_id"]))
            replacement_notes.append(self._clip_note_tuple(transformed))

        if changed_note_ids:
            clip_obj.remove_notes_by_id(changed_note_ids)
            clip_obj.set_notes(tuple(replacement_notes))

        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            **(metadata or {}),
            "changed_count": len(changed_note_ids),
        }

    @staticmethod
    def _clip_groove_attr_name(clip_obj: Any) -> str | None:
        for attribute in ("groove", "groove_assignment"):
            if hasattr(clip_obj, attribute):
                return attribute
        return None

    @staticmethod
    def _clip_groove_amount_attr_name(clip_obj: Any) -> str | None:
        for attribute in ("groove_amount", "groove_amount_value"):
            if hasattr(clip_obj, attribute):
                return attribute
        return None

    def _require_clip_with_groove_support(self, *, track: int, clip: int) -> tuple[Any, str]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before using groove commands.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        groove_attr = self._clip_groove_attr_name(clip_obj)
        if groove_attr is None:
            raise _not_supported_by_live_api(
                message="Clip groove API is not available in Live API",
                hint="Use a Live version exposing clip groove assignment.",
            )
        return clip_obj, groove_attr

    @staticmethod
    def _is_groove_item_name(name: str) -> bool:
        return name.lower().endswith(".agr")

    def _resolve_groove_target(self, target: str) -> dict[str, str | None]:
        parsed_target = str(target).strip()
        if "/" in parsed_target:
            item = self._resolve_browser_path(parsed_target)
            item_path = parsed_target
            uri_raw = getattr(item, "uri", None)
            item_uri = str(uri_raw).strip() if uri_raw is not None else None
        elif ":" in parsed_target:
            item = self._find_browser_item_by_uri(parsed_target)
            if item is None:
                raise _invalid_argument(
                    message=f"Browser item with URI '{parsed_target}' not found",
                    hint="Use browser search/items to choose a valid groove URI.",
                )
            item_path = self._item_path_by_uri(parsed_target)
            uri_raw = getattr(item, "uri", None)
            item_uri = str(uri_raw).strip() if uri_raw is not None else parsed_target
        else:
            raise _invalid_argument(
                message=f"target must include '/' (path) or ':' (uri), got {parsed_target!r}",
                hint="Use a groove path like grooves/Hip Hop Boom Bap 16ths 90 bpm.agr.",
            )

        item_name = str(getattr(item, "name", "")).strip()
        if not self._is_groove_item_name(item_name):
            raise _invalid_argument(
                message=f"Target is not a groove .agr item: {item_name or parsed_target}",
                hint="Select a .agr groove file from browser search/items.",
            )

        return {
            "uri": item_uri,
            "path": item_path,
            "name": item_name,
        }

    def _clip_groove_payload(
        self,
        *,
        track: int,
        clip: int,
        clip_obj: Any,
        groove_attr: str,
    ) -> dict[str, Any]:
        current_groove = getattr(clip_obj, groove_attr, None)
        stored_uri = getattr(clip_obj, "_ableton_cli_groove_uri", None)
        stored_path = getattr(clip_obj, "_ableton_cli_groove_path", None)
        stored_name = getattr(clip_obj, "_ableton_cli_groove_name", None)
        groove_uri = (
            str(stored_uri).strip()
            if isinstance(stored_uri, str) and str(stored_uri).strip()
            else None
        )
        if groove_uri is None and isinstance(current_groove, str):
            normalized_current = current_groove.strip()
            groove_uri = normalized_current or None
        groove_path = (
            str(stored_path).strip()
            if isinstance(stored_path, str) and str(stored_path).strip()
            else None
        )
        groove_name = (
            str(stored_name).strip()
            if isinstance(stored_name, str) and str(stored_name).strip()
            else None
        )

        amount_attr = self._clip_groove_amount_attr_name(clip_obj)
        amount: float | None = None
        if amount_attr is not None:
            raw_amount = getattr(clip_obj, amount_attr, None)
            if isinstance(raw_amount, (int, float)):
                amount = float(raw_amount)

        return {
            "track": track,
            "clip": clip,
            "has_groove": bool(groove_uri or groove_path or current_groove),
            "groove_uri": groove_uri,
            "groove_path": groove_path,
            "groove_name": groove_name,
            "amount": amount,
        }

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

    def clip_groove_get(self, track: int, clip: int) -> dict[str, Any]:
        clip_obj, groove_attr = self._require_clip_with_groove_support(track=track, clip=clip)
        return self._clip_groove_payload(
            track=track,
            clip=clip,
            clip_obj=clip_obj,
            groove_attr=groove_attr,
        )

    def clip_groove_set(self, track: int, clip: int, target: str) -> dict[str, Any]:
        clip_obj, groove_attr = self._require_clip_with_groove_support(track=track, clip=clip)
        target_info = self._resolve_groove_target(target)
        groove_value = target_info["uri"] or target_info["path"]
        setattr(clip_obj, groove_attr, groove_value)
        clip_obj._ableton_cli_groove_uri = target_info["uri"]  # noqa: SLF001
        clip_obj._ableton_cli_groove_path = target_info["path"]  # noqa: SLF001
        clip_obj._ableton_cli_groove_name = target_info["name"]  # noqa: SLF001
        return self._clip_groove_payload(
            track=track,
            clip=clip,
            clip_obj=clip_obj,
            groove_attr=groove_attr,
        )

    def clip_groove_amount_set(self, track: int, clip: int, value: float) -> dict[str, Any]:
        clip_obj, groove_attr = self._require_clip_with_groove_support(track=track, clip=clip)
        current_payload = self._clip_groove_payload(
            track=track,
            clip=clip,
            clip_obj=clip_obj,
            groove_attr=groove_attr,
        )
        if not current_payload["has_groove"]:
            raise _invalid_argument(
                message="No groove is assigned to this clip",
                hint="Set a groove with 'clip groove set' before changing amount.",
            )
        amount_attr = self._clip_groove_amount_attr_name(clip_obj)
        if amount_attr is None:
            raise _not_supported_by_live_api(
                message="Clip groove amount API is not available in Live API",
                hint="Use a Live version exposing clip groove amount.",
            )
        setattr(clip_obj, amount_attr, float(value))
        return self._clip_groove_payload(
            track=track,
            clip=clip,
            clip_obj=clip_obj,
            groove_attr=groove_attr,
        )

    def clip_groove_clear(self, track: int, clip: int) -> dict[str, Any]:
        clip_obj, groove_attr = self._require_clip_with_groove_support(track=track, clip=clip)
        setattr(clip_obj, groove_attr, None)
        clip_obj._ableton_cli_groove_uri = None  # noqa: SLF001
        clip_obj._ableton_cli_groove_path = None  # noqa: SLF001
        clip_obj._ableton_cli_groove_name = None  # noqa: SLF001
        return self._clip_groove_payload(
            track=track,
            clip=clip,
            clip_obj=clip_obj,
            groove_attr=groove_attr,
        )

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
