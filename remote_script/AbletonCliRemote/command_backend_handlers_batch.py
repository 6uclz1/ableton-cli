from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend, CommandError
from .command_backend_validators import _invalid_argument, _non_empty_string

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]
DispatchCallable = Callable[[CommandBackend, str, dict[str, Any]], dict[str, Any]]


def _parse_batch_steps(args: dict[str, Any]) -> list[dict[str, Any]]:
    raw_steps = args.get("steps")
    if not isinstance(raw_steps, list):
        raise _invalid_argument(
            message="steps must be an array",
            hint="Pass a JSON array of step objects.",
        )
    if not raw_steps:
        raise _invalid_argument(
            message="steps must not be empty",
            hint="Provide at least one step.",
        )

    steps: list[dict[str, Any]] = []
    for index, item in enumerate(raw_steps):
        steps.append(_parse_batch_step(index=index, item=item))
    return steps


def _parse_batch_step(*, index: int, item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise _invalid_argument(
            message=f"steps[{index}] must be an object",
            hint="Each step must include name and optional args.",
        )

    name = _non_empty_string("name", item.get("name"))
    if name == "execute_batch":
        raise _invalid_argument(
            message="steps[].name cannot be execute_batch",
            hint="Nested batch execution is not supported.",
        )

    raw_args = item.get("args", {})
    if not isinstance(raw_args, dict):
        raise _invalid_argument(
            message=f"steps[{index}].args must be an object",
            hint="Pass args as a JSON object.",
        )

    return {"name": name, "args": raw_args}


def make_execute_batch_handler(dispatch_command: DispatchCallable) -> Handler:
    def _handle_execute_batch(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
        steps = _parse_batch_steps(args)
        results: list[dict[str, Any]] = []

        for index, step in enumerate(steps):
            step_name = str(step["name"])
            step_args = dict(step["args"])
            try:
                step_result = dispatch_command(backend, step_name, step_args)
                results.append(
                    {
                        "index": index,
                        "name": step_name,
                        "result": step_result,
                    }
                )
            except CommandError as exc:
                raise CommandError(
                    code="BATCH_STEP_FAILED",
                    message=f"Batch step failed at index {index}: {step_name}",
                    hint="Inspect error.details for failed step context.",
                    details={
                        "failed_step_index": index,
                        "failed_step_name": step_name,
                        "failed_error": {
                            "code": exc.code,
                            "message": exc.message,
                            "hint": exc.hint,
                            "details": exc.details,
                        },
                        "results": results,
                    },
                ) from exc

        return {
            "step_count": len(steps),
            "stopped_at": None,
            "results": results,
        }

    return _handle_execute_batch
