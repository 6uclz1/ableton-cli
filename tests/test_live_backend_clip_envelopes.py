from __future__ import annotations

import pytest
from test_live_backend import _Device, _Parameter, _SurfaceStub

from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command
from remote_script.AbletonCliRemote.live_backend import LiveBackend


class _FakeEnvelope:
    def __init__(self) -> None:
        self.steps: list[tuple[float, float, float]] = []

    def insert_step(self, time: float, length: float, value: float) -> None:
        self.steps.append((float(time), float(length), float(value)))


def _attach_envelope_support(clip: object) -> dict[int, _FakeEnvelope]:
    envelopes: dict[int, _FakeEnvelope] = {}

    def create_automation_envelope(parameter: object) -> _FakeEnvelope:
        envelope = _FakeEnvelope()
        envelopes[id(parameter)] = envelope
        return envelope

    def clear_envelope(parameter: object) -> None:
        envelopes.pop(id(parameter), None)

    def clear_all_envelopes() -> None:
        envelopes.clear()

    clip.create_automation_envelope = create_automation_envelope  # type: ignore[attr-defined]
    clip.clear_envelope = clear_envelope  # type: ignore[attr-defined]
    clip.clear_all_envelopes = clear_all_envelopes  # type: ignore[attr-defined]
    return envelopes


def _backend_with_envelope_capable_clip() -> tuple[LiveBackend, dict[int, _FakeEnvelope]]:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).devices = [
        _Device("Filter", "AudioEffect", [_Parameter("Cutoff", 0.5, min=0.0, max=1.0)])
    ]
    backend.create_clip(0, 0, 4.0)
    clip_obj = backend.context._clip_slot_at(0, 0).clip
    envelopes = _attach_envelope_support(clip_obj)
    return backend, envelopes


_POINTS = [
    {"time": 0.0, "value": 0.1},
    {"time": 1.0, "value": 0.5},
    {"time": 2.0, "value": 0.9},
]


def test_clip_envelope_set_creates_envelope_and_inserts_steps() -> None:
    backend, envelopes = _backend_with_envelope_capable_clip()

    result = backend.clip_envelope_set(0, 0, 0, 0, _POINTS, "replace")

    assert result["point_count"] == 3
    assert len(envelopes) == 1
    steps = next(iter(envelopes.values())).steps
    assert steps == [(0.0, 1.0, 0.1), (1.0, 1.0, 0.5), (2.0, 0.0, 0.9)]


def test_clip_envelope_set_replace_mode_clears_existing_envelope_first() -> None:
    backend, envelopes = _backend_with_envelope_capable_clip()
    backend.clip_envelope_set(0, 0, 0, 0, _POINTS, "replace")
    first_envelope = next(iter(envelopes.values()))

    backend.clip_envelope_set(0, 0, 0, 0, [{"time": 0.0, "value": 0.2}], "replace")

    assert len(envelopes) == 1
    assert next(iter(envelopes.values())) is not first_envelope


def test_clip_envelope_set_rejects_out_of_range_values_with_offending_indices() -> None:
    backend, _envelopes = _backend_with_envelope_capable_clip()
    points = [
        {"time": 0.0, "value": 0.1},
        {"time": 1.0, "value": 5.0},
        {"time": 2.0, "value": -1.0},
    ]

    with pytest.raises(CommandError) as exc_info:
        backend.clip_envelope_set(0, 0, 0, 0, points, "replace")

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert exc_info.value.details == {"offending_indices": [1, 2]}


def test_clip_envelope_set_not_supported_by_live_api_when_method_missing() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).devices = [
        _Device("Filter", "AudioEffect", [_Parameter("Cutoff", 0.5, min=0.0, max=1.0)])
    ]
    backend.create_clip(0, 0, 4.0)

    with pytest.raises(CommandError) as exc_info:
        backend.clip_envelope_set(0, 0, 0, 0, _POINTS, "replace")

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


def test_clip_envelope_set_requires_existing_clip() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).devices = [
        _Device("Filter", "AudioEffect", [_Parameter("Cutoff", 0.5, min=0.0, max=1.0)])
    ]

    with pytest.raises(CommandError) as exc_info:
        backend.clip_envelope_set(0, 0, 0, 0, _POINTS, "replace")

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_clip_envelope_clear_single_parameter() -> None:
    backend, envelopes = _backend_with_envelope_capable_clip()
    backend.clip_envelope_set(0, 0, 0, 0, _POINTS, "replace")
    assert len(envelopes) == 1

    result = backend.clip_envelope_clear(0, 0, 0, 0, False)

    assert result["cleared_all"] is False
    assert len(envelopes) == 0


def test_clip_envelope_clear_all() -> None:
    backend, envelopes = _backend_with_envelope_capable_clip()
    backend.clip_envelope_set(0, 0, 0, 0, _POINTS, "replace")

    result = backend.clip_envelope_clear(0, 0, None, None, True)

    assert result["cleared_all"] is True
    assert len(envelopes) == 0


def test_clip_envelope_clear_not_supported_by_live_api_when_method_missing() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).devices = [
        _Device("Filter", "AudioEffect", [_Parameter("Cutoff", 0.5, min=0.0, max=1.0)])
    ]
    backend.create_clip(0, 0, 4.0)

    with pytest.raises(CommandError) as exc_info:
        backend.clip_envelope_clear(0, 0, 0, 0, False)

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


def test_dispatch_clip_envelope_set_resolves_refs_end_to_end() -> None:
    backend, envelopes = _backend_with_envelope_capable_clip()

    result = dispatch_command(
        backend,
        "clip_envelope_set",
        {
            "track": 0,
            "clip": 0,
            "device_ref": {"mode": "index", "index": 0},
            "parameter_ref": {"mode": "index", "index": 0},
            "points": _POINTS,
        },
    )

    assert result["point_count"] == 3
    assert len(envelopes) == 1


def test_dispatch_clip_envelope_clear_all_end_to_end() -> None:
    backend, envelopes = _backend_with_envelope_capable_clip()
    backend.clip_envelope_set(0, 0, 0, 0, _POINTS, "replace")

    result = dispatch_command(
        backend,
        "clip_envelope_clear",
        {"track": 0, "clip": 0, "clear_all": True},
    )

    assert result["cleared_all"] is True
    assert len(envelopes) == 0


def test_dispatch_clip_envelope_set_rejects_non_increasing_times() -> None:
    backend, _envelopes = _backend_with_envelope_capable_clip()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "clip_envelope_set",
            {
                "track": 0,
                "clip": 0,
                "device_ref": {"mode": "index", "index": 0},
                "parameter_ref": {"mode": "index", "index": 0},
                "points": [{"time": 1.0, "value": 0.1}, {"time": 1.0, "value": 0.2}],
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_clip_envelope_set_rejects_empty_points() -> None:
    backend, _envelopes = _backend_with_envelope_capable_clip()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "clip_envelope_set",
            {
                "track": 0,
                "clip": 0,
                "device_ref": {"mode": "index", "index": 0},
                "parameter_ref": {"mode": "index", "index": 0},
                "points": [],
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_clip_envelope_clear_rejects_mixing_clear_all_and_refs() -> None:
    backend, _envelopes = _backend_with_envelope_capable_clip()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(
            backend,
            "clip_envelope_clear",
            {
                "track": 0,
                "clip": 0,
                "clear_all": True,
                "device_ref": {"mode": "index", "index": 0},
                "parameter_ref": {"mode": "index", "index": 0},
            },
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"
