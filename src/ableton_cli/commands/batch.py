from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Annotated, Any

import typer

from ..capabilities import parse_supported_commands, required_remote_commands
from ..errors import AppError, ExitCode
from ..runtime import execute_command, get_client, get_runtime
from ._validation import invalid_argument, require_non_empty_string

batch_app = typer.Typer(help="Batch commands", no_args_is_help=True)
_ASSERT_OPERATORS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte"})
_DEFAULT_RETRY_CODES = ("TIMEOUT", "REMOTE_BUSY")


def _parse_retry_object(raw_retry: Any, *, step_index: int) -> dict[str, Any] | None:
    if raw_retry is None:
        return None
    if not isinstance(raw_retry, dict):
        raise invalid_argument(
            message=f"steps[{step_index}].retry must be an object",
            hint="Use retry object: {'max_attempts': 3, 'backoff_ms': 200, 'on': ['TIMEOUT']}.",
        )

    raw_max_attempts = raw_retry.get("max_attempts", 1)
    if not isinstance(raw_max_attempts, int) or raw_max_attempts < 1:
        raise invalid_argument(
            message=f"steps[{step_index}].retry.max_attempts must be an integer >= 1",
            hint="Set max_attempts to 1 or greater.",
        )
    raw_backoff_ms = raw_retry.get("backoff_ms", 0)
    if not isinstance(raw_backoff_ms, int) or raw_backoff_ms < 0:
        raise invalid_argument(
            message=f"steps[{step_index}].retry.backoff_ms must be an integer >= 0",
            hint="Set backoff_ms to 0 or greater.",
        )
    raw_retry_on = raw_retry.get("on", list(_DEFAULT_RETRY_CODES))
    if not isinstance(raw_retry_on, list) or not raw_retry_on:
        raise invalid_argument(
            message=f"steps[{step_index}].retry.on must be a non-empty array of error codes",
            hint="Use retry.on such as ['TIMEOUT', 'REMOTE_BUSY'].",
        )

    retry_on: list[str] = []
    for code_index, raw_code in enumerate(raw_retry_on):
        if not isinstance(raw_code, str):
            raise invalid_argument(
                message=f"steps[{step_index}].retry.on[{code_index}] must be a string",
                hint="Use uppercase error-code strings.",
            )
        retry_on.append(
            require_non_empty_string(
                "retry.on",
                raw_code,
                hint=f"steps[{step_index}].retry.on[{code_index}] must be non-empty.",
            )
        )

    return {
        "max_attempts": raw_max_attempts,
        "backoff_ms": raw_backoff_ms,
        "on": retry_on,
    }


def _parse_assert_object(raw_assert: Any, *, step_index: int) -> list[dict[str, Any]]:
    if raw_assert is None:
        return []

    if isinstance(raw_assert, dict):
        raw_conditions = [raw_assert]
    elif isinstance(raw_assert, list):
        if not raw_assert:
            raise invalid_argument(
                message=f"steps[{step_index}].assert must not be an empty array",
                hint="Provide at least one assert condition object.",
            )
        raw_conditions = raw_assert
    else:
        raise invalid_argument(
            message=f"steps[{step_index}].assert must be an object or array",
            hint="Use assert object: {'path': 'tempo', 'op': 'gte', 'value': 120.0}.",
        )

    parsed_conditions: list[dict[str, Any]] = []
    for condition_index, raw_condition in enumerate(raw_conditions):
        if not isinstance(raw_condition, dict):
            raise invalid_argument(
                message=f"steps[{step_index}].assert[{condition_index}] must be an object",
                hint="Use assert object fields: path/op/value/source.",
            )
        raw_source = raw_condition.get("source", "previous")
        if raw_source not in {"previous", "current"}:
            raise invalid_argument(
                message=(
                    f"steps[{step_index}].assert[{condition_index}].source "
                    "must be previous or current"
                ),
                hint="Set assert source to 'previous' or 'current'.",
            )
        raw_path = raw_condition.get("path")
        if not isinstance(raw_path, str):
            raise invalid_argument(
                message=f"steps[{step_index}].assert[{condition_index}].path must be a string",
                hint="Use dot notation such as 'tempo' or 'tracks.0.name'.",
            )
        path = require_non_empty_string(
            "assert.path",
            raw_path,
            hint=f"steps[{step_index}].assert[{condition_index}].path must be non-empty.",
        )
        raw_op = raw_condition.get("op")
        if not isinstance(raw_op, str) or raw_op not in _ASSERT_OPERATORS:
            allowed = ", ".join(sorted(_ASSERT_OPERATORS))
            raise invalid_argument(
                message=(
                    f"steps[{step_index}].assert[{condition_index}].op must be one of: {allowed}"
                ),
                hint="Set assert op to one of the supported operators.",
            )
        if "value" not in raw_condition:
            raise invalid_argument(
                message=f"steps[{step_index}].assert[{condition_index}].value is required",
                hint="Set expected value for assertion comparison.",
            )
        parsed_conditions.append(
            {
                "source": raw_source,
                "path": path,
                "op": raw_op,
                "value": raw_condition["value"],
            }
        )
    return parsed_conditions


