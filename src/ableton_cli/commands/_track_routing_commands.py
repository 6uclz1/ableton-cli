from __future__ import annotations

from typing import Annotated

import typer

from ._track_shared import TrackArgument
from ._validation import TRACK_INDEX_HINT, require_non_empty_string, require_track_index

ROUTING_TYPE_HINT = "Use one of the exact routing types returned by track routing get."
ROUTING_CHANNEL_HINT = "Use one of the exact routing channels returned by track routing get."


def register_commands(
    routing_app: typer.Typer,
    *,
    run_track_routing_get,
    run_track_routing_set,
) -> None:
    input_app = typer.Typer(help="Track input routing commands", no_args_is_help=True)
    output_app = typer.Typer(help="Track output routing commands", no_args_is_help=True)

    @input_app.command("get")
    def track_routing_input_get(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_routing_get(
            ctx,
            command_name="track routing input get",
            track=track,
            fn_name="track_routing_input_get",
        )

    @input_app.command("set")
    def track_routing_input_set(
        ctx: typer.Context,
        track: TrackArgument,
        routing_type: Annotated[str, typer.Option("--type", help="Input routing type")] = "",
        routing_channel: Annotated[
            str,
            typer.Option("--channel", help="Input routing channel"),
        ] = "",
    ) -> None:
        valid_track = require_track_index(track, hint=TRACK_INDEX_HINT)
        valid_type = require_non_empty_string("type", routing_type, hint=ROUTING_TYPE_HINT)
        valid_channel = require_non_empty_string(
            "channel",
            routing_channel,
            hint=ROUTING_CHANNEL_HINT,
        )
        run_track_routing_set(
            ctx,
            command_name="track routing input set",
            track=valid_track,
            routing_type=valid_type,
            routing_channel=valid_channel,
            fn_name="track_routing_input_set",
        )

    @output_app.command("get")
    def track_routing_output_get(
        ctx: typer.Context,
        track: TrackArgument,
    ) -> None:
        run_track_routing_get(
            ctx,
            command_name="track routing output get",
            track=track,
            fn_name="track_routing_output_get",
        )

    @output_app.command("set")
    def track_routing_output_set(
        ctx: typer.Context,
        track: TrackArgument,
        routing_type: Annotated[str, typer.Option("--type", help="Output routing type")] = "",
        routing_channel: Annotated[
            str,
            typer.Option("--channel", help="Output routing channel"),
        ] = "",
    ) -> None:
        valid_track = require_track_index(track, hint=TRACK_INDEX_HINT)
        valid_type = require_non_empty_string("type", routing_type, hint=ROUTING_TYPE_HINT)
        valid_channel = require_non_empty_string(
            "channel",
            routing_channel,
            hint=ROUTING_CHANNEL_HINT,
        )
        run_track_routing_set(
            ctx,
            command_name="track routing output set",
            track=valid_track,
            routing_type=valid_type,
            routing_channel=valid_channel,
            fn_name="track_routing_output_set",
        )

    routing_app.add_typer(input_app, name="input")
    routing_app.add_typer(output_app, name="output")
