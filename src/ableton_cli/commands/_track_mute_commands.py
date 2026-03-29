from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..refs import (
    SelectedTrackOption,
    TrackIndexOption,
    TrackNameOption,
    TrackQueryOption,
    TrackStableRefOption,
    build_track_ref,
)
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
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=MUTE_GET_SPEC,
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
        )

    @mute_app.command("set")
    def mute_set(
        ctx: typer.Context,
        value: Annotated[bool, typer.Argument(help="Mute value: true|false")],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=MUTE_SET_SPEC,
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            value=value,
        )
