from __future__ import annotations

from typing import Any

import pytest
from test_live_backend import _Device, _Parameter, _SurfaceStub, _Track

from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command
from remote_script.AbletonCliRemote.live_backend import LiveBackend


class _RichParameter:
    """A DeviceParameter exposing the display helpers Live 12 provides."""

    def __init__(
        self,
        name: str,
        value: float,
        *,
        min: float = 0.0,  # noqa: A002
        max: float = 1.0,  # noqa: A002
        is_quantized: bool = False,
        value_items: list[str] | None = None,
        unit: str = "",
        display_scale: float = 1.0,
    ) -> None:
        self.name = name
        self.original_name = name
        self.value = value
        self.min = min
        self.max = max
        self.is_enabled = True
        self.is_quantized = is_quantized
        self.value_items = value_items or []
        self.default_value = min
        self._unit = unit
        self._display_scale = display_scale

    def str_for_value(self, value: float) -> str:
        if self.is_quantized:
            return self.value_items[int(value)]
        return f"{value * self._display_scale:.1f} {self._unit}".strip()

    @property
    def display_value(self) -> float:
        return self.value * self._display_scale

    @display_value.setter
    def display_value(self, value: float) -> None:
        self.value = value / self._display_scale


class _LiveArgumentError(Exception):
    """Stands in for the Boost.Python exception Live raises; it is not a RuntimeError."""


class _SteppedParameter:
    """A non-quantized parameter whose display snaps to labelled integer steps.

    Live reports Beat Repeat Grid or Glue Compressor Ratio this way:
    ``is_quantized`` is False and ``value_items`` is empty, but every integer
    raw value has its own label and values in between snap to a neighbour.
    For some of them (Auto Pan-Tremolo Rate) reading ``display_value`` raises
    "Invalid display value", while writing it silently clamps the raw value to
    ``max``, so a write must never be attempted for them.
    """

    def __init__(self, name: str, labels: list[str], value: float = 0.0) -> None:
        self.name = name
        self.original_name = name
        self.value = value
        self.min = 0.0
        self.max = float(len(labels) - 1)
        self.is_enabled = True
        self.is_quantized = False
        self.value_items: list[str] = []
        self._labels = labels

    def str_for_value(self, value: float) -> str:
        return self._labels[int(round(value))]

    @property
    def display_value(self) -> float:
        raise _LiveArgumentError("Invalid display value")

    @display_value.setter
    def display_value(self, value: float) -> None:
        self.value = self.max


_GRID_LABELS = ["1/4", "1/6", "1/8", "1/12", "1/16", "1/24", "1/32"]


class _BeatRepeatDevice:
    def __init__(self) -> None:
        self.name = "Beat Repeat"
        self.class_name = "BeatRepeat"
        self.class_display_name = "Beat Repeat"
        self.can_have_chains = False
        self.can_have_drum_pads = False
        self.parameters = [
            _RichParameter("Device On", 1.0, is_quantized=True, value_items=["Off", "On"]),
            _SteppedParameter("Grid", _GRID_LABELS, value=2.0),
            _RichParameter("Dry/Wet", 0.5, unit="%", display_scale=100.0),
            _RichParameter("Volume", 0.0, max=36.0, unit="dB"),
        ]


class _RoutingTarget:
    def __init__(self, display_name: str) -> None:
        self.display_name = display_name


class _CompressorDevice:
    def __init__(self) -> None:
        self.name = "Compressor"
        self.class_name = "Compressor2"
        self.class_display_name = "Compressor"
        self.can_have_chains = False
        self.can_have_drum_pads = False
        self.parameters = [
            _RichParameter("Device On", 1.0, is_quantized=True, value_items=["Off", "On"]),
            _RichParameter("Threshold", 0.5, unit="dB", display_scale=-60.0),
            _RichParameter(
                "Model", 0.0, max=2.0, is_quantized=True, value_items=["Peak", "RMS", "Expand"]
            ),
        ]
        self._types = [_RoutingTarget("No Input"), _RoutingTarget("1-Kick")]
        self._channels_by_type = {
            "No Input": [_RoutingTarget("")],
            "1-Kick": [_RoutingTarget("Pre FX"), _RoutingTarget("Post FX")],
        }
        self.input_routing_type = self._types[0]
        self.input_routing_channel = self._channels_by_type["No Input"][0]

    @property
    def available_input_routing_types(self) -> list[_RoutingTarget]:
        return list(self._types)

    @property
    def available_input_routing_channels(self) -> list[_RoutingTarget]:
        return list(self._channels_by_type[self.input_routing_type.display_name])


