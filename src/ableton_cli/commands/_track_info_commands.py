from __future__ import annotations

from collections.abc import Callable

import typer

from ..refs import (
    SelectedTrackOption,
    TrackIndexOption,
    TrackNameOption,
    TrackQueryOption,
    TrackStableRefOption,
    build_track_ref,
)
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
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=TRACK_INFO_SPEC,
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
        )
