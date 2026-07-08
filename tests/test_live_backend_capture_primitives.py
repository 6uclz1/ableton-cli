from __future__ import annotations

import pytest
from test_live_backend import _SurfaceStub

from remote_script.AbletonCliRemote.command_backend import CommandError
from remote_script.AbletonCliRemote.live_backend import LiveBackend


def test_fire_clip_on_empty_slot_succeeds() -> None:
    backend = LiveBackend(_SurfaceStub())

    result = backend.fire_clip(0, 0)

    assert result == {"track": 0, "clip": 0, "fired": True}


def test_clip_file_path_get_returns_path_for_recorded_audio_clip() -> None:
    backend = LiveBackend(_SurfaceStub())
    slot = backend._clip_slot_at(0, 0)
    slot.create_clip(4.0)
    slot.clip.is_audio_clip = True
    slot.clip.is_midi_clip = False
    slot.clip.file_path = "/tmp/capture/Track 1.wav"

    result = backend.clip_file_path_get(0, 0)

    assert result == {"track": 0, "clip": 0, "file_path": "/tmp/capture/Track 1.wav"}


def test_clip_file_path_get_rejects_midi_clip() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.create_clip(0, 0, 4.0)

    with pytest.raises(CommandError) as exc_info:
        backend.clip_file_path_get(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_clip_file_path_get_rejects_missing_clip() -> None:
    backend = LiveBackend(_SurfaceStub())

    with pytest.raises(CommandError) as exc_info:
        backend.clip_file_path_get(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_clip_file_path_get_rejects_audio_clip_with_no_file_path() -> None:
    backend = LiveBackend(_SurfaceStub())
    slot = backend._clip_slot_at(0, 0)
    slot.create_clip(4.0)
    slot.clip.is_audio_clip = True
    slot.clip.is_midi_clip = False
    slot.clip.file_path = None

    with pytest.raises(CommandError) as exc_info:
        backend.clip_file_path_get(0, 0)

    assert exc_info.value.code == "INVALID_ARGUMENT"