class _PluginDevice:
    def __init__(self) -> None:
        self.name = "Auto-Tune"
        self.class_name = "PluginDevice"
        self.class_display_name = "VST3"
        self.can_have_chains = False
        self.can_have_drum_pads = False
        self.parameters = [_RichParameter("Device On", 1.0, is_quantized=True)]
        self.presets = ["Init", "Hard Tune", "Natural"]
        self.selected_preset_index = 0


class _EditableTrack(_Track):
    """A track exposing the device insertion/deletion API (Live 12.3+)."""

    def insert_device(self, device_name: str, target_index: int | None = None) -> None:
        device = _Device(device_name, "AudioEffect", [_Parameter("Device On", 1.0)])
        if target_index is None:
            self.devices.append(device)
            return
        self.devices.insert(target_index, device)

    def delete_device(self, index: int) -> None:
        del self.devices[index]


def _backend_with_devices(*devices: Any) -> LiveBackend:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).devices = list(devices)
    return backend


def _backend_with_editable_track() -> tuple[LiveBackend, _EditableTrack]:
    backend = LiveBackend(_SurfaceStub())
    track = _EditableTrack(name="Vox", has_audio_input=True, has_midi_input=False)
    track.devices = [_Device("EQ Eight", "Eq8", [_Parameter("Device On", 1.0)])]
    backend.context._song().tracks[0] = track
    return backend, track


def test_device_parameters_list_reports_display_strings_and_items() -> None:
    backend = _backend_with_devices(_CompressorDevice())

    result = backend.device_parameters_list(0, 0)

    assert result["device_name"] == "Compressor"
    assert result["class_name"] == "Compressor2"
    threshold = result["parameters"][1]
    assert threshold["name"] == "Threshold"
    assert threshold["display"] == "-30.0 dB"
    assert threshold["value_items"] is None
    model = result["parameters"][2]
    assert model["value_items"] == ["Peak", "RMS", "Expand"]
    assert model["display"] == "Peak"
    assert model["stable_ref"].startswith("parameter:")


def test_device_parameters_list_reports_null_display_without_str_for_value() -> None:
    backend = _backend_with_devices(_Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)]))

    result = backend.device_parameters_list(0, 0)

    assert result["parameters"][0]["display"] is None


def test_device_parameter_select_sets_quantized_item_by_name() -> None:
    compressor = _CompressorDevice()
    backend = _backend_with_devices(compressor)

    result = backend.device_parameter_select(0, 0, 2, "RMS")

    assert compressor.parameters[2].value == 1.0
    assert result["item"] == "RMS"
    assert result["before"] == 0.0
    assert result["after"] == 1.0
    assert result["display"] == "RMS"


def test_device_parameter_select_rejects_unknown_item() -> None:
    backend = _backend_with_devices(_CompressorDevice())

    with pytest.raises(CommandError) as exc_info:
        backend.device_parameter_select(0, 0, 2, "Opto")

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert "Peak" in exc_info.value.hint


def test_device_parameter_select_rejects_continuous_parameter() -> None:
    backend = _backend_with_devices(_CompressorDevice())

    with pytest.raises(CommandError) as exc_info:
        backend.device_parameter_select(0, 0, 1, "RMS")

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_parameter_display_set_writes_display_value() -> None:
    compressor = _CompressorDevice()
    backend = _backend_with_devices(compressor)

    result = backend.device_parameter_display_set(0, 0, 1, -12.0)

    assert compressor.parameters[1].value == pytest.approx(0.2)
    assert result["display_value"] == pytest.approx(-12.0)
    assert result["display"] == "-12.0 dB"


def test_device_parameter_display_set_not_supported_without_display_value() -> None:
    backend = _backend_with_devices(_Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)]))

    with pytest.raises(CommandError) as exc_info:
        backend.device_parameter_display_set(0, 0, 0, -3.0)

    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


def test_device_parameters_list_reports_step_labels_for_stepped_parameter() -> None:
    backend = _backend_with_devices(_BeatRepeatDevice())

    parameters = backend.device_parameters_list(0, 0)["parameters"]

    grid = parameters[1]
    assert grid["is_quantized"] is False
    assert grid["value_items"] is None
    assert grid["step_labels"] == _GRID_LABELS


