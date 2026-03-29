from __future__ import annotations

from collections.abc import Callable

import typer

from ._track_shared import SendArgument, TrackArgument, VolumeValueArgument
from ._validation import require_track_send, require_track_send_and_volume


def register_commands(
    send_app: typer.Typer,
    *,
    run_track_send_command: Callable[..., None],
    run_track_send_value_command: Callable[..., None],
) -> None:
    @send_app.command("get")
    def send_get(
        ctx: typer.Context,
        track: TrackArgument,
        send: SendArgument,
    ) -> None:
        run_track_send_command(
            ctx,
            command_name="track send get",
            track=track,
            send=send,
            fn=lambda client, valid_track, valid_send: client.track_send_get(
                valid_track,
                valid_send,
            ),
            validator=require_track_send,
        )

    @send_app.command("set")
    def send_set(
        ctx: typer.Context,
        track: TrackArgument,
        send: SendArgument,
        value: VolumeValueArgument,
    ) -> None:
        run_track_send_value_command(
            ctx,
            command_name="track send set",
            track=track,
            send=send,
            value=value,
            fn=(
                lambda client, valid_track, valid_send, valid_value: client.track_send_set(
                    valid_track,
                    valid_send,
                    valid_value,
                )
            ),
            validator=require_track_send_and_volume,
        )
