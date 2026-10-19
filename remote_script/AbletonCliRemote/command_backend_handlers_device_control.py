from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _as_bool,
    _as_float,
    _as_str,
    _device_ref_args,
    _insert_index,
    _non_empty_string,
    _parameter_ref,
    _track_index,
    _track_ref,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _resolve_device(
    backend: CommandBackend, args: dict[str, Any]
) -> tuple[int, int | tuple[int, ...]]:
    track_ref, device_ref = _device_ref_args(args)
    track = backend.resolve_track_ref(track_ref)
    return track, backend.resolve_device_ref(track, device_ref)


def _resolve_parameter(
    backend: CommandBackend, args: dict[str, Any]
) -> tuple[int, int | tuple[int, ...], int]:
    track, device = _resolve_device(backend, args)
    parameter = backend.resolve_parameter_ref(
        track, device, _parameter_ref(args.get("parameter_ref"))
    )
    return track, device, parameter


def _handle_device_parameters_list(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.device_parameters_list(*_resolve_device(backend, args))


def _handle_device_parameter_select(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    item = _non_empty_string("item", args.get("item"))
    track, device, parameter = _resolve_parameter(backend, args)
    return backend.device_parameter_select(track, device, parameter, item)


def _handle_device_parameter_display_set(
    backend: CommandBackend, args: dict[str, Any]
) -> dict[str, Any]:
    value = _as_float("value", args.get("value"))
    track, device, parameter = _resolve_parameter(backend, args)
    return backend.device_parameter_display_set(track, device, parameter, value)


def _handle_device_active_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.device_active_get(*_resolve_device(backend, args))


def _handle_device_active_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    value = _as_bool("value", args.get("value"))
    track, device = _resolve_device(backend, args)
    return backend.device_active_set(track, device, value)


def _handle_device_preset_list(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.device_preset_list(*_resolve_device(backend, args))


def _handle_device_preset_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    preset_index = _track_index("preset_index", args.get("preset_index"))
    track, device = _resolve_device(backend, args)
    return backend.device_preset_set(track, device, preset_index)


def _handle_device_sidechain_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.device_sidechain_get(*_resolve_device(backend, args))


def _handle_device_sidechain_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    routing_type = _non_empty_string("routing_type", args.get("routing_type"))
    raw_channel = args.get("routing_channel")
    routing_channel = None if raw_channel is None else _as_str("routing_channel", raw_channel)
    track, device = _resolve_device(backend, args)
    return backend.device_sidechain_set(track, device, routing_type, routing_channel)


def _handle_device_insert(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    device_name = _non_empty_string("device_name", args.get("device_name"))
    index = _insert_index("index", args.get("index", -1))
    track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
    return backend.device_insert(track, device_name, index)


def _handle_device_delete(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.device_delete(*_resolve_device(backend, args))


def _handle_device_move(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    to_index = _track_index("to_index", args.get("to_index"))
    track, device = _resolve_device(backend, args)
    return backend.device_move(track, device, to_index)


DEVICE_CONTROL_HANDLERS: dict[str, Handler] = {
    "device_parameters_list": _handle_device_parameters_list,
    "device_parameter_select": _handle_device_parameter_select,
    "device_parameter_display_set": _handle_device_parameter_display_set,
    "device_active_get": _handle_device_active_get,
    "device_active_set": _handle_device_active_set,
    "device_preset_list": _handle_device_preset_list,
    "device_preset_set": _handle_device_preset_set,
    "device_sidechain_get": _handle_device_sidechain_get,
    "device_sidechain_set": _handle_device_sidechain_set,
    "device_insert": _handle_device_insert,
    "device_delete": _handle_device_delete,
    "device_move": _handle_device_move,
}
