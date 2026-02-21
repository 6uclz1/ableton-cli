from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import typer

from .client.ableton_client import AbletonClient
from .config import Settings
from .errors import AppError, ExitCode
from .output import (
    OutputMode,
    emit_human_error,
    emit_human_result,
    emit_json,
    error_payload,
    success_payload,
)


@dataclass(slots=True)
class RuntimeContext:
    settings: Settings
    output_mode: OutputMode
    quiet: bool
    no_color: bool


def get_runtime(ctx: typer.Context) -> RuntimeContext:
    runtime = ctx.obj
    if not isinstance(runtime, RuntimeContext):
        raise RuntimeError("Runtime context is not initialized")
    return runtime


def get_client(ctx: typer.Context) -> AbletonClient:
    runtime = get_runtime(ctx)
    return AbletonClient(runtime.settings)


def execute_command(
    ctx: typer.Context,
    *,
    command: str,
    args: dict[str, Any],
    action: Callable[[], dict[str, Any]],
    human_formatter: Callable[[dict[str, Any]], str] | None = None,
) -> None:
    runtime = get_runtime(ctx)
    logger = logging.getLogger("ableton_cli")

    try:
        result = action()
        payload = success_payload(command=command, args=args, result=result)
        if runtime.output_mode == OutputMode.JSON:
            emit_json(payload)
        else:
            if human_formatter is not None and not runtime.quiet:
                typer.echo(human_formatter(result))
            else:
                emit_human_result(command, result, runtime.quiet)
        raise typer.Exit(ExitCode.SUCCESS.value)
    except typer.Exit:
        raise
    except AppError as exc:
        payload = error_payload(
            command=command,
            args=args,
            code=exc.error_code,
            message=exc.message,
            hint=exc.hint,
            details=exc.details or None,
        )
        if runtime.output_mode == OutputMode.JSON:
            emit_json(payload)
        else:
            emit_human_error(exc.error_code, exc.message, exc.hint)
        raise typer.Exit(exc.exit_code.value) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled command failure")
        code = "INTERNAL_ERROR"
        message = "Unexpected internal error"
        hint = "Run with --verbose and check stderr/log-file for details."
        payload = error_payload(command=command, args=args, code=code, message=message, hint=hint)
        if runtime.output_mode == OutputMode.JSON:
            emit_json(payload)
        else:
            emit_human_error(code, message, hint)
        raise typer.Exit(ExitCode.INTERNAL_ERROR.value) from exc