def _parse_preflight_object(raw_preflight: Any, *, source_name: str) -> dict[str, Any] | None:
    if raw_preflight is None or raw_preflight is False:
        return None
    if raw_preflight is True:
        return {}
    if not isinstance(raw_preflight, dict):
        raise invalid_argument(
            message=f"{source_name}.preflight must be an object or boolean",
            hint="Use preflight object with protocol_version/command_set_hash/required_commands.",
        )

    parsed: dict[str, Any] = {}

    if "protocol_version" in raw_preflight:
        protocol_version = raw_preflight["protocol_version"]
        if not isinstance(protocol_version, int):
            raise invalid_argument(
                message=f"{source_name}.preflight.protocol_version must be an integer",
                hint="Set preflight.protocol_version to a positive integer.",
            )
        parsed["protocol_version"] = protocol_version

    if "command_set_hash" in raw_preflight:
        raw_hash = raw_preflight["command_set_hash"]
        if not isinstance(raw_hash, str):
            raise invalid_argument(
                message=f"{source_name}.preflight.command_set_hash must be a string",
                hint="Set preflight.command_set_hash to a non-empty hash string.",
            )
        parsed["command_set_hash"] = require_non_empty_string(
            "command_set_hash",
            raw_hash,
            hint=f"{source_name}.preflight.command_set_hash must be non-empty.",
        )

    if "required_commands" in raw_preflight:
        raw_required = raw_preflight["required_commands"]
        if not isinstance(raw_required, list):
            raise invalid_argument(
                message=f"{source_name}.preflight.required_commands must be an array",
                hint="Use required_commands such as ['ping', 'tracks_list'].",
            )
        required_commands: list[str] = []
        for index, raw_name in enumerate(raw_required):
            if not isinstance(raw_name, str):
                raise invalid_argument(
                    message=f"{source_name}.preflight.required_commands[{index}] must be a string",
                    hint="Use non-empty command-name strings.",
                )
            required_commands.append(
                require_non_empty_string(
                    "required_commands",
                    raw_name,
                    hint=f"{source_name}.preflight.required_commands[{index}] must be non-empty.",
                )
            )
        parsed["required_commands"] = required_commands

    return parsed


def _parse_batch_object(payload: Any, *, source_name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise invalid_argument(
            message=f"{source_name} root must be an object",
            hint="Use JSON object format: {'steps': [{...}]}",
        )

    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list):
        raise invalid_argument(
            message="steps must be an array",
            hint="Use JSON object format: {'steps': [{...}]}",
        )
    if not raw_steps:
        raise invalid_argument(
            message="steps must not be empty",
            hint="Add at least one step in steps file.",
        )

    steps: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, dict):
            raise invalid_argument(
                message=f"steps[{index}] must be an object",
                hint="Each step must include name and optional args.",
            )

        raw_name = raw_step.get("name")
        if not isinstance(raw_name, str):
            raise invalid_argument(
                message=f"steps[{index}].name must be a string",
                hint="Use a remote command name string.",
            )
        name = require_non_empty_string(
            "name",
            raw_name,
            hint=f"steps[{index}].name must be non-empty.",
        )
        raw_args = raw_step.get("args", {})
        if not isinstance(raw_args, dict):
            raise invalid_argument(
                message=f"steps[{index}].args must be an object",
                hint="Use a JSON object for step args.",
            )

        parsed_step = {
            "name": name,
            "args": raw_args,
            "retry": _parse_retry_object(raw_step.get("retry"), step_index=index),
            "assert": _parse_assert_object(raw_step.get("assert"), step_index=index),
        }
        steps.append(parsed_step)

    preflight = _parse_preflight_object(payload.get("preflight"), source_name=source_name)
    return {
        "preflight": preflight,
        "steps": steps,
    }


