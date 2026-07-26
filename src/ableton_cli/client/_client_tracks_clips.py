from __future__ import annotations

from typing import Any

from ..refs import RefPayload


class _AbletonClientTracksClipsMixin:
    def _call_clip_note_transform(
        self,
        command_name: str,
        *,
        track: int,
        clip: int,
        extra_args: dict[str, Any],
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
        args.update(extra_args)
        return self._call(command_name, args)

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

    def update_clip_notes(
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
        return self._call("update_clip_notes", args)

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

    def clip_envelope_clear(
        self,
        track: int,
        clip: int,
        device_ref: RefPayload | None = None,
        parameter_ref: RefPayload | None = None,
        clear_all: bool = False,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "clip": clip, "clear_all": clear_all}
        self._add_if_not_none(args, "device_ref", device_ref)
        self._add_if_not_none(args, "parameter_ref", parameter_ref)
        return self._call("clip_envelope_clear", args)

    def clip_notes_quantize(
        self,
        track: int,
        clip: int,
        grid: str,
        strength: float,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        return self._call_clip_note_transform(
            "clip_notes_quantize",
            track=track,
            clip=clip,
            extra_args={"grid": grid, "strength": strength},
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
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
        return self._call_clip_note_transform(
            "clip_notes_humanize",
            track=track,
            clip=clip,
            extra_args={"timing": timing, "velocity": velocity},
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
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
        return self._call_clip_note_transform(
            "clip_notes_velocity_scale",
            track=track,
            clip=clip,
            extra_args={"scale": scale, "offset": offset},
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
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
        return self._call_clip_note_transform(
            "clip_notes_transpose",
            track=track,
            clip=clip,
            extra_args={"semitones": semitones},
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )

    def clip_warp_set(
        self,
        track: int,
        clip: int,
        enabled: bool,
        mode: str | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "clip": clip, "enabled": enabled}
        self._add_if_not_none(args, "mode", mode)
        return self._call("clip_warp_set", args)

    def clip_warp_marker_add(
        self,
        track: int,
        clip: int,
        beat_time: float,
        sample_time: float | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "clip": clip, "beat_time": beat_time}
        self._add_if_not_none(args, "sample_time", sample_time)
        return self._call("clip_warp_marker_add", args)

    def clip_duplicate(
        self,
        track: int,
        src_clip: int,
        dst_clip: int | None = None,
        dst_clips: list[int] | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "src_clip": src_clip}
        self._add_if_not_none(args, "dst_clip", dst_clip)
        self._add_if_not_none(args, "dst_clips", dst_clips)
        return self._call("clip_duplicate", args)

    def clip_cut_to_drum_rack(
        self,
        *,
        source_track: int | None,
        source_clip: int | None,
        source_uri: str | None,
        source_path: str | None,
        target_track: int | None,
        grid: str | None,
        slice_count: int | None,
        start_pad: int,
        create_trigger_clip: bool,
        trigger_clip_slot: int | None,
        source_file: str | None = None,
        source_file_duration_beats: float | None = None,
        slice_ranges: list[dict[str, float]] | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "start_pad": start_pad,
            "create_trigger_clip": create_trigger_clip,
        }
        self._add_if_not_none(args, "source_track", source_track)
        self._add_if_not_none(args, "source_clip", source_clip)
        self._add_if_not_none(args, "source_uri", source_uri)
        self._add_if_not_none(args, "source_path", source_path)
        self._add_if_not_none(args, "source_file", source_file)
        self._add_if_not_none(args, "source_file_duration_beats", source_file_duration_beats)
        self._add_if_not_none(args, "target_track", target_track)
        self._add_if_not_none(args, "grid", grid)
        self._add_if_not_none(args, "slice_count", slice_count)
        self._add_if_not_none(args, "slice_ranges", slice_ranges)
        self._add_if_not_none(args, "trigger_clip_slot", trigger_clip_slot)
        return self._call("clip_cut_to_drum_rack", args)
