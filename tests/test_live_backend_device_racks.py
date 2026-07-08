from __future__ import annotations

import pytest
from test_live_backend import _Chain, _Device, _Parameter, _SurfaceStub

from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command
from remote_script.AbletonCliRemote.live_backend import LiveBackend


def _rack_device(*, macros: int = 2, chains: list[_Chain] | None = None) -> _Device:
    parameters = [_Parameter("Chain Selector", 0.0)]
    parameters.extend(
        _Parameter(f"Macro {index + 1}", 0.0, min=0.0, max=127.0) for index in range(macros)
    )
    return _Device(
        "Rack",
        "InstrumentGroupDevice",
        parameters,
        can_have_chains=True,
        chains=chains or [],
    )


def _backend_with_rack(rack: _Device) -> LiveBackend:
    backend = LiveBackend(_SurfaceStub())
    backend._track_at(0).devices = [rack]
    return backend


def test_device_chains_list_returns_nested_devices_with_stable_refs() -> None:
    inner_device_a = _Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)])
    inner_device_b = _Device("EQ Eight", "AudioEffect", [_Parameter("Gain", 0.0)])
    chain_one = _Chain("Chain 1", devices=[inner_device_a])
    chain_two = _Chain("Chain 2", devices=[inner_device_b])
    rack = _rack_device(chains=[chain_one, chain_two])
    backend = _backend_with_rack(rack)

    result = backend.device_chains_list(0, 0)

    assert result["chains"][0]["name"] == "Chain 1"
    assert result["chains"][0]["devices"][0]["name"] == "Utility"
    assert result["chains"][1]["devices"][0]["name"] == "EQ Eight"
    stable_ref = result["chains"][0]["devices"][0]["stable_ref"]
    assert stable_ref.startswith("device:")


def test_device_chains_list_rejects_non_rack_device() -> None:
    plain_device = _Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)])
    backend = _backend_with_rack(plain_device)

    with pytest.raises(CommandError) as exc_info:
        backend.device_chains_list(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_chains_list_not_supported_when_chains_attribute_missing() -> None:
    # Simulate an older Live API: can_have_chains True but chains unavailable.
    rack = _rack_device(chains=[])
    rack.chains = None  # type: ignore[assignment]
    backend = _backend_with_rack(rack)

    with pytest.raises(CommandError) as exc_info:
        backend.device_chains_list(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


def test_device_macro_list_returns_only_macro_parameters() -> None:
    rack = _rack_device(macros=3)
    backend = _backend_with_rack(rack)

    result = backend.device_macro_list(0, 0)

    assert [macro["name"] for macro in result["macros"]] == ["Macro 1", "Macro 2", "Macro 3"]
    assert result["macros"][0]["min"] == 0.0
    assert result["macros"][0]["max"] == 127.0


def test_device_macro_list_rejects_non_rack_device() -> None:
    plain_device = _Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)])
    backend = _backend_with_rack(plain_device)

    with pytest.raises(CommandError) as exc_info:
        backend.device_macro_list(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_macro_set_updates_value() -> None:
    rack = _rack_device(macros=2)
    backend = _backend_with_rack(rack)

    result = backend.device_macro_set(0, 0, 1, 64.0)

    assert result["value"] == 64.0
    assert result["name"] == "Macro 2"
    macro_list = backend.device_macro_list(0, 0)
    assert macro_list["macros"][1]["value"] == 64.0


def test_device_macro_set_rejects_out_of_range_index() -> None:
    rack = _rack_device(macros=2)
    backend = _backend_with_rack(rack)

    with pytest.raises(CommandError) as exc_info:
        backend.device_macro_set(0, 0, 5, 10.0)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_device_macro_set_rejects_out_of_range_value() -> None:
    rack = _rack_device(macros=2)
    backend = _backend_with_rack(rack)

    with pytest.raises(CommandError) as exc_info:
        backend.device_macro_set(0, 0, 0, 200.0)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_chain_nested_device_parameter_settable_via_set_device_parameter() -> None:
    inner_device = _Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0, min=-1.0, max=1.0)])
    chain = _Chain("Chain 1", devices=[inner_device])
    rack = _rack_device(chains=[chain])
    backend = _backend_with_rack(rack)

    stable_ref = backend.device_chains_list(0, 0)["chains"][0]["devices"][0]["stable_ref"]

    device_path = backend.resolve_device_ref(0, {"mode": "stable_ref", "stable_ref": stable_ref})
    assert device_path == (0, 0, 0)

    parameter = backend.resolve_parameter_ref(0, device_path, {"mode": "index", "index": 0})
    result = backend.set_device_parameter(0, device_path, parameter, 0.5)

    assert result["value"] == 0.5
    assert inner_device.parameters[0].value == 0.5


def test_dispatch_device_chains_list_end_to_end() -> None:
    inner_device = _Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)])
    chain = _Chain("Chain 1", devices=[inner_device])
    rack = _rack_device(chains=[chain])
    backend = _backend_with_rack(rack)

    result = dispatch_command(
        backend,
        "device_chains_list",
        {
            "track_ref": {"mode": "index", "index": 0},
            "device_ref": {"mode": "index", "index": 0},
        },
    )

    assert result["chains"][0]["devices"][0]["name"] == "Utility"


def test_dispatch_device_macro_set_end_to_end() -> None:
    rack = _rack_device(macros=2)
    backend = _backend_with_rack(rack)

    result = dispatch_command(
        backend,
        "device_macro_set",
        {
            "track_ref": {"mode": "index", "index": 0},
            "device_ref": {"mode": "index", "index": 0},
            "macro_index": 0,
            "value": 100.0,
        },
    )

    assert result["value"] == 100.0