def _parse_batch_payload(raw: str, *, source_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise invalid_argument(
            message=f"{source_name} must be valid JSON: {exc.msg}",
            hint="Use JSON object format: {'steps': [{...}]}",
        ) from exc
    return _parse_batch_object(payload, source_name=source_name)


def _stream_error_payload(error: AppError) -> dict[str, Any]:
    return {
        "code": error.error_code,
        "message": error.message,
        "hint": error.hint,
        "details": error.details or None,
    }


def _emit_stream_line(
    *,
    request_id: str | None,
    ok: bool,
    result: Any,
    error: dict[str, Any] | None,
) -> None:
    typer.echo(
        json.dumps(
            {
                "id": request_id,
                "ok": ok,
                "result": result,
                "error": error,
            }
        )
    )


def _extract_path_value(payload: Any, path: str) -> tuple[bool, Any]:
    current = payload
    for token in path.split("."):
        if isinstance(current, dict):
            if token not in current:
                return False, None
            current = current[token]
            continue
        if isinstance(current, list):
            try:
                index = int(token)
            except ValueError:
                return False, None
            if not (0 <= index < len(current)):
                return False, None
            current = current[index]
            continue
        return False, None
    return True, current


def _assert_match(*, op: str, actual: Any, expected: Any) -> bool:
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "lte":
        return actual <= expected
    raise RuntimeError(f"Unsupported assert op: {op}")


def _raise_assert_failure(
    *,
    step_index: int,
    condition: dict[str, Any],
    reason: str,
    actual: Any = None,
) -> None:
    raise AppError(
        error_code="BATCH_ASSERT_FAILED",
        message=f"Batch assert failed at step {step_index}",
        hint="Fix batch assert conditions or preceding step behavior.",
        exit_code=ExitCode.EXECUTION_FAILED,
        details={
            "step_index": step_index,
            "condition": condition,
            "reason": reason,
            "actual": actual,
        },
    )


def _evaluate_assertions(
    *,
    step_index: int,
    source: str,
    conditions: list[dict[str, Any]],
    payload: Any,
) -> None:
    scoped_conditions = [condition for condition in conditions if condition["source"] == source]
    if not scoped_conditions:
        return
    if payload is None:
        _raise_assert_failure(
            step_index=step_index,
            condition=scoped_conditions[0],
            reason=f"{source} payload is missing",
        )

    for condition in scoped_conditions:
        found, actual = _extract_path_value(payload, condition["path"])
        if not found:
            _raise_assert_failure(
                step_index=step_index,
                condition=condition,
                reason=f"path not found: {condition['path']}",
            )
        try:
            matched = _assert_match(op=condition["op"], actual=actual, expected=condition["value"])
        except TypeError as exc:
            _raise_assert_failure(
                step_index=step_index,
                condition=condition,
                reason=f"type mismatch: {exc}",
                actual=actual,
            )
        if not matched:
            _raise_assert_failure(
                step_index=step_index,
                condition=condition,
                reason="comparison failed",
                actual=actual,
            )


def _run_preflight(
    client: Any,
    *,
    preflight: dict[str, Any],
    default_protocol_version: int,
) -> dict[str, Any]:
    try:
        ping_result = client.ping()
        supported_commands = parse_supported_commands(ping_result)
    except AppError as exc:
        raise AppError(
            error_code="BATCH_PREFLIGHT_FAILED",
            message="Batch preflight failed while validating ping/capabilities",
            hint=exc.hint or "Fix protocol/capability mismatch before retrying batch.",
            exit_code=ExitCode.EXECUTION_FAILED,
            details={
                "error_code": exc.error_code,
                "message": exc.message,
            },
        ) from exc

    expected_protocol = preflight.get("protocol_version", default_protocol_version)
    remote_protocol = ping_result.get("protocol_version")
    if remote_protocol != expected_protocol:
        raise AppError(
            error_code="BATCH_PREFLIGHT_FAILED",
            message="Batch preflight protocol_version mismatch",
            hint="Align CLI protocol version and Remote Script protocol version.",
            exit_code=ExitCode.EXECUTION_FAILED,
            details={
                "expected_protocol_version": expected_protocol,
                "remote_protocol_version": remote_protocol,
            },
        )

    expected_hash = preflight.get("command_set_hash")
    remote_hash = ping_result.get("command_set_hash")
    if expected_hash is not None and remote_hash != expected_hash:
        raise AppError(
            error_code="BATCH_PREFLIGHT_FAILED",
            message="Batch preflight command_set_hash mismatch",
            hint="Update Remote Script or batch preflight command_set_hash.",
            exit_code=ExitCode.EXECUTION_FAILED,
            details={
                "expected_command_set_hash": expected_hash,
                "remote_command_set_hash": remote_hash,
            },
        )

    required_commands = preflight.get("required_commands")
    if required_commands is None:
        required = required_remote_commands()
    else:
        required = set(required_commands)
    missing = sorted(required.difference(supported_commands))
    if missing:
        raise AppError(
            error_code="BATCH_PREFLIGHT_FAILED",
            message="Batch preflight detected missing required commands",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.EXECUTION_FAILED,
            details={
                "missing_required_commands": missing,
                "required_command_count": len(required),
                "supported_command_count": len(supported_commands),
            },
        )

    return {
        "checked": True,
        "protocol_version": remote_protocol,
        "command_set_hash": remote_hash,
        "required_command_count": len(required),
        "supported_command_count": len(supported_commands),
    }


def _execute_step(
    client: Any,
    *,
    step: dict[str, Any],
    step_index: int,
) -> tuple[dict[str, Any], int]:
    retry = step["retry"]
    if retry is None:
        result = client.execute_remote_command(step["name"], step["args"])
        return result, 1

    max_attempts = retry["max_attempts"]
    retry_on = set(retry["on"])
    backoff_ms = retry["backoff_ms"]

    attempt = 0
    while True:
        attempt += 1
        try:
            result = client.execute_remote_command(step["name"], step["args"])
            return result, attempt
        except AppError as exc:
            if exc.error_code not in retry_on:
                raise
            if attempt >= max_attempts:
                raise AppError(
                    error_code="BATCH_RETRY_EXHAUSTED",
                    message=f"Retry exhausted for step {step_index}",
                    hint="Increase retry.max_attempts or fix underlying command errors.",
                    exit_code=ExitCode.EXECUTION_FAILED,
                    details={
                        "step_index": step_index,
                        "name": step["name"],
                        "attempts": attempt,
                        "retry_on": sorted(retry_on),
                        "last_error": exc.to_payload(),
                    },
                ) from exc
            sleep_seconds = (backoff_ms * (2 ** (attempt - 1))) / 1000
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)


