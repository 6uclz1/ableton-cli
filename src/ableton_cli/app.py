from __future__ import annotations

import platform
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
from .platform_paths import PlatformPaths, PosixPlatformPaths, WindowsPlatformPaths
from .runtime import RuntimeContext

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


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=ExitCode.SUCCESS.value)


def _build_platform_paths_for_current_os() -> PlatformPaths:
    detected_os = platform.system().lower()
    home = Path.home()

    if detected_os == "windows":
        return WindowsPlatformPaths(home=home)
    if detected_os == "darwin":
        return PosixPlatformPaths(
            home=home,
            remote_script_relative_dirs=(
                ("Music", "Ableton", "User Library", "Remote Scripts"),
                ("Documents", "Ableton", "User Library", "Remote Scripts"),
            ),
        )
    if detected_os == "linux":
        return PosixPlatformPaths(
            home=home,
            remote_script_relative_dirs=(("Ableton", "User Library", "Remote Scripts"),),
        )

    raise AppError(
        error_code="UNSUPPORTED_OS",
        message=f"Unsupported operating system: {detected_os}",
        hint="Use Windows, macOS, or Linux.",
        exit_code=ExitCode.EXECUTION_FAILED,
    )


def _register_subcommands(app: typer.Typer) -> None:
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
        platform_paths = _build_platform_paths_for_current_os()
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
        platform_paths=platform_paths,
        output_mode=output,
        quiet=quiet,
        no_color=no_color,
    )


def create_app() -> typer.Typer:
    app = typer.Typer(
        help="Control and inspect Ableton Live through a local Remote Script.",
        no_args_is_help=True,
        add_completion=True,
    )
    app.callback()(main)
    _register_subcommands(app)
    return app
