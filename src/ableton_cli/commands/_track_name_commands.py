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
from ._track_specs import TrackValueCommandSpec
from ._validation import require_non_empty_string

NAME_SET_SPEC = TrackValueCommandSpec[str](
    command_name="track name set",
    client_method="set_track_name",
    value_name="name",
    validators=(
        lambda value: require_non_empty_string("name", value, hint="Pass a non-empty track name."),
    ),
)


def register_commands(
    name_app: typer.Typer,
    *,
    run_track_value_command_spec: Callable[..., None],
) -> None:
    @name_app.command("set")
    def track_name_set(
        ctx: typer.Context,
        name: Annotated[str, typer.Argument(help="New track name")],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=NAME_SET_SPEC,
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            value=name,
        )
