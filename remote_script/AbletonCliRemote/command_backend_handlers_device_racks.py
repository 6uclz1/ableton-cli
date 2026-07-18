from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import _device_macro_set_args, _device_ref_args

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _handle_device_chains_list(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track_ref, device_ref = _device_ref_args(args)
    track = backend.resolve_track_ref(track_ref)
    device = backend.resolve_device_ref(track, device_ref)
    return backend.device_chains_list(track, device)


def _handle_device_macro_list(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track_ref, device_ref = _device_ref_args(args)
    track = backend.resolve_track_ref(track_ref)
    device = backend.resolve_device_ref(track, device_ref)
    return backend.device_macro_list(track, device)


def _handle_device_macro_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track_ref, device_ref, macro_index, value = _device_macro_set_args(args)
    track = backend.resolve_track_ref(track_ref)
    device = backend.resolve_device_ref(track, device_ref)
    return backend.device_macro_set(track, device, macro_index, value)


DEVICE_RACKS_HANDLERS: dict[str, Handler] = {
    "device_chains_list": _handle_device_chains_list,
    "device_macro_list": _handle_device_macro_list,
    "device_macro_set": _handle_device_macro_set,
}
