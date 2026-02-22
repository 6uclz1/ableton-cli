from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .bootstrap import build_runtime_context
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
from .errors import AppError
from .output import OutputMode, emit_human_error, emit_json, error_payload
from .version import version_callback

_COMMAND_MODULES = (
    setup,
    batch,
    song,
    arrangement,
    session,
    scenes,
    tracks,
    transport,
    track,
    clip,
    browser,
    device,
    synth,
    effect,
)


def register_commands(app: typer.Typer) -> None:
    for command_module in _COMMAND_MODULES:
        command_module.register(app)


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
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
) -> None:
    del version

    try:
        ctx.obj = build_runtime_context(
            host=host,
            port=port,
            timeout_ms=timeout_ms,
            protocol_version=protocol_version,
            output=output,
            verbose=verbose,
            log_file=log_file,
            config=config,
            no_color=no_color,
            quiet=quiet,
        )
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


def create_app() -> typer.Typer:
    app = typer.Typer(
        help="Control and inspect Ableton Live through a local Remote Script.",
        no_args_is_help=True,
        add_completion=True,
    )
    app.callback()(main)
    register_commands(app)
    return app
