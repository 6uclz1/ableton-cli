from __future__ import annotations

from collections.abc import Callable

import typer

from ..runtime import execute_command, get_client
from ._arrangement_clip_commands import register_commands as register_clip_commands
from ._arrangement_notes_commands import register_commands as register_notes_commands
from ._arrangement_record_commands import register_commands as register_record_commands
from ._arrangement_session_commands import register_commands as register_session_commands
from ._arrangement_specs import ArrangementCommandSpec
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared

arrangement_app = typer.Typer(help="Arrangement commands", no_args_is_help=True)
record_app = typer.Typer(help="Arrangement recording commands", no_args_is_help=True)
clip_app = typer.Typer(help="Arrangement clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Arrangement clip note commands", no_args_is_help=True)


def run_client_command(
    ctx: typer.Context,
    *,
    command_name: str,
    args: dict[str, object],
    fn: Callable[[object], dict[str, object]],
) -> None:
    run_client_command_shared(
        ctx,
        command_name=command_name,
        args=args,
        fn=fn,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


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
register_notes_commands(notes_app, run_client_command_spec=run_client_command_spec)
register_session_commands(arrangement_app, run_client_command_spec=run_client_command_spec)


arrangement_app.add_typer(record_app, name="record")
clip_app.add_typer(notes_app, name="notes")
arrangement_app.add_typer(clip_app, name="clip")


def register(app: typer.Typer) -> None:
    app.add_typer(arrangement_app, name="arrangement")
