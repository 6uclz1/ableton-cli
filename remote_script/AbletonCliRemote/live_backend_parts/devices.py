from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ..device_families import EFFECT_FAMILY, SYNTH_FAMILY, DeviceFamily
from ..effect_specs import (
    canonicalize_effect_type,
    resolve_standard_effect_key_indexes,
    standard_effect_keys,
)
from .base import DeviceLocator, _invalid_argument
from .device_control import parameter_display


class LiveBackendDeviceSharedMixin:
    def _master_track(self) -> Any:
        return self._ctx._main_track()

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
            return self._ctx._resolve_by_name_or_query(
                kind="master device",
                candidates=[
                    (index, str(getattr(device, "name", "")))
                    for index, device in enumerate(devices)
                ],
                ref=device_ref,
            )
        if mode == "stable_ref":
            return self._ctx._resolve_stable_ref(
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
            return self._ctx._resolve_by_name_or_query(
                kind="master parameter",
                candidates=[
                    (index, str(getattr(parameter, "name", "")))
                    for index, parameter in enumerate(parameters)
                ],
                ref=parameter_ref,
            )
        if mode == "stable_ref":
            return self._ctx._resolve_stable_ref(
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
                effect_type=str(EFFECT_FAMILY.detect(target_device)),
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
        return self._ctx._stable_ref("device", device, locator=locator)

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
        return self._ctx._stable_ref("parameter", parameter, locator=locator)

    def _resolve_track_indexes(self, track: int | None) -> Iterable[int]:
        if track is None:
            return range(len(list(self._ctx._song().tracks)))
        self._ctx._track_at(track)
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
            target_track = self._ctx._track_at(track_index)
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

        target_parameter = self._ctx._parameter_at(track, device, parameter)
        serialized_parameter = self._ctx._serialize_parameter(target_parameter, parameter)

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
            "track_stable_ref": self._ctx._track_stable_ref(
                self._ctx._track_at(track), index=track
            ),
            "device_stable_ref": self._ctx._device_stable_ref(
                self._ctx._device_at(track, device),
                track_index=track,
                device_index=device,
            ),
            "parameter_stable_ref": self._ctx._parameter_stable_ref(
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
        device: DeviceLocator,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        target_param = self._ctx._parameter_at(track, device, parameter)
        target_param.value = float(value)
        parameter_stable_ref = self._ctx._parameter_stable_ref_for(
            target_param, track, device, parameter
        )
        return {
            "track": self._ctx._track_field(track),
            "device": device,
            "parameter": parameter,
            "track_stable_ref": self._ctx._track_stable_ref(
                self._ctx._track_at(track), index=track
            ),
            "device_stable_ref": self._ctx._device_stable_ref_for(track, device),
            "parameter_stable_ref": parameter_stable_ref,
            "value": float(target_param.value),
            "display": parameter_display(target_param, float(target_param.value)),
        }

    def _set_master_parameter(self, device: int, parameter: int, value: float) -> dict[str, Any]:
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
            parameter = self._master_effect_key_index(effect_type, device, key)
        else:
            parameter = self._resolve_master_parameter_ref(device, parameter_ref)
        result = self._set_master_parameter(device, parameter, value)
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
        target_device = self._master_device_at(device)
        parameters = list(getattr(target_device, "parameters", []))
        state = {
            key: float(getattr(parameters[index], "value", 0.0))
            for key, index in key_indexes.items()
        }
        return {
            "effect_type": parsed_type,
            "device": device,
            "device_stable_ref": self._master_device_stable_ref(
                target_device,
                device_index=device,
            ),
            "key_count": len(state),
            "keys": standard_effect_keys(parsed_type),
            "state": state,
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
        detected_type = EFFECT_FAMILY.detect(target_device)
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


class LiveBackendFamilyDevicesMixin:
    """The synth and effect surfaces: one implementation, one thin entry point per command."""

    def _find_family_devices(
        self, family: DeviceFamily, track: int | None, device_type: str | None
    ) -> dict[str, Any]:
        parsed_type = self._canonicalize_optional_type(
            value=device_type,
            kind=family.type_arg,
            canonicalize=family.canonicalize,
            supported_types=family.supported_types,
        )
        devices = self._find_devices(
            track=track,
            requested_type=parsed_type,
            detector=family.detect,
            payload_builder=self._ctx._device_payload,
        )
        return {
            "track": track,
            family.type_arg: parsed_type,
            "count": len(devices),
            "devices": devices,
        }

    def _set_family_parameter_safe(
        self, family: DeviceFamily, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]:
        return self._set_parameter_safe(
            track=track,
            device=device,
            parameter=parameter,
            value=value,
            require_supported_device=lambda track_index, device_index: (
                self._ctx._require_supported_device(family, track_index, device_index)
            ),
        )

    def _list_standard_family_keys(self, family: DeviceFamily, device_type: str) -> dict[str, Any]:
        try:
            parsed_type = family.canonicalize(device_type)
        except ValueError as exc:
            raise _invalid_argument(
                message=f"Unsupported {family.type_arg}: {device_type}",
                hint=f"Use one of: {', '.join(family.supported_types)}.",
            ) from exc
        keys = family.standard_keys(parsed_type)
        return {
            family.type_arg: parsed_type,
            "key_count": len(keys),
            "keys": keys,
        }

    def _set_standard_family_parameter_safe(
        self,
        family: DeviceFamily,
        *,
        device_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._ctx._resolved_standard_key_indexes(
            family,
            device_type=device_type,
            track=track,
            device=device,
        )
        if key not in key_indexes:
            raise _invalid_argument(
                message=f"Unsupported key for {parsed_type}: {key}",
                hint=f"Use one of: {', '.join(family.standard_keys(parsed_type))}.",
            )

        parameter_index = key_indexes[key]
        result = self._set_family_parameter_safe(family, track, device, parameter_index, value)
        return {
            **result,
            family.type_arg: parsed_type,
            "key": key,
            "resolved_parameter": parameter_index,
        }

    def _observe_standard_family_state(
        self, family: DeviceFamily, *, device_type: str, track: int, device: int
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._ctx._resolved_standard_key_indexes(
            family,
            device_type=device_type,
            track=track,
            device=device,
        )
        observed = self._ctx._list_parameters_payload(family, track, device)
        parameters = observed["parameters"]
        state = {key: float(parameters[index]["value"]) for key, index in key_indexes.items()}
        return {
            family.type_arg: parsed_type,
            "track": track,
            "device": device,
            "track_stable_ref": observed["track_stable_ref"],
            "device_stable_ref": observed["device_stable_ref"],
            "key_count": len(state),
            "keys": family.standard_keys(parsed_type),
            "state": state,
        }

    def find_synth_devices(self, track: int | None, synth_type: str | None) -> dict[str, Any]:
        return self._find_family_devices(SYNTH_FAMILY, track, synth_type)

    def list_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._ctx._list_parameters_payload(SYNTH_FAMILY, track, device)

    def set_synth_parameter_safe(
        self, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]:
        return self._set_family_parameter_safe(SYNTH_FAMILY, track, device, parameter, value)

    def observe_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._ctx._list_parameters_payload(SYNTH_FAMILY, track, device)

    def list_standard_synth_keys(self, synth_type: str) -> dict[str, Any]:
        return self._list_standard_family_keys(SYNTH_FAMILY, synth_type)

    def set_standard_synth_parameter_safe(
        self, synth_type: str, track: int, device: int, key: str, value: float
    ) -> dict[str, Any]:
        return self._set_standard_family_parameter_safe(
            SYNTH_FAMILY, device_type=synth_type, track=track, device=device, key=key, value=value
        )

    def observe_standard_synth_state(
        self, synth_type: str, track: int, device: int
    ) -> dict[str, Any]:
        return self._observe_standard_family_state(
            SYNTH_FAMILY, device_type=synth_type, track=track, device=device
        )

    def find_effect_devices(self, track: int | None, effect_type: str | None) -> dict[str, Any]:
        return self._find_family_devices(EFFECT_FAMILY, track, effect_type)

    def list_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._ctx._list_parameters_payload(EFFECT_FAMILY, track, device)

    def set_effect_parameter_safe(
        self, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]:
        return self._set_family_parameter_safe(EFFECT_FAMILY, track, device, parameter, value)

    def observe_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._ctx._list_parameters_payload(EFFECT_FAMILY, track, device)

    def list_standard_effect_keys(self, effect_type: str) -> dict[str, Any]:
        return self._list_standard_family_keys(EFFECT_FAMILY, effect_type)

    def set_standard_effect_parameter_safe(
        self, effect_type: str, track: int, device: int, key: str, value: float
    ) -> dict[str, Any]:
        return self._set_standard_family_parameter_safe(
            EFFECT_FAMILY, device_type=effect_type, track=track, device=device, key=key, value=value
        )

    def observe_standard_effect_state(
        self, effect_type: str, track: int, device: int
    ) -> dict[str, Any]:
        return self._observe_standard_family_state(
            EFFECT_FAMILY, device_type=effect_type, track=track, device=device
        )
