from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast

import typer

from ..refs import RefPayload
from ..runtime import execute_command, get_client
from ._track_arm_commands import register_commands as register_arm_commands
from ._track_info_commands import register_commands as register_info_commands
from ._track_mute_commands import register_commands as register_mute_commands
from ._track_name_commands import register_commands as register_name_commands
from ._track_panning_commands import register_commands as register_panning_commands
from ._track_routing_commands import register_commands as register_routing_commands
from ._track_send_commands import register_commands as register_send_commands
from ._track_shared import (
    TrackAction,
    TrackValueAction,
    TValue,
    ValueValidator,
)
from ._track_solo_commands import register_commands as register_solo_commands
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec
from ._track_volume_commands import register_commands as register_volume_commands


def _resolve_track_ref(track_ref: RefPayload | Callable[[], RefPayload]) -> RefPayload:
    if callable(track_ref):
        return cast(RefPayload, track_ref())
    return track_ref


def run_track_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: RefPayload | Callable[[], RefPayload],
    fn: TrackAction,
) -> None:
    def _run() -> dict[str, object]:
        client = get_client(ctx)
        return fn(client, _resolve_track_ref(track_ref))

    execute_kwargs: dict[str, object] = {
        "command": command_name,
        "args": {"track_ref": None if callable(track_ref) else track_ref},
        "action": _run,
    }
    if callable(track_ref):
        execute_kwargs["resolved_args"] = lambda: {"track_ref": _resolve_track_ref(track_ref)}
    execute_command(ctx, **execute_kwargs)


def run_track_value_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: RefPayload | Callable[[], RefPayload],
    value: TValue,
    fn: TrackValueAction[TValue],
    value_name: str = "value",
    validators: Sequence[ValueValidator[TValue]] | None = None,
) -> None:
    active_validators = validators if validators is not None else ()

    def _run() -> dict[str, object]:
        resolved_track_ref = _resolve_track_ref(track_ref)
        valid_value = value
        for validator in active_validators:
            valid_value = validator(valid_value)
        client = get_client(ctx)
        return fn(client, resolved_track_ref, valid_value)

    execute_kwargs: dict[str, object] = {
        "command": command_name,
        "args": {"track_ref": None if callable(track_ref) else track_ref, value_name: value},
        "action": _run,
    }
    if callable(track_ref):
        execute_kwargs["resolved_args"] = lambda: {
            "track_ref": _resolve_track_ref(track_ref),
            value_name: value,
        }
    execute_command(ctx, **execute_kwargs)


def run_track_command_spec(
    ctx: typer.Context,
    *,
    spec: TrackCommandSpec,
    track_ref: RefPayload,
) -> None:
    run_track_command(
        ctx,
        command_name=spec.command_name,
        track_ref=track_ref,
        fn=lambda client, resolved_track_ref: cast(
            dict[str, object],
            getattr(client, spec.client_method)(resolved_track_ref),
        ),
    )


def run_track_value_command_spec(
    ctx: typer.Context,
    *,
    spec: TrackValueCommandSpec[TValue],
    track_ref: RefPayload,
    value: TValue,
) -> None:
    run_track_value_command(
        ctx,
        command_name=spec.command_name,
        track_ref=track_ref,
        value=value,
        value_name=spec.value_name,
        validators=spec.validators,
        fn=lambda client, resolved_track_ref, valid_value: cast(
            dict[str, object],
            getattr(client, spec.client_method)(resolved_track_ref, valid_value),
        ),
    )


track_app = typer.Typer(help="Single-track commands", no_args_is_help=True)
volume_app = typer.Typer(help="Track volume commands", no_args_is_help=True)
name_app = typer.Typer(help="Track naming commands", no_args_is_help=True)
mute_app = typer.Typer(help="Track mute commands", no_args_is_help=True)
solo_app = typer.Typer(help="Track solo commands", no_args_is_help=True)
arm_app = typer.Typer(help="Track arm commands", no_args_is_help=True)
panning_app = typer.Typer(help="Track panning commands", no_args_is_help=True)
send_app = typer.Typer(help="Track send commands", no_args_is_help=True)
routing_app = typer.Typer(help="Track routing commands", no_args_is_help=True)

register_info_commands(track_app, run_track_command_spec=run_track_command_spec)
register_volume_commands(
    volume_app,
    run_track_command_spec=run_track_command_spec,
    run_track_value_command_spec=run_track_value_command_spec,
)
register_name_commands(
    name_app,
    run_track_value_command_spec=run_track_value_command_spec,
)
register_mute_commands(
    mute_app,
    run_track_command_spec=run_track_command_spec,
    run_track_value_command_spec=run_track_value_command_spec,
)
register_solo_commands(
    solo_app,
    run_track_command_spec=run_track_command_spec,
    run_track_value_command_spec=run_track_value_command_spec,
)
register_arm_commands(
    arm_app,
    run_track_command_spec=run_track_command_spec,
    run_track_value_command_spec=run_track_value_command_spec,
)
register_panning_commands(
    panning_app,
    run_track_command_spec=run_track_command_spec,
    run_track_value_command_spec=run_track_value_command_spec,
)


