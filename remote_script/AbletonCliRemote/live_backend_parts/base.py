from __future__ import annotations

from typing import Any

from ..command_backend import PROTOCOL_VERSION, REMOTE_SCRIPT_VERSION, CommandError
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
    return CommandError(code="INVALID_ARGUMENT", message=message, hint=hint)


def _not_supported_by_live_api(message: str, hint: str) -> CommandError:
    return CommandError(
        code="INVALID_ARGUMENT",
        message=message,
        hint=hint,
        details={"reason": "not_supported_by_live_api"},
    )


class LiveBackendBaseMixin:
    _control_surface: Any

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

    def _safe_float(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _serialize_parameter(self, parameter: Any, index: int) -> dict[str, Any]:
        minimum = self._safe_float(getattr(parameter, "min", None))
        maximum = self._safe_float(getattr(parameter, "max", None))
        return {
            "index": index,
            "name": str(getattr(parameter, "name", f"Parameter {index}")),
            "value": float(getattr(parameter, "value", 0.0)),
            "min": minimum,
            "max": maximum,
            "is_enabled": bool(getattr(parameter, "is_enabled", True)),
            "is_quantized": bool(getattr(parameter, "is_quantized", False)),
        }

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
            self._serialize_parameter(parameter, index)
            for index, parameter in enumerate(list(getattr(target_device, "parameters", [])))
        ]
        return {
            "track": track,
            "device": device,
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
            self._serialize_parameter(parameter, index)
            for index, parameter in enumerate(list(getattr(target_device, "parameters", [])))
        ]
        return {
            "track": track,
            "device": device,
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
            if "audio_effect" in class_name:
                return "audio_effect"
            if "midi_effect" in class_name:
                return "midi_effect"
            return "unknown"
        except Exception:  # noqa: BLE001
            return "unknown"
