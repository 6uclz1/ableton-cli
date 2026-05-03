from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _as_float,
    _device_parameter_args,
    _device_ref,
    _effect_type,
    _non_empty_string,
    _non_negative_int,
    _optional_track_index,
    _parameter_ref,
    _synth_type,
    _track_ref,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _handle_set_device_parameter(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track_ref, device_ref, parameter_ref, value = _device_parameter_args(args)
    track = backend.resolve_track_ref(track_ref)
    device = backend.resolve_device_ref(track, device_ref)
    parameter = backend.resolve_parameter_ref(track, device, parameter_ref)
    return backend.set_device_parameter(track, device, parameter, value)


def _handle_find_synth_devices(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _optional_track_index("track", args.get("track"))
    synth_type_raw = args.get("synth_type")
    synth_type = _synth_type(synth_type_raw) if synth_type_raw is not None else None
    return backend.find_synth_devices(track, synth_type)


def _handle_list_synth_parameters(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
    return backend.list_synth_parameters(track, device)


def _handle_set_synth_parameter_safe(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track_ref, device_ref, parameter_ref, value = _device_parameter_args(args)
    track = backend.resolve_track_ref(track_ref)
    device = backend.resolve_device_ref(track, device_ref)
    parameter = backend.resolve_parameter_ref(track, device, parameter_ref)
    return backend.set_synth_parameter_safe(track, device, parameter, value)


def _handle_observe_synth_parameters(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
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
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
    key = _parameter_ref(args.get("parameter_ref")).get("key")
    if not isinstance(key, str):
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
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
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
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
    return backend.list_effect_parameters(track, device)


def _handle_set_effect_parameter_safe(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track_ref, device_ref, parameter_ref, value = _device_parameter_args(args)
    track = backend.resolve_track_ref(track_ref)
    device = backend.resolve_device_ref(track, device_ref)
    parameter = backend.resolve_parameter_ref(track, device, parameter_ref)
    return backend.set_effect_parameter_safe(track, device, parameter, value)


def _handle_observe_effect_parameters(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
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
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
    key = _parameter_ref(args.get("parameter_ref")).get("key")
    if not isinstance(key, str):
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
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    device = backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))
    return backend.observe_standard_effect_state(
        effect_type=effect_type,
        track=track,
        device=device,
    )


def _handle_master_device_load(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    raw_target = args.get("target")
    if raw_target is None:
        raw_target = args.get("uri", args.get("path"))
    target = _non_empty_string("target", raw_target)
    position = _non_empty_string("position", args.get("position", "end"))
    return backend.master_device_load(target, position)


def _handle_master_device_move(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    device_index = _non_negative_int("device_index", args.get("device_index"))
    to_index = _non_negative_int("to_index", args.get("to_index"))
    return backend.master_device_move(device_index, to_index)


def _handle_master_device_delete(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    device_index = _non_negative_int("device_index", args.get("device_index"))
    return backend.master_device_delete(device_index)


def _handle_master_device_parameters_list(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    return backend.master_device_parameters_list(_device_ref(args.get("device_ref")))


def _handle_master_device_parameter_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    device_ref = _device_ref(args.get("device_ref"))
    raw_parameter_ref = args.get("parameter_ref")
    if raw_parameter_ref is None and args.get("parameter_key") is not None:
        raw_parameter_ref = {"mode": "key", "key": args.get("parameter_key")}
    parameter_ref = _parameter_ref(raw_parameter_ref)
    value = _as_float("value", args.get("value"))
    return backend.master_device_parameter_set(device_ref, parameter_ref, value)


def _handle_master_effect_keys(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    return backend.master_effect_keys(effect_type)


def _handle_master_effect_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    device_ref = _device_ref(args.get("device_ref"))
    raw_parameter_ref = args.get("parameter_ref")
    if raw_parameter_ref is None and args.get("parameter_key") is not None:
        raw_parameter_ref = {"mode": "key", "key": args.get("parameter_key")}
    parameter_ref = _parameter_ref(raw_parameter_ref)
    value = _as_float("value", args.get("value"))
    return backend.master_effect_set(effect_type, device_ref, parameter_ref, value)


def _handle_master_effect_observe(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    effect_type = _effect_type(args.get("effect_type"))
    device_ref = _device_ref(args.get("device_ref"))
    return backend.master_effect_observe(effect_type, device_ref)


def _handle_named_master_effect_set(
    effect_type: str,
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    named_args = {**args, "effect_type": effect_type}
    return _handle_master_effect_set(backend, named_args)


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
    "master_device_load": _handle_master_device_load,
    "master_device_move": _handle_master_device_move,
    "master_device_delete": _handle_master_device_delete,
    "master_device_parameters_list": _handle_master_device_parameters_list,
    "master_device_parameter_set": _handle_master_device_parameter_set,
    "master_effect_keys": _handle_master_effect_keys,
    "master_effect_set": _handle_master_effect_set,
    "master_effect_observe": _handle_master_effect_observe,
    "master_effect_eq8_set": lambda backend, args: _handle_named_master_effect_set(
        "eq8",
        backend,
        args,
    ),
    "master_effect_limiter_set": lambda backend, args: _handle_named_master_effect_set(
        "limiter",
        backend,
        args,
    ),
    "master_effect_compressor_set": lambda backend, args: _handle_named_master_effect_set(
        "compressor",
        backend,
        args,
    ),
    "master_effect_utility_set": lambda backend, args: _handle_named_master_effect_set(
        "utility",
        backend,
        args,
    ),
}
