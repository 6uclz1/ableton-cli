from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._track_shared import TrackArgument
from ._track_specs import TrackValueCommandSpec
from ._validation import require_track_and_name

NAME_SET_SPEC = TrackValueCommandSpec[str](
    command_name="track name set",
    client_method="set_track_name",
    value_name="name",
    validators=(require_track_and_name,),
)


def register_commands(
    name_app: typer.Typer,
    *,
    run_track_value_command_spec: Callable[..., None],
) -> None:
    @name_app.command("set")
    def track_name_set(
        ctx: typer.Context,
        track: TrackArgument,
        name: Annotated[str, typer.Argument(help="New track name")],
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=NAME_SET_SPEC,
            track=track,
            value=name,
        )
