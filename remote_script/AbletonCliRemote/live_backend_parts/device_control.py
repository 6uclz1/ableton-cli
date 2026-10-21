"""Device-level control on regular tracks, for any device type.

``devices.py`` owns the typed synth/effect surfaces (known parameter keys per
device). This module owns operations that work on whatever device sits at a
location: listing parameters with their display strings, choosing enum items
by name, writing values in display units, toggling the device, plug-in
presets, compressor sidechain routing, and inserting/deleting/moving devices.
"""

from __future__ import annotations

from typing import Any

from .base import DeviceLocator, _invalid_argument, _not_supported_by_live_api
from .routing import apply_routing, routing_state

_DEVICE_ON_PARAMETER = "Device On"
_SIDECHAIN_DIRECTION = "input"
_SIDECHAIN_SUBJECT = "device sidechain"
# Upper bound on integer steps probed when detecting a stepped parameter, so a
# wide continuous range never costs hundreds of str_for_value calls.
_MAX_PARAMETER_STEPS = 128


def parameter_display(parameter: Any, value: float) -> str | None:
    str_for_value = getattr(parameter, "str_for_value", None)
    if not callable(str_for_value):
        return None
    return str(str_for_value(value))


def parameter_step_labels(parameter: Any) -> list[str] | None:
    """Labels of a non-quantized parameter whose display snaps to integer steps.

    Live reports parameters such as Beat Repeat Grid or Glue Compressor Ratio
    with ``is_quantized`` False and no ``value_items``, yet each integer raw
    value has its own label ("1/32", "4"). A parameter counts as stepped only
    when all of these hold:

    - ``min`` and ``max`` are integers at most ``_MAX_PARAMETER_STEPS`` apart;
    - every integer raw value in range has a distinct display label;
    - every midpoint ``n + 0.5`` displays the label of ``n`` or ``n + 1``.

    The midpoint rule keeps continuous parameters (Dry/Wet, Volume in dB) out:
    their midpoints display a value of their own.
    """
    if bool(getattr(parameter, "is_quantized", False)):
        return None
    if not callable(getattr(parameter, "str_for_value", None)):
        return None
    try:
        minimum = float(parameter.min)
        maximum = float(parameter.max)
    except (AttributeError, TypeError, ValueError):
        return None
    if not (minimum.is_integer() and maximum.is_integer()):
        return None
    step_count = int(maximum) - int(minimum)
    if step_count < 1 or step_count > _MAX_PARAMETER_STEPS:
        return None
    labels = [
        parameter_display(parameter, float(step)) for step in range(int(minimum), int(maximum) + 1)
    ]
    if len(set(labels)) != len(labels):
        return None
    for offset in range(step_count):
        midpoint = parameter_display(parameter, minimum + offset + 0.5)
        if midpoint not in (labels[offset], labels[offset + 1]):
            return None
    return [str(label) for label in labels]


