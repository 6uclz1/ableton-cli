from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _as_float,
    _device_group_parameter_args,
    _device_parameter_args,
    _device_ref,
    _effect_type,
    _non_empty_string,
    _optional_track_index,
    _parameter_ref,
    _synth_type,
    _track_ref,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _handle_set_device_parameter(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track_ref, device_ref, parameter_ref, value = _device_group_parameter_args(args)
    track = backend.resolve_device_track_ref(track_ref)
    device = backend.resolve_device_ref(track, device_ref)
    parameter = backend.resolve_parameter_ref(track, device, parameter_ref)
    return backend.set_device_parameter(track, device, parameter, value)


BackendMethod = Callable[[CommandBackend], Callable[..., dict[str, Any]]]


class _FamilyMethods(NamedTuple):
    """The backend entry points of one family, named so the parity test can see each call."""

    find: BackendMethod
    list_parameters: BackendMethod
    set_parameter: BackendMethod
    observe_parameters: BackendMethod
    list_standard_keys: BackendMethod
    set_standard_parameter: BackendMethod
    observe_standard_state: BackendMethod


def _device_family_handlers(
    family: str,
    parse_type: Callable[[Any], str],
    methods: _FamilyMethods,
) -> dict[str, Handler]:
    """Handlers for one synth/effect family; they differ only in names and the type parser."""
    type_arg = f"{family}_type"

    def _track_and_device(backend: CommandBackend, args: dict[str, Any]) -> tuple[int, int]:
        track = backend.resolve_track_ref(_track_ref(args.get("track_ref")))
        return track, backend.resolve_device_ref(track, _device_ref(args.get("device_ref")))

    def _find(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        track = _optional_track_index("track", args.get("track"))
        raw_type = args.get(type_arg)
        device_type = parse_type(raw_type) if raw_type is not None else None
        return methods.find(backend)(track, device_type)

    def _list_parameters(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        return methods.list_parameters(backend)(*_track_and_device(backend, args))

    def _set_parameter(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        track_ref, device_ref, parameter_ref, value = _device_parameter_args(args)
        track = backend.resolve_track_ref(track_ref)
        device = backend.resolve_device_ref(track, device_ref)
        parameter = backend.resolve_parameter_ref(track, device, parameter_ref)
        return methods.set_parameter(backend)(track, device, parameter, value)

    def _observe_parameters(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        return methods.observe_parameters(backend)(*_track_and_device(backend, args))

    def _list_standard_keys(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        return methods.list_standard_keys(backend)(parse_type(args.get(type_arg)))

    def _set_standard_parameter(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        device_type = parse_type(args.get(type_arg))
        track, device = _track_and_device(backend, args)
        key = _parameter_ref(args.get("parameter_ref")).get("key")
        if not isinstance(key, str):
            key = _non_empty_string("key", args.get("key"))
        value = _as_float("value", args.get("value"))
        return methods.set_standard_parameter(backend)(
            **{type_arg: device_type},
            track=track,
            device=device,
            key=key,
            value=value,
        )

    def _observe_standard_state(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        device_type = parse_type(args.get(type_arg))
        track, device = _track_and_device(backend, args)
        return methods.observe_standard_state(backend)(
            **{type_arg: device_type},
            track=track,
            device=device,
        )

    return {
        f"find_{family}_devices": _find,
        f"list_{family}_parameters": _list_parameters,
        f"set_{family}_parameter_safe": _set_parameter,
        f"observe_{family}_parameters": _observe_parameters,
        f"list_standard_{family}_keys": _list_standard_keys,
        f"set_standard_{family}_parameter_safe": _set_standard_parameter,
        f"observe_standard_{family}_state": _observe_standard_state,
    }


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
    **_device_family_handlers(
        "synth",
        _synth_type,
        _FamilyMethods(
            find=lambda backend: backend.find_synth_devices,
            list_parameters=lambda backend: backend.list_synth_parameters,
            set_parameter=lambda backend: backend.set_synth_parameter_safe,
            observe_parameters=lambda backend: backend.observe_synth_parameters,
            list_standard_keys=lambda backend: backend.list_standard_synth_keys,
            set_standard_parameter=lambda backend: backend.set_standard_synth_parameter_safe,
            observe_standard_state=lambda backend: backend.observe_standard_synth_state,
        ),
    ),
    **_device_family_handlers(
        "effect",
        _effect_type,
        _FamilyMethods(
            find=lambda backend: backend.find_effect_devices,
            list_parameters=lambda backend: backend.list_effect_parameters,
            set_parameter=lambda backend: backend.set_effect_parameter_safe,
            observe_parameters=lambda backend: backend.observe_effect_parameters,
            list_standard_keys=lambda backend: backend.list_standard_effect_keys,
            set_standard_parameter=lambda backend: backend.set_standard_effect_parameter_safe,
            observe_standard_state=lambda backend: backend.observe_standard_effect_state,
        ),
    ),
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
