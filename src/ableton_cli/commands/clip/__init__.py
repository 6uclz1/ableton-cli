from __future__ import annotations

from typing import Annotated

import typer

from ...runtime import execute_command
from ...runtime import get_client as _runtime_get_client
from ...warp_conform import conform_session_clip_warp
from .._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._active_commands import register_active_commands
from ._clip_root_commands import register_clip_root_commands
from ._groove_commands import register_groove_commands
from ._name_commands import register_name_commands
from ._notes_commands import register_notes_commands
from ._props_commands import register_prop_commands

clip_app = typer.Typer(help="Clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Clip note commands", no_args_is_help=True)
name_app = typer.Typer(help="Clip naming commands", no_args_is_help=True)
active_app = typer.Typer(help="Clip active-state commands", no_args_is_help=True)
groove_app = typer.Typer(help="Clip groove commands", no_args_is_help=True)
groove_amount_app = typer.Typer(help="Clip groove amount commands", no_args_is_help=True)
props_app = typer.Typer(help="Clip property commands", no_args_is_help=True)
loop_app = typer.Typer(help="Clip loop commands", no_args_is_help=True)
marker_app = typer.Typer(help="Clip marker commands", no_args_is_help=True)
warp_app = typer.Typer(help="Clip warp commands", no_args_is_help=True)
warp_marker_app = typer.Typer(help="Clip warp marker commands", no_args_is_help=True)
gain_app = typer.Typer(help="Clip gain commands", no_args_is_help=True)
transpose_app = typer.Typer(help="Clip transpose commands", no_args_is_help=True)
file_app = typer.Typer(help="Clip file commands", no_args_is_help=True)


def get_client(ctx: typer.Context):  # noqa: ANN201
    return _runtime_get_client(ctx)


def run_client_command_spec(ctx: typer.Context, **kwargs: object) -> None:
    run_client_command_spec_shared(
        ctx,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
        **kwargs,
    )


register_notes_commands(notes_app)
register_name_commands(name_app)
register_active_commands(active_app)
register_groove_commands(groove_app, groove_amount_app)
register_clip_root_commands(clip_app)
register_prop_commands(
    props_app=props_app,
    loop_app=loop_app,
    marker_app=marker_app,
    warp_app=warp_app,
    warp_marker_app=warp_marker_app,
    gain_app=gain_app,
    transpose_app=transpose_app,
    file_app=file_app,
    run_client_command_spec=run_client_command_spec,
)


@warp_app.command("conform")
def clip_warp_conform(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index")],
    clip: Annotated[int, typer.Argument(help="Clip slot index")],
    source_bpm: Annotated[float, typer.Option("--source-bpm", help="Source BPM")],
    target_bpm: Annotated[float, typer.Option("--target-bpm", help="Target BPM")],
    profile: Annotated[str, typer.Option("--profile", help="Warp profile")] = "full-mix",
    markers: Annotated[str, typer.Option("--markers", help="Marker strategy")] = "two-point",
    verify: Annotated[
        bool, typer.Option("--verify", help="Verify readback after conforming")
    ] = False,
    force_large_stretch: Annotated[
        bool,
        typer.Option(
            "--force-large-stretch",
            help="Allow stretch ratios below 0.80 or above 1.25",
        ),
    ] = False,
) -> None:
    execute_command(
        ctx,
        command="clip warp conform",
        args={
            "track": track,
            "clip": clip,
            "source_bpm": source_bpm,
            "target_bpm": target_bpm,
            "profile": profile,
            "markers": markers,
            "verify": verify,
            "force_large_stretch": force_large_stretch,
        },
        action=lambda: conform_session_clip_warp(
            get_client(ctx),
            track=track,
            clip=clip,
            source_bpm=source_bpm,
            target_bpm=target_bpm,
            profile=profile,
            markers=markers,
            verify=verify,
            force_large_stretch=force_large_stretch,
        ),
    )


clip_app.add_typer(notes_app, name="notes")
clip_app.add_typer(name_app, name="name")
clip_app.add_typer(active_app, name="active")
clip_app.add_typer(props_app, name="props")
clip_app.add_typer(loop_app, name="loop")
clip_app.add_typer(marker_app, name="marker")
clip_app.add_typer(warp_app, name="warp")
clip_app.add_typer(warp_marker_app, name="warp-marker")
clip_app.add_typer(gain_app, name="gain")
clip_app.add_typer(transpose_app, name="transpose")
clip_app.add_typer(file_app, name="file")
groove_app.add_typer(groove_amount_app, name="amount")
clip_app.add_typer(groove_app, name="groove")


def register(app: typer.Typer) -> None:
    app.add_typer(clip_app, name="clip")
