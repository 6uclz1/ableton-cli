from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypeVar

import typer

from ..runtime import execute_command, get_client
from ._validation import require_float_in_range, require_non_empty_string, require_track_index

TValue = TypeVar("TValue")

TrackArgument = Annotated[int, typer.Argument(help="Track index (0-based)")]
VolumeValueArgument = Annotated[float, typer.Argument(help="Volume value in [0.0, 1.0]")]
PanningValueArgument = Annotated[float, typer.Argument(help="Panning value in [-1.0, 1.0]")]


def _execute_track_get(
    ctx: typer.Context,
    *,
    command: str,
    track: int,
    action: Callable[[int], dict[str, object]],
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_track_index(track)
        return action(valid_track)

    execute_command(
        ctx,
        command=command,
        args={"track": track},
        action=_run,
    )


def _execute_track_set(
    ctx: typer.Context,
    *,
    command: str,
    track: int,
    value: TValue,
    action: Callable[[int, TValue], dict[str, object]],
    value_name: str = "value",
    validator: Callable[[TValue], TValue] | None = None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_track_index(track)
        valid_value = validator(value) if validator is not None else value
        return action(valid_track, valid_value)

    execute_command(
        ctx,
        command=command,
        args={"track": track, value_name: value},
        action=_run,
    )


def _require_volume_value(value: float) -> float:
    return require_float_in_range(
        "value",
        value,
        minimum=0.0,
        maximum=1.0,
        hint="Use a normalized volume value such as 0.75.",
    )


def _require_panning_value(value: float) -> float:
    return require_float_in_range(
        "value",
        value,
        minimum=-1.0,
        maximum=1.0,
        hint="Use a normalized panning value such as -0.25.",
    )


def _require_track_name(value: str) -> str:
    return require_non_empty_string(
        "name",
        value,
        hint="Pass a non-empty track name.",
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
    _execute_track_get(
        ctx,
        command="track info",
        track=track,
        action=lambda valid_track: get_client(ctx).get_track_info(valid_track),
    )


@volume_app.command("get")
def volume_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    _execute_track_get(
        ctx,
        command="track volume get",
        track=track,
        action=lambda valid_track: get_client(ctx).track_volume_get(valid_track),
    )


@volume_app.command("set")
def volume_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: VolumeValueArgument,
) -> None:
    _execute_track_set(
        ctx,
        command="track volume set",
        track=track,
        value=value,
        validator=_require_volume_value,
        action=lambda valid_track, valid_value: get_client(ctx).track_volume_set(
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
    _execute_track_set(
        ctx,
        command="track name set",
        track=track,
        value=name,
        value_name="name",
        validator=_require_track_name,
        action=lambda valid_track, valid_name: get_client(ctx).set_track_name(
            valid_track,
            valid_name,
        ),
    )


@mute_app.command("get")
def mute_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    _execute_track_get(
        ctx,
        command="track mute get",
        track=track,
        action=lambda valid_track: get_client(ctx).track_mute_get(valid_track),
    )


@mute_app.command("set")
def mute_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: Annotated[bool, typer.Argument(help="Mute value: true|false")],
) -> None:
    _execute_track_set(
        ctx,
        command="track mute set",
        track=track,
        value=value,
        action=lambda valid_track, valid_value: get_client(ctx).track_mute_set(
            valid_track,
            valid_value,
        ),
    )


@solo_app.command("get")
def solo_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    _execute_track_get(
        ctx,
        command="track solo get",
        track=track,
        action=lambda valid_track: get_client(ctx).track_solo_get(valid_track),
    )


@solo_app.command("set")
def solo_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: Annotated[bool, typer.Argument(help="Solo value: true|false")],
) -> None:
    _execute_track_set(
        ctx,
        command="track solo set",
        track=track,
        value=value,
        action=lambda valid_track, valid_value: get_client(ctx).track_solo_set(
            valid_track,
            valid_value,
        ),
    )


@arm_app.command("get")
def arm_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    _execute_track_get(
        ctx,
        command="track arm get",
        track=track,
        action=lambda valid_track: get_client(ctx).track_arm_get(valid_track),
    )


@arm_app.command("set")
def arm_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: Annotated[bool, typer.Argument(help="Arm value: true|false")],
) -> None:
    _execute_track_set(
        ctx,
        command="track arm set",
        track=track,
        value=value,
        action=lambda valid_track, valid_value: get_client(ctx).track_arm_set(
            valid_track,
            valid_value,
        ),
    )


@panning_app.command("get")
def panning_get(
    ctx: typer.Context,
    track: TrackArgument,
) -> None:
    _execute_track_get(
        ctx,
        command="track panning get",
        track=track,
        action=lambda valid_track: get_client(ctx).track_panning_get(valid_track),
    )


@panning_app.command("set")
def panning_set(
    ctx: typer.Context,
    track: TrackArgument,
    value: PanningValueArgument,
) -> None:
    _execute_track_set(
        ctx,
        command="track panning set",
        track=track,
        value=value,
        validator=_require_panning_value,
        action=lambda valid_track, valid_value: get_client(ctx).track_panning_set(
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
