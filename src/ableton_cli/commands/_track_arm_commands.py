from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._track_shared import TrackArgument
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec

ARM_GET_SPEC = TrackCommandSpec(
    command_name="track arm get",
    client_method="track_arm_get",
)

ARM_SET_SPEC = TrackValueCommandSpec[bool](
    command_name="track arm set",
    client_method="track_arm_set",
)


def register_commands(
    arm_app: typer.Typer,
    *,
    run_track_command_spec: Callable[..., None],
    run_track_value_command_spec: Callable[..., None],
) -> None:
    @arm_app.command("get")
    def arm_get(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=ARM_GET_SPEC,
            track=track,
        )

    @arm_app.command("set")
    def arm_set(
        ctx: typer.Context,
        track: TrackArgument,
        value: Annotated[bool, typer.Argument(help="Arm value: true|false")],
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=ARM_SET_SPEC,
            track=track,
            value=value,
        )
