from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .commands import (
    arrangement,
    batch,
    browser,
    clip,
    device,
    effect,
    scenes,
    session,
    setup,
    song,
    synth,
    track,
    tracks,
    transport,
)
from .config import resolve_settings
from .errors import AppError, ExitCode
from .logging_setup import configure_logging
from .output import OutputMode, emit_human_error, emit_json, error_payload
from .runtime import RuntimeContext

app = typer.Typer(
    help="Control and inspect Ableton Live through a local Remote Script.",
    no_args_is_help=True,
    add_completion=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=ExitCode.SUCCESS.value)


@app.callback()
def main(
    ctx: typer.Context,
    host: Annotated[str | None, typer.Option("--host", help="Remote host")] = None,
    port: Annotated[int | None, typer.Option("--port", help="Remote port")] = None,
    timeout_ms: Annotated[
        int | None,
        typer.Option("--timeout-ms", help="Request timeout in milliseconds"),
    ] = None,
    protocol_version: Annotated[
        int | None,
        typer.Option("--protocol-version", help="Protocol version for CLI/Remote handshake"),
    ] = None,
    output: Annotated[
        OutputMode,
        typer.Option("--output", help="Output mode", case_sensitive=False),
    ] = OutputMode.HUMAN,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging")] = False,
    log_file: Annotated[str | None, typer.Option("--log-file", help="Log file path")] = None,
    config: Annotated[Path | None, typer.Option("--config", help="Config file path")] = None,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color output")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", help="Suppress human success output")] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
) -> None:
    del version

    cli_overrides = {
        "host": host,
        "port": port,
        "timeout_ms": timeout_ms,
        "log_file": log_file,
        "protocol_version": protocol_version,
    }

    try:
        settings = resolve_settings(cli_overrides=cli_overrides, config_path=config)
    except AppError as exc:
        payload = error_payload(
            command="bootstrap",
            args={},
            code=exc.error_code,
            message=exc.message,
            hint=exc.hint,
            details=exc.details or None,
        )
        if output == OutputMode.JSON:
            emit_json(payload)
        else:
            emit_human_error(exc.error_code, exc.message, exc.hint)
        raise typer.Exit(code=exc.exit_code.value) from exc

    configure_logging(verbose=verbose, quiet=quiet, log_file=settings.log_file)

    ctx.obj = RuntimeContext(
        settings=settings,
        output_mode=output,
        quiet=quiet,
        no_color=no_color,
    )


setup.register(app)
batch.register(app)
song.register(app)
arrangement.register(app)
session.register(app)
scenes.register(app)
tracks.register(app)
transport.register(app)
track.register(app)
clip.register(app)
browser.register(app)
device.register(app)
synth.register(app)
effect.register(app)