def test_device_parameters_list_keeps_continuous_parameters_unstepped() -> None:
    backend = _backend_with_devices(_BeatRepeatDevice())

    parameters = backend.device_parameters_list(0, 0)["parameters"]

    assert parameters[2]["name"] == "Dry/Wet"
    assert parameters[2]["step_labels"] is None
    # Integer bounds alone are not enough: midpoints carry their own label.
    assert parameters[3]["name"] == "Volume"
    assert parameters[3]["step_labels"] is None
    # Quantized parameters keep reporting value_items only.
    assert parameters[0]["step_labels"] is None


def test_device_parameter_select_accepts_step_label() -> None:
    beat_repeat = _BeatRepeatDevice()
    backend = _backend_with_devices(beat_repeat)

    result = backend.device_parameter_select(0, 0, 1, "1/32")

    assert beat_repeat.parameters[1].value == 6.0
    assert result["item"] == "1/32"
    assert result["display"] == "1/32"


def test_device_parameter_select_rejects_unknown_step_label() -> None:
    backend = _backend_with_devices(_BeatRepeatDevice())

    with pytest.raises(CommandError) as exc_info:
        backend.device_parameter_select(0, 0, 1, "1/64")

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert "1/32" in exc_info.value.hint


def test_device_parameter_display_set_maps_live_rejection_to_invalid_argument() -> None:
    beat_repeat = _BeatRepeatDevice()
    backend = _backend_with_devices(beat_repeat)

    with pytest.raises(CommandError) as exc_info:
        backend.device_parameter_display_set(0, 0, 1, 4.0)

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert "device parameter select" in exc_info.value.hint
    assert beat_repeat.parameters[1].value == 2.0


def test_set_device_parameter_reports_display() -> None:
    backend = _backend_with_devices(_BeatRepeatDevice())

    result = backend.set_device_parameter(0, 0, 1, 4.0)

    assert result["value"] == 4.0
    assert result["display"] == "1/16"


def test_device_active_set_toggles_device_on_parameter() -> None:
    compressor = _CompressorDevice()
    backend = _backend_with_devices(compressor)

    result = backend.device_active_set(0, 0, False)

    assert compressor.parameters[0].value == 0.0
    assert result == {"track": 0, "device": 0, "name": "Compressor", "active": False}
    assert backend.device_active_get(0, 0)["active"] is False


