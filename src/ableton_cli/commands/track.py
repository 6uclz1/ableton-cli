from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import typer

from ..runtime import execute_command, get_client
from ._track_arm_commands import register_commands as register_arm_commands
from ._track_info_commands import register_commands as register_info_commands
from ._track_mute_commands import register_commands as register_mute_commands
from ._track_name_commands import register_commands as register_name_commands
from ._track_panning_commands import register_commands as register_panning_commands
from ._track_shared import (
    TrackAction,
    TrackValidator,
    TrackValueAction,
    TrackValueValidator,
    TValue,
)
from ._track_solo_commands import register_commands as register_solo_commands
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec
from ._track_volume_commands import register_commands as register_volume_commands
from ._validation import (
    require_track_and_value,
    require_track_index,
)


def run_track_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track: int,
    fn: TrackAction,
    validators: Sequence[TrackValidator] | None = None,
) -> None:
    active_validators = validators if validators is not None else (require_track_index,)

    def _run() -> dict[str, object]:
        valid_track = track
        for validator in active_validators:
            valid_track = validator(valid_track)
        client = get_client(ctx)
        return fn(client, valid_track)

    execute_command(
        ctx,
        command=command_name,
        args={"track": track},
        action=_run,
    )


def run_track_value_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track: int,
    value: TValue,
    fn: TrackValueAction[TValue],
    value_name: str = "value",
    validators: Sequence[TrackValueValidator[TValue]] | None = None,
) -> None:
    active_validators = validators if validators is not None else (require_track_and_value,)

    def _run() -> dict[str, object]:
        valid_track = track
        valid_value = value
        for validator in active_validators:
            valid_track, valid_value = validator(valid_track, valid_value)
        client = get_client(ctx)
        return fn(client, valid_track, valid_value)

    execute_command(
        ctx,
        command=command_name,
        args={"track": track, value_name: value},
        action=_run,
    )


def run_track_command_spec(
    ctx: typer.Context,
    *,
    spec: TrackCommandSpec,
    track: int,
) -> None:
    run_track_command(
        ctx,
        command_name=spec.command_name,
        track=track,
        validators=spec.validators,
        fn=lambda client, valid_track: cast(
            dict[str, object],
            getattr(client, spec.client_method)(valid_track),
        ),
    )


def run_track_value_command_spec(
    ctx: typer.Context,
    *,
    spec: TrackValueCommandSpec[TValue],
    track: int,
    value: TValue,
) -> None:
    run_track_value_command(
        ctx,
        command_name=spec.command_name,
        track=track,
        value=value,
        value_name=spec.value_name,
        validators=spec.validators,
        fn=lambda client, valid_track, valid_value: cast(
            dict[str, object],
            getattr(client, spec.client_method)(valid_track, valid_value),
        ),
    )


track_app = typer.Typer(help="Single-track commands", no_args_is_help=True)
volume_app = typer.Typer(help="Track volume commands", no_args_is_help=True)
name_app = typer.Typer(help="Track naming commands", no_args_is_help=True)
mute_app = typer.Typer(help="Track mute commands", no_args_is_help=True)
solo_app = typer.Typer(help="Track solo commands", no_args_is_help=True)
arm_app = typer.Typer(help="Track arm commands", no_args_is_help=True)
panning_app = typer.Typer(help="Track panning commands", no_args_is_help=True)

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


track_app.add_typer(volume_app, name="volume")
track_app.add_typer(name_app, name="name")
track_app.add_typer(mute_app, name="mute")
track_app.add_typer(solo_app, name="solo")
track_app.add_typer(arm_app, name="arm")
track_app.add_typer(panning_app, name="panning")


def register(app: typer.Typer) -> None:
    app.add_typer(track_app, name="track")
