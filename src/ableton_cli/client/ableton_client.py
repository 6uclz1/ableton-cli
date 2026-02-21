from __future__ import annotations

from typing import Any

from ..capabilities import parse_supported_commands
from ..config import Settings
from ..errors import AppError, ExitCode, remote_error_to_app_error
from .protocol import make_request, parse_response
from .transport import TcpJsonlTransport


class AbletonClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.transport = TcpJsonlTransport(
            host=settings.host,
            port=settings.port,
            timeout_ms=settings.timeout_ms,
        )
        self._supported_commands: set[str] | None = None

    def _ensure_remote_supports(self, command_name: str) -> None:
        if command_name == "ping":
            return

        if self._supported_commands is None:
            ping_result = self.ping()
            self._supported_commands = parse_supported_commands(ping_result)

        if command_name not in self._supported_commands:
            raise AppError(
                error_code="REMOTE_SCRIPT_INCOMPATIBLE",
                message=f"Remote Script does not support command: {command_name}",
                hint="Run 'ableton-cli install-remote-script --yes' and restart Ableton Live.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        request = make_request(
            name=name,
            args=args,
            protocol_version=self.settings.protocol_version,
            meta={"request_timeout_ms": self.settings.timeout_ms},
        )
        raw_response = self.transport.send(request.to_dict())
        response = parse_response(
            payload=raw_response,
            expected_request_id=request.request_id,
            expected_protocol=self.settings.protocol_version,
        )

        if response.ok:
            if response.result is None:
                return {}
            return response.result

        if response.error is None:
            raise AppError(
                error_code="INTERNAL_ERROR",
                message="Remote command failed without structured error payload",
                hint="Update Remote Script error handling.",
                exit_code=ExitCode.EXECUTION_FAILED,
            )

        raise remote_error_to_app_error(response.error)

    def _call(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        args = args or {}
        self._ensure_remote_supports(name)
        return self._dispatch(name, args)

    def ping(self) -> dict[str, Any]:
        return self._call("ping")

    def song_info(self) -> dict[str, Any]:
        return self._call("song_info")

    def song_new(self) -> dict[str, Any]:
        return self._call("song_new")

    def song_save(self, path: str) -> dict[str, Any]:
        return self._call("song_save", {"path": path})

    def song_export_audio(self, path: str) -> dict[str, Any]:
        return self._call("song_export_audio", {"path": path})

    def get_session_info(self) -> dict[str, Any]:
        return self._call("get_session_info")

    def session_snapshot(self) -> dict[str, Any]:
        return self._call("session_snapshot")

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

    def transport_play(self) -> dict[str, Any]:
        return self._call("transport_play")

    def transport_stop(self) -> dict[str, Any]:
        return self._call("transport_stop")

    def transport_toggle(self) -> dict[str, Any]:
        return self._call("transport_toggle")

    def transport_tempo_get(self) -> dict[str, Any]:
        return self._call("transport_tempo_get")

    def transport_tempo_set(self, bpm: float) -> dict[str, Any]:
        return self._call("transport_tempo_set", {"bpm": bpm})

    def start_playback(self) -> dict[str, Any]:
        return self._call("start_playback")

    def stop_playback(self) -> dict[str, Any]:
        return self._call("stop_playback")

    def set_tempo(self, tempo: float) -> dict[str, Any]:
        return self._call("set_tempo", {"tempo": tempo})

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
        self, track: int, clip: int, notes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._call("add_notes_to_clip", {"track": track, "clip": clip, "notes": notes})

    def get_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "clip": clip}
        if start_time is not None:
            args["start_time"] = start_time
        if end_time is not None:
            args["end_time"] = end_time
        if pitch is not None:
            args["pitch"] = pitch
        return self._call("get_clip_notes", args)

    def clear_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "clip": clip}
        if start_time is not None:
            args["start_time"] = start_time
        if end_time is not None:
            args["end_time"] = end_time
        if pitch is not None:
            args["pitch"] = pitch
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
        args: dict[str, Any] = {"track": track, "clip": clip, "notes": notes}
        if start_time is not None:
            args["start_time"] = start_time
        if end_time is not None:
            args["end_time"] = end_time
        if pitch is not None:
            args["pitch"] = pitch
        return self._call("replace_clip_notes", args)

    def set_clip_name(self, track: int, clip: int, name: str) -> dict[str, Any]:
        return self._call("set_clip_name", {"track": track, "clip": clip, "name": name})

    def fire_clip(self, track: int, clip: int) -> dict[str, Any]:
        return self._call("fire_clip", {"track": track, "clip": clip})

    def stop_clip(self, track: int, clip: int) -> dict[str, Any]:
        return self._call("stop_clip", {"track": track, "clip": clip})

    def clip_duplicate(self, track: int, src_clip: int, dst_clip: int) -> dict[str, Any]:
        return self._call(
            "clip_duplicate",
            {"track": track, "src_clip": src_clip, "dst_clip": dst_clip},
        )

    def load_instrument_or_effect(
        self, track: int, uri: str | None = None, path: str | None = None
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track}
        if uri is not None:
            args["uri"] = uri
        if path is not None:
            args["path"] = path
        return self._call("load_instrument_or_effect", args)

    def get_browser_tree(self, category_type: str = "all") -> dict[str, Any]:
        return self._call("get_browser_tree", {"category_type": category_type})

    def get_browser_items_at_path(self, path: str) -> dict[str, Any]:
        return self._call("get_browser_items_at_path", {"path": path})

    def get_browser_item(self, uri: str | None, path: str | None) -> dict[str, Any]:
        args: dict[str, Any] = {}
        if uri is not None:
            args["uri"] = uri
        if path is not None:
            args["path"] = path
        return self._call("get_browser_item", args)

    def get_browser_categories(self, category_type: str = "all") -> dict[str, Any]:
        return self._call("get_browser_categories", {"category_type": category_type})

    def get_browser_items(
        self,
        path: str,
        item_type: str = "all",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self._call(
            "get_browser_items",
            {"path": path, "item_type": item_type, "limit": limit, "offset": offset},
        )

    def search_browser_items(
        self,
        query: str,
        path: str | None = None,
        item_type: str = "loadable",
        limit: int = 50,
        offset: int = 0,
        exact: bool = False,
        case_sensitive: bool = False,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "query": query,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "exact": exact,
            "case_sensitive": case_sensitive,
        }
        if path is not None:
            args["path"] = path
        return self._call("search_browser_items", args)

    def load_drum_kit(
        self,
        track: int,
        rack_uri: str,
        kit_uri: str | None,
        kit_path: str | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "rack_uri": rack_uri}
        if kit_uri is not None:
            args["kit_uri"] = kit_uri
        if kit_path is not None:
            args["kit_path"] = kit_path
        return self._call("load_drum_kit", args)

    def scenes_list(self) -> dict[str, Any]:
        return self._call("scenes_list")

    def create_scene(self, index: int) -> dict[str, Any]:
        return self._call("create_scene", {"index": index})

    def set_scene_name(self, scene: int, name: str) -> dict[str, Any]:
        return self._call("set_scene_name", {"scene": scene, "name": name})

    def fire_scene(self, scene: int) -> dict[str, Any]:
        return self._call("fire_scene", {"scene": scene})

    def scenes_move(self, from_index: int, to_index: int) -> dict[str, Any]:
        return self._call("scenes_move", {"from": from_index, "to": to_index})

    def stop_all_clips(self) -> dict[str, Any]:
        return self._call("stop_all_clips")

    def arrangement_record_start(self) -> dict[str, Any]:
        return self._call("arrangement_record_start")

    def arrangement_record_stop(self) -> dict[str, Any]:
        return self._call("arrangement_record_stop")

    def tracks_delete(self, track: int) -> dict[str, Any]:
        return self._call("tracks_delete", {"track": track})

    def execute_batch(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        return self._call("execute_batch", {"steps": steps})

    def set_device_parameter(
        self, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]:
        return self._call(
            "set_device_parameter",
            {"track": track, "device": device, "parameter": parameter, "value": value},
        )

    def find_synth_devices(
        self,
        track: int | None = None,
        synth_type: str | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {}
        if track is not None:
            args["track"] = track
        if synth_type is not None:
            args["synth_type"] = synth_type
        return self._call("find_synth_devices", args)

    def list_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._call(
            "list_synth_parameters",
            {"track": track, "device": device},
        )

    def set_synth_parameter_safe(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        return self._call(
            "set_synth_parameter_safe",
            {"track": track, "device": device, "parameter": parameter, "value": value},
        )

    def observe_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._call(
            "observe_synth_parameters",
            {"track": track, "device": device},
        )

    def list_standard_synth_keys(self, synth_type: str) -> dict[str, Any]:
        return self._call(
            "list_standard_synth_keys",
            {"synth_type": synth_type},
        )

    def set_standard_synth_parameter_safe(
        self,
        synth_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]:
        return self._call(
            "set_standard_synth_parameter_safe",
            {
                "synth_type": synth_type,
                "track": track,
                "device": device,
                "key": key,
                "value": value,
            },
        )

    def observe_standard_synth_state(
        self,
        synth_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]:
        return self._call(
            "observe_standard_synth_state",
            {"synth_type": synth_type, "track": track, "device": device},
        )

    def find_effect_devices(
        self,
        track: int | None = None,
        effect_type: str | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {}
        if track is not None:
            args["track"] = track
        if effect_type is not None:
            args["effect_type"] = effect_type
        return self._call("find_effect_devices", args)

    def list_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._call(
            "list_effect_parameters",
            {"track": track, "device": device},
        )

    def set_effect_parameter_safe(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        return self._call(
            "set_effect_parameter_safe",
            {"track": track, "device": device, "parameter": parameter, "value": value},
        )

    def observe_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._call(
            "observe_effect_parameters",
            {"track": track, "device": device},
        )

    def list_standard_effect_keys(self, effect_type: str) -> dict[str, Any]:
        return self._call(
            "list_standard_effect_keys",
            {"effect_type": effect_type},
        )

    def set_standard_effect_parameter_safe(
        self,
        effect_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]:
        return self._call(
            "set_standard_effect_parameter_safe",
            {
                "effect_type": effect_type,
                "track": track,
                "device": device,
                "key": key,
                "value": value,
            },
        )

    def observe_standard_effect_state(
        self,
        effect_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]:
        return self._call(
            "observe_standard_effect_state",
            {"effect_type": effect_type, "track": track, "device": device},
        )
