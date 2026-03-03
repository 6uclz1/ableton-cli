from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._track_shared import TrackArgument
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec

MUTE_GET_SPEC = TrackCommandSpec(
    command_name="track mute get",
    client_method="track_mute_get",
)

MUTE_SET_SPEC = TrackValueCommandSpec[bool](
    command_name="track mute set",
    client_method="track_mute_set",
)


def register_commands(
    mute_app: typer.Typer,
    *,
    run_track_command_spec: Callable[..., None],
    run_track_value_command_spec: Callable[..., None],
) -> None:
    @mute_app.command("get")
    def mute_get(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=MUTE_GET_SPEC,
            track=track,
        )

    @mute_app.command("set")
    def mute_set(
        ctx: typer.Context,
        track: TrackArgument,
        value: Annotated[bool, typer.Argument(help="Mute value: true|false")],
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=MUTE_SET_SPEC,
            track=track,
            value=value,
        )
