from __future__ import annotations

from collections.abc import Callable

import typer

from ._track_shared import PanningValueArgument, TrackArgument
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec
from ._validation import require_track_and_pan

PANNING_GET_SPEC = TrackCommandSpec(
    command_name="track panning get",
    client_method="track_panning_get",
)

PANNING_SET_SPEC = TrackValueCommandSpec[float](
    command_name="track panning set",
    client_method="track_panning_set",
    validators=(require_track_and_pan,),
)


def register_commands(
    panning_app: typer.Typer,
    *,
    run_track_command_spec: Callable[..., None],
    run_track_value_command_spec: Callable[..., None],
) -> None:
    @panning_app.command("get")
    def panning_get(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=PANNING_GET_SPEC,
            track=track,
        )

    @panning_app.command("set")
    def panning_set(
        ctx: typer.Context,
        track: TrackArgument,
        value: PanningValueArgument,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=PANNING_SET_SPEC,
            track=track,
            value=value,
        )