def test_device_active_requires_device_on_parameter() -> None:
    backend = _backend_with_devices(_Device("Odd", "AudioEffect", [_Parameter("Gain", 0.0)]))

    with pytest.raises(CommandError) as exc_info:
        backend.device_active_get(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_preset_list_and_set_on_plugin() -> None:
    plugin = _PluginDevice()
    backend = _backend_with_devices(plugin)

    listed = backend.device_preset_list(0, 0)
    selected = backend.device_preset_set(0, 0, 1)

    assert listed["presets"] == [
        {"index": 0, "name": "Init"},
        {"index": 1, "name": "Hard Tune"},
        {"index": 2, "name": "Natural"},
    ]
    assert listed["selected_preset_index"] == 0
    assert plugin.selected_preset_index == 1
    assert selected["selected_preset"] == "Hard Tune"


def test_device_preset_set_rejects_out_of_range_index() -> None:
    backend = _backend_with_devices(_PluginDevice())

    with pytest.raises(CommandError) as exc_info:
        backend.device_preset_set(0, 0, 3)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_preset_list_rejects_native_device() -> None:
    backend = _backend_with_devices(_CompressorDevice())

    with pytest.raises(CommandError) as exc_info:
        backend.device_preset_list(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert "plug-in" in exc_info.value.message


def test_device_sidechain_get_reports_current_and_available() -> None:
    backend = _backend_with_devices(_CompressorDevice())

    result = backend.device_sidechain_get(0, 0)

    assert result["current"] == {"type": "No Input", "channel": ""}
    assert result["available"]["types"] == ["No Input", "1-Kick"]


def test_device_sidechain_set_routes_compressor_to_source_track() -> None:
    compressor = _CompressorDevice()
    backend = _backend_with_devices(compressor)

    result = backend.device_sidechain_set(0, 0, "1-Kick", "Post FX")

    assert compressor.input_routing_type.display_name == "1-Kick"
    assert compressor.input_routing_channel.display_name == "Post FX"
    assert result["current"] == {"type": "1-Kick", "channel": "Post FX"}
    assert result["available"]["channels"] == ["Pre FX", "Post FX"]


def test_device_sidechain_set_rejects_unknown_source() -> None:
    backend = _backend_with_devices(_CompressorDevice())

    with pytest.raises(CommandError) as exc_info:
        backend.device_sidechain_set(0, 0, "9-Snare", None)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_sidechain_rejects_device_without_sidechain_routing() -> None:
    backend = _backend_with_devices(_PluginDevice())

    with pytest.raises(CommandError) as exc_info:
        backend.device_sidechain_get(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert "Compressor" in exc_info.value.hint


def test_device_insert_appends_native_device_by_name() -> None:
    backend, track = _backend_with_editable_track()

    result = backend.device_insert(0, "Compressor", -1)

    assert [device.name for device in track.devices] == ["EQ Eight", "Compressor"]
    assert result["device"] == 1
    assert result["name"] == "Compressor"
    assert result["device_count"] == 2


def test_device_insert_at_index() -> None:
    backend, track = _backend_with_editable_track()

    result = backend.device_insert(0, "Auto Shift", 0)

    assert [device.name for device in track.devices] == ["Auto Shift", "EQ Eight"]
    assert result["device"] == 0


def test_device_insert_rejects_out_of_range_index() -> None:
    backend, _ = _backend_with_editable_track()

    with pytest.raises(CommandError) as exc_info:
        backend.device_insert(0, "Compressor", 5)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_insert_not_supported_before_live_12_3() -> None:
    backend = LiveBackend(_SurfaceStub())

    with pytest.raises(CommandError) as exc_info:
        backend.device_insert(0, "Compressor", -1)

    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}
    assert "12.3" in exc_info.value.hint


def test_device_delete_removes_top_level_device() -> None:
    backend, track = _backend_with_editable_track()

    result = backend.device_delete(0, 0)

    assert track.devices == []
    assert result == {"track": 0, "device": 0, "name": "EQ Eight", "device_count": 0}


def test_device_delete_rejects_chain_nested_device() -> None:
    backend, _ = _backend_with_editable_track()

    with pytest.raises(CommandError) as exc_info:
        backend.device_delete(0, (0, 0, 0))

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_move_uses_song_move_device() -> None:
    backend = LiveBackend(_SurfaceStub())
    song = backend.context._song()
    track = song.tracks[0]
    first = _Device("A", "AudioEffect", [])
    second = _Device("B", "AudioEffect", [])
    track.devices = [first, second]
    calls: list[tuple[Any, Any, int]] = []

    def move_device(device: Any, target: Any, target_position: int) -> None:
        calls.append((device, target, target_position))
        target.devices.remove(device)
        target.devices.insert(target_position, device)

    song.move_device = move_device

    result = backend.device_move(0, 0, 1)

    assert calls == [(first, track, 1)]
    assert [device.name for device in track.devices] == ["B", "A"]
    assert result == {"track": 0, "device": 0, "to_index": 1, "name": "A"}


def test_device_move_not_supported_without_song_move_device() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).devices = [
        _Device("A", "AudioEffect", []),
        _Device("B", "AudioEffect", []),
    ]

    with pytest.raises(CommandError) as exc_info:
        backend.device_move(0, 0, 1)

    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


_TRACK_0 = {"mode": "index", "index": 0}
_DEVICE_0 = {"mode": "index", "index": 0}


def test_dispatch_device_sidechain_set_end_to_end() -> None:
    compressor = _CompressorDevice()
    backend = _backend_with_devices(compressor)

    result = dispatch_command(
        backend,
        "device_sidechain_set",
        {
            "track_ref": _TRACK_0,
            "device_ref": _DEVICE_0,
            "routing_type": "1-Kick",
            "routing_channel": None,
        },
    )

    assert result["current"]["type"] == "1-Kick"


def test_dispatch_device_parameter_select_by_parameter_name() -> None:
    compressor = _CompressorDevice()
    backend = _backend_with_devices(compressor)

    result = dispatch_command(
        backend,
        "device_parameter_select",
        {
            "track_ref": _TRACK_0,
            "device_ref": _DEVICE_0,
            "parameter_ref": {"mode": "name", "name": "Model"},
            "item": "Expand",
        },
    )

    assert result["parameter"] == 2
    assert compressor.parameters[2].value == 2.0


def test_dispatch_device_insert_rejects_empty_name() -> None:
    backend, _ = _backend_with_editable_track()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend, "device_insert", {"track_ref": _TRACK_0, "device_name": " ", "index": -1}
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_device_active_set_requires_boolean() -> None:
    backend = _backend_with_devices(_CompressorDevice())

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "device_active_set",
            {"track_ref": _TRACK_0, "device_ref": _DEVICE_0, "value": "off"},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"
