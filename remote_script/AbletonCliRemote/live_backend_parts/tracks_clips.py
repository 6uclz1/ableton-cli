from __future__ import annotations

import math
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
    _SUPPORTED_AUDIO_EXTENSIONS = (".wav", ".aif", ".aiff")
    _DEFAULT_DRUM_RACK_URI = "rack:drums"

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

    def _require_supported_audio_source(self, *, source_ref: str, source_label: str) -> None:
        normalized = source_ref.strip().lower()
        if any(normalized.endswith(ext) for ext in self._SUPPORTED_AUDIO_EXTENSIONS):
            return
        raise _invalid_argument(
            message=f"{source_label} must be a WAV/AIFF source, got {source_ref!r}",
            hint="Use a .wav or .aif/.aiff source.",
        )

    def _resolve_session_audio_source(
        self,
        *,
        source_track: int,
        source_clip: int,
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(source_track, source_clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in source slot",
                hint="Use a source slot containing an audio clip.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        if not bool(getattr(clip_obj, "is_audio_clip", False)):
            raise _invalid_argument(
                message="source clip must be an audio clip",
                hint="Use an audio clip source.",
            )
        file_path_raw = getattr(clip_obj, "file_path", None)
        if not isinstance(file_path_raw, str) or not file_path_raw.strip():
            raise _not_supported_by_live_api(
                message="Audio clip file_path API is not available in Live API",
                hint="Use a Live version exposing audio clip file_path.",
            )
        source_ref = file_path_raw.strip()
        self._require_supported_audio_source(source_ref=source_ref, source_label="source clip")

        start_raw = getattr(clip_obj, "start_marker", None)
        end_raw = getattr(clip_obj, "end_marker", None)
        if not isinstance(start_raw, (int, float)) or not isinstance(end_raw, (int, float)):
            raise _not_supported_by_live_api(
                message="Audio clip marker API is not available in Live API",
                hint="Use a Live version exposing clip start_marker/end_marker.",
            )
        range_start = float(start_raw)
        range_end = float(end_raw)
        if range_end <= range_start:
            raise _invalid_argument(
                message=(
                    f"source clip audible range must be positive "
                    f"(start={range_start}, end={range_end})"
                ),
                hint="Use an audio clip with a positive audible range.",
            )
        return {
            "source_mode": "session",
            "source_ref": source_ref,
            "range_start": range_start,
            "range_end": range_end,
            "source_track": source_track,
            "source_clip": source_clip,
            "source_uri": None,
            "source_path": None,
        }

    def _resolve_browser_audio_source(
        self,
        *,
        source_uri: str | None,
        source_path: str | None,
    ) -> dict[str, Any]:
        if source_uri is None and source_path is None:
            raise _invalid_argument(
                message="Either source_uri or source_path must be provided",
                hint="Use a browser URI or path source.",
            )
        if source_uri is not None and source_path is not None:
            raise _invalid_argument(
                message="source_uri and source_path are mutually exclusive",
                hint="Provide only one browser source selector.",
            )

        if source_uri is not None:
            item = self._find_browser_item_by_uri(source_uri)
            if item is None:
                raise _invalid_argument(
                    message=f"Browser item with URI '{source_uri}' not found",
                    hint="Choose a valid browser URI from browser items/search.",
                )
            resolved_path = self._item_path_by_uri(source_uri)
            serialized = self._serialize_browser_item(item, path=resolved_path)
        else:
            assert source_path is not None
            item = self._resolve_browser_path(source_path)
            serialized = self._serialize_browser_item(item, path=source_path)

        if not bool(serialized["is_loadable"]):
            raise _invalid_argument(
                message="Browser source item must be loadable",
                hint="Choose a loadable browser item.",
            )
        resolved_source_path = serialized["path"]
        if not isinstance(resolved_source_path, str) or not resolved_source_path.strip():
            raise _not_supported_by_live_api(
                message="Browser source path metadata is not available in Live API",
                hint="Use a Live version exposing browser item path metadata.",
            )
        self._require_supported_audio_source(
            source_ref=resolved_source_path,
            source_label="browser source",
        )

        length_raw = getattr(item, "length_beats", None)
        if not isinstance(length_raw, (int, float)) or float(length_raw) <= 0:
            raise _not_supported_by_live_api(
                message="Browser source length metadata is not available in Live API",
                hint="Use a source with deterministic length metadata.",
            )
        range_end = float(length_raw)
        return {
            "source_mode": "browser",
            "source_ref": resolved_source_path,
            "range_start": 0.0,
            "range_end": range_end,
            "source_track": None,
            "source_clip": None,
            "source_uri": source_uri,
            "source_path": resolved_source_path,
        }

    @staticmethod
    def _slice_ranges_by_count(
        *,
        range_start: float,
        range_end: float,
        slice_count: int,
    ) -> list[tuple[float, float]]:
        if slice_count <= 0:
            raise _invalid_argument(
                message=f"slice_count must be > 0, got {slice_count}",
                hint="Use a positive slice_count.",
            )
        span = range_end - range_start
        if span <= 0:
            raise _invalid_argument(
                message=f"source range must be positive (start={range_start}, end={range_end})",
                hint="Use a source with a positive range.",
            )
        step = span / float(slice_count)
        return [
            (
                round(range_start + (step * float(index)), 6),
                round(range_start + (step * float(index + 1)), 6),
            )
            for index in range(slice_count)
        ]

    @staticmethod
    def _slice_ranges_by_grid(
        *,
        range_start: float,
        range_end: float,
        grid: float,
    ) -> list[tuple[float, float]]:
        if grid <= 0:
            raise _invalid_argument(
                message=f"grid must be > 0, got {grid}",
                hint="Use a positive slicing grid.",
            )
        span = range_end - range_start
        if span <= 0:
            raise _invalid_argument(
                message=f"source range must be positive (start={range_start}, end={range_end})",
                hint="Use a source with a positive range.",
            )
        slice_count = int(math.ceil(span / grid))
        ranges: list[tuple[float, float]] = []
        for index in range(slice_count):
            current_start = range_start + (grid * float(index))
            current_end = min(range_end, current_start + grid)
            ranges.append((round(current_start, 6), round(current_end, 6)))
        return ranges

    def _resolve_cut_slice_ranges(
        self,
        *,
        range_start: float,
        range_end: float,
        grid: float | None,
        slice_count: int | None,
    ) -> list[tuple[float, float]]:
        if grid is None and slice_count is None:
            raise _invalid_argument(
                message="Either grid or slice_count must be provided",
                hint="Choose one slicing mode.",
            )
        if grid is not None and slice_count is not None:
            raise _invalid_argument(
                message="grid and slice_count are mutually exclusive",
                hint="Use either grid or slice_count.",
            )
        if slice_count is not None:
            return self._slice_ranges_by_count(
                range_start=range_start,
                range_end=range_end,
                slice_count=slice_count,
            )
        assert grid is not None
        return self._slice_ranges_by_grid(
            range_start=range_start,
            range_end=range_end,
            grid=grid,
        )

    def _resolve_target_track_for_cut(
        self,
        *,
        target_track: int | None,
    ) -> tuple[int, Any, bool]:
        if target_track is not None:
            return target_track, self._track_at(target_track), False
        song = self._song()
        create_midi_track = getattr(song, "create_midi_track", None)
        if not callable(create_midi_track):
            raise _not_supported_by_live_api(
                message="Track creation API is not available in Live API",
                hint="Use a Live version exposing song.create_midi_track.",
            )
        create_midi_track(-1)
        resolved_target_track = len(list(getattr(song, "tracks", []))) - 1
        return resolved_target_track, self._track_at(resolved_target_track), True

    @staticmethod
    def _find_drum_rack_device_on_track(track_obj: Any) -> tuple[int, Any] | None:
        for index, device in enumerate(list(getattr(track_obj, "devices", []))):
            if bool(getattr(device, "can_have_drum_pads", False)):
                return index, device
        return None

    def _ensure_drum_rack_for_cut(
        self,
        *,
        target_track: int,
        track_obj: Any,
    ) -> tuple[int, Any, bool]:
        existing = self._find_drum_rack_device_on_track(track_obj)
        if existing is not None:
            return existing[0], existing[1], False

        self.load_instrument_or_effect(
            target_track,
            uri=self._DEFAULT_DRUM_RACK_URI,
            path=None,
            target_track_mode="existing",
            clip_slot=None,
            preserve_track_name=False,
            notes_mode=None,
            import_length=False,
            import_groove=False,
        )
        refreshed_track = self._track_at(target_track)
        created = self._find_drum_rack_device_on_track(refreshed_track)
        if created is None:
            raise _not_supported_by_live_api(
                message="Drum Rack auto-load did not expose drum pad API",
                hint="Use a Live version exposing drum rack drum_pads.",
            )
        return created[0], created[1], True

    def _assign_cut_slices_to_drum_rack(
        self,
        *,
        drum_rack: Any,
        source_ref: str,
        slice_ranges: list[tuple[float, float]],
        start_pad: int,
    ) -> list[dict[str, Any]]:
        drum_pads = list(getattr(drum_rack, "drum_pads", []))
        if not drum_pads:
            raise _not_supported_by_live_api(
                message="Drum pad API is not available in Live API",
                hint="Use a Live version exposing drum_rack.drum_pads.",
            )
        if start_pad < 0:
            raise _invalid_argument(
                message=f"start_pad must be >= 0, got {start_pad}",
                hint="Use a non-negative start_pad.",
            )
        if start_pad >= len(drum_pads):
            raise _invalid_argument(
                message=f"start_pad out of range: {start_pad}",
                hint="Use a start_pad inside the available drum pad range.",
            )
        if start_pad + len(slice_ranges) > len(drum_pads):
            raise _invalid_argument(
                message=(
                    "slice count exceeds available drum pads "
                    f"(start_pad={start_pad}, "
                    f"slice_count={len(slice_ranges)}, pads={len(drum_pads)})"
                ),
                hint="Reduce slice_count/grid or choose a lower start_pad.",
            )

        assigned: list[dict[str, Any]] = []
        for offset, (slice_start, slice_end) in enumerate(slice_ranges):
            pad_index = start_pad + offset
            pad = drum_pads[pad_index]
            load_audio_slice = getattr(pad, "load_audio_slice", None)
            if not callable(load_audio_slice):
                raise _not_supported_by_live_api(
                    message="Drum pad audio slice load API is not available in Live API",
                    hint="Use a Live version exposing pad slice load API.",
                )
            load_audio_slice(source_ref, slice_start, slice_end)
            assigned.append(
                {
                    "pad": pad_index,
                    "slice_start": slice_start,
                    "slice_end": slice_end,
                }
            )
        return assigned

    def _create_trigger_clip_for_cut(
        self,
        *,
        target_track: int,
        trigger_clip_slot: int,
        assignments: list[dict[str, Any]],
        source_length: float,
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(target_track, trigger_clip_slot)
        if slot.has_clip:
            raise _invalid_argument(
                message=f"Trigger clip slot already has a clip: {trigger_clip_slot}",
                hint="Use an empty trigger clip slot.",
            )
        if not assignments:
            raise _invalid_argument(
                message="No assignments available to create trigger clip",
                hint="Ensure at least one slice is assigned before creating trigger clip.",
            )

        slot.create_clip(max(source_length, 0.000001))
        if not slot.has_clip:
            raise CommandError(
                code="INTERNAL_ERROR",
                message="Trigger clip creation did not produce a clip",
                hint="Retry and check Ableton logs.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        set_notes = getattr(clip_obj, "set_notes", None)
        if not callable(set_notes):
            raise _not_supported_by_live_api(
                message="Clip note write API is not available in Live API",
                hint="Use a Live version exposing clip.set_notes.",
            )

        step = max(source_length / float(len(assignments)), 0.000001)
        notes: list[tuple[int, float, float, int, bool]] = []
        for index, assignment in enumerate(assignments):
            pitch = 36 + int(assignment["pad"])
            if pitch > NOTE_PITCH_MAX:
                raise _invalid_argument(
                    message=f"Trigger note pitch out of MIDI range: {pitch}",
                    hint="Use a lower start_pad for trigger clip creation.",
                )
            notes.append(
                (
                    pitch,
                    round(step * float(index), 6),
                    round(step, 6),
                    100,
                    False,
                )
            )
        set_notes(tuple(notes))
        return {
            "trigger_clip_created": True,
            "trigger_clip_slot": trigger_clip_slot,
            "trigger_note_count": len(notes),
        }

    def clip_cut_to_drum_rack(
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
    ) -> dict[str, Any]:
        if source_track is not None or source_clip is not None:
            if source_track is None or source_clip is None:
                raise _invalid_argument(
                    message="source_track and source_clip must be provided together",
                    hint="Provide both source_track and source_clip.",
                )
            source_info = self._resolve_session_audio_source(
                source_track=source_track,
                source_clip=source_clip,
            )
        else:
            source_info = self._resolve_browser_audio_source(
                source_uri=source_uri,
                source_path=source_path,
            )

        range_start = float(source_info["range_start"])
        range_end = float(source_info["range_end"])
        slice_ranges = self._resolve_cut_slice_ranges(
            range_start=range_start,
            range_end=range_end,
            grid=grid,
            slice_count=slice_count,
        )
        resolved_target_track, track_obj, created_target_track = self._resolve_target_track_for_cut(
            target_track=target_track,
        )
        drum_rack_index, drum_rack, created_drum_rack = self._ensure_drum_rack_for_cut(
            target_track=resolved_target_track,
            track_obj=track_obj,
        )
        assignments = self._assign_cut_slices_to_drum_rack(
            drum_rack=drum_rack,
            source_ref=str(source_info["source_ref"]),
            slice_ranges=slice_ranges,
            start_pad=start_pad,
        )

        trigger_payload = {
            "trigger_clip_created": False,
            "trigger_clip_slot": None,
            "trigger_note_count": 0,
        }
        if create_trigger_clip:
            if trigger_clip_slot is None:
                raise _invalid_argument(
                    message="trigger_clip_slot is required when create_trigger_clip is true",
                    hint="Provide trigger_clip_slot for trigger clip creation.",
                )
            trigger_payload = self._create_trigger_clip_for_cut(
                target_track=resolved_target_track,
                trigger_clip_slot=trigger_clip_slot,
                assignments=assignments,
                source_length=max(range_end - range_start, 0.000001),
            )

        return {
            "source_mode": source_info["source_mode"],
            "source_track": source_info["source_track"],
            "source_clip": source_info["source_clip"],
            "source_uri": source_info["source_uri"],
            "source_path": source_info["source_path"],
            "source_ref": source_info["source_ref"],
            "range_start": range_start,
            "range_end": range_end,
            "target_track": resolved_target_track,
            "created_target_track": created_target_track,
            "drum_rack_device": drum_rack_index,
            "created_drum_rack": created_drum_rack,
            "grid": grid,
            "slice_count": len(slice_ranges),
            "start_pad": start_pad,
            "assigned_count": len(assignments),
            "assignments": assignments,
            "create_trigger_clip": create_trigger_clip,
            **trigger_payload,
        }

    def _duplicate_clip_to_destination(
        self,
        *,
        track: int,
        destination_clip: int,
        source_clip: Any,
        source_length: float,
        live_notes: list[tuple[int, float, float, int, bool]],
    ) -> None:
        destination_slot = self._clip_slot_at(track, destination_clip)
        if destination_slot.has_clip:
            raise _invalid_argument(
                message=f"Destination clip slot already has a clip: {destination_clip}",
                hint="Use empty destination clip slots.",
            )

        destination_slot.create_clip(source_length)
        if not destination_slot.has_clip:
            raise CommandError(
                code="INTERNAL_ERROR",
                message="Clip duplication did not create destination clip",
                hint="Retry and check Ableton logs.",
            )
        destination_clip_obj = destination_slot.clip
        assert destination_clip_obj is not None
        if live_notes:
            destination_clip_obj.set_notes(tuple(live_notes))
        destination_clip_obj.name = str(getattr(source_clip, "name", ""))

    def clip_duplicate(
        self,
        track: int,
        src_clip: int,
        dst_clip: int | None = None,
        dst_clips: list[int] | None = None,
    ) -> dict[str, Any]:
        if dst_clip is None and dst_clips is None:
            raise _invalid_argument(
                message="Either dst_clip or dst_clips must be provided",
                hint="Provide one destination clip slot or multiple destination clip slots.",
            )
        if dst_clip is not None and dst_clips is not None:
            raise _invalid_argument(
                message="dst_clip and dst_clips are mutually exclusive",
                hint="Provide either dst_clip or dst_clips.",
            )

        source_slot = self._clip_slot_at(track, src_clip)
        if not source_slot.has_clip:
            raise _invalid_argument(
                message="Source clip does not exist",
                hint="Create a clip in the source slot before duplicating.",
            )

        source_clip = source_slot.clip
        assert source_clip is not None
        source_length = float(getattr(source_clip, "length", 0.0))
        if source_length <= 0:
            raise _invalid_argument(
                message="Source clip length must be > 0",
                hint="Duplicate only clips with positive length.",
            )

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
        destination_clips = [dst_clip] if dst_clip is not None else list(dst_clips or [])
        if not destination_clips:
            raise _invalid_argument(
                message="dst_clips must not be empty",
                hint="Pass at least one destination clip index.",
            )
        seen: set[int] = set()
        for destination in destination_clips:
            if destination == src_clip:
                raise _invalid_argument(
                    message=f"Destination clip index must differ from src_clip ({src_clip})",
                    hint="Use destination clip slots that are not the source clip.",
                )
            if destination in seen:
                raise _invalid_argument(
                    message=f"Duplicate destination clip index: {destination}",
                    hint="Remove duplicate destination clip indexes.",
                )
            seen.add(destination)
            self._duplicate_clip_to_destination(
                track=track,
                destination_clip=destination,
                source_clip=source_clip,
                source_length=source_length,
                live_notes=live_notes,
            )

        if len(destination_clips) == 1:
            return {
                "track": track,
                "src_clip": src_clip,
                "dst_clip": destination_clips[0],
                "duplicated": True,
                "note_count": len(live_notes),
            }
        return {
            "track": track,
            "src_clip": src_clip,
            "dst_clips": destination_clips,
            "duplicated": True,
            "duplicated_count": len(destination_clips),
            "note_count": len(live_notes),
        }
