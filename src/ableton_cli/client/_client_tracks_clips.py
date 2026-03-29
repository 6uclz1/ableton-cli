from __future__ import annotations

from typing import Any


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

    def track_send_get(self, track: int, send: int) -> dict[str, Any]:
        return self._call("track_send_get", {"track": track, "send": send})

    def track_send_set(self, track: int, send: int, value: float) -> dict[str, Any]:
        return self._call("track_send_set", {"track": track, "send": send, "value": value})

    def return_tracks_list(self) -> dict[str, Any]:
        return self._call("return_tracks_list")

    def return_track_volume_get(self, return_track: int) -> dict[str, Any]:
        return self._call("return_track_volume_get", {"return_track": return_track})

    def return_track_volume_set(self, return_track: int, value: float) -> dict[str, Any]:
        return self._call("return_track_volume_set", {"return_track": return_track, "value": value})

    def return_track_mute_get(self, return_track: int) -> dict[str, Any]:
        return self._call("return_track_mute_get", {"return_track": return_track})

    def return_track_mute_set(self, return_track: int, value: bool) -> dict[str, Any]:
        return self._call("return_track_mute_set", {"return_track": return_track, "value": value})

    def return_track_solo_get(self, return_track: int) -> dict[str, Any]:
        return self._call("return_track_solo_get", {"return_track": return_track})

    def return_track_solo_set(self, return_track: int, value: bool) -> dict[str, Any]:
        return self._call("return_track_solo_set", {"return_track": return_track, "value": value})

    def master_info(self) -> dict[str, Any]:
        return self._call("master_info")

    def master_volume_get(self) -> dict[str, Any]:
        return self._call("master_volume_get")

    def master_panning_get(self) -> dict[str, Any]:
        return self._call("master_panning_get")

    def master_devices_list(self) -> dict[str, Any]:
        return self._call("master_devices_list")

    def mixer_crossfader_get(self) -> dict[str, Any]:
        return self._call("mixer_crossfader_get")

    def mixer_crossfader_set(self, value: float) -> dict[str, Any]:
        return self._call("mixer_crossfader_set", {"value": value})

    def mixer_cue_volume_get(self) -> dict[str, Any]:
        return self._call("mixer_cue_volume_get")

    def mixer_cue_volume_set(self, value: float) -> dict[str, Any]:
        return self._call("mixer_cue_volume_set", {"value": value})

    def mixer_cue_routing_get(self) -> dict[str, Any]:
        return self._call("mixer_cue_routing_get")

    def mixer_cue_routing_set(self, routing: str) -> dict[str, Any]:
        return self._call("mixer_cue_routing_set", {"routing": routing})

    def track_routing_input_get(self, track: int) -> dict[str, Any]:
        return self._call("track_routing_input_get", {"track": track})

    def track_routing_input_set(
        self,
        track: int,
        routing_type: str,
        routing_channel: str,
    ) -> dict[str, Any]:
        return self._call(
            "track_routing_input_set",
            {
                "track": track,
                "routing_type": routing_type,
                "routing_channel": routing_channel,
            },
        )

    def track_routing_output_get(self, track: int) -> dict[str, Any]:
        return self._call("track_routing_output_get", {"track": track})

    def track_routing_output_set(
        self,
        track: int,
        routing_type: str,
        routing_channel: str,
    ) -> dict[str, Any]:
        return self._call(
            "track_routing_output_set",
            {
                "track": track,
                "routing_type": routing_type,
                "routing_channel": routing_channel,
            },
        )

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

    def clip_groove_get(self, track: int, clip: int) -> dict[str, Any]:
        return self._call("clip_groove_get", {"track": track, "clip": clip})

    def clip_groove_set(self, track: int, clip: int, target: str) -> dict[str, Any]:
        return self._call("clip_groove_set", {"track": track, "clip": clip, "target": target})

    def clip_groove_amount_set(self, track: int, clip: int, value: float) -> dict[str, Any]:
        return self._call(
            "clip_groove_amount_set",
            {"track": track, "clip": clip, "value": value},
        )

    def clip_groove_clear(self, track: int, clip: int) -> dict[str, Any]:
        return self._call("clip_groove_clear", {"track": track, "clip": clip})

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
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "start_pad": start_pad,
            "create_trigger_clip": create_trigger_clip,
        }
        self._add_if_not_none(args, "source_track", source_track)
        self._add_if_not_none(args, "source_clip", source_clip)
        self._add_if_not_none(args, "source_uri", source_uri)
        self._add_if_not_none(args, "source_path", source_path)
        self._add_if_not_none(args, "target_track", target_track)
        self._add_if_not_none(args, "grid", grid)
        self._add_if_not_none(args, "slice_count", slice_count)
        self._add_if_not_none(args, "trigger_clip_slot", trigger_clip_slot)
        return self._call("clip_cut_to_drum_rack", args)

    def execute_batch(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        return self._call("execute_batch", {"steps": steps})
