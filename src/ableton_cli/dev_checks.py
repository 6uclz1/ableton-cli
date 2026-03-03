from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CHECK_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "ruff", "format", "--check", "."),
    ("uv", "run", "python", "tools/generate_skill_docs.py", "--check"),
    ("uv", "run", "python", "-m", "ableton_cli.contract_checks"),
    ("uv", "run", "pytest"),
)
PYTEST_COMMAND_PREFIX = ("uv", "run", "pytest")
REPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    exit_code: int
    status: str
    duration_seconds: float


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run default lint/test checks")
    parser.add_argument(
        "--report",
        default=None,
        help="Optional path to write a machine-readable JSON report.",
    )
    parser.add_argument(
        "--pytest-junitxml",
        default=None,
        help="Optional path passed to pytest as --junitxml=PATH.",
    )
    return parser


def _run_command(command: Sequence[str]) -> CommandResult:
    print(f"$ {' '.join(command)}", flush=True)
    started = time.monotonic()
    completed = subprocess.run(tuple(command), check=False)
    duration_seconds = time.monotonic() - started
    exit_code = int(completed.returncode)
    return CommandResult(
        command=tuple(command),
        exit_code=exit_code,
        status="pass" if exit_code == 0 else "fail",
        duration_seconds=duration_seconds,
    )


def _build_command_list(
    *,
    commands: Sequence[Sequence[str]],
    pytest_junitxml_path: Path | None,
) -> tuple[tuple[str, ...], ...]:
    if pytest_junitxml_path is None:
        return tuple(tuple(command) for command in commands)

    built: list[tuple[str, ...]] = []
    for command in commands:
        normalized = tuple(command)
        if normalized[:3] == PYTEST_COMMAND_PREFIX:
            normalized = (*normalized, f"--junitxml={pytest_junitxml_path}")
        built.append(normalized)
    return tuple(built)


def execute_checks(
    *,
    commands: Sequence[Sequence[str]] = DEFAULT_CHECK_COMMANDS,
    pytest_junitxml_path: Path | None = None,
) -> tuple[int, tuple[CommandResult, ...]]:
    resolved_commands = _build_command_list(
        commands=commands,
        pytest_junitxml_path=pytest_junitxml_path,
    )
    results: list[CommandResult] = []
    has_failure = False
    for command in resolved_commands:
        result = _run_command(command)
        results.append(result)
        if result.exit_code != 0:
            has_failure = True
    return (1 if has_failure else 0), tuple(results)


def _serialize_report(*, exit_code: int, results: Sequence[CommandResult]) -> dict[str, object]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "pass" if exit_code == 0 else "fail",
        "exit_code": exit_code,
        "command_count": len(results),
        "failure_count": sum(1 for item in results if item.exit_code != 0),
        "commands": [
            {
                "command": list(item.command),
                "exit_code": item.exit_code,
                "status": item.status,
                "duration_seconds": item.duration_seconds,
            }
            for item in results
        ],
    }


def write_report(path: Path, *, exit_code: int, results: Sequence[CommandResult]) -> None:
    payload = _serialize_report(exit_code=exit_code, results=results)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_default_checks(
    *,
    commands: Sequence[Sequence[str]] = DEFAULT_CHECK_COMMANDS,
    pytest_junitxml_path: Path | None = None,
) -> int:
    exit_code, _results = execute_checks(
        commands=commands,
        pytest_junitxml_path=pytest_junitxml_path,
    )
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pytest_junitxml_path = Path(args.pytest_junitxml) if args.pytest_junitxml else None
    exit_code, results = execute_checks(pytest_junitxml_path=pytest_junitxml_path)
    if args.report:
        write_report(Path(args.report), exit_code=exit_code, results=results)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
