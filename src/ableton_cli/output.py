from __future__ import annotations

import json
from enum import Enum
from typing import Any

import typer


class OutputMode(str, Enum):
    HUMAN = "human"
    JSON = "json"


def success_payload(command: str, args: dict[str, Any], result: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "args": args,
        "result": result,
        "error": None,
    }


def error_payload(
    command: str,
    args: dict[str, Any],
    code: str,
    message: str,
    hint: str | None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "args": args,
        "result": None,
        "error": {
            "code": code,
            "message": message,
            "hint": hint,
            "details": details,
        },
    }


def emit_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False))


def format_human_result(command: str, result: Any) -> str:
    if result is None:
        return f"OK: {command}"
    if isinstance(result, (str, int, float, bool)):
        return f"OK: {command}\n{result}"
    pretty = json.dumps(result, ensure_ascii=False, indent=2)
    return f"OK: {command}\n{pretty}"


def emit_human_result(command: str, result: Any, quiet: bool) -> None:
    if quiet:
        return
    typer.echo(format_human_result(command, result))


def emit_human_error(code: str, message: str, hint: str | None) -> None:
    lines = [f"ERROR [{code}] {message}"]
    if hint:
        lines.append(f"Hint: {hint}")
    typer.echo("\n".join(lines), err=True)
