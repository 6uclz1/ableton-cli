from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import invalid_argument, require_non_empty_string, require_non_negative

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
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).get_track_info(track)

    execute_command(
        ctx,
        command="track info",
        args={"track": track},
        action=_run,
    )


@volume_app.command("get")
def volume_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _run() -> dict[str, float | int]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_volume_get(track)

    execute_command(
        ctx,
        command="track volume get",
        args={"track": track},
        action=_run,
    )


@volume_app.command("set")
def volume_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    value: Annotated[float, typer.Argument(help="Volume value in [0.0, 1.0]")],
) -> None:
    def _run() -> dict[str, float | int]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        if value < 0.0 or value > 1.0:
            raise invalid_argument(
                message=f"value must be between 0.0 and 1.0, got {value}",
                hint="Use a normalized volume value such as 0.75.",
            )
        return get_client(ctx).track_volume_set(track, value)

    execute_command(
        ctx,
        command="track volume set",
        args={"track": track, "value": value},
        action=_run,
    )


@name_app.command("set")
def track_name_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    name: Annotated[str, typer.Argument(help="New track name")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_name = require_non_empty_string(
            "name",
            name,
            hint="Pass a non-empty track name.",
        )
        return get_client(ctx).set_track_name(track, valid_name)

    execute_command(
        ctx,
        command="track name set",
        args={"track": track, "name": name},
        action=_run,
    )


@mute_app.command("get")
def mute_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_mute_get(track)

    execute_command(
        ctx,
        command="track mute get",
        args={"track": track},
        action=_run,
    )


@mute_app.command("set")
def mute_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    value: Annotated[bool, typer.Argument(help="Mute value: true|false")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_mute_set(track, value)

    execute_command(
        ctx,
        command="track mute set",
        args={"track": track, "value": value},
        action=_run,
    )


@solo_app.command("get")
def solo_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_solo_get(track)

    execute_command(
        ctx,
        command="track solo get",
        args={"track": track},
        action=_run,
    )


@solo_app.command("set")
def solo_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    value: Annotated[bool, typer.Argument(help="Solo value: true|false")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_solo_set(track, value)

    execute_command(
        ctx,
        command="track solo set",
        args={"track": track, "value": value},
        action=_run,
    )


@arm_app.command("get")
def arm_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_arm_get(track)

    execute_command(
        ctx,
        command="track arm get",
        args={"track": track},
        action=_run,
    )


@arm_app.command("set")
def arm_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    value: Annotated[bool, typer.Argument(help="Arm value: true|false")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_arm_set(track, value)

    execute_command(
        ctx,
        command="track arm set",
        args={"track": track, "value": value},
        action=_run,
    )


@panning_app.command("get")
def panning_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        return get_client(ctx).track_panning_get(track)

    execute_command(
        ctx,
        command="track panning get",
        args={"track": track},
        action=_run,
    )


@panning_app.command("set")
def panning_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    value: Annotated[float, typer.Argument(help="Panning value in [-1.0, 1.0]")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        if value < -1.0 or value > 1.0:
            raise invalid_argument(
                message=f"value must be between -1.0 and 1.0, got {value}",
                hint="Use a normalized panning value such as -0.25.",
            )
        return get_client(ctx).track_panning_set(track, value)

    execute_command(
        ctx,
        command="track panning set",
        args={"track": track, "value": value},
        action=_run,
    )


track_app.add_typer(volume_app, name="volume")
track_app.add_typer(name_app, name="name")
track_app.add_typer(mute_app, name="mute")
track_app.add_typer(solo_app, name="solo")
track_app.add_typer(arm_app, name="arm")
track_app.add_typer(panning_app, name="panning")


def register(app: typer.Typer) -> None:
    app.add_typer(track_app, name="track")
