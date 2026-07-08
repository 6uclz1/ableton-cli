from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import _clip_envelope_clear_args, _clip_envelope_set_args

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _handle_clip_envelope_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track, clip, device_ref, parameter_ref, points, mode = _clip_envelope_set_args(args)
    device = backend.resolve_device_ref(track, device_ref)
    parameter = backend.resolve_parameter_ref(track, device, parameter_ref)
    return backend.clip_envelope_set(track, clip, device, parameter, points, mode)


def _handle_clip_envelope_clear(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track, clip, device_ref, parameter_ref, clear_all = _clip_envelope_clear_args(args)
    if clear_all:
        return backend.clip_envelope_clear(track, clip, None, None, True)
    assert device_ref is not None and parameter_ref is not None
    device = backend.resolve_device_ref(track, device_ref)
    parameter = backend.resolve_parameter_ref(track, device, parameter_ref)
    return backend.clip_envelope_clear(track, clip, device, parameter, False)


ENVELOPE_HANDLERS: dict[str, Handler] = {
    "clip_envelope_set": _handle_clip_envelope_set,
    "clip_envelope_clear": _handle_clip_envelope_clear,
}