def _execute_batch_spec(
    ctx: typer.Context,
    spec: dict[str, Any],
    *,
    client_override: Any | None = None,
) -> dict[str, Any]:
    runtime = get_runtime(ctx)
    client = get_client(ctx) if client_override is None else client_override
    preflight = spec["preflight"]
    preflight_result: dict[str, Any] | None = None
    if preflight is not None:
        preflight_result = _run_preflight(
            client,
            preflight=preflight,
            default_protocol_version=runtime.settings.protocol_version,
        )

    results: list[dict[str, Any]] = []
    previous_result: dict[str, Any] | None = None
    for step_index, step in enumerate(spec["steps"]):
        _evaluate_assertions(
            step_index=step_index,
            source="previous",
            conditions=step["assert"],
            payload=previous_result,
        )

        step_result, attempts = _execute_step(client, step=step, step_index=step_index)

        _evaluate_assertions(
            step_index=step_index,
            source="current",
            conditions=step["assert"],
            payload=step_result,
        )
        results.append(
            {
                "index": step_index,
                "name": step["name"],
                "attempts": attempts,
                "result": step_result,
            }
        )
        previous_result = step_result

    return {
        "step_count": len(spec["steps"]),
        "results": results,
        "preflight": preflight_result,
    }


@batch_app.command("run")
def batch_run(
    ctx: typer.Context,
    steps_file: Annotated[
        str | None,
        typer.Option("--steps-file", help="Path to JSON file with batch steps"),
    ] = None,
    steps_json: Annotated[
        str | None,
        typer.Option("--steps-json", help="Inline JSON object with 'steps' array"),
    ] = None,
    steps_stdin: Annotated[
        bool,
        typer.Option("--steps-stdin", help="Read JSON object with 'steps' array from stdin"),
    ] = False,
) -> None:
    def _run() -> dict[str, Any]:
        selected_sources = (
            int(steps_file is not None) + int(steps_json is not None) + int(steps_stdin)
        )
        if selected_sources != 1:
            raise invalid_argument(
                message=(
                    "Exactly one of --steps-file, --steps-json, or --steps-stdin must be provided"
                ),
                hint="Choose exactly one batch input source.",
            )

        if steps_file is not None:
            steps_path = Path(steps_file)
            try:
                raw = steps_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise invalid_argument(
                    message=f"steps file could not be read: {steps_path}",
                    hint="Pass a readable UTF-8 JSON file path for --steps-file.",
                ) from exc
            spec = _parse_batch_payload(raw, source_name="steps file")
        elif steps_json is not None:
            spec = _parse_batch_payload(steps_json, source_name="steps json")
        else:
            raw_stdin = sys.stdin.read()
            spec = _parse_batch_payload(raw_stdin, source_name="steps stdin")

        return _execute_batch_spec(ctx, spec)

    execute_command(
        ctx,
        command="batch run",
        args={"steps_file": steps_file, "steps_json": steps_json, "steps_stdin": steps_stdin},
        action=_run,
    )


