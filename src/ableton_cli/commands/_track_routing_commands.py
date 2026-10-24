from __future__ import annotations

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
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_routing_get(
            ctx,
            command_name="track routing input get",
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            fn_name="track_routing_input_get",
        )

    @input_app.command("set")
    def track_routing_input_set(
        ctx: typer.Context,
        routing_type: Annotated[str, typer.Option("--type", help="Input routing type")],
        routing_channel: Annotated[
            str | None,
            typer.Option("--channel", help="Input routing channel; omit for Live's default"),
        ] = None,
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_routing_set(
            ctx,
            command_name="track routing input set",
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            routing_type=routing_type,
            routing_channel=routing_channel,
            fn_name="track_routing_input_set",
        )

    @output_app.command("get")
    def track_routing_output_get(
        ctx: typer.Context,
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_routing_get(
            ctx,
            command_name="track routing output get",
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            fn_name="track_routing_output_get",
        )

    @output_app.command("set")
    def track_routing_output_set(
        ctx: typer.Context,
        routing_type: Annotated[str, typer.Option("--type", help="Output routing type")],
        routing_channel: Annotated[
            str | None,
            typer.Option("--channel", help="Output routing channel; omit for Live's default"),
        ] = None,
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_routing_set(
            ctx,
            command_name="track routing output set",
            track_ref=lambda: build_track_ref(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            routing_type=routing_type,
            routing_channel=routing_channel,
            fn_name="track_routing_output_set",
        )

    routing_app.add_typer(input_app, name="input")
    routing_app.add_typer(output_app, name="output")
