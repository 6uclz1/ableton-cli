from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import typer

from ..completion import completion_help
from ..config import default_config_path, init_config_file, update_config_value
from ..doctor import run_doctor
from ..errors import AppError, ExitCode
from ..installer import install_remote_script, install_skill
from ..runtime import execute_command, get_client, get_runtime
from ._validation import invalid_argument, require_non_empty_string

config_app = typer.Typer(help="Configuration commands", no_args_is_help=True)


def _format_doctor_human(result: dict[str, object]) -> str:
    summary = result.get("summary", {})
    checks = result.get("checks", [])

    lines = [
        "Doctor Results",
        (
            f"PASS={summary.get('pass', 0)} "
            f"WARN={summary.get('warn', 0)} "
            f"FAIL={summary.get('fail', 0)}"
        ),
    ]

    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            status = check.get("status", "UNKNOWN")
            name = check.get("name", "unknown")
            hint = check.get("hint")
            lines.append(f"[{status}] {name}")
            if hint:
                lines.append(f"hint: {hint}")

    return "\n".join(lines)


@config_app.command("init")
def config_init(
    ctx: typer.Context,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Print what would be written without creating/updating the config file.",
        ),
    ] = False,
) -> None:
    runtime = get_runtime(ctx)
    config_path = Path(runtime.settings.config_path or default_config_path())

    execute_command(
        ctx,
        command="config init",
        args={"path": str(config_path), "dry_run": dry_run},
        action=lambda: init_config_file(path=config_path, dry_run=dry_run),
    )


@config_app.command("show")
def config_show(ctx: typer.Context) -> None:
    runtime = get_runtime(ctx)

    execute_command(
        ctx,
        command="config show",
        args={},
        action=lambda: runtime.settings.to_public_dict(),
    )


