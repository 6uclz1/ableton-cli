from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..command_backend import (
    PROTOCOL_VERSION,
    REMOTE_SCRIPT_VERSION,
    CommandError,
    RemoteErrorCode,
    RemoteErrorReason,
    details_with_reason,
)
from ..effect_specs import (
    SUPPORTED_EFFECT_TYPES,
    canonicalize_effect_type,
    detect_effect_type,
    resolve_standard_effect_key_indexes,
)
from ..synth_specs import (
    SUPPORTED_SYNTH_TYPES,
    canonicalize_synth_type,
    detect_synth_type,
    resolve_standard_synth_key_indexes,
)


def _invalid_argument(message: str, hint: str) -> CommandError:
    return CommandError(code=RemoteErrorCode.INVALID_ARGUMENT, message=message, hint=hint)


def _not_supported_by_live_api(message: str, hint: str) -> CommandError:
    return CommandError(
        code=RemoteErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        details=details_with_reason(RemoteErrorReason.NOT_SUPPORTED_BY_LIVE_API),
    )


class LiveBackendBaseMixin:
    _control_surface: Any

    def _ensure_stable_ref_state(self) -> None:
        if not hasattr(self, "_stable_ref_counter"):
            self._stable_ref_counter = 0
        if not hasattr(self, "_stable_ref_by_locator"):
            self._stable_ref_by_locator = {}
        if not hasattr(self, "_stable_ref_by_object"):
            self._stable_ref_by_object = {}
        if not hasattr(self, "_stable_ref_entries"):
            self._stable_ref_entries = {}

    @staticmethod
    def _unwrap_live_object(target: Any) -> Any:
        return getattr(target, "_target", target)

    def _same_live_object(self, left: Any, right: Any) -> bool:
        return self._unwrap_live_object(left) is self._unwrap_live_object(right)

    @staticmethod
    def _is_callable_attribute(target: Any, name: str) -> bool:
        return bool(callable(getattr(target, name, None)))

    def _live_api_support(self) -> dict[str, bool]:
        app = self._control_surface.application()
        song = self._control_surface.song()

        song_new_supported = self._is_callable_attribute(app, "new_live_set")
        song_save_supported = self._is_callable_attribute(app, "save_live_set")
        song_export_audio_supported = self._is_callable_attribute(app, "export_audio")
        has_record_mode = hasattr(song, "record_mode")
        arrangement_record_start_supported = has_record_mode or self._is_callable_attribute(
            song,
            "start_arrangement_recording",
        )
        arrangement_record_stop_supported = has_record_mode or self._is_callable_attribute(
            song,
            "stop_arrangement_recording",
        )

        return {
            "song_new_supported": song_new_supported,
            "song_save_supported": song_save_supported,
            "song_export_audio_supported": song_export_audio_supported,
            "arrangement_record_start_supported": arrangement_record_start_supported,
            "arrangement_record_stop_supported": arrangement_record_stop_supported,
            "arrangement_record_supported": (
                arrangement_record_start_supported and arrangement_record_stop_supported
            ),
        }

    def _song(self) -> Any:
        return self._control_surface.song()

    def _application(self) -> Any:
        app = self._control_surface.application()
        if app is None:
            raise _invalid_argument(
                message="Live application is not available",
                hint="Make sure Ableton Live is running and fully loaded.",
            )
        return app

    def _track_at(self, index: int) -> Any:
        tracks = list(self._song().tracks)
        if index < 0 or index >= len(tracks):
            raise _invalid_argument(
                message=f"track out of range: {index}",
                hint="Use a valid track index from tracks list.",
            )
        return tracks[index]

    def _selected_track(self) -> Any:
        view = getattr(self._song(), "view", None)
        if view is None or not hasattr(view, "selected_track"):
            raise _not_supported_by_live_api(
                message="Song view selected_track API is not available in Live API",
                hint="Use a Live version exposing song.view.selected_track.",
            )
        selected_track = getattr(view, "selected_track", None)
        if selected_track is None:
            raise _invalid_argument(
                message="No track is currently selected",
                hint="Select a track in Ableton Live and retry.",
            )
        return selected_track

    def _clip_slot_at(self, track: int, clip: int) -> Any:
        target = self._track_at(track)
        slots = list(target.clip_slots)
        if clip < 0 or clip >= len(slots):
            raise _invalid_argument(
                message=f"clip out of range: {clip}",
                hint="Use a valid clip slot index for the target track.",
            )
        return slots[clip]

    def _scene_at(self, index: int) -> Any:
        scenes = list(getattr(self._song(), "scenes", []))
        if index < 0 or index >= len(scenes):
            raise _invalid_argument(
                message=f"scene out of range: {index}",
                hint="Use a valid scene index from scenes list.",
            )
        return scenes[index]

    def _return_track_at(self, index: int) -> Any:
        tracks = list(getattr(self._song(), "return_tracks", []))
        if index < 0 or index >= len(tracks):
            raise _invalid_argument(
                message=f"return_track out of range: {index}",
                hint="Use a valid return track index from return-tracks list.",
            )
        return tracks[index]

    def _device_at(self, track: int, device: int) -> Any:
        target = self._track_at(track)
        devices = list(target.devices)
        if device < 0 or device >= len(devices):
            raise _invalid_argument(
                message=f"device out of range: {device}",
                hint="Use a valid device index from track info.",
            )
        return devices[device]

    def _parameter_at(self, track: int, device: int, parameter: int) -> Any:
        target_device = self._device_at(track, device)
        parameters = list(getattr(target_device, "parameters", []))
        if parameter < 0 or parameter >= len(parameters):
            raise _invalid_argument(
                message=f"parameter out of range: {parameter}",
                hint="Use a valid parameter index from track info.",
            )
        return parameters[parameter]

    def _next_stable_ref(self, kind: str) -> str:
        self._ensure_stable_ref_state()
        self._stable_ref_counter += 1
        return f"{kind}:{self._stable_ref_counter}"

    def _track_locator(self, track: Any) -> tuple[str, int] | None:
        for index, candidate in enumerate(list(self._song().tracks)):
            if self._same_live_object(candidate, track):
                return ("track", index)
        return None

    def _device_locator(self, device: Any) -> tuple[str, int, int] | tuple[str, int] | None:
        for track_index, track in enumerate(list(self._song().tracks)):
            for device_index, candidate in enumerate(list(getattr(track, "devices", []))):
                if self._same_live_object(candidate, device):
                    return ("track", track_index, device_index)
        master_track = getattr(self._song(), "master_track", None)
        if master_track is None:
            return None
        for device_index, candidate in enumerate(list(getattr(master_track, "devices", []))):
            if self._same_live_object(candidate, device):
                return ("master", device_index)
        return None

    def _parameter_locator(
        self,
        parameter: Any,
    ) -> tuple[str, int, int, int] | tuple[str, int, int] | None:
        for track_index, track in enumerate(list(self._song().tracks)):
            for device_index, device in enumerate(list(getattr(track, "devices", []))):
                parameters = list(getattr(device, "parameters", []))
                for parameter_index, candidate in enumerate(parameters):
                    if self._same_live_object(candidate, parameter):
                        return ("track", track_index, device_index, parameter_index)
        master_track = getattr(self._song(), "master_track", None)
        if master_track is None:
            return None
        for device_index, device in enumerate(list(getattr(master_track, "devices", []))):
            for parameter_index, candidate in enumerate(list(getattr(device, "parameters", []))):
                if self._same_live_object(candidate, parameter):
                    return ("master", device_index, parameter_index)
        return None

    def _stable_ref_locator(self, kind: str, target: Any) -> tuple[Any, ...] | None:
        if kind == "track":
            return self._track_locator(target)
        if kind == "device":
            return self._device_locator(target)
        if kind == "parameter":
            return self._parameter_locator(target)
        return None

    def _stable_ref(
        self,
        kind: str,
        target: Any,
        *,
        locator: tuple[Any, ...] | None = None,
    ) -> str:
        self._ensure_stable_ref_state()
        canonical_target = self._unwrap_live_object(target)
        if locator is None:
            locator = self._stable_ref_locator(kind, target)
        token = None
        if locator is not None:
            token = self._stable_ref_by_locator.get((kind, locator))
        if token is None:
            token = self._stable_ref_by_object.get((kind, id(canonical_target)))
        if token is None:
            token = self._next_stable_ref(kind)
        if locator is not None:
            self._stable_ref_by_locator[(kind, locator)] = token
        self._stable_ref_by_object[(kind, id(canonical_target))] = token
        self._stable_ref_entries[token] = {
            "kind": kind,
            "locator": locator,
            "target": canonical_target,
        }
        return token

    def _track_stable_ref(self, track: Any, *, index: int | None = None) -> str:
        locator = None if index is None else ("track", index)
        return self._stable_ref("track", track, locator=locator)

    def _device_stable_ref(
        self,
        device: Any,
        *,
        track_index: int | None = None,
        device_index: int | None = None,
    ) -> str:
        locator = None
        if track_index is not None and device_index is not None:
            locator = ("track", track_index, device_index)
        return self._stable_ref("device", device, locator=locator)

    def _parameter_stable_ref(
        self,
        parameter: Any,
        *,
        track_index: int | None = None,
        device_index: int | None = None,
        parameter_index: int | None = None,
    ) -> str:
        locator = None
        if track_index is not None and device_index is not None and parameter_index is not None:
            locator = ("track", track_index, device_index, parameter_index)
        return self._stable_ref("parameter", parameter, locator=locator)

    def _resolve_by_name_or_query(
        self,
        *,
        kind: str,
        candidates: list[tuple[int, str]],
        ref: dict[str, Any],
    ) -> int:
        mode = str(ref["mode"])
        if mode == "name":
            expected = str(ref["name"]).strip()
            matches = [index for index, name in candidates if name.strip() == expected]
        else:
            query = str(ref["query"]).strip().lower()
            matches = [index for index, name in candidates if query in name.strip().lower()]
        if not matches:
            raise _invalid_argument(
                message=f"{kind} {mode} did not match any item",
                hint=f"Use a unique existing {kind} {mode}.",
            )
        if len(matches) > 1:
            raise _invalid_argument(
                message=f"{kind} {mode} matched multiple items",
                hint=f"Use a unique {kind} selector.",
            )
        return matches[0]

    def _resolve_stable_ref(
        self,
        *,
        kind: str,
        stable_ref: str,
        candidates: list[tuple[int, Any]],
        locator_matcher: Callable[[tuple[Any, ...]], int | None] | None = None,
    ) -> int:
        self._ensure_stable_ref_state()
        entry = self._stable_ref_entries.get(stable_ref)
        if entry is None or entry["kind"] != kind:
            raise _invalid_argument(
                message=f"Unknown {kind} stable_ref: {stable_ref}",
                hint=f"Use a {kind} stable_ref emitted by the current session.",
            )
        target = entry["target"]
        for index, candidate in candidates:
            if self._same_live_object(candidate, target):
                return index
        locator = entry["locator"]
        if locator_matcher is not None and locator is not None:
            index = locator_matcher(locator)
            if index is not None:
                return index
        raise _invalid_argument(
            message=f"Stale {kind} stable_ref: {stable_ref}",
            hint=f"Refresh {kind} refs from the current Ableton session and retry.",
        )

    def _track_index_from_locator(self, locator: tuple[Any, ...]) -> int | None:
        if len(locator) != 2 or locator[0] != "track":
            return None
        index = int(locator[1])
        tracks = list(self._song().tracks)
        if index < 0 or index >= len(tracks):
            return None
        return index

    def _device_index_from_locator(self, track: int, locator: tuple[Any, ...]) -> int | None:
        if len(locator) != 3 or locator[0] != "track":
            return None
        locator_track = int(locator[1])
        locator_device = int(locator[2])
        if locator_track != track:
            return None
        devices = list(self._track_at(track).devices)
        if locator_device < 0 or locator_device >= len(devices):
            return None
        return locator_device

    def _parameter_index_from_locator(
        self,
        track: int,
        device: int,
        locator: tuple[Any, ...],
    ) -> int | None:
        if len(locator) != 4 or locator[0] != "track":
            return None
        locator_track = int(locator[1])
        locator_device = int(locator[2])
        locator_parameter = int(locator[3])
        if locator_track != track or locator_device != device:
            return None
        parameters = list(getattr(self._device_at(track, device), "parameters", []))
        if locator_parameter < 0 or locator_parameter >= len(parameters):
            return None
        return locator_parameter

    def resolve_track_ref(self, track_ref: dict[str, Any]) -> int:
        mode = str(track_ref["mode"])
        tracks = list(self._song().tracks)
        if mode == "index":
            index = int(track_ref["index"])
            self._track_at(index)
            return index
        if mode == "selected":
            selected_track = self._selected_track()
            for index, track in enumerate(tracks):
                if self._same_live_object(track, selected_track):
                    return index
            raise _invalid_argument(
                message="Selected track is not part of the current song tracks",
                hint="Select a regular song track and retry.",
            )
        if mode in {"name", "query"}:
            return self._resolve_by_name_or_query(
                kind="track",
                candidates=[
                    (index, str(getattr(track, "name", ""))) for index, track in enumerate(tracks)
                ],
                ref=track_ref,
            )
        if mode == "stable_ref":
            return self._resolve_stable_ref(
                kind="track",
                stable_ref=str(track_ref["stable_ref"]),
                candidates=[(index, track) for index, track in enumerate(tracks)],
                locator_matcher=self._track_index_from_locator,
            )
        raise AssertionError(f"unsupported track mode: {mode}")

    def _selected_device(self, track: Any) -> Any:
        view = getattr(track, "view", None)
        if view is None or not hasattr(view, "selected_device"):
            raise _not_supported_by_live_api(
                message="Track view selected_device API is not available in Live API",
                hint="Use a Live version exposing track.view.selected_device.",
            )
        selected_device = getattr(view, "selected_device", None)
        if selected_device is None:
            raise _invalid_argument(
                message="No device is currently selected on the target track",
                hint="Select a device on the target track and retry.",
            )
        return selected_device

    def resolve_device_ref(self, track: int, device_ref: dict[str, Any]) -> int:
        target_track = self._track_at(track)
        devices = list(target_track.devices)
        mode = str(device_ref["mode"])
        if mode == "index":
            index = int(device_ref["index"])
            self._device_at(track, index)
            return index
        if mode == "selected":
            selected_device = self._selected_device(target_track)
            for index, device in enumerate(devices):
                if self._same_live_object(device, selected_device):
                    return index
            raise _invalid_argument(
                message="Selected device is not part of the target track",
                hint="Select a device on the target track and retry.",
            )
        if mode in {"name", "query"}:
            return self._resolve_by_name_or_query(
                kind="device",
                candidates=[
                    (index, str(getattr(device, "name", "")))
                    for index, device in enumerate(devices)
                ],
                ref=device_ref,
            )
        if mode == "stable_ref":
            return self._resolve_stable_ref(
                kind="device",
                stable_ref=str(device_ref["stable_ref"]),
                candidates=[(index, device) for index, device in enumerate(devices)],
                locator_matcher=lambda locator: self._device_index_from_locator(track, locator),
            )
        raise AssertionError(f"unsupported device mode: {mode}")

    def resolve_parameter_ref(self, track: int, device: int, parameter_ref: dict[str, Any]) -> int:
        target_device = self._device_at(track, device)
        parameters = list(getattr(target_device, "parameters", []))
        mode = str(parameter_ref["mode"])
        if mode == "index":
            index = int(parameter_ref["index"])
            self._parameter_at(track, device, index)
            return index
        if mode in {"name", "query"}:
            return self._resolve_by_name_or_query(
                kind="parameter",
                candidates=[
                    (index, str(getattr(parameter, "name", "")))
                    for index, parameter in enumerate(parameters)
                ],
                ref=parameter_ref,
            )
        if mode == "stable_ref":
            return self._resolve_stable_ref(
                kind="parameter",
                stable_ref=str(parameter_ref["stable_ref"]),
                candidates=[(index, parameter) for index, parameter in enumerate(parameters)],
                locator_matcher=lambda locator: self._parameter_index_from_locator(
                    track,
                    device,
                    locator,
                ),
            )
        if mode == "key":
            key = str(parameter_ref["key"])
            detected_synth_type = self._synth_type_for_device(target_device)
            if detected_synth_type is not None:
                key_indexes, _ = self._resolved_standard_synth_key_indexes(
                    synth_type=detected_synth_type,
                    track=track,
                    device=device,
                )
                if key in key_indexes:
                    return key_indexes[key]
            detected_effect_type = self._effect_type_for_device(target_device)
            if detected_effect_type is not None:
                key_indexes, _ = self._resolved_standard_effect_key_indexes(
                    effect_type=detected_effect_type,
                    track=track,
                    device=device,
                )
                if key in key_indexes:
                    return key_indexes[key]
            raise _invalid_argument(
                message=f"Unsupported parameter key for target device: {key}",
                hint="Use a supported synth/effect parameter key for the selected device.",
            )
        raise AssertionError(f"unsupported parameter mode: {mode}")

    def _safe_float(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _serialize_parameter(
        self,
        parameter: Any,
        index: int,
        *,
        track_index: int | None = None,
        device_index: int | None = None,
    ) -> dict[str, Any]:
        minimum = self._safe_float(getattr(parameter, "min", None))
        maximum = self._safe_float(getattr(parameter, "max", None))
        return {
            "index": index,
            "stable_ref": self._parameter_stable_ref(
                parameter,
                track_index=track_index,
                device_index=device_index,
                parameter_index=index,
            ),
            "name": str(getattr(parameter, "name", f"Parameter {index}")),
            "value": float(getattr(parameter, "value", 0.0)),
            "min": minimum,
            "max": maximum,
            "is_enabled": bool(getattr(parameter, "is_enabled", True)),
            "is_quantized": bool(getattr(parameter, "is_quantized", False)),
        }

    def _serialize_devices(
        self,
        devices: list[Any],
        *,
        track_index: int | None = None,
        track_stable_ref: str | None = None,
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for device_index, device in enumerate(devices):
            parameters = [
                {
                    "index": parameter_index,
                    "stable_ref": self._parameter_stable_ref(
                        parameter,
                        track_index=track_index,
                        device_index=device_index,
                        parameter_index=parameter_index,
                    ),
                    "name": str(getattr(parameter, "name", f"Parameter {parameter_index}")),
                    "value": float(getattr(parameter, "value", 0.0)),
                }
                for parameter_index, parameter in enumerate(list(getattr(device, "parameters", [])))
            ]
            serialized = {
                "index": device_index,
                "stable_ref": self._device_stable_ref(
                    device,
                    track_index=track_index,
                    device_index=device_index,
                ),
                "name": str(getattr(device, "name", "")),
                "class_name": str(getattr(device, "class_name", "")),
                "type": self._get_device_type(device),
                "parameters": parameters,
            }
            if track_stable_ref is not None:
                serialized["track_stable_ref"] = track_stable_ref
            payload.append(serialized)
        return payload

    def _synth_type_for_device(self, device: Any) -> str | None:
        return detect_synth_type(device)

    def _effect_type_for_device(self, device: Any) -> str | None:
        return detect_effect_type(device)

    def _require_supported_synth_device(self, track: int, device: int) -> tuple[Any, str]:
        target_device = self._device_at(track, device)
        detected_type = self._synth_type_for_device(target_device)
        if detected_type is None:
            raise _invalid_argument(
                message=(
                    "Device is not a supported synth "
                    f"(supported: {', '.join(SUPPORTED_SYNTH_TYPES)})"
                ),
                hint="Choose a Wavetable, Drift, or Meld device.",
            )
        return target_device, detected_type

    def _require_supported_effect_device(self, track: int, device: int) -> tuple[Any, str]:
        target_device = self._device_at(track, device)
        detected_type = self._effect_type_for_device(target_device)
        if detected_type is None:
            raise _invalid_argument(
                message=(
                    "Device is not a supported effect "
                    f"(supported: {', '.join(SUPPORTED_EFFECT_TYPES)})"
                ),
                hint="Choose one of the supported audio effects.",
            )
        return target_device, detected_type

    def _device_payload(
        self,
        *,
        track: int,
        device_index: int,
        device: Any,
        detected_type: str,
    ) -> dict[str, Any]:
        return {
            "track": track,
            "device": device_index,
            "track_stable_ref": self._track_stable_ref(self._track_at(track), index=track),
            "stable_ref": self._device_stable_ref(
                device,
                track_index=track,
                device_index=device_index,
            ),
            "track_name": str(getattr(self._track_at(track), "name", "")),
            "device_name": str(getattr(device, "name", "")),
            "class_name": str(getattr(device, "class_name", "")),
            "detected_type": detected_type,
        }

    def _synth_device_payload(
        self,
        *,
        track: int,
        device_index: int,
        device: Any,
        detected_type: str,
    ) -> dict[str, Any]:
        return self._device_payload(
            track=track,
            device_index=device_index,
            device=device,
            detected_type=detected_type,
        )

    def _effect_device_payload(
        self,
        *,
        track: int,
        device_index: int,
        device: Any,
        detected_type: str,
    ) -> dict[str, Any]:
        return self._device_payload(
            track=track,
            device_index=device_index,
            device=device,
            detected_type=detected_type,
        )

    def _list_synth_parameters_payload(self, track: int, device: int) -> dict[str, Any]:
        target_device, detected_type = self._require_supported_synth_device(track, device)
        serialized_parameters = [
            self._serialize_parameter(
                parameter,
                index,
                track_index=track,
                device_index=device,
            )
            for index, parameter in enumerate(list(getattr(target_device, "parameters", [])))
        ]
        return {
            "track": track,
            "device": device,
            "track_stable_ref": self._track_stable_ref(self._track_at(track), index=track),
            "device_stable_ref": self._device_stable_ref(
                target_device,
                track_index=track,
                device_index=device,
            ),
            "device_name": str(getattr(target_device, "name", "")),
            "class_name": str(getattr(target_device, "class_name", "")),
            "detected_type": detected_type,
            "parameter_count": len(serialized_parameters),
            "parameters": serialized_parameters,
        }

    def _resolved_standard_synth_key_indexes(
        self,
        *,
        synth_type: str,
        track: int,
        device: int,
    ) -> tuple[dict[str, int], str]:
        parsed_type = canonicalize_synth_type(synth_type)
        target_device, detected_type = self._require_supported_synth_device(track, device)
        if detected_type != parsed_type:
            raise _invalid_argument(
                message=(
                    f"Device synth type mismatch: requested={parsed_type}, detected={detected_type}"
                ),
                hint="Select a device that matches the requested synth type.",
            )

        parameter_names = [
            str(getattr(parameter, "name", ""))
            for parameter in list(getattr(target_device, "parameters", []))
        ]
        key_indexes, missing_keys = resolve_standard_synth_key_indexes(parameter_names, parsed_type)
        if missing_keys:
            raise _invalid_argument(
                message=(
                    f"Missing required standard synth keys for {parsed_type}: "
                    f"{', '.join(missing_keys)}"
                ),
                hint="Use the exact English standard synth parameter names.",
            )
        return key_indexes, parsed_type

    def _list_effect_parameters_payload(self, track: int, device: int) -> dict[str, Any]:
        target_device, detected_type = self._require_supported_effect_device(track, device)
        serialized_parameters = [
            self._serialize_parameter(
                parameter,
                index,
                track_index=track,
                device_index=device,
            )
            for index, parameter in enumerate(list(getattr(target_device, "parameters", [])))
        ]
        return {
            "track": track,
            "device": device,
            "track_stable_ref": self._track_stable_ref(self._track_at(track), index=track),
            "device_stable_ref": self._device_stable_ref(
                target_device,
                track_index=track,
                device_index=device,
            ),
            "device_name": str(getattr(target_device, "name", "")),
            "class_name": str(getattr(target_device, "class_name", "")),
            "detected_type": detected_type,
            "parameter_count": len(serialized_parameters),
            "parameters": serialized_parameters,
        }

    def _resolved_standard_effect_key_indexes(
        self,
        *,
        effect_type: str,
        track: int,
        device: int,
    ) -> tuple[dict[str, int], str]:
        parsed_type = canonicalize_effect_type(effect_type)
        target_device, detected_type = self._require_supported_effect_device(track, device)
        if detected_type != parsed_type:
            raise _invalid_argument(
                message=(
                    f"Device effect type mismatch: requested={parsed_type}, "
                    f"detected={detected_type}"
                ),
                hint="Select a device that matches the requested effect type.",
            )

        parameter_names = [
            str(getattr(parameter, "name", ""))
            for parameter in list(getattr(target_device, "parameters", []))
        ]
        key_indexes, missing_keys = resolve_standard_effect_key_indexes(
            parameter_names,
            parsed_type,
        )
        if missing_keys:
            raise _invalid_argument(
                message=(
                    f"Missing required standard effect keys for {parsed_type}: "
                    f"{', '.join(missing_keys)}"
                ),
                hint="Use the exact English standard effect parameter names.",
            )
        return key_indexes, parsed_type

    def ping_info(self) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "remote_script_version": REMOTE_SCRIPT_VERSION,
            "api_support": self._live_api_support(),
        }

    def _get_device_type(self, device: Any) -> str:
        try:
            if bool(getattr(device, "can_have_drum_pads", False)):
                return "drum_machine"
            if bool(getattr(device, "can_have_chains", False)):
                return "rack"
            class_display_name = str(getattr(device, "class_display_name", "")).lower()
            class_name = str(getattr(device, "class_name", "")).lower()
            if "instrument" in class_display_name:
                return "instrument"
            if "audio_effect" in class_name or "audioeffect" in class_name:
                return "audio_effect"
            if "midi_effect" in class_name or "midieffect" in class_name:
                return "midi_effect"
            return "unknown"
        except Exception:  # noqa: BLE001
            return "unknown"
