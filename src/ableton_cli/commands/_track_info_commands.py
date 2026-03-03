from __future__ import annotations

from collections.abc import Callable

import typer

from ._track_shared import TrackArgument
from ._track_specs import TrackCommandSpec

TRACK_INFO_SPEC = TrackCommandSpec(
    command_name="track info",
    client_method="get_track_info",
)


def register_commands(
    track_app: typer.Typer,
    *,
    run_track_command_spec: Callable[..., None],
) -> None:
    @track_app.command("info")
    def track_info(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=TRACK_INFO_SPEC,
            track=track,
        )
