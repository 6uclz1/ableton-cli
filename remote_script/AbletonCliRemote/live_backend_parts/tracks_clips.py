from __future__ import annotations

import math
from typing import Any

from ..command_backend import CommandError
from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendTracksClipsMixin:
    _WARP_MODE_VALUES = {
        "beats": 0,
        "tones": 1,
        "texture": 2,
        "re-pitch": 3,
        "repitch": 3,
        "complex": 4,
        "rex": 5,
        "complex-pro": 6,
        "complex_pro": 6,
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
        # Firing an empty slot is valid Live API usage: on an armed,
        # record-enabled track this is how session recording starts, so no
        # has_clip guard here (unlike the other clip-slot commands below,
        # which operate on an existing clip's contents).
        slot = self._clip_slot_at(track, clip)
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

    def _require_session_clip(self, track: int, clip: int, *, action: str) -> Any:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint=f"Create a clip in the target slot before {action}.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        return clip_obj

    def _require_session_audio_clip(self, track: int, clip: int, *, action: str) -> Any:
        clip_obj = self._require_session_clip(track, clip, action=action)
        if not bool(getattr(clip_obj, "is_audio_clip", False)):
            raise _invalid_argument(
                message="clip must be an audio clip",
                hint=f"Use an audio clip before {action}.",
            )
        return clip_obj

    def _clip_props_payload(
        self,
        *,
        clip_obj: Any,
        track: int,
        clip: int | None,
        index: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "track": track,
            "name": str(self._safe_clip_attr(clip_obj, "name", "")),
            "length": self._safe_float(self._safe_clip_attr(clip_obj, "length")),
            "is_audio_clip": bool(self._safe_clip_attr(clip_obj, "is_audio_clip", False)),
            "is_midi_clip": bool(self._safe_clip_attr(clip_obj, "is_midi_clip", False)),
            "loop_start": self._safe_float(self._safe_clip_attr(clip_obj, "loop_start")),
            "loop_end": self._safe_float(self._safe_clip_attr(clip_obj, "loop_end")),
            "looping": bool(self._safe_clip_attr(clip_obj, "looping", False)),
            "start_marker": self._safe_float(self._safe_clip_attr(clip_obj, "start_marker")),
            "end_marker": self._safe_float(self._safe_clip_attr(clip_obj, "end_marker")),
            "warping": bool(self._safe_clip_attr(clip_obj, "warping", False)),
            "warp_mode": self._safe_clip_attr(clip_obj, "warp_mode"),
            "gain_db": self._safe_clip_attr(clip_obj, "_ableton_cli_gain_db"),
            "pitch_coarse": self._safe_clip_attr(clip_obj, "pitch_coarse"),
        }
        if clip is not None:
            payload["clip"] = clip
        if index is not None:
            payload["index"] = index
            payload["start_time"] = self._safe_float(self._safe_clip_attr(clip_obj, "start_time"))
        return payload

    @staticmethod
    def _set_required_clip_attr(clip_obj: Any, attr: str, value: Any, *, api_name: str) -> None:
        if not hasattr(clip_obj, attr):
            raise _not_supported_by_live_api(
                message=f"Clip {api_name} API is not available in Live API",
                hint=f"Use a Live version exposing clip.{attr}.",
            )
        setattr(clip_obj, attr, value)

    @staticmethod
    def _safe_clip_attr(clip_obj: Any, attr: str, default: Any = None) -> Any:
        try:
            return getattr(clip_obj, attr)
        except Exception:  # noqa: BLE001
            return default

    @classmethod
    def _warp_mode_value(cls, mode: str | int) -> int:
        if isinstance(mode, int):
            return mode
        normalized = str(mode).strip().lower()
        if normalized.isdecimal():
            return int(normalized)
        value = cls._WARP_MODE_VALUES.get(normalized)
        if value is None:
            raise _invalid_argument(
                message=f"unsupported warp mode: {mode}",
                hint="Use beats, tones, texture, re-pitch, complex, rex, or complex-pro.",
            )
        return value

    def clip_props_get(self, track: int, clip: int) -> dict[str, Any]:
        clip_obj = self._require_session_clip(track, clip, action="reading clip properties")
        return self._clip_props_payload(clip_obj=clip_obj, track=track, clip=clip, index=None)

    def clip_file_path_get(self, track: int, clip: int) -> dict[str, Any]:
        clip_obj = self._require_session_audio_clip(track, clip, action="reading clip file path")
        if not hasattr(clip_obj, "file_path"):
            raise _not_supported_by_live_api(
                message="Clip file_path API is not available in Live API",
                hint="Use a Live version exposing clip.file_path.",
            )
        file_path = self._safe_clip_attr(clip_obj, "file_path")
        if not file_path:
            raise _invalid_argument(
                message="Clip has no recorded/rendered file path",
                hint="Record or render audio into this clip before reading its file path.",
            )
        return {"track": track, "clip": clip, "file_path": str(file_path)}

    def clip_loop_set(
        self,
        track: int,
        clip: int,
        start: float,
        end: float,
        enabled: bool,
    ) -> dict[str, Any]:
        clip_obj = self._require_session_clip(track, clip, action="updating clip loop")
        self._set_required_clip_attr(clip_obj, "loop_start", float(start), api_name="loop start")
        self._set_required_clip_attr(clip_obj, "loop_end", float(end), api_name="loop end")
        self._set_required_clip_attr(clip_obj, "looping", bool(enabled), api_name="loop")
        return self.clip_props_get(track, clip)

    def clip_marker_set(
        self,
        track: int,
        clip: int,
        start_marker: float,
        end_marker: float,
    ) -> dict[str, Any]:
        clip_obj = self._require_session_clip(track, clip, action="updating clip markers")
        self._set_required_clip_attr(
            clip_obj,
            "start_marker",
            float(start_marker),
            api_name="start marker",
        )
        self._set_required_clip_attr(
            clip_obj, "end_marker", float(end_marker), api_name="end marker"
        )
        return self.clip_props_get(track, clip)

    def clip_warp_get(self, track: int, clip: int) -> dict[str, Any]:
        clip_obj = self._require_session_audio_clip(track, clip, action="reading warp state")
        return {
            "track": track,
            "clip": clip,
            "warping": bool(getattr(clip_obj, "warping", False)),
            "warp_mode": getattr(clip_obj, "warp_mode", None),
            "available_warp_modes": list(getattr(clip_obj, "available_warp_modes", [])),
        }

    def clip_warp_set(
        self,
        track: int,
        clip: int,
        enabled: bool,
        mode: str | None,
    ) -> dict[str, Any]:
        clip_obj = self._require_session_audio_clip(track, clip, action="updating warp state")
        self._set_required_clip_attr(clip_obj, "warping", bool(enabled), api_name="warp")
        if mode is not None:
            self._set_required_clip_attr(
                clip_obj,
                "warp_mode",
                self._warp_mode_value(mode),
                api_name="warp mode",
            )
        return self.clip_warp_get(track, clip)

    def clip_warp_marker_list(self, track: int, clip: int) -> dict[str, Any]:
        clip_obj = self._require_session_audio_clip(track, clip, action="reading warp markers")
        markers = getattr(clip_obj, "warp_markers", None)
        if markers is None:
            raise _not_supported_by_live_api(
                message="Clip warp marker list API is not available in Live API",
                hint="Use a Live version exposing clip.warp_markers.",
            )
        return {"track": track, "clip": clip, "warp_markers": list(markers)}

    def clip_warp_marker_add(
        self,
        track: int,
        clip: int,
        beat_time: float,
        sample_time: float | None,
    ) -> dict[str, Any]:
        clip_obj = self._require_session_audio_clip(track, clip, action="adding a warp marker")
        add_warp_marker = getattr(clip_obj, "add_warp_marker", None)
        if not callable(add_warp_marker):
            raise _not_supported_by_live_api(
                message="Clip warp marker write API is not available in Live API",
                hint="Use a Live version exposing clip.add_warp_marker.",
            )
        marker = {"beat_time": float(beat_time)}
        if sample_time is not None:
            marker["sample_time"] = float(sample_time)
        add_warp_marker(marker)
        return {
            "track": track,
            "clip": clip,
            "beat_time": float(beat_time),
            "sample_time": float(sample_time) if sample_time is not None else None,
            "created": True,
        }

    def clip_warp_marker_move(
        self,
        track: int,
        clip: int,
        beat_time: float,
        distance: float,
    ) -> dict[str, Any]:
        clip_obj = self._require_session_audio_clip(track, clip, action="moving a warp marker")
        move_warp_marker = getattr(clip_obj, "move_warp_marker", None)
        if not callable(move_warp_marker):
            raise _not_supported_by_live_api(
                message="Clip warp marker move API is not available in Live API",
                hint="Use a Live version exposing clip.move_warp_marker.",
            )
        move_warp_marker(float(beat_time), float(distance))
        return {
            "track": track,
            "clip": clip,
            "beat_time": float(beat_time),
            "distance": float(distance),
            "moved": True,
        }

    def clip_warp_marker_remove(
        self,
        track: int,
        clip: int,
        beat_time: float,
    ) -> dict[str, Any]:
        clip_obj = self._require_session_audio_clip(track, clip, action="removing a warp marker")
        remove_warp_marker = getattr(clip_obj, "remove_warp_marker", None)
        if not callable(remove_warp_marker):
            raise _not_supported_by_live_api(
                message="Clip warp marker remove API is not available in Live API",
                hint="Use a Live version exposing clip.remove_warp_marker.",
            )
        remove_warp_marker(float(beat_time))
        return {
            "track": track,
            "clip": clip,
            "beat_time": float(beat_time),
            "removed": True,
        }

    def clip_gain_set(self, track: int, clip: int, db: float) -> dict[str, Any]:
        clip_obj = self._require_session_clip(track, clip, action="updating clip gain")
        if not hasattr(clip_obj, "gain"):
            raise _not_supported_by_live_api(
                message="Clip gain API is not available in Live API",
                hint="Use a Live version exposing clip.gain.",
            )
        clip_obj.gain = math.pow(10.0, float(db) / 20.0)
        clip_obj._ableton_cli_gain_db = float(db)  # noqa: SLF001
        return {"track": track, "clip": clip, "gain_db": float(db), "gain": float(clip_obj.gain)}

    def clip_transpose_set(self, track: int, clip: int, semitones: int) -> dict[str, Any]:
        clip_obj = self._require_session_clip(track, clip, action="updating clip transpose")
        self._set_required_clip_attr(clip_obj, "pitch_coarse", int(semitones), api_name="transpose")
        return {"track": track, "clip": clip, "pitch_coarse": int(clip_obj.pitch_coarse)}

    def clip_file_replace(self, track: int, clip: int, audio_path: str) -> dict[str, Any]:
        clip_obj = self._require_session_clip(track, clip, action="replacing clip audio file")
        replace_file = getattr(clip_obj, "replace_file", None)
        if not callable(replace_file):
            raise _not_supported_by_live_api(
                message="Clip file replacement API is not available in Live API",
                hint="Use manual replacement in Ableton Live for this Live version.",
            )
        replace_file(audio_path)
        return {"track": track, "clip": clip, "audio_path": audio_path, "replaced": True}

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
