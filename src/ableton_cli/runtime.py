from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import typer

from .client.ableton_client import AbletonClient
from .command_specs import CommandSpec, command_spec_map
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
    require_confirmation: bool = False
    confirm_destructive: bool = False
    plan: bool = False
    dry_run: bool = False
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


def _command_spec(command: str) -> CommandSpec:
    return command_spec_map()[command]


def build_command_plan(command: str, args: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    spec = _command_spec(command)
    return {
        "command": command,
        "remote_command": spec.remote_command,
        "args": args,
        "side_effect": spec.side_effect.to_contract_metadata(),
        "requires_confirmation": spec.side_effect.requires_confirmation,
        "dry_run": dry_run,
        "will_dispatch": False,
    }


def enforce_destructive_confirmation(
    runtime: RuntimeContext, command: str, args: dict[str, Any]
) -> None:
    if (
        not runtime.require_confirmation
        or runtime.confirm_destructive
        or args.get("yes") is True
        or args.get("dry_run") is True
    ):
        return

    spec = _command_spec(command)
    if not spec.side_effect.requires_confirmation:
        return

    raise AppError(
        error_code=ErrorCode.CONFIRMATION_REQUIRED,
        message=f"Command '{command}' requires confirmation",
        hint="Pass --yes together with --require-confirmation to execute this command.",
        exit_code=ExitCode.EXECUTION_FAILED,
        details={
            "command": command,
            "remote_command": spec.remote_command,
            "side_effect": spec.side_effect.to_contract_metadata(),
        },
    )


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
    resolved_args: Callable[[], dict[str, Any]] | None = None,
    human_formatter: Callable[[dict[str, Any]], str] | None = None,
) -> None:
    runtime = get_runtime(ctx)
    logger = logging.getLogger("ableton_cli")

    try:
        payload_args = resolved_args() if resolved_args is not None else args
        if runtime.plan or runtime.dry_run:
            result = build_command_plan(command, payload_args, dry_run=runtime.dry_run)
            payload = success_payload(command=command, args=payload_args, result=result)
            if runtime.output_mode == OutputMode.JSON:
                emit_json(payload)
            else:
                emit_human_result(command, result, runtime.quiet)
            raise typer.Exit(ExitCode.SUCCESS.value)

        enforce_destructive_confirmation(runtime, command, payload_args)
        result = action()
        validate_command_contract(command=command, args=payload_args, result=result)
        payload = success_payload(command=command, args=payload_args, result=result)
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
