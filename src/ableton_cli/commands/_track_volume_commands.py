from __future__ import annotations

from collections.abc import Callable

import typer

from ._track_shared import TrackArgument, VolumeValueArgument
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec
from ._validation import require_track_and_volume

VOLUME_GET_SPEC = TrackCommandSpec(
    command_name="track volume get",
    client_method="track_volume_get",
)

VOLUME_SET_SPEC = TrackValueCommandSpec[float](
    command_name="track volume set",
    client_method="track_volume_set",
    validators=(require_track_and_volume,),
)


def register_commands(
    volume_app: typer.Typer,
    *,
    run_track_command_spec: Callable[..., None],
    run_track_value_command_spec: Callable[..., None],
) -> None:
    @volume_app.command("get")
    def volume_get(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=VOLUME_GET_SPEC,
            track=track,
        )

    @volume_app.command("set")
    def volume_set(
        ctx: typer.Context,
        track: TrackArgument,
        value: VolumeValueArgument,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=VOLUME_SET_SPEC,
            track=track,
            value=value,
        )
