from __future__ import annotations

import typer

from . import __version__
from .errors import ExitCode


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=ExitCode.SUCCESS.value)
