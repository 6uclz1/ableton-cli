"""Device commands dispatched with a return-track selector act on return-track devices."""

from __future__ import annotations

import pytest
from test_live_backend import _Device, _Parameter, _SurfaceStub
from test_live_backend_device_control import _CompressorDevice, _EditableTrack

from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command
from remote_script.AbletonCliRemote.live_backend import LiveBackend

_RETURN_1 = {"mode": "return_index", "index": 1}
_DEVICE_0 = {"mode": "index", "index": 0}
_RETURN_LOCATOR = {"kind": "return", "index": 1}


def _backend() -> tuple[LiveBackend, _CompressorDevice, _EditableTrack]:
    backend = LiveBackend(_SurfaceStub())
    compressor = _CompressorDevice()
    delay = _EditableTrack(name="Delay", has_audio_input=False, has_midi_input=False)
    delay.devices = [compressor]
    backend.context._song().return_tracks[1] = delay
    return backend, compressor, delay


def test_parameters_list_reads_the_return_track_device() -> None:
    backend, _, _ = _backend()

    result = dispatch_command(
        backend, "device_parameters_list", {"track_ref": _RETURN_1, "device_ref": _DEVICE_0}
    )

    assert result["track"] == _RETURN_LOCATOR
    assert result["device_name"] == "Compressor"
    assert result["parameters"][1]["name"] == "Threshold"


def test_display_set_and_select_write_the_return_track_device() -> None:
    backend, compressor, _ = _backend()

    dispatch_command(
        backend,
        "device_parameter_display_set",
        {
            "track_ref": _RETURN_1,
            "device_ref": _DEVICE_0,
            "parameter_ref": {"mode": "name", "name": "Threshold"},
            "value": -12.0,
        },
    )
    selected = dispatch_command(
        backend,
        "device_parameter_select",
        {
            "track_ref": _RETURN_1,
            "device_ref": _DEVICE_0,
            "parameter_ref": {"mode": "name", "name": "Model"},
            "item": "RMS",
        },
    )

    assert compressor.parameters[1].value == pytest.approx(0.2)
    assert compressor.parameters[2].value == 1.0
    assert selected["track"] == _RETURN_LOCATOR


def test_raw_parameter_set_reports_the_return_track() -> None:
    backend, compressor, _ = _backend()

    result = dispatch_command(
        backend,
        "set_device_parameter",
        {
            "track_ref": _RETURN_1,
            "device_ref": _DEVICE_0,
            "parameter_ref": {"mode": "index", "index": 1},
            "value": 0.25,
        },
    )

    assert compressor.parameters[1].value == 0.25
    assert result["track"] == _RETURN_LOCATOR
    assert result["track_stable_ref"].startswith("track:")


def test_insert_adds_a_device_to_the_return_track() -> None:
    backend, _, delay = _backend()

    result = dispatch_command(
        backend,
        "device_insert",
        {"track_ref": _RETURN_1, "device_name": "Hybrid Reverb", "index": -1},
    )

    assert [device.name for device in delay.devices] == ["Compressor", "Hybrid Reverb"]
    assert result["track"] == _RETURN_LOCATOR
    assert result["device"] == 1


def test_return_name_selector_resolves_by_name() -> None:
    backend, _, _ = _backend()

    result = dispatch_command(
        backend,
        "device_active_get",
        {"track_ref": {"mode": "return_name", "name": "Delay"}, "device_ref": _DEVICE_0},
    )

    assert result["track"] == _RETURN_LOCATOR


def test_device_stable_ref_from_a_return_track_round_trips() -> None:
    backend, compressor, _ = _backend()
    listing = dispatch_command(
        backend, "device_parameters_list", {"track_ref": _RETURN_1, "device_ref": _DEVICE_0}
    )

    dispatch_command(
        backend,
        "device_parameter_display_set",
        {
            "track_ref": _RETURN_1,
            "device_ref": {"mode": "stable_ref", "stable_ref": listing["device_stable_ref"]},
            "parameter_ref": {
                "mode": "stable_ref",
                "stable_ref": listing["parameters"][1]["stable_ref"],
            },
            "value": -30.0,
        },
    )

    assert compressor.parameters[1].value == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("track_ref", "message"),
    [
        ({"mode": "return_index", "index": 5}, "return_track out of range"),
        ({"mode": "return_name", "name": "Nope"}, "did not match"),
    ],
)
def test_unknown_return_track_fails_explicitly(track_ref, message) -> None:
    backend, _, _ = _backend()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend, "device_parameters_list", {"track_ref": track_ref, "device_ref": _DEVICE_0}
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert message in exc_info.value.message


def test_track_commands_outside_the_device_group_reject_return_selectors() -> None:
    backend, _, _ = _backend()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "track_volume_get", {"track_ref": _RETURN_1})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_regular_track_results_keep_integer_track() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).devices = [
        _Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)])
    ]

    result = dispatch_command(
        backend,
        "device_parameters_list",
        {"track_ref": {"mode": "index", "index": 0}, "device_ref": _DEVICE_0},
    )

    assert result["track"] == 0


def test_return_track_stable_ref_selects_the_return_track() -> None:
    backend, _, _ = _backend()
    first = dispatch_command(
        backend,
        "set_device_parameter",
        {
            "track_ref": _RETURN_1,
            "device_ref": _DEVICE_0,
            "parameter_ref": {"mode": "index", "index": 1},
            "value": 0.25,
        },
    )

    result = dispatch_command(
        backend,
        "device_active_get",
        {
            "track_ref": {"mode": "stable_ref", "stable_ref": first["track_stable_ref"]},
            "device_ref": _DEVICE_0,
        },
    )

    assert result["track"] == _RETURN_LOCATOR
