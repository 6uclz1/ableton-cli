from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Annotated, TypeVar

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    require_track_and_name,
    require_track_and_pan,
    require_track_and_value,
    require_track_and_volume,
    require_track_index,
)

TValue = TypeVar("TValue")

TrackArgument = Annotated[int, typer.Argument(help="Track index (0-based)")]
VolumeValueArgument = Annotated[float, typer.Argument(help="Volume value in [0.0, 1.0]")]
PanningValueArgument = Annotated[float, typer.Argument(help="Panning value in [-1.0, 1.0]")]

TrackValidator = Callable[[int], int]
TrackValueValidator = Callable[[int, TValue], tuple[int, TValue]]
TrackAction = Callable[[object, int], dict[str, object]]
TrackValueAction = Callable[[object, int, TValue], dict[str, object]]


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


track_app = typer.Typer(help="Single-track commands", no_args_is_help=True)
volume_app = typer.Typer(help="Track volume commands", no_args_is_help=True)
name_app = typer.Typer(help="Track naming commands", no_args_is_help=True)
mute_app = typer.Typer(help="Track mute commands", no_args_is_help=True)
solo_app = typer.Typer(help="Track solo commands", no_args_is_help=True)
arm_app = typer.Typer(help="Track arm commands", no_args_is_help=True)
panning_app = typer.Typer(help="Track panning commands", no_args_is_help=True)


@track_app.command("info")
def track_info(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    run_track_command(
        ctx,
        command_name="track info",
        track=track,
        fn=lambda client, valid_track: client.get_track_info(valid_track),
    )


@volume_app.command("get")
def volume_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    run_track_command(
        ctx,
        command_name="track volume get",
        track=track,
        fn=lambda client, valid_track: client.track_volume_get(valid_track),
    )


@volume_app.command("set")
def volume_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: VolumeValueArgument,
) -> None:
    run_track_value_command(
        ctx,
        command_name="track volume set",
        track=track,
        value=value,
        validators=[require_track_and_volume],
        fn=lambda client, valid_track, valid_value: client.track_volume_set(
            valid_track,
            valid_value,
        ),
    )


@name_app.command("set")
def track_name_set(
    ctx: typer.Context,
    track: TrackArgument,
    name: Annotated[str, typer.Argument(help="New track name")],
) -> None:
    run_track_value_command(
        ctx,
        command_name="track name set",
        track=track,
        value=name,
        value_name="name",
        validators=[require_track_and_name],
        fn=lambda client, valid_track, valid_name: client.set_track_name(
            valid_track,
            valid_name,
        ),
    )


@mute_app.command("get")
def mute_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    run_track_command(
        ctx,
        command_name="track mute get",
        track=track,
        fn=lambda client, valid_track: client.track_mute_get(valid_track),
    )


@mute_app.command("set")
def mute_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: Annotated[bool, typer.Argument(help="Mute value: true|false")],
) -> None:
    run_track_value_command(
        ctx,
        command_name="track mute set",
        track=track,
        value=value,
        fn=lambda client, valid_track, valid_value: client.track_mute_set(
            valid_track,
            valid_value,
        ),
    )


@solo_app.command("get")
def solo_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    run_track_command(
        ctx,
        command_name="track solo get",
        track=track,
        fn=lambda client, valid_track: client.track_solo_get(valid_track),
    )


@solo_app.command("set")
def solo_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: Annotated[bool, typer.Argument(help="Solo value: true|false")],
) -> None:
    run_track_value_command(
        ctx,
        command_name="track solo set",
        track=track,
        value=value,
        fn=lambda client, valid_track, valid_value: client.track_solo_set(
            valid_track,
            valid_value,
        ),
    )


@arm_app.command("get")
def arm_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    run_track_command(
        ctx,
        command_name="track arm get",
        track=track,
        fn=lambda client, valid_track: client.track_arm_get(valid_track),
    )


@arm_app.command("set")
def arm_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: Annotated[bool, typer.Argument(help="Arm value: true|false")],
) -> None:
    run_track_value_command(
        ctx,
        command_name="track arm set",
        track=track,
        value=value,
        fn=lambda client, valid_track, valid_value: client.track_arm_set(
            valid_track,
            valid_value,
        ),
    )


@panning_app.command("get")
def panning_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    run_track_command(
        ctx,
        command_name="track panning get",
        track=track,
        fn=lambda client, valid_track: client.track_panning_get(valid_track),
    )


@panning_app.command("set")
def panning_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: PanningValueArgument,
) -> None:
    run_track_value_command(
        ctx,
        command_name="track panning set",
        track=track,
        value=value,
        validators=[require_track_and_pan],
        fn=lambda client, valid_track, valid_value: client.track_panning_set(
            valid_track,
            valid_value,
        ),
    )


track_app.add_typer(volume_app, name="volume")
track_app.add_typer(name_app, name="name")
track_app.add_typer(mute_app, name="mute")
track_app.add_typer(solo_app, name="solo")
track_app.add_typer(arm_app, name="arm")
track_app.add_typer(panning_app, name="panning")


def register(app: typer.Typer) -> None:
    app.add_typer(track_app, name="track")
