from __future__ import annotations

import pytest
from test_live_backend import _SurfaceStub, _Track

from remote_script.AbletonCliRemote.command_backend import CommandError, dispatch_command
from remote_script.AbletonCliRemote.live_backend import LiveBackend


def _backend_with_return_track_api() -> LiveBackend:
    backend = LiveBackend(_SurfaceStub())
    song = backend.context._song()

    def create_return_track() -> None:
        song.return_tracks.append(
            _Track(name="C-Return", has_audio_input=False, has_midi_input=False)
        )

    def delete_return_track(index: int) -> None:
        del song.return_tracks[index]

    song.create_return_track = create_return_track
    song.delete_return_track = delete_return_track
    return backend


def _backend_with_scale_api() -> LiveBackend:
    backend = LiveBackend(_SurfaceStub())
    song = backend.context._song()
    song.root_note = 0
    song.scale_name = "Major"
    song.scale_mode = False
    song.scale_intervals = [0, 2, 4, 5, 7, 9, 11]
    return backend


def test_return_track_create_appends_and_reports_index() -> None:
    backend = _backend_with_return_track_api()

    result = backend.return_track_create()

    assert result == {"return_track": 2, "name": "C-Return", "return_track_count": 3}


def test_return_track_create_not_supported_without_live_api() -> None:
    backend = LiveBackend(_SurfaceStub())

    with pytest.raises(CommandError) as exc_info:
        backend.return_track_create()

    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


def test_return_track_delete_removes_by_index() -> None:
    backend = _backend_with_return_track_api()

    result = backend.return_track_delete(0)

    assert result == {"return_track": 0, "name": "Reverb", "return_track_count": 1}
    assert [track.name for track in backend.context._song().return_tracks] == ["Delay"]


def test_return_track_delete_rejects_out_of_range() -> None:
    backend = _backend_with_return_track_api()

    with pytest.raises(CommandError) as exc_info:
        backend.return_track_delete(5)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_song_scale_get_reports_scale_state() -> None:
    backend = _backend_with_scale_api()

    result = backend.song_scale_get()

    assert result == {
        "root_note": 0,
        "root_name": "C",
        "scale_name": "Major",
        "scale_mode": False,
        "scale_intervals": [0, 2, 4, 5, 7, 9, 11],
    }


def test_song_scale_set_updates_only_given_fields() -> None:
    backend = _backend_with_scale_api()

    result = backend.song_scale_set(9, None, True)

    assert result["root_note"] == 9
    assert result["root_name"] == "A"
    assert result["scale_name"] == "Major"
    assert result["scale_mode"] is True


def test_song_scale_set_rejects_name_live_does_not_accept() -> None:
    backend = _backend_with_scale_api()
    song = backend.context._song()

    class _StrictSong(type(song)):  # type: ignore[misc]
        @property
        def scale_name(self) -> str:
            return "Major"

        @scale_name.setter
        def scale_name(self, value: str) -> None:
            del value

    song.__class__ = _StrictSong

    with pytest.raises(CommandError) as exc_info:
        backend.song_scale_set(None, "Nonexistent", None)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_song_scale_set_rejects_root_out_of_range() -> None:
    backend = _backend_with_scale_api()

    with pytest.raises(CommandError) as exc_info:
        backend.song_scale_set(12, None, None)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_song_scale_not_supported_without_live_api() -> None:
    backend = LiveBackend(_SurfaceStub())

    with pytest.raises(CommandError) as exc_info:
        backend.song_scale_get()

    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


def test_dispatch_song_scale_set_requires_a_field() -> None:
    backend = _backend_with_scale_api()

    with pytest.raises(CommandError) as exc_info:
        dispatch_command(backend, "song_scale_set", {})

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_dispatch_song_scale_set_end_to_end() -> None:
    backend = _backend_with_scale_api()

    result = dispatch_command(
        backend, "song_scale_set", {"root_note": 2, "scale_name": "Dorian", "scale_mode": True}
    )

    assert result["root_name"] == "D"
    assert result["scale_name"] == "Dorian"
    assert result["scale_mode"] is True


def test_dispatch_return_track_delete_end_to_end() -> None:
    backend = _backend_with_return_track_api()

    result = dispatch_command(backend, "return_track_delete", {"return_track": 1})

    assert result["name"] == "Delay"
