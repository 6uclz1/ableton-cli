from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer

from ..runtime import execute_command, get_client
from ._validation import invalid_argument, require_non_empty_string

batch_app = typer.Typer(help="Batch commands", no_args_is_help=True)


def _parse_steps_payload(raw: str, *, source_name: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise invalid_argument(
            message=f"{source_name} must be valid JSON: {exc.msg}",
            hint="Use JSON object format: {'steps': [{...}]}",
        ) from exc

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

        steps.append({"name": name, "args": raw_args})

    return steps


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
    def _run() -> dict[str, object]:
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
            steps = _parse_steps_payload(raw, source_name="steps file")
        elif steps_json is not None:
            steps = _parse_steps_payload(steps_json, source_name="steps json")
        else:
            raw_stdin = sys.stdin.read()
            steps = _parse_steps_payload(raw_stdin, source_name="steps stdin")

        return get_client(ctx).execute_batch(steps)

    execute_command(
        ctx,
        command="batch run",
        args={"steps_file": steps_file, "steps_json": steps_json, "steps_stdin": steps_stdin},
        action=_run,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(batch_app, name="batch")
