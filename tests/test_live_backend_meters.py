from __future__ import annotations

import pytest
from test_live_backend import _SurfaceStub, _Track

from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command
from remote_script.AbletonCliRemote.live_backend import LiveBackend


class _MeteredTrack(_Track):
    """A track exposing Live's output meter properties."""


def _metered(name: str, left: float, right: float) -> _MeteredTrack:
    track = _MeteredTrack(name=name, has_audio_input=True, has_midi_input=False)
    track.output_meter_left = left
    track.output_meter_right = right
    track.output_meter_level = max(left, right)
    return track


def _backend() -> LiveBackend:
    backend = LiveBackend(_SurfaceStub())
    song = backend.context._song()
    song.tracks[1] = _metered("Bass", 0.6, 0.4)
    song.return_tracks[0] = _metered("Reverb", 0.3, 0.2)
    song.master_track = _metered("Main", 0.9, 0.8)
    song.is_playing = True
    return backend


def test_track_meter_reads_output_meters() -> None:
    result = dispatch_command(
        _backend(), "track_meter_get", {"track_ref": {"mode": "index", "index": 1}}
    )

    assert result == {"track": 1, "left": 0.6, "right": 0.4, "level": 0.6, "is_playing": True}


def test_return_track_and_master_meters() -> None:
    backend = _backend()

    assert dispatch_command(backend, "return_track_meter_get", {"return_track": 0}) == {
        "return_track": 0,
        "left": 0.3,
        "right": 0.2,
        "level": 0.3,
        "is_playing": True,
    }
    assert dispatch_command(backend, "master_meter_get", {}) == {
        "left": 0.9,
        "right": 0.8,
        "level": 0.9,
        "is_playing": True,
    }


def test_missing_meter_api_fails_explicitly() -> None:
    backend = LiveBackend(_SurfaceStub())

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "master_meter_get", {})

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert exc_info.value.details["reason"] == "not_supported_by_live_api"


def test_return_track_meter_rejects_unknown_index() -> None:
    with pytest.raises(CommandError) as exc_info:
        dispatch_command(_backend(), "return_track_meter_get", {"return_track": 9})

    assert exc_info.value.code == "INVALID_ARGUMENT"
