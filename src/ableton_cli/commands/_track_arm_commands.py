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
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=ARM_GET_SPEC,
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
        )

    @arm_app.command("set")
    def arm_set(
        ctx: typer.Context,
        value: Annotated[bool, typer.Argument(help="Arm value: true|false")],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=ARM_SET_SPEC,
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            value=value,
        )