@batch_app.command("stream")
def batch_stream(ctx: typer.Context) -> None:
    client = get_client(ctx)
    for line_number, raw_line in enumerate(sys.stdin, start=1):
        line = raw_line.strip()
        if not line:
            continue

        request_id: str | None = None
        try:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise invalid_argument(
                    message=f"line {line_number} must be valid JSON: {exc.msg}",
                    hint="Use one JSON object per line: {'id': 'optional', 'steps': [{...}]}",
                ) from exc

            if not isinstance(payload, dict):
                raise invalid_argument(
                    message=f"line {line_number} root must be an object",
                    hint="Use one JSON object per line: {'id': 'optional', 'steps': [{...}]}",
                )

            raw_id = payload.get("id")
            if raw_id is not None:
                if not isinstance(raw_id, str):
                    raise invalid_argument(
                        message=f"line {line_number}.id must be a string",
                        hint="Use a string id value or omit id.",
                    )
                request_id = require_non_empty_string(
                    "id",
                    raw_id,
                    hint=f"line {line_number}.id must be non-empty when provided.",
                )

            spec = _parse_batch_object(payload, source_name=f"line {line_number}")
            result = _execute_batch_spec(ctx, spec, client_override=client)
            _emit_stream_line(request_id=request_id, ok=True, result=result, error=None)
        except AppError as exc:
            _emit_stream_line(
                request_id=request_id,
                ok=False,
                result=None,
                error=_stream_error_payload(exc),
            )
        except Exception:  # noqa: BLE001
            _emit_stream_line(
                request_id=request_id,
                ok=False,
                result=None,
                error={
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected internal error",
                    "hint": "Run with --verbose and inspect logs.",
                    "details": {"line_number": line_number},
                },
            )


def register(app: typer.Typer) -> None:
    app.add_typer(batch_app, name="batch")
