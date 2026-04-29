from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import resolve_settings
from .logging_setup import configure_logging
from .output import OutputMode
from .platform_detection import build_platform_paths_for_current_os
from .runtime import RuntimeContext


def build_runtime_context(
    *,
    host: str | None,
    port: int | None,
    timeout_ms: int | None,
    protocol_version: int | None,
    output: OutputMode,
    verbose: bool,
    log_file: str | None,
    config: Path | None,
    no_color: bool,
    quiet: bool,
    record: str | None,
    replay: str | None,
    read_only: bool,
    require_confirmation: bool = False,
    yes: bool = False,
    plan: bool = False,
    dry_run: bool = False,
    compact: bool = False,
) -> RuntimeContext:
    cli_overrides: dict[str, Any] = {
        "host": host,
        "port": port,
        "timeout_ms": timeout_ms,
        "log_file": log_file,
        "protocol_version": protocol_version,
    }

    settings = resolve_settings(cli_overrides=cli_overrides, config_path=config)
    platform_paths = build_platform_paths_for_current_os()
    configure_logging(verbose=verbose, quiet=quiet, log_file=settings.log_file)

    return RuntimeContext(
        settings=settings,
        platform_paths=platform_paths,
        output_mode=output,
        quiet=quiet,
        no_color=no_color,
        record_path=record,
        replay_path=replay,
        read_only=read_only,
        require_confirmation=require_confirmation,
        confirm_destructive=yes,
        plan=plan,
        dry_run=dry_run,
        compact=compact,
    )
