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
from ._validation import require_send_index, require_volume_value


def register_commands(
    send_app: typer.Typer,
    *,
    run_track_send_command: Callable[..., None],
    run_track_send_value_command: Callable[..., None],
) -> None:
    @send_app.command("get")
    def send_get(
        ctx: typer.Context,
        send: Annotated[int, typer.Argument(help="Send index (0-based)")],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_send_command(
            ctx,
            command_name="track send get",
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            send=require_send_index(send),
            fn=lambda client, resolved_track_ref, valid_send: client.track_send_get(
                resolved_track_ref,
                valid_send,
            ),
        )

    @send_app.command("set")
    def send_set(
        ctx: typer.Context,
        send: Annotated[int, typer.Argument(help="Send index (0-based)")],
        value: Annotated[float, typer.Argument(help="Volume value in [0.0, 1.0]")],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_send_value_command(
            ctx,
            command_name="track send set",
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            send=require_send_index(send),
            value=require_volume_value(value),
            fn=lambda client, resolved_track_ref, valid_send, valid_value: client.track_send_set(
                resolved_track_ref,
                valid_send,
                valid_value,
            ),
        )
