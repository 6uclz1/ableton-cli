"""Device commands dispatched with the main-track selector act on main-track devices."""

from __future__ import annotations

from typing import Any

import pytest
from test_live_backend import _SurfaceStub
from test_live_backend_device_control import _BeatRepeatDevice, _CompressorDevice, _EditableTrack

from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command
from remote_script.AbletonCliRemote.live_backend import LiveBackend

_MAIN = {"mode": "main"}
_DEVICE_0 = {"mode": "index", "index": 0}
_MAIN_LOCATOR = {"kind": "main"}


def _backend() -> tuple[LiveBackend, _CompressorDevice, _EditableTrack]:
    backend = LiveBackend(_SurfaceStub())
    compressor = _CompressorDevice()
    main = _EditableTrack(name="Main", has_audio_input=False, has_midi_input=False)
    main.devices = [compressor, _BeatRepeatDevice()]
    backend.context._song().master_track = main
    return backend, compressor, main


def test_parameters_list_reads_the_main_track_device() -> None:
    backend, _, _ = _backend()

    result = dispatch_command(
        backend, "device_parameters_list", {"track_ref": _MAIN, "device_ref": _DEVICE_0}
    )

    assert result["track"] == _MAIN_LOCATOR
    assert result["device_name"] == "Compressor"
    assert result["parameters"][1]["display"] == "-30.0 dB"


def test_display_set_and_select_by_name_write_the_main_track_device() -> None:
    backend, compressor, main = _backend()

    display = dispatch_command(
        backend,
        "device_parameter_display_set",
        {
            "track_ref": _MAIN,
            "device_ref": {"mode": "name", "name": "Compressor"},
            "parameter_ref": {"mode": "name", "name": "Threshold"},
            "value": -12.0,
        },
    )
    selected = dispatch_command(
        backend,
        "device_parameter_select",
        {
            "track_ref": _MAIN,
            "device_ref": {"mode": "name", "name": "Beat Repeat"},
            "parameter_ref": {"mode": "name", "name": "Grid"},
            "item": "1/32",
        },
    )

    assert compressor.parameters[1].value == pytest.approx(0.2)
    assert display["track"] == _MAIN_LOCATOR
    assert main.devices[1].parameters[1].value == 6.0
    assert selected["track"] == _MAIN_LOCATOR


def test_raw_parameter_set_reports_the_main_track() -> None:
    backend, compressor, _ = _backend()

    result = dispatch_command(
        backend,
        "set_device_parameter",
        {
            "track_ref": _MAIN,
            "device_ref": _DEVICE_0,
            "parameter_ref": {"mode": "index", "index": 1},
            "value": 0.25,
        },
    )

    assert compressor.parameters[1].value == 0.25
    assert result["track"] == _MAIN_LOCATOR
    assert result["display"] == "-15.0 dB"


def test_insert_delete_and_move_on_the_main_track() -> None:
    backend, _, main = _backend()
    song = backend.context._song()

    def move_device(device: Any, target: Any, target_position: int) -> None:
        target.devices.remove(device)
        target.devices.insert(target_position, device)

    song.move_device = move_device

    inserted = dispatch_command(
        backend, "device_insert", {"track_ref": _MAIN, "device_name": "Limiter", "index": -1}
    )
    moved = dispatch_command(
        backend,
        "device_move",
        {"track_ref": _MAIN, "device_ref": {"mode": "index", "index": 2}, "to_index": 0},
    )
    deleted = dispatch_command(
        backend, "device_delete", {"track_ref": _MAIN, "device_ref": {"mode": "index", "index": 1}}
    )

    assert inserted["track"] == _MAIN_LOCATOR
    assert moved["track"] == _MAIN_LOCATOR
    assert deleted["name"] == "Compressor"
    assert [device.name for device in main.devices] == ["Limiter", "Beat Repeat"]


def test_main_device_stable_ref_matches_master_effect_listing() -> None:
    backend, compressor, _ = _backend()
    listing = dispatch_command(
        backend, "device_parameters_list", {"track_ref": _MAIN, "device_ref": _DEVICE_0}
    )

    dispatch_command(
        backend,
        "device_parameter_display_set",
        {
            "track_ref": _MAIN,
            "device_ref": {"mode": "stable_ref", "stable_ref": listing["device_stable_ref"]},
            "parameter_ref": {
                "mode": "stable_ref",
                "stable_ref": listing["parameters"][1]["stable_ref"],
            },
            "value": -30.0,
        },
    )

    assert compressor.parameters[1].value == pytest.approx(0.5)
    assert listing["device_stable_ref"] == backend.services.devices._master_device_stable_ref(
        compressor, device_index=0
    )


def test_main_selector_rejects_extra_fields() -> None:
    backend, _, _ = _backend()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "device_parameters_list",
            {"track_ref": {"mode": "main", "index": 0}, "device_ref": _DEVICE_0},
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_track_commands_outside_the_device_group_reject_the_main_selector() -> None:
    backend, _, _ = _backend()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "track_volume_get", {"track_ref": _MAIN})

    assert exc_info.value.code == "INVALID_ARGUMENT"
