from __future__ import annotations

from collections.abc import Callable

import typer

from ..runtime import execute_command, get_client
from ._arrangement_clip_commands import register_commands as register_clip_commands
from ._arrangement_clip_props_commands import register_commands as register_clip_props_commands
from ._arrangement_notes_commands import register_commands as register_notes_commands
from ._arrangement_record_commands import register_commands as register_record_commands
from ._arrangement_session_commands import register_commands as register_session_commands
from ._arrangement_specs import ArrangementCommandSpec
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared

arrangement_app = typer.Typer(help="Arrangement commands", no_args_is_help=True)
record_app = typer.Typer(help="Arrangement recording commands", no_args_is_help=True)
clip_app = typer.Typer(help="Arrangement clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Arrangement clip note commands", no_args_is_help=True)
props_app = typer.Typer(help="Arrangement clip property commands", no_args_is_help=True)
loop_app = typer.Typer(help="Arrangement clip loop commands", no_args_is_help=True)
marker_app = typer.Typer(help="Arrangement clip marker commands", no_args_is_help=True)
warp_app = typer.Typer(help="Arrangement clip warp commands", no_args_is_help=True)
gain_app = typer.Typer(help="Arrangement clip gain commands", no_args_is_help=True)
transpose_app = typer.Typer(help="Arrangement clip transpose commands", no_args_is_help=True)
file_app = typer.Typer(help="Arrangement clip file commands", no_args_is_help=True)


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: ArrangementCommandSpec,
    args: dict[str, object],
    method_kwargs: dict[str, object] | Callable[[], dict[str, object]] | None = None,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
        method_kwargs=method_kwargs,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


register_record_commands(record_app, run_client_command_spec=run_client_command_spec)
register_clip_commands(clip_app, run_client_command_spec=run_client_command_spec)
register_clip_props_commands(
    props_app=props_app,
    loop_app=loop_app,
    marker_app=marker_app,
    warp_app=warp_app,
    gain_app=gain_app,
    transpose_app=transpose_app,
    file_app=file_app,
    run_client_command_spec=run_client_command_spec,
)
register_notes_commands(notes_app, run_client_command_spec=run_client_command_spec)
register_session_commands(arrangement_app, run_client_command_spec=run_client_command_spec)


arrangement_app.add_typer(record_app, name="record")
clip_app.add_typer(notes_app, name="notes")
clip_app.add_typer(props_app, name="props")
clip_app.add_typer(loop_app, name="loop")
clip_app.add_typer(marker_app, name="marker")
clip_app.add_typer(warp_app, name="warp")
clip_app.add_typer(gain_app, name="gain")
clip_app.add_typer(transpose_app, name="transpose")
clip_app.add_typer(file_app, name="file")
arrangement_app.add_typer(clip_app, name="clip")


def register(app: typer.Typer) -> None:
    app.add_typer(arrangement_app, name="arrangement")
