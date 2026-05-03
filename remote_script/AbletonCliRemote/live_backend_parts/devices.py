from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ..effect_specs import (
    SUPPORTED_EFFECT_TYPES,
    canonicalize_effect_type,
    resolve_standard_effect_key_indexes,
    standard_effect_keys,
)
from ..synth_specs import SUPPORTED_SYNTH_TYPES, canonicalize_synth_type, standard_synth_keys
from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendDeviceSharedMixin:
    def _master_track(self) -> Any:
        master = getattr(self._song(), "master_track", None)
        if master is None:
            raise _not_supported_by_live_api(
                message="Master track API is not available in Live API",
                hint="Use a Live version exposing song.master_track.",
            )
        return master

    def _master_device_at(self, device: int) -> Any:
        devices = list(getattr(self._master_track(), "devices", []))
        if device < 0 or device >= len(devices):
            raise _invalid_argument(
                message=f"master device out of range: {device}",
                hint="Use a valid device index from 'master devices list'.",
            )
        return devices[device]

    def _master_parameter_at(self, device: int, parameter: int) -> Any:
        target_device = self._master_device_at(device)
        parameters = list(getattr(target_device, "parameters", []))
        if parameter < 0 or parameter >= len(parameters):
            raise _invalid_argument(
                message=f"master parameter out of range: {parameter}",
                hint="Use a valid parameter index from parameter listing commands.",
            )
        return parameters[parameter]

    def _resolve_master_device_ref(self, device_ref: dict[str, Any]) -> int:
        devices = list(getattr(self._master_track(), "devices", []))
        mode = str(device_ref["mode"])
        if mode == "index":
            index = int(device_ref["index"])
            self._master_device_at(index)
            return index
        if mode in {"name", "query"}:
            return self._resolve_by_name_or_query(
                kind="master device",
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
                locator_matcher=self._master_device_index_from_locator,
            )
        raise AssertionError(f"unsupported master device mode: {mode}")

    def _resolve_master_parameter_ref(
        self,
        device: int,
        parameter_ref: dict[str, Any],
    ) -> int:
        target_device = self._master_device_at(device)
        parameters = list(getattr(target_device, "parameters", []))
        mode = str(parameter_ref["mode"])
        if mode == "index":
            index = int(parameter_ref["index"])
            self._master_parameter_at(device, index)
            return index
        if mode in {"name", "query"}:
            return self._resolve_by_name_or_query(
                kind="master parameter",
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
                locator_matcher=lambda locator: self._master_parameter_index_from_locator(
                    device,
                    locator,
                ),
            )
        if mode == "key":
            key_indexes, _ = self._resolved_master_standard_effect_key_indexes(
                effect_type=str(self._effect_type_for_device(target_device)),
                device=device,
            )
            key = str(parameter_ref["key"])
            if key in key_indexes:
                return key_indexes[key]
            raise _invalid_argument(
                message=f"Unsupported parameter key for master device: {key}",
                hint="Use a supported effect parameter key for the selected master device.",
            )
        raise AssertionError(f"unsupported master parameter mode: {mode}")

    def _master_device_index_from_locator(self, locator: tuple[Any, ...]) -> int | None:
        if len(locator) != 2 or locator[0] != "master":
            return None
        index = int(locator[1])
        devices = list(getattr(self._master_track(), "devices", []))
        if index < 0 or index >= len(devices):
            return None
        return index

    def _master_parameter_index_from_locator(
        self,
        device: int,
        locator: tuple[Any, ...],
    ) -> int | None:
        if len(locator) != 3 or locator[0] != "master":
            return None
        locator_device = int(locator[1])
        locator_parameter = int(locator[2])
        if locator_device != device:
            return None
        parameters = list(getattr(self._master_device_at(device), "parameters", []))
        if locator_parameter < 0 or locator_parameter >= len(parameters):
            return None
        return locator_parameter

    def _master_device_stable_ref(self, device: Any, *, device_index: int | None = None) -> str:
        locator = None if device_index is None else ("master", device_index)
        return self._stable_ref("device", device, locator=locator)

    def _master_parameter_stable_ref(
        self,
        parameter: Any,
        *,
        device_index: int | None = None,
        parameter_index: int | None = None,
    ) -> str:
        locator = None
        if device_index is not None and parameter_index is not None:
            locator = ("master", device_index, parameter_index)
        return self._stable_ref("parameter", parameter, locator=locator)

    def _resolve_track_indexes(self, track: int | None) -> Iterable[int]:
        if track is None:
            return range(len(list(self._song().tracks)))
        self._track_at(track)
        return (track,)

    def _canonicalize_optional_type(
        self,
        *,
        value: str | None,
        kind: str,
        canonicalize: Callable[[str], str],
        supported_types: list[str],
    ) -> str | None:
        if value is None:
            return None
        try:
            return canonicalize(value)
        except ValueError as exc:
            raise _invalid_argument(
                message=f"Unsupported {kind}: {value}",
                hint=f"Use one of: {', '.join(supported_types)}.",
            ) from exc

    def _iter_track_devices(self, track_indexes: Iterable[int]) -> Iterator[tuple[int, int, Any]]:
        for track_index in track_indexes:
            target_track = self._track_at(track_index)
            for device_index, target_device in enumerate(list(target_track.devices)):
                yield track_index, device_index, target_device

    def _find_devices(
        self,
        *,
        track: int | None,
        requested_type: str | None,
        detector: Callable[[Any], str | None],
        payload_builder: Callable[..., dict[str, Any]],
    ) -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []
        track_indexes = self._resolve_track_indexes(track)
        for track_index, device_index, target_device in self._iter_track_devices(track_indexes):
            detected_type = detector(target_device)
            if detected_type is None:
                continue
            if requested_type is not None and detected_type != requested_type:
                continue
            devices.append(
                payload_builder(
                    track=track_index,
                    device_index=device_index,
                    device=target_device,
                    detected_type=detected_type,
                )
            )
        return devices

    def _set_parameter_safe(
        self,
        *,
        track: int,
        device: int,
        parameter: int,
        value: float,
        require_supported_device: Callable[[int, int], tuple[Any, str]],
    ) -> dict[str, Any]:
        target_device, detected_type = require_supported_device(track, device)
        del target_device

        target_parameter = self._parameter_at(track, device, parameter)
        serialized_parameter = self._serialize_parameter(target_parameter, parameter)

        if not serialized_parameter["is_enabled"]:
            raise _invalid_argument(
                message=f"Parameter is disabled at index {parameter}",
                hint="Choose an enabled parameter from parameters list.",
            )

        minimum = serialized_parameter["min"]
        maximum = serialized_parameter["max"]
        if minimum is None or maximum is None:
            raise _invalid_argument(
                message=f"Parameter bounds are unavailable at index {parameter}",
                hint="Choose a parameter with numeric min/max bounds.",
            )
        if value < minimum or value > maximum:
            raise _invalid_argument(
                message=f"value must be between {minimum} and {maximum}",
                hint="Use a value within the reported parameter range.",
            )

        before = float(getattr(target_parameter, "value", 0.0))
        target_parameter.value = float(value)
        after = float(getattr(target_parameter, "value", 0.0))
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "track_stable_ref": self._track_stable_ref(self._track_at(track), index=track),
            "device_stable_ref": self._device_stable_ref(
                self._device_at(track, device),
                track_index=track,
                device_index=device,
            ),
            "parameter_stable_ref": self._parameter_stable_ref(
                target_parameter,
                track_index=track,
                device_index=device,
                parameter_index=parameter,
            ),
            "detected_type": detected_type,
            "before": before,
            "after": after,
            "min": minimum,
            "max": maximum,
            "is_enabled": serialized_parameter["is_enabled"],
            "is_quantized": serialized_parameter["is_quantized"],
        }

    def set_device_parameter(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        target_param = self._parameter_at(track, device, parameter)
        target_param.value = float(value)
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "track_stable_ref": self._track_stable_ref(self._track_at(track), index=track),
            "device_stable_ref": self._device_stable_ref(
                self._device_at(track, device),
                track_index=track,
                device_index=device,
            ),
            "parameter_stable_ref": self._parameter_stable_ref(
                target_param,
                track_index=track,
                device_index=device,
                parameter_index=parameter,
            ),
            "value": float(target_param.value),
        }

    def master_device_load(self, target: str, position: str) -> dict[str, Any]:
        uri, path = self._master_load_target(target)
        if uri is not None:
            item = self._find_browser_item_by_uri(uri)
            if item is None:
                raise _invalid_argument(
                    message=f"Browser item with URI '{uri}' not found",
                    hint="Inspect browser search results and choose a valid URI.",
                )
            serialized = self._serialize_browser_item(item, path=self._item_path_by_uri(uri))
        else:
            assert path is not None
            item = self._resolve_browser_path(path)
            serialized = self._serialize_browser_item(item, path=path)
            if not serialized["is_loadable"]:
                raise _invalid_argument(
                    message=f"Browser item at path '{path}' is not loadable",
                    hint="Use browser search/items to select a loadable item.",
                )
        master = self._master_track()
        before = len(list(getattr(master, "devices", [])))
        self._select_track_for_load(song=self._song(), target_track=master)
        self._browser().load_item(item)
        after_devices = list(getattr(master, "devices", []))
        loaded_index = max(0, len(after_devices) - 1)
        target_index = self._master_insert_index(position, len(after_devices))
        if after_devices and target_index != loaded_index:
            self.master_device_move(loaded_index, target_index)
            loaded_index = target_index
        return {
            "target": target,
            "uri": uri if uri is not None else serialized["uri"],
            "path": path,
            "position": position,
            "device": loaded_index,
            "device_count_before": before,
            "device_count_after": len(list(getattr(master, "devices", []))),
        }

    def master_device_move(self, device_index: int, to_index: int) -> dict[str, Any]:
        master = self._master_track()
        devices = list(getattr(master, "devices", []))
        self._master_device_at(device_index)
        if to_index < 0 or to_index >= len(devices):
            raise _invalid_argument(
                message=f"destination master device out of range: {to_index}",
                hint="Use a valid destination index from 'master devices list'.",
            )
        move_device = getattr(master, "move_device", None)
        if not callable(move_device):
            raise _not_supported_by_live_api(
                message="Master device move API is not available in Live API",
                hint=(
                    "Move the master device manually or use a Live version exposing "
                    "track.move_device."
                ),
            )
        move_device(device_index, to_index)
        return {"device": device_index, "to_index": to_index}

    def master_device_delete(self, device_index: int) -> dict[str, Any]:
        master = self._master_track()
        self._master_device_at(device_index)
        delete_device = getattr(master, "delete_device", None)
        if not callable(delete_device):
            raise _not_supported_by_live_api(
                message="Master device delete API is not available in Live API",
                hint=(
                    "Delete the master device manually or use a Live version exposing "
                    "track.delete_device."
                ),
            )
        delete_device(device_index)
        return {
            "device": device_index,
            "deleted": True,
            "device_count": len(list(getattr(master, "devices", []))),
        }

    def master_device_parameters_list(self, device_ref: dict[str, Any]) -> dict[str, Any]:
        device = self._resolve_master_device_ref(device_ref)
        target_device = self._master_device_at(device)
        parameters = [
            self._serialize_master_parameter(parameter, device, index)
            for index, parameter in enumerate(list(getattr(target_device, "parameters", [])))
        ]
        return {
            "device": device,
            "device_stable_ref": self._master_device_stable_ref(
                target_device,
                device_index=device,
            ),
            "device_name": str(getattr(target_device, "name", "")),
            "class_name": str(getattr(target_device, "class_name", "")),
            "parameter_count": len(parameters),
            "parameters": parameters,
        }

    def master_device_parameter_set(
        self,
        device_ref: dict[str, Any],
        parameter_ref: dict[str, Any],
        value: float,
    ) -> dict[str, Any]:
        device = self._resolve_master_device_ref(device_ref)
        parameter = self._resolve_master_parameter_ref(device, parameter_ref)
        target_parameter = self._master_parameter_at(device, parameter)
        target_parameter.value = float(value)
        return {
            "device": device,
            "parameter": parameter,
            "device_stable_ref": self._master_device_stable_ref(
                self._master_device_at(device),
                device_index=device,
            ),
            "parameter_stable_ref": self._master_parameter_stable_ref(
                target_parameter,
                device_index=device,
                parameter_index=parameter,
            ),
            "value": float(target_parameter.value),
        }

    def master_effect_keys(self, effect_type: str) -> dict[str, Any]:
        parsed_type = canonicalize_effect_type(effect_type)
        keys = standard_effect_keys(parsed_type)
        return {"effect_type": parsed_type, "key_count": len(keys), "keys": keys}

    def master_effect_set(
        self,
        effect_type: str,
        device_ref: dict[str, Any],
        parameter_ref: dict[str, Any],
        value: float,
    ) -> dict[str, Any]:
        device = self._resolve_master_device_ref(device_ref)
        key = parameter_ref.get("key")
        if isinstance(key, str):
            parameter_ref = {
                "mode": "index",
                "index": self._master_effect_key_index(effect_type, device, key),
            }
        result = self.master_device_parameter_set(device_ref, parameter_ref, value)
        return {**result, "effect_type": canonicalize_effect_type(effect_type)}

    def master_effect_observe(
        self,
        effect_type: str,
        device_ref: dict[str, Any],
    ) -> dict[str, Any]:
        device = self._resolve_master_device_ref(device_ref)
        key_indexes, parsed_type = self._resolved_master_standard_effect_key_indexes(
            effect_type=effect_type,
            device=device,
        )
        observed = self.master_device_parameters_list(device_ref)
        parameters = observed["parameters"]
        state = {key: float(parameters[index]["value"]) for key, index in key_indexes.items()}
        return {
            "effect_type": parsed_type,
            "device": device,
            "device_stable_ref": observed["device_stable_ref"],
            "key_count": len(state),
            "keys": standard_effect_keys(parsed_type),
            "state": state,
        }

    def _master_load_target(self, target: str) -> tuple[str | None, str | None]:
        first_colon = target.find(":")
        first_slash = target.find("/")
        if first_colon >= 0 and (first_slash < 0 or first_colon < first_slash):
            return target, None
        if "/" in target:
            return None, target
        if ":" in target:
            return target, None
        raise _invalid_argument(
            message=f"target must include '/' (path) or ':' (uri), got {target!r}",
            hint="Use a browser path or URI from browser search results.",
        )

    def _master_insert_index(self, position: str, device_count: int) -> int:
        normalized = position.strip().lower()
        if normalized == "end":
            return max(0, device_count - 1)
        if normalized == "start":
            return 0
        try:
            index = int(normalized)
        except ValueError as exc:
            raise _invalid_argument(
                message=f"Unsupported master device position: {position}",
                hint="Use start, end, or a non-negative device index.",
            ) from exc
        if index < 0 or index >= device_count:
            raise _invalid_argument(
                message=f"master device position out of range: {index}",
                hint="Use a valid insertion index.",
            )
        return index

    def _serialize_master_parameter(
        self,
        parameter: Any,
        device_index: int,
        parameter_index: int,
    ) -> dict[str, Any]:
        return {
            "index": parameter_index,
            "stable_ref": self._master_parameter_stable_ref(
                parameter,
                device_index=device_index,
                parameter_index=parameter_index,
            ),
            "name": str(getattr(parameter, "name", f"Parameter {parameter_index}")),
            "value": float(getattr(parameter, "value", 0.0)),
            "min": self._safe_float(getattr(parameter, "min", None)),
            "max": self._safe_float(getattr(parameter, "max", None)),
            "is_enabled": bool(getattr(parameter, "is_enabled", True)),
            "is_quantized": bool(getattr(parameter, "is_quantized", False)),
        }

    def _master_effect_key_index(self, effect_type: str, device: int, key: str) -> int:
        key_indexes, parsed_type = self._resolved_master_standard_effect_key_indexes(
            effect_type=effect_type,
            device=device,
        )
        if key not in key_indexes:
            raise _invalid_argument(
                message=f"Unsupported key for {parsed_type}: {key}",
                hint=f"Use one of: {', '.join(standard_effect_keys(parsed_type))}.",
            )
        return key_indexes[key]

    def _resolved_master_standard_effect_key_indexes(
        self,
        *,
        effect_type: str,
        device: int,
    ) -> tuple[dict[str, int], str]:
        parsed_type = canonicalize_effect_type(effect_type)
        target_device = self._master_device_at(device)
        detected_type = self._effect_type_for_device(target_device)
        if detected_type != parsed_type:
            raise _invalid_argument(
                message=(
                    f"Master device effect type mismatch: requested={parsed_type}, "
                    f"detected={detected_type}"
                ),
                hint="Select a master device that matches the requested effect type.",
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
                hint="Use generic master device parameter commands for this device variant.",
            )
        return key_indexes, parsed_type