class LiveBackendDeviceControlMixin:
    # -- parameters ---------------------------------------------------------

    @staticmethod
    def _parameter_value_items(parameter: Any) -> list[str] | None:
        if not bool(getattr(parameter, "is_quantized", False)):
            return None
        items = getattr(parameter, "value_items", None)
        if items is None:
            return None
        return [str(item) for item in list(items)]

    def device_parameters_list(self, track: int, device: DeviceLocator) -> dict[str, Any]:
        target_device = self._ctx._device_at(track, device)
        parameters = []
        for index, parameter in enumerate(list(getattr(target_device, "parameters", []))):
            value = float(getattr(parameter, "value", 0.0))
            parameters.append(
                {
                    "index": index,
                    "stable_ref": self._ctx._parameter_stable_ref_for(
                        parameter, track, device, index
                    ),
                    "name": str(getattr(parameter, "name", f"Parameter {index}")),
                    "value": value,
                    "display": parameter_display(parameter, value),
                    "min": self._ctx._safe_float(getattr(parameter, "min", None)),
                    "max": self._ctx._safe_float(getattr(parameter, "max", None)),
                    "is_enabled": bool(getattr(parameter, "is_enabled", True)),
                    "is_quantized": bool(getattr(parameter, "is_quantized", False)),
                    "value_items": self._parameter_value_items(parameter),
                    "step_labels": parameter_step_labels(parameter),
                }
            )
        return {
            "track": self._ctx._track_field(track),
            "device": device,
            "device_stable_ref": self._ctx._device_stable_ref_for(track, device),
            "device_name": str(getattr(target_device, "name", "")),
            "class_name": str(getattr(target_device, "class_name", "")),
            "parameters": parameters,
        }

    def _require_enabled_parameter(self, parameter: Any, index: int) -> None:
        if not bool(getattr(parameter, "is_enabled", True)):
            raise _invalid_argument(
                message=f"Parameter is disabled at index {index}",
                hint="Choose an enabled parameter from 'device parameters list'.",
            )

    def device_parameter_select(
        self,
        track: int,
        device: DeviceLocator,
        parameter: int,
        item: str,
    ) -> dict[str, Any]:
        target = self._ctx._parameter_at(track, device, parameter)
        self._require_enabled_parameter(target, parameter)
        items = self._parameter_value_items(target)
        if items is None:
            items = parameter_step_labels(target)
        if items is None:
            raise _invalid_argument(
                message=f"Parameter at index {parameter} is not a choice or stepped parameter",
                hint="Use 'device parameter set' or 'device parameter set-display' instead.",
            )
        if item not in items:
            raise _invalid_argument(
                message=f"Unknown item for parameter {parameter}: {item}",
                hint=f"Use one of {items}.",
            )
        before = float(target.value)
        target.value = float(getattr(target, "min", 0.0)) + float(items.index(item))
        after = float(target.value)
        return {
            "track": self._ctx._track_field(track),
            "device": device,
            "parameter": parameter,
            "name": str(getattr(target, "name", "")),
            "item": item,
            "before": before,
            "after": after,
            "display": parameter_display(target, after),
        }

    @staticmethod
    def _display_value_rejected(value: float, parameter: int, exc: Exception) -> Exception:
        return _invalid_argument(
            message=f"Live rejected display value {value} for parameter {parameter}: {exc}",
            hint=(
                "Use 'device parameter select' with a label from step_labels/value_items, "
                "or 'device parameter set' with a raw value."
            ),
        )

    def device_parameter_display_set(
        self,
        track: int,
        device: DeviceLocator,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        target = self._ctx._parameter_at(track, device, parameter)
        self._require_enabled_parameter(target, parameter)
        # Checked on the class: for some parameters (Auto Pan-Tremolo Rate) even
        # reading display_value raises, which an instance hasattr would let escape.
        if not hasattr(type(target), "display_value"):
            raise _not_supported_by_live_api(
                message="DeviceParameter.display_value is not available in Live API",
                hint="Use 'device parameter set' with the raw value instead.",
            )
        before = float(target.value)
        # Live signals "Invalid display value" with a Boost.Python exception type
        # that scripts cannot import, so its calls are guarded broadly. The read
        # comes first: where reading fails (Auto Pan-Tremolo Rate), a write would
        # still clamp the raw value to max before failing, so none is attempted.
        try:
            float(target.display_value)
        except Exception as exc:  # noqa: BLE001
            raise self._display_value_rejected(value, parameter, exc) from exc
        try:
            target.display_value = float(value)
            display_value = float(target.display_value)
        except Exception as exc:  # noqa: BLE001
            raise self._display_value_rejected(value, parameter, exc) from exc
        after = float(target.value)
        return {
            "track": self._ctx._track_field(track),
            "device": device,
            "parameter": parameter,
            "name": str(getattr(target, "name", "")),
            "before": before,
            "after": after,
            "display_value": display_value,
            "display": parameter_display(target, after),
        }

    # -- on/off ---------------------------------------------------------------

    def _device_on_parameter(self, target_device: Any) -> Any:
        for parameter in list(getattr(target_device, "parameters", [])):
            if str(getattr(parameter, "original_name", "") or "") == _DEVICE_ON_PARAMETER:
                return parameter
            if str(getattr(parameter, "name", "")) == _DEVICE_ON_PARAMETER:
                return parameter
        raise _invalid_argument(
            message=f"Device has no '{_DEVICE_ON_PARAMETER}' parameter",
            hint="Inspect the device with 'device parameters list'.",
        )

    def device_active_get(self, track: int, device: DeviceLocator) -> dict[str, Any]:
        target_device = self._ctx._device_at(track, device)
        parameter = self._device_on_parameter(target_device)
        return {
            "track": self._ctx._track_field(track),
            "device": device,
            "name": str(getattr(target_device, "name", "")),
            "active": float(parameter.value) > float(getattr(parameter, "min", 0.0)),
        }

    def device_active_set(self, track: int, device: DeviceLocator, value: bool) -> dict[str, Any]:
        target_device = self._ctx._device_at(track, device)
        parameter = self._device_on_parameter(target_device)
        parameter.value = float(
            getattr(parameter, "max", 1.0) if value else getattr(parameter, "min", 0.0)
        )
        return self.device_active_get(track, device)

    # -- plug-in presets ------------------------------------------------------

    def _require_plugin_device(self, target_device: Any) -> list[str]:
        if not hasattr(target_device, "presets") or not hasattr(
            target_device, "selected_preset_index"
        ):
            raise _invalid_argument(
                message="Device is not a plug-in device with presets",
                hint="Target a VST/AU plug-in (class_name 'PluginDevice' or 'AuPluginDevice').",
            )
        return [str(name) for name in list(target_device.presets)]

    def _preset_payload(
        self, track: int, device: DeviceLocator, target_device: Any, presets: list[str]
    ) -> dict[str, Any]:
        selected = int(target_device.selected_preset_index)
        return {
            "track": self._ctx._track_field(track),
            "device": device,
            "name": str(getattr(target_device, "name", "")),
            "presets": [{"index": index, "name": name} for index, name in enumerate(presets)],
            "selected_preset_index": selected,
            "selected_preset": presets[selected] if 0 <= selected < len(presets) else None,
        }

    def device_preset_list(self, track: int, device: DeviceLocator) -> dict[str, Any]:
        target_device = self._ctx._device_at(track, device)
        presets = self._require_plugin_device(target_device)
        return self._preset_payload(track, device, target_device, presets)

    def device_preset_set(
        self, track: int, device: DeviceLocator, preset_index: int
    ) -> dict[str, Any]:
        target_device = self._ctx._device_at(track, device)
        presets = self._require_plugin_device(target_device)
        if preset_index < 0 or preset_index >= len(presets):
            raise _invalid_argument(
                message=f"preset_index out of range: {preset_index}",
                hint=(
                    f"Use a preset_index in 0..{max(len(presets) - 1, 0)} "
                    "(see 'device preset list')."
                ),
            )
        target_device.selected_preset_index = int(preset_index)
        return self._preset_payload(track, device, target_device, presets)

    # -- sidechain ------------------------------------------------------------

    def _require_sidechain_device(self, target_device: Any) -> Any:
        if not hasattr(target_device, f"available_{_SIDECHAIN_DIRECTION}_routing_types"):
            raise _invalid_argument(
                message="Device does not expose sidechain routing",
                hint=(
                    "Live exposes sidechain routing to scripts for Compressor only; "
                    "target a Compressor device."
                ),
            )
        return target_device

    def _sidechain_payload(
        self, track: int, device: DeviceLocator, target_device: Any
    ) -> dict[str, Any]:
        return {
            "track": self._ctx._track_field(track),
            "device": device,
            "name": str(getattr(target_device, "name", "")),
            **routing_state(target_device, _SIDECHAIN_DIRECTION, subject=_SIDECHAIN_SUBJECT),
        }

    def device_sidechain_get(self, track: int, device: DeviceLocator) -> dict[str, Any]:
        target_device = self._require_sidechain_device(self._ctx._device_at(track, device))
        return self._sidechain_payload(track, device, target_device)

    def device_sidechain_set(
        self,
        track: int,
        device: DeviceLocator,
        routing_type: str,
        routing_channel: str | None,
    ) -> dict[str, Any]:
        target_device = self._require_sidechain_device(self._ctx._device_at(track, device))
        apply_routing(
            target_device,
            _SIDECHAIN_DIRECTION,
            subject=_SIDECHAIN_SUBJECT,
            routing_type=routing_type,
            routing_channel=routing_channel,
        )
        return self._sidechain_payload(track, device, target_device)

    # -- insert / delete / move ----------------------------------------------

    @staticmethod
    def _require_top_level_device(device: DeviceLocator) -> int:
        if not isinstance(device, int):
            raise _invalid_argument(
                message="Chain-nested devices cannot be targeted by this command",
                hint="Target a top-level track device (from 'track info').",
            )
        return device

    def device_insert(self, track: int, device_name: str, index: int) -> dict[str, Any]:
        target_track = self._ctx._track_at(track)
        insert_device = getattr(target_track, "insert_device", None)
        if not callable(insert_device):
            raise _not_supported_by_live_api(
                message="Track.insert_device is not available in Live API",
                hint="Use Live 12.3 or later, or load the device with 'browser load'.",
            )
        device_count = len(list(target_track.devices))
        if index != -1 and (index < 0 or index > device_count):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint=f"Use -1 to append or an insertion index in 0..{device_count}.",
            )
        before = list(target_track.devices)
        if index == -1:
            insert_device(device_name)
        else:
            insert_device(device_name, index)
        devices = list(target_track.devices)
        # Live may reorder (an instrument always precedes audio effects), so
        # locate the new device instead of trusting the requested index.
        added = [
            position
            for position, candidate in enumerate(devices)
            if not any(candidate == existing for existing in before)
        ]
        if len(added) != 1:
            raise _invalid_argument(
                message=f"Live did not insert exactly one device for {device_name!r}",
                hint="Use the exact device name shown in Live's browser (e.g. 'Compressor').",
            )
        inserted_index = added[0]
        inserted = devices[inserted_index]
        return {
            "track": self._ctx._track_field(track),
            "device": inserted_index,
            "name": str(getattr(inserted, "name", "")),
            "device_stable_ref": self._ctx._device_stable_ref_for(track, inserted_index),
            "device_count": len(devices),
        }

    def device_delete(self, track: int, device: DeviceLocator) -> dict[str, Any]:
        device_index = self._require_top_level_device(device)
        target_track = self._ctx._track_at(track)
        target_device = self._ctx._device_at(track, device_index)
        delete_device = getattr(target_track, "delete_device", None)
        if not callable(delete_device):
            raise _not_supported_by_live_api(
                message="Track.delete_device is not available in Live API",
                hint="Delete the device manually in Ableton Live.",
            )
        name = str(getattr(target_device, "name", ""))
        delete_device(device_index)
        return {
            "track": self._ctx._track_field(track),
            "device": device_index,
            "name": name,
            "device_count": len(list(target_track.devices)),
        }

    def device_move(self, track: int, device: DeviceLocator, to_index: int) -> dict[str, Any]:
        device_index = self._require_top_level_device(device)
        target_track = self._ctx._track_at(track)
        target_device = self._ctx._device_at(track, device_index)
        device_count = len(list(target_track.devices))
        if to_index < 0 or to_index >= device_count:
            raise _invalid_argument(
                message=f"to_index out of range: {to_index}",
                hint=f"Use a destination index in 0..{device_count - 1}.",
            )
        move_device = getattr(self._ctx._song(), "move_device", None)
        if not callable(move_device):
            raise _not_supported_by_live_api(
                message="Song.move_device is not available in Live API",
                hint="Move the device manually in Ableton Live.",
            )
        move_device(target_device, target_track, to_index)
        return {
            "track": self._ctx._track_field(track),
            "device": device_index,
            "to_index": to_index,
            "name": str(getattr(target_device, "name", "")),
        }
