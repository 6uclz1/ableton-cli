from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import typer

from .client.ableton_client import AbletonClient
from .compact import compact_payload
from .config import Settings
from .contracts import validate_command_contract
from .errors import AppError, ErrorCode, ExitCode
from .output import (
    OutputMode,
    emit_human_error,
    emit_human_result,
    emit_json,
    error_payload,
    success_payload,
)
from .platform_paths import PlatformPaths


@dataclass(slots=True)
class RuntimeContext:
    settings: Settings
    platform_paths: PlatformPaths
    output_mode: OutputMode
    quiet: bool
    no_color: bool
    record_path: str | None = None
    replay_path: str | None = None
    read_only: bool = False
    compact: bool = False
    _client: AbletonClient | None = None

    def client(self) -> AbletonClient:
        if self._client is None:
            if self.record_path is None and self.replay_path is None and not self.read_only:
                self._client = AbletonClient(self.settings)
            else:
                self._client = AbletonClient(
                    self.settings,
                    record_path=self.record_path,
                    replay_path=self.replay_path,
                    read_only=self.read_only,
                )
        return self._client


def get_runtime(ctx: typer.Context) -> RuntimeContext:
    runtime = ctx.obj
    if not isinstance(runtime, RuntimeContext):
        raise RuntimeError("Runtime context is not initialized")
    return runtime


def get_client(ctx: typer.Context) -> AbletonClient:
    runtime = get_runtime(ctx)
    return runtime.client()


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
        validate_command_contract(command=command, args=args, result=result)
        payload = success_payload(command=command, args=args, result=result)
        if runtime.output_mode == OutputMode.JSON:
            if runtime.compact:
                payload = compact_payload(payload)
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
        serialized_error = exc.to_payload()
        payload = error_payload(
            command=command,
            args=args,
            code=serialized_error["code"],
            message=exc.message,
            hint=exc.hint,
            details=exc.details or None,
        )
        if runtime.output_mode == OutputMode.JSON:
            emit_json(payload)
        else:
            emit_human_error(serialized_error["code"], exc.message, exc.hint)
        raise typer.Exit(exc.exit_code.value) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled command failure")
        code = ErrorCode.INTERNAL_ERROR.value
        message = "Unexpected internal error"
        hint = "Run with --verbose and check stderr/log-file for details."
        payload = error_payload(command=command, args=args, code=code, message=message, hint=hint)
        if runtime.output_mode == OutputMode.JSON:
            emit_json(payload)
        else:
            emit_human_error(code, message, hint)
        raise typer.Exit(ExitCode.INTERNAL_ERROR.value) from exc