@config_app.command("set")
def config_set(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Config key: host|port|timeout_ms|protocol_version")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    def _parse_value(raw_key: str, raw_value: str) -> tuple[str, object]:
        normalized_key = raw_key.strip().lower().replace("-", "_")
        parsed_value = require_non_empty_string(
            "value",
            raw_value,
            hint="Pass a non-empty value.",
        )

        if normalized_key == "host":
            return normalized_key, parsed_value
        if normalized_key in {"port", "timeout_ms", "protocol_version"}:
            try:
                return normalized_key, int(parsed_value)
            except ValueError as exc:
                raise invalid_argument(
                    message=f"value for {normalized_key} must be an integer, got {raw_value!r}",
                    hint=f"Pass an integer value for '{normalized_key}'.",
                ) from exc
        raise invalid_argument(
            message=f"unsupported config key: {raw_key}",
            hint="Use one of: host, port, timeout_ms, protocol_version.",
        )

    def _run() -> dict[str, object]:
        runtime = get_runtime(ctx)
        config_path = Path(runtime.settings.config_path or default_config_path())
        normalized_key, parsed_value = _parse_value(key, value)
        return update_config_value(config_path, key=normalized_key, value=parsed_value)

    execute_command(
        ctx,
        command="config set",
        args={"key": key, "value": value},
        action=_run,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(config_app, name="config")

    @app.command("doctor")
    def doctor(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command="doctor",
            args={},
            action=lambda: run_doctor(get_runtime(ctx).settings),
            human_formatter=_format_doctor_human,
        )

    @app.command("install-remote-script")
    def install_remote_script_command(
        ctx: typer.Context,
        yes: Annotated[
            bool,
            typer.Option(
                "--yes",
                "-y",
                help="Confirm installation in non-interactive runs.",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Print the installation plan without modifying files.",
            ),
        ] = False,
        verify: Annotated[
            bool,
            typer.Option(
                "--verify",
                help="Run doctor after installation and include capability checks.",
            ),
        ] = False,
    ) -> None:
        def _run() -> dict[str, object]:
            install_result = install_remote_script(yes=yes, dry_run=dry_run)
            if not verify:
                return install_result
            doctor_result = run_doctor(get_runtime(ctx).settings)
            return {
                **install_result,
                "verification": doctor_result,
            }

        execute_command(
            ctx,
            command="install-remote-script",
            args={"yes": yes, "dry_run": dry_run, "verify": verify},
            action=_run,
        )

    @app.command("install-skill")
    def install_skill_command(
        ctx: typer.Context,
        yes: Annotated[
            bool,
            typer.Option(
                "--yes",
                "-y",
                help="Confirm installation in non-interactive runs.",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Print the installation plan without modifying files.",
            ),
        ] = False,
        target: Annotated[
            str,
            typer.Option(
                "--target",
                help="Skill installation target (codex or claude).",
                case_sensitive=False,
            ),
        ] = "codex",
    ) -> None:
        normalized_target = target.strip().lower()
        execute_command(
            ctx,
            command="install-skill",
            args={"yes": yes, "dry_run": dry_run, "target": normalized_target},
            action=lambda: install_skill(yes=yes, dry_run=dry_run, target=normalized_target),
        )

    @app.command("ping")
    def ping(ctx: typer.Context) -> None:
        def _run() -> dict[str, object]:
            start = time.perf_counter()
            result = get_client(ctx).ping()
            rtt_ms = (time.perf_counter() - start) * 1000
            runtime = get_runtime(ctx)
            return {
                "host": runtime.settings.host,
                "port": runtime.settings.port,
                "protocol_version": result.get("protocol_version"),
                "remote_script_version": result.get("remote_script_version"),
                "supported_commands": result.get("supported_commands"),
                "command_set_hash": result.get("command_set_hash"),
                "api_support": result.get("api_support"),
                "rtt_ms": round(rtt_ms, 3),
            }

        execute_command(
            ctx,
            command="ping",
            args={},
            action=_run,
        )

    @app.command("wait-ready")
    def wait_ready(
        ctx: typer.Context,
        max_wait_ms: Annotated[
            int,
            typer.Option("--max-wait-ms", help="Maximum wait duration in milliseconds"),
        ] = 60000,
        interval_ms: Annotated[
            int,
            typer.Option("--interval-ms", help="Polling interval in milliseconds"),
        ] = 250,
    ) -> None:
        def _run() -> dict[str, object]:
            if max_wait_ms <= 0:
                raise AppError(
                    error_code="INVALID_ARGUMENT",
                    message=f"max_wait_ms must be > 0, got {max_wait_ms}",
                    hint="Use a positive --max-wait-ms value.",
                    exit_code=ExitCode.INVALID_ARGUMENT,
                )
            if interval_ms <= 0:
                raise AppError(
                    error_code="INVALID_ARGUMENT",
                    message=f"interval_ms must be > 0, got {interval_ms}",
                    hint="Use a positive --interval-ms value.",
                    exit_code=ExitCode.INVALID_ARGUMENT,
                )

            started_at = time.perf_counter()
            attempts = 0
            last_error: AppError | None = None
            while True:
                attempts += 1
                try:
                    ping_result = get_client(ctx).ping()
                    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
                    return {
                        "ready": True,
                        "attempts": attempts,
                        "elapsed_ms": round(elapsed_ms, 3),
                        "protocol_version": ping_result.get("protocol_version"),
                        "remote_script_version": ping_result.get("remote_script_version"),
                    }
                except AppError as exc:
                    last_error = exc
                    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
                    if elapsed_ms >= float(max_wait_ms):
                        timeout_message = (
                            "Timed out waiting for Ableton readiness after "
                            f"{round(elapsed_ms, 3)}ms"
                        )
                        raise AppError(
                            error_code="TIMEOUT",
                            message=timeout_message,
                            hint=exc.hint
                            or "Start Ableton Live and enable the Remote Script, then retry.",
                            exit_code=ExitCode.TIMEOUT,
                            details={
                                "attempts": attempts,
                                "elapsed_ms": round(elapsed_ms, 3),
                                "last_error": last_error.to_payload() if last_error else None,
                            },
                        ) from exc
                    time.sleep(interval_ms / 1000.0)

        execute_command(
            ctx,
            command="wait-ready",
            args={"max_wait_ms": max_wait_ms, "interval_ms": interval_ms},
            action=_run,
        )

    @app.command("completion")
    def completion(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command="completion",
            args={},
            action=lambda: {"message": completion_help()},
        )