class LiveBackendSynthDevicesMixin:
    def find_synth_devices(
        self,
        track: int | None,
        synth_type: str | None,
    ) -> dict[str, Any]:
        parsed_type = self._canonicalize_optional_type(
            value=synth_type,
            kind="synth_type",
            canonicalize=canonicalize_synth_type,
            supported_types=SUPPORTED_SYNTH_TYPES,
        )
        devices = self._find_devices(
            track=track,
            requested_type=parsed_type,
            detector=self._synth_type_for_device,
            payload_builder=self._synth_device_payload,
        )
        return {
            "track": track,
            "synth_type": parsed_type,
            "count": len(devices),
            "devices": devices,
        }

    def list_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_synth_parameters_payload(track, device)

    def set_synth_parameter_safe(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        return self._set_parameter_safe(
            track=track,
            device=device,
            parameter=parameter,
            value=value,
            require_supported_device=self._require_supported_synth_device,
        )

    def observe_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_synth_parameters_payload(track, device)

    def list_standard_synth_keys(self, synth_type: str) -> dict[str, Any]:
        try:
            parsed_type = canonicalize_synth_type(synth_type)
        except ValueError as exc:
            raise _invalid_argument(
                message=f"Unsupported synth_type: {synth_type}",
                hint=f"Use one of: {', '.join(SUPPORTED_SYNTH_TYPES)}.",
            ) from exc
        keys = standard_synth_keys(parsed_type)
        return {
            "synth_type": parsed_type,
            "key_count": len(keys),
            "keys": keys,
        }

    def set_standard_synth_parameter_safe(
        self,
        synth_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_synth_key_indexes(
            synth_type=synth_type,
            track=track,
            device=device,
        )
        if key not in key_indexes:
            raise _invalid_argument(
                message=f"Unsupported key for {parsed_type}: {key}",
                hint=f"Use one of: {', '.join(standard_synth_keys(parsed_type))}.",
            )

        parameter_index = key_indexes[key]
        result = self.set_synth_parameter_safe(
            track=track,
            device=device,
            parameter=parameter_index,
            value=value,
        )
        return {
            **result,
            "synth_type": parsed_type,
            "key": key,
            "resolved_parameter": parameter_index,
        }

    def observe_standard_synth_state(
        self,
        synth_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_synth_key_indexes(
            synth_type=synth_type,
            track=track,
            device=device,
        )
        observed = self.observe_synth_parameters(track, device)
        parameters = observed["parameters"]
        state = {key: float(parameters[index]["value"]) for key, index in key_indexes.items()}
        return {
            "synth_type": parsed_type,
            "track": track,
            "device": device,
            "track_stable_ref": observed["track_stable_ref"],
            "device_stable_ref": observed["device_stable_ref"],
            "key_count": len(state),
            "keys": standard_synth_keys(parsed_type),
            "state": state,
        }


class LiveBackendEffectDevicesMixin:
    def find_effect_devices(
        self,
        track: int | None,
        effect_type: str | None,
    ) -> dict[str, Any]:
        parsed_type = self._canonicalize_optional_type(
            value=effect_type,
            kind="effect_type",
            canonicalize=canonicalize_effect_type,
            supported_types=SUPPORTED_EFFECT_TYPES,
        )
        devices = self._find_devices(
            track=track,
            requested_type=parsed_type,
            detector=self._effect_type_for_device,
            payload_builder=self._effect_device_payload,
        )
        return {
            "track": track,
            "effect_type": parsed_type,
            "count": len(devices),
            "devices": devices,
        }

    def list_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_effect_parameters_payload(track, device)

    def set_effect_parameter_safe(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        return self._set_parameter_safe(
            track=track,
            device=device,
            parameter=parameter,
            value=value,
            require_supported_device=self._require_supported_effect_device,
        )

    def observe_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_effect_parameters_payload(track, device)

    def list_standard_effect_keys(self, effect_type: str) -> dict[str, Any]:
        try:
            parsed_type = canonicalize_effect_type(effect_type)
        except ValueError as exc:
            raise _invalid_argument(
                message=f"Unsupported effect_type: {effect_type}",
                hint=f"Use one of: {', '.join(SUPPORTED_EFFECT_TYPES)}.",
            ) from exc
        keys = standard_effect_keys(parsed_type)
        return {
            "effect_type": parsed_type,
            "key_count": len(keys),
            "keys": keys,
        }

    def set_standard_effect_parameter_safe(
        self,
        effect_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_effect_key_indexes(
            effect_type=effect_type,
            track=track,
            device=device,
        )
        if key not in key_indexes:
            raise _invalid_argument(
                message=f"Unsupported key for {parsed_type}: {key}",
                hint=f"Use one of: {', '.join(standard_effect_keys(parsed_type))}.",
            )

        parameter_index = key_indexes[key]
        result = self.set_effect_parameter_safe(
            track=track,
            device=device,
            parameter=parameter_index,
            value=value,
        )
        return {
            **result,
            "effect_type": parsed_type,
            "key": key,
            "resolved_parameter": parameter_index,
        }

    def observe_standard_effect_state(
        self,
        effect_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_effect_key_indexes(
            effect_type=effect_type,
            track=track,
            device=device,
        )
        observed = self.observe_effect_parameters(track, device)
        parameters = observed["parameters"]
        state = {key: float(parameters[index]["value"]) for key, index in key_indexes.items()}
        return {
            "effect_type": parsed_type,
            "track": track,
            "device": device,
            "track_stable_ref": observed["track_stable_ref"],
            "device_stable_ref": observed["device_stable_ref"],
            "key_count": len(state),
            "keys": standard_effect_keys(parsed_type),
            "state": state,
        }
