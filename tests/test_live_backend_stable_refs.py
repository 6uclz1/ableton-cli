"""Stable refs against Live-like objects.

Live's Python API hands out a new wrapper on every access, so ``is`` never
matches the same track or device twice. The wrappers compare equal and expose
``_live_ptr``, the address of the underlying Live object. Refs must follow
that object, not the position it happened to occupy when the ref was issued.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from test_live_backend import _Device, _Parameter, _ProxyIdentitySong, _SurfaceStub
from test_live_backend_device_control import _EditableTrack

from remote_script.AbletonCliRemote.command_backend import CommandError
from remote_script.AbletonCliRemote.live_backend import LiveBackend


class _LiveWrapper:
    """A fresh wrapper per access, identified by ``_live_ptr`` like Live's API objects."""

    __slots__ = ("_wrapped",)

    def __init__(self, wrapped: Any) -> None:
        object.__setattr__(self, "_wrapped", wrapped)

    @property
    def _live_ptr(self) -> int:
        return id(self._wrapped)

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._wrapped, name)
        if name in {"devices", "parameters"}:
            return [_LiveWrapper(item) for item in value]
        if name == "view":
            return SimpleNamespace(selected_device=_LiveWrapper(value.selected_device))
        return value

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._wrapped, name, value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _LiveWrapper) and self._live_ptr == other._live_ptr

    def __hash__(self) -> int:
        return hash(self._live_ptr)


class _LiveSong(_ProxyIdentitySong):
    @property
    def tracks(self) -> list[_LiveWrapper]:
        return [_LiveWrapper(track) for track in self._stable_tracks]

    @tracks.setter
    def tracks(self, value: list[Any]) -> None:
        self._stable_tracks = list(value)

    def move_device(self, device: _LiveWrapper, target: _LiveWrapper, position: int) -> None:
        devices = target._wrapped.devices
        devices.remove(device._wrapped)
        devices.insert(position, device._wrapped)


class _LiveSurfaceStub(_SurfaceStub):
    def __init__(self) -> None:
        super().__init__()
        self._song_obj = _LiveSong()


def _backend(*device_names: str) -> LiveBackend:
    surface = _LiveSurfaceStub()
    track = _EditableTrack(name="1-Audio", has_audio_input=True, has_midi_input=False)
    track.devices = [
        _Device(name, "AudioEffect", [_Parameter("Gain", 0.0)]) for name in device_names
    ]
    surface.song().tracks = [track]
    return LiveBackend(surface)


def _device_refs(backend: LiveBackend) -> list[tuple[str, str]]:
    return [
        (device["name"], device["stable_ref"]) for device in backend.get_track_info(0)["devices"]
    ]


def _stable(ref: str) -> dict[str, str]:
    return {"mode": "stable_ref", "stable_ref": ref}


def test_inserting_a_device_gives_it_a_new_ref_and_keeps_existing_refs() -> None:
    backend = _backend("Compressor")
    [(_, compressor_ref)] = _device_refs(backend)

    inserted = backend.device_insert(0, "Utility", 0)

    assert inserted["device_stable_ref"] != compressor_ref
    assert _device_refs(backend) == [
        ("Utility", inserted["device_stable_ref"]),
        ("Compressor", compressor_ref),
    ]


def test_a_device_ref_follows_the_device_when_it_moves() -> None:
    backend = _backend("Compressor", "Utility")
    [(_, compressor_ref), (_, utility_ref)] = _device_refs(backend)

    backend.device_move(0, 1, 0)

    assert backend.resolve_device_ref(0, _stable(compressor_ref)) == 1
    assert _device_refs(backend) == [("Utility", utility_ref), ("Compressor", compressor_ref)]


def test_a_deleted_device_ref_is_stale_instead_of_naming_its_successor() -> None:
    backend = _backend("Compressor", "Utility")
    [(_, compressor_ref), _] = _device_refs(backend)

    backend.device_delete(0, 0)

    with pytest.raises(CommandError) as raised:
        backend.resolve_device_ref(0, _stable(compressor_ref))
    assert raised.value.message == f"Stale device stable_ref: {compressor_ref}"


def test_a_track_ref_follows_the_track_when_a_track_is_inserted_before_it() -> None:
    backend = _backend("Compressor")
    [track_ref] = [track["stable_ref"] for track in backend.tracks_list()["tracks"]]

    backend.context._song().create_midi_track(0)

    refs = [track["stable_ref"] for track in backend.tracks_list()["tracks"]]
    assert refs[1] == track_ref
    assert refs[0] != track_ref
    assert backend.resolve_track_ref(_stable(track_ref)) == 1


def test_the_selected_device_is_found_through_a_fresh_wrapper() -> None:
    backend = _backend("Compressor", "Utility")
    track = backend.context._song()._stable_tracks[0]
    track.view = SimpleNamespace(selected_device=track.devices[1])

    assert backend.resolve_device_ref(0, {"mode": "selected"}) == 1
