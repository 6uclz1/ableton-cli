from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
import typer

from .bootstrap import build_runtime_context
from .commands import (
    arrangement,
    audio,
    batch,
    browser,
    clip,
    device,
    effect,
    master,
    mixer,
    remix,
    return_track,
    return_tracks,
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
    remix,
    audio,
    batch,
    song,
    arrangement,
    session,
    scenes,
    master,
    mixer,
    return_tracks,
    return_track,
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
    record: Annotated[
        str | None,
        typer.Option("--record", help="Record request/response transport data to JSONL file"),
    ] = None,
    replay: Annotated[
        str | None,
        typer.Option("--replay", help="Replay request/response transport data from JSONL file"),
    ] = None,
    read_only: Annotated[
        bool,
        typer.Option("--read-only", help="Reject write commands before dispatch"),
    ] = False,
    require_confirmation: Annotated[
        bool,
        typer.Option(
            "--require-confirmation",
            help="Reject destructive commands unless --yes is also provided",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm destructive commands when confirmation is required"),
    ] = False,
    plan: Annotated[
        bool,
        typer.Option("--plan", help="Emit command side-effect metadata without dispatching"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Emit the planned command payload without dispatching"),
    ] = False,
    compact: Annotated[
        bool,
        typer.Option("--compact", help="Compact large JSON arrays into summaries"),
    ] = False,
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
        click.get_current_context().obj = build_runtime_context(
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
            record=record,
            replay=replay,
            read_only=read_only,
            require_confirmation=require_confirmation,
            yes=yes,
            plan=plan,
            dry_run=dry_run,
            compact=compact,
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
