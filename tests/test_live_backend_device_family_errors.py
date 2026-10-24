from __future__ import annotations

import pytest

from remote_script.AbletonCliRemote.command_backend import CommandError
from remote_script.AbletonCliRemote.live_backend import LiveBackend
from tests.test_live_backend import (
    _set_track_device_to_effect,
    _set_track_device_to_synth,
    _SurfaceStub,
)

_FAMILIES = {
    "synth": (_set_track_device_to_synth, "wavetable", "drift"),
    "effect": (_set_track_device_to_effect, "eq8", "limiter"),
}


def _backend(family: str, device_type: str) -> LiveBackend:
    surface = _SurfaceStub()
    set_device, _, _ = _FAMILIES[family]
    set_device(surface, track=0, device=0, **{f"{family}_type": device_type})
    return LiveBackend(surface)


def _error(call) -> tuple[str, str | None]:  # noqa: ANN001
    with pytest.raises(CommandError) as exc_info:
        call()
    assert exc_info.value.code == "INVALID_ARGUMENT"
    return exc_info.value.message, exc_info.value.hint


@pytest.mark.parametrize(
    ("family", "message", "hint"),
    (
        (
            "synth",
            "Device is not a supported synth (supported: wavetable, drift, meld)",
            "Choose a Wavetable, Drift, or Meld device.",
        ),
        (
            "effect",
            "Device is not a supported effect "
            "(supported: eq8, limiter, compressor, auto_filter, reverb, utility)",
            "Choose one of the supported audio effects.",
        ),
    ),
)
def test_family_rejects_a_device_of_another_kind(family: str, message: str, hint: str) -> None:
    other = "effect" if family == "synth" else "synth"
    backend = _backend(other, _FAMILIES[other][1])

    assert _error(lambda: getattr(backend, f"list_{family}_parameters")(0, 0)) == (message, hint)


@pytest.mark.parametrize("family", ("synth", "effect"))
def test_family_rejects_a_standard_type_mismatch(family: str) -> None:
    _, detected, requested = _FAMILIES[family]
    backend = _backend(family, detected)

    assert _error(
        lambda: getattr(backend, f"observe_standard_{family}_state")(
            **{f"{family}_type": requested}, track=0, device=0
        )
    ) == (
        f"Device {family} type mismatch: requested={requested}, detected={detected}",
        f"Select a device that matches the requested {family} type.",
    )


@pytest.mark.parametrize("family", ("synth", "effect"))
def test_family_rejects_an_unknown_standard_key(family: str) -> None:
    _, device_type, _ = _FAMILIES[family]
    backend = _backend(family, device_type)
    keys = getattr(backend, f"list_standard_{family}_keys")(device_type)["keys"]

    assert _error(
        lambda: getattr(backend, f"set_standard_{family}_parameter_safe")(
            **{f"{family}_type": device_type}, track=0, device=0, key="nope", value=0.5
        )
    ) == (f"Unsupported key for {device_type}: nope", f"Use one of: {', '.join(keys)}.")


@pytest.mark.parametrize("family", ("synth", "effect"))
def test_family_rejects_an_unknown_type_name(family: str) -> None:
    backend = LiveBackend(_SurfaceStub())

    message, _ = _error(lambda: getattr(backend, f"list_standard_{family}_keys")("bogus"))
    assert message == f"Unsupported {family}_type: bogus"
    message, _ = _error(lambda: getattr(backend, f"find_{family}_devices")(None, "bogus"))
    assert message == f"Unsupported {family}_type: bogus"
