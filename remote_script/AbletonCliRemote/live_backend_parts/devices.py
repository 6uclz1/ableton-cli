from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ..effect_specs import (
    SUPPORTED_EFFECT_TYPES,
    canonicalize_effect_type,
    standard_effect_keys,
)
from ..synth_specs import SUPPORTED_SYNTH_TYPES, canonicalize_synth_type, standard_synth_keys
from .base import _invalid_argument


class LiveBackendDeviceSharedMixin:
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
