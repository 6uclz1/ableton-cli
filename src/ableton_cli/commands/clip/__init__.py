from __future__ import annotations

import typer

from ...runtime import get_client as _runtime_get_client
from ._active_commands import register_active_commands
from ._clip_root_commands import register_clip_root_commands
from ._groove_commands import register_groove_commands
from ._name_commands import register_name_commands
from ._notes_commands import register_notes_commands

clip_app = typer.Typer(help="Clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Clip note commands", no_args_is_help=True)
name_app = typer.Typer(help="Clip naming commands", no_args_is_help=True)
active_app = typer.Typer(help="Clip active-state commands", no_args_is_help=True)
groove_app = typer.Typer(help="Clip groove commands", no_args_is_help=True)
groove_amount_app = typer.Typer(help="Clip groove amount commands", no_args_is_help=True)


def get_client(ctx: typer.Context):  # noqa: ANN201
    return _runtime_get_client(ctx)


register_notes_commands(notes_app)
register_name_commands(name_app)
register_active_commands(active_app)
register_groove_commands(groove_app, groove_amount_app)
register_clip_root_commands(clip_app)

clip_app.add_typer(notes_app, name="notes")
clip_app.add_typer(name_app, name="name")
clip_app.add_typer(active_app, name="active")
groove_app.add_typer(groove_amount_app, name="amount")
clip_app.add_typer(groove_app, name="groove")


def register(app: typer.Typer) -> None:
    app.add_typer(clip_app, name="clip")
