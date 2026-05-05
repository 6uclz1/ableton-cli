from __future__ import annotations

import math
from typing import Any

from ..command_backend import NOTE_PITCH_MAX, CommandError
from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendTracksCutToDrumRackMixin:
    _SUPPORTED_AUDIO_EXTENSIONS = (".wav", ".aif", ".aiff")
    _DEFAULT_DRUM_RACK_URI = "rack:drums"
    _SLICE_RANGE_END_TOLERANCE_BEATS = 1e-6
    _TRIGGER_PITCH_BASE = 36

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
            "source_file": None,
            "source_file_duration_beats": None,
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
            "source_file": None,
            "source_file_duration_beats": None,
        }

    def _resolve_file_audio_source(
        self,
        *,
        source_file: str,
        source_file_duration_beats: float,
    ) -> dict[str, Any]:
        if not source_file.strip():
            raise _invalid_argument(
                message="source_file must not be empty",
                hint="Use a non-empty source file path.",
            )
        if source_file_duration_beats <= 0:
            raise _invalid_argument(
                message="source_file_duration_beats must be > 0",
                hint="Pass a positive source file duration in beats.",
            )
        self._require_supported_audio_source(
            source_ref=source_file,
            source_label="source_file",
        )
        return {
            "source_mode": "file",
            "source_ref": source_file,
            "range_start": 0.0,
            "range_end": float(source_file_duration_beats),
            "source_track": None,
            "source_clip": None,
            "source_uri": None,
            "source_path": None,
            "source_file": source_file,
            "source_file_duration_beats": float(source_file_duration_beats),
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
        slice_ranges: list[dict[str, float]] | None,
    ) -> list[tuple[float, float]]:
        selector_count = (
            int(grid is not None) + int(slice_count is not None) + int(slice_ranges is not None)
        )
        if selector_count == 0:
            raise _invalid_argument(
                message="Either grid, slice_count, or slice_ranges must be provided",
                hint="Choose one slicing mode.",
            )
        if selector_count > 1:
            raise _invalid_argument(
                message="grid, slice_count, and slice_ranges are mutually exclusive",
                hint="Use exactly one slicing mode.",
            )
        if slice_ranges is not None:
            return self._normalize_explicit_slice_ranges(
                slice_ranges=slice_ranges,
                source_duration_beats=range_end,
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

    def _normalize_explicit_slice_ranges(
        self,
        *,
        slice_ranges: list[dict[str, float]],
        source_duration_beats: float,
    ) -> list[tuple[float, float]]:
        if not isinstance(slice_ranges, list):
            raise _invalid_argument(
                message="slice_ranges must be a list",
                hint="Pass a non-empty list of {slice_start, slice_end} objects.",
            )
        if not slice_ranges:
            raise _invalid_argument(
                message="slice_ranges must not be empty",
                hint="Pass at least one slice range.",
            )
        parsed: list[tuple[float, float]] = []
        previous_end: float | None = None
        for index, item in enumerate(slice_ranges):
            if not isinstance(item, dict):
                raise _invalid_argument(
                    message=f"slice_ranges[{index}] must be an object",
                    hint="Use objects with numeric slice_start and slice_end fields.",
                )
            start_raw = item.get("slice_start")
            end_raw = item.get("slice_end")
            if (
                isinstance(start_raw, bool)
                or isinstance(end_raw, bool)
                or not isinstance(start_raw, (int, float))
                or not isinstance(end_raw, (int, float))
            ):
                raise _invalid_argument(
                    message=f"slice_ranges[{index}].slice_start/slice_end must be numbers",
                    hint="Use numeric beat positions for slice ranges.",
                )
            start = float(start_raw)
            end = float(end_raw)
            if start < 0 or end <= start:
                raise _invalid_argument(
                    message=f"slice_ranges[{index}] must satisfy 0 <= start < end",
                    hint="Use positive, non-empty slice ranges.",
                )
            if previous_end is not None and start < previous_end:
                raise _invalid_argument(
                    message=f"slice_ranges[{index}] overlaps or is out of order",
                    hint="Sort slice_ranges by start and avoid overlaps.",
                )
            if end > source_duration_beats + self._SLICE_RANGE_END_TOLERANCE_BEATS:
                raise _invalid_argument(
                    message=(
                        f"slice_ranges[{index}].end exceeds source_file_duration_beats "
                        f"({end} > {source_duration_beats})"
                    ),
                    hint="Keep slice ranges inside the source file duration.",
                )
            parsed.append((start, end))
            previous_end = end
        return parsed

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
        range_start: float,
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

        notes: list[tuple[int, float, float, int, bool]] = []
        for assignment in assignments:
            pitch = self._TRIGGER_PITCH_BASE + int(assignment["pad"])
            if pitch > NOTE_PITCH_MAX:
                raise _invalid_argument(
                    message=f"Trigger note pitch out of MIDI range: {pitch}",
                    hint="Use a lower start_pad for trigger clip creation.",
                )
            slice_start = float(assignment["slice_start"])
            slice_end = float(assignment["slice_end"])
            notes.append(
                (
                    pitch,
                    round(slice_start - range_start, 6),
                    round(slice_end - slice_start, 6),
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
        source_file: str | None,
        source_file_duration_beats: float | None,
        target_track: int | None,
        grid: float | None,
        slice_count: int | None,
        slice_ranges: list[dict[str, float]] | None,
        start_pad: int,
        create_trigger_clip: bool,
        trigger_clip_slot: int | None,
    ) -> dict[str, Any]:
        has_session_source = source_track is not None or source_clip is not None
        has_browser_source = source_uri is not None or source_path is not None
        has_file_source = source_file is not None
        source_selector_count = (
            int(has_session_source) + int(has_browser_source) + int(has_file_source)
        )
        if source_selector_count > 1:
            raise _invalid_argument(
                message="session, browser, and file sources are mutually exclusive",
                hint="Use exactly one source selector.",
            )
        if source_selector_count == 0:
            raise _invalid_argument(
                message="Either session, browser, or file source must be provided",
                hint="Use source_track/source_clip, source_uri/source_path, or source_file.",
            )
        if source_file_duration_beats is not None and not has_file_source:
            raise _invalid_argument(
                message="source_file_duration_beats requires source_file",
                hint="Use source_file when passing source_file_duration_beats.",
            )

        if has_session_source:
            if source_track is None or source_clip is None:
                raise _invalid_argument(
                    message="source_track and source_clip must be provided together",
                    hint="Provide both source_track and source_clip.",
                )
            source_info = self._resolve_session_audio_source(
                source_track=source_track,
                source_clip=source_clip,
            )
        elif has_browser_source:
            source_info = self._resolve_browser_audio_source(
                source_uri=source_uri,
                source_path=source_path,
            )
        else:
            if source_file_duration_beats is None:
                raise _invalid_argument(
                    message="source_file_duration_beats is required with source_file",
                    hint="Pass the source file duration in beats.",
                )
            assert source_file is not None
            source_info = self._resolve_file_audio_source(
                source_file=source_file,
                source_file_duration_beats=source_file_duration_beats,
            )

        range_start = float(source_info["range_start"])
        range_end = float(source_info["range_end"])
        resolved_slice_ranges = self._resolve_cut_slice_ranges(
            range_start=range_start,
            range_end=range_end,
            grid=grid,
            slice_count=slice_count,
            slice_ranges=slice_ranges,
        )
        if slice_ranges is not None:
            range_start = resolved_slice_ranges[0][0]
            range_end = resolved_slice_ranges[-1][1]
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
            slice_ranges=resolved_slice_ranges,
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
                range_start=range_start,
                source_length=max(range_end - range_start, 0.000001),
            )

        return {
            "source_mode": source_info["source_mode"],
            "source_track": source_info["source_track"],
            "source_clip": source_info["source_clip"],
            "source_uri": source_info["source_uri"],
            "source_path": source_info["source_path"],
            "source_file": source_info["source_file"],
            "source_file_duration_beats": source_info["source_file_duration_beats"],
            "source_ref": source_info["source_ref"],
            "range_start": range_start,
            "range_end": range_end,
            "target_track": resolved_target_track,
            "created_target_track": created_target_track,
            "drum_rack_device": drum_rack_index,
            "created_drum_rack": created_drum_rack,
            "grid": grid,
            "slice_count": len(resolved_slice_ranges),
            "start_pad": start_pad,
            "assigned_count": len(assignments),
            "assignments": assignments,
            "create_trigger_clip": create_trigger_clip,
            **trigger_payload,
        }
