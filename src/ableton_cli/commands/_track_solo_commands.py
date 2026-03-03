from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._track_shared import TrackArgument
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec

SOLO_GET_SPEC = TrackCommandSpec(
    command_name="track solo get",
    client_method="track_solo_get",
)

SOLO_SET_SPEC = TrackValueCommandSpec[bool](
    command_name="track solo set",
    client_method="track_solo_set",
)


def register_commands(
    solo_app: typer.Typer,
    *,
    run_track_command_spec: Callable[..., None],
    run_track_value_command_spec: Callable[..., None],
) -> None:
    @solo_app.command("get")
    def solo_get(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=SOLO_GET_SPEC,
            track=track,
        )

    @solo_app.command("set")
    def solo_set(
        ctx: typer.Context,
        track: TrackArgument,
        value: Annotated[bool, typer.Argument(help="Solo value: true|false")],
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=SOLO_SET_SPEC,
            track=track,
            value=value,
        )