def _run_send_command(ctx, *, command_name, track_ref, send, fn) -> None:
    run_track_send_command(
        ctx,
        command_name=command_name,
        track_ref=track_ref,
        send=send,
        fn=fn,
    )


def _run_send_value_command(ctx, *, command_name, track_ref, send, value, fn) -> None:
    run_track_send_value_command(
        ctx,
        command_name=command_name,
        track_ref=track_ref,
        send=send,
        value=value,
        fn=fn,
    )


register_send_commands(
    send_app,
    run_track_send_command=_run_send_command,
    run_track_send_value_command=_run_send_value_command,
)


def _run_routing_get(ctx, *, command_name, track_ref, fn_name) -> None:
    run_track_routing_get(
        ctx,
        command_name=command_name,
        track_ref=track_ref,
        fn_name=fn_name,
    )


def _run_routing_set(
    ctx,
    *,
    command_name,
    track_ref,
    routing_type,
    routing_channel,
    fn_name,
) -> None:
    run_track_routing_set(
        ctx,
        command_name=command_name,
        track_ref=track_ref,
        routing_type=routing_type,
        routing_channel=routing_channel,
        fn_name=fn_name,
    )


register_routing_commands(
    routing_app,
    run_track_routing_get=_run_routing_get,
    run_track_routing_set=_run_routing_set,
)


track_app.add_typer(volume_app, name="volume")
track_app.add_typer(name_app, name="name")
track_app.add_typer(mute_app, name="mute")
track_app.add_typer(solo_app, name="solo")
track_app.add_typer(arm_app, name="arm")
track_app.add_typer(panning_app, name="panning")
track_app.add_typer(send_app, name="send")
track_app.add_typer(routing_app, name="routing")


def run_track_send_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: RefPayload | Callable[[], RefPayload],
    send: int,
    fn,
) -> None:
    def _run() -> dict[str, object]:
        client = get_client(ctx)
        return fn(client, _resolve_track_ref(track_ref), send)

    execute_kwargs: dict[str, object] = {
        "command": command_name,
        "args": {"track_ref": None if callable(track_ref) else track_ref, "send": send},
        "action": _run,
    }
    if callable(track_ref):
        execute_kwargs["resolved_args"] = lambda: {
            "track_ref": _resolve_track_ref(track_ref),
            "send": send,
        }
    execute_command(ctx, **execute_kwargs)


def run_track_send_value_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: RefPayload | Callable[[], RefPayload],
    send: int,
    value: float,
    fn,
) -> None:
    def _run() -> dict[str, object]:
        client = get_client(ctx)
        return fn(client, _resolve_track_ref(track_ref), send, value)

    execute_kwargs: dict[str, object] = {
        "command": command_name,
        "args": {
            "track_ref": None if callable(track_ref) else track_ref,
            "send": send,
            "value": value,
        },
        "action": _run,
    }
    if callable(track_ref):
        execute_kwargs["resolved_args"] = lambda: {
            "track_ref": _resolve_track_ref(track_ref),
            "send": send,
            "value": value,
        }
    execute_command(ctx, **execute_kwargs)


def run_track_routing_get(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: RefPayload | Callable[[], RefPayload],
    fn_name: str,
) -> None:
    def _run() -> dict[str, object]:
        client = get_client(ctx)
        return cast(dict[str, object], getattr(client, fn_name)(_resolve_track_ref(track_ref)))

    execute_kwargs: dict[str, object] = {
        "command": command_name,
        "args": {"track_ref": None if callable(track_ref) else track_ref},
        "action": _run,
    }
    if callable(track_ref):
        execute_kwargs["resolved_args"] = lambda: {"track_ref": _resolve_track_ref(track_ref)}
    execute_command(ctx, **execute_kwargs)


def run_track_routing_set(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: RefPayload | Callable[[], RefPayload],
    routing_type: str,
    routing_channel: str,
    fn_name: str,
) -> None:
    def _run() -> dict[str, object]:
        client = get_client(ctx)
        return cast(
            dict[str, object],
            getattr(client, fn_name)(_resolve_track_ref(track_ref), routing_type, routing_channel),
        )

    execute_kwargs: dict[str, object] = {
        "command": command_name,
        "args": {
            "track_ref": None if callable(track_ref) else track_ref,
            "routing_type": routing_type,
            "routing_channel": routing_channel,
        },
        "action": _run,
    }
    if callable(track_ref):
        execute_kwargs["resolved_args"] = lambda: {
            "track_ref": _resolve_track_ref(track_ref),
            "routing_type": routing_type,
            "routing_channel": routing_channel,
        }
    execute_command(ctx, **execute_kwargs)


def register(app: typer.Typer) -> None:
    app.add_typer(track_app, name="track")
