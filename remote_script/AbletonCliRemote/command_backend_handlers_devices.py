from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _as_float,
    _device_parameter_args,
    _effect_type,
    _non_empty_string,
    _optional_track_index,
    _synth_type,
    _track_index,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _handle_set_device_parameter(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track, device, parameter, value = _device_parameter_args(args)
    return backend.set_device_parameter(track, device, parameter, value)


def _handle_find_synth_devices(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _optional_track_index("track", args.get("track"))
    synth_type_raw = args.get("synth_type")
    synth_type = _synth_type(synth_type_raw) if synth_type_raw is not None else None
    return backend.find_synth_devices(track, synth_type)


def _handle_list_synth_parameters(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.list_synth_parameters(track, device)


def _handle_set_synth_parameter_safe(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track, device, parameter, value = _device_parameter_args(args)
    return backend.set_synth_parameter_safe(track, device, parameter, value)


def _handle_observe_synth_parameters(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_synth_parameters(track, device)


def _handle_list_standard_synth_keys(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    synth_type = _synth_type(args.get("synth_type"))
    return backend.list_standard_synth_keys(synth_type)


def _handle_set_standard_synth_parameter_safe(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    synth_type = _synth_type(args.get("synth_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    key = _non_empty_string("key", args.get("key"))
    value = _as_float("value", args.get("value"))
    return backend.set_standard_synth_parameter_safe(
        synth_type=synth_type,
        track=track,
        device=device,
        key=key,
        value=value,
    )


def _handle_observe_standard_synth_state(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    synth_type = _synth_type(args.get("synth_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_standard_synth_state(
        synth_type=synth_type,
        track=track,
        device=device,
    )


def _handle_find_effect_devices(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _optional_track_index("track", args.get("track"))
    effect_type_raw = args.get("effect_type")
    effect_type = _effect_type(effect_type_raw) if effect_type_raw is not None else None
    return backend.find_effect_devices(track, effect_type)


def _handle_list_effect_parameters(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.list_effect_parameters(track, device)


def _handle_set_effect_parameter_safe(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track, device, parameter, value = _device_parameter_args(args)
    return backend.set_effect_parameter_safe(track, device, parameter, value)


def _handle_observe_effect_parameters(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_effect_parameters(track, device)


def _handle_list_standard_effect_keys(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    return backend.list_standard_effect_keys(effect_type)


def _handle_set_standard_effect_parameter_safe(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    key = _non_empty_string("key", args.get("key"))
    value = _as_float("value", args.get("value"))
    return backend.set_standard_effect_parameter_safe(
        effect_type=effect_type,
        track=track,
        device=device,
        key=key,
        value=value,
    )


def _handle_observe_standard_effect_state(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    return backend.observe_standard_effect_state(
        effect_type=effect_type,
        track=track,
        device=device,
    )


DEVICE_HANDLERS: dict[str, Handler] = {
    "set_device_parameter": _handle_set_device_parameter,
    "find_synth_devices": _handle_find_synth_devices,
    "list_synth_parameters": _handle_list_synth_parameters,
    "set_synth_parameter_safe": _handle_set_synth_parameter_safe,
    "observe_synth_parameters": _handle_observe_synth_parameters,
    "list_standard_synth_keys": _handle_list_standard_synth_keys,
    "set_standard_synth_parameter_safe": _handle_set_standard_synth_parameter_safe,
    "observe_standard_synth_state": _handle_observe_standard_synth_state,
    "find_effect_devices": _handle_find_effect_devices,
    "list_effect_parameters": _handle_list_effect_parameters,
    "set_effect_parameter_safe": _handle_set_effect_parameter_safe,
    "observe_effect_parameters": _handle_observe_effect_parameters,
    "list_standard_effect_keys": _handle_list_standard_effect_keys,
    "set_standard_effect_parameter_safe": _handle_set_standard_effect_parameter_safe,
    "observe_standard_effect_state": _handle_observe_standard_effect_state,
}
