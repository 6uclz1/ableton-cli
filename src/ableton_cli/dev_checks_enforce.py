from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .quality_harness.baseline import BaselineError
from .quality_harness.config import ConfigError
from .quality_harness.runner import run_quality_harness

REPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ActionSpec:
    name: str
    command: tuple[str, ...]


_AUTO_FIX_ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec(name="ruff_check_fix", command=("uv", "run", "ruff", "check", "--fix", ".")),
    ActionSpec(name="ruff_format", command=("uv", "run", "ruff", "format", ".")),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run quality harness and enforce deterministic autofix actions.",
    )
    parser.add_argument(
        "--config",
        default=".quality-harness.yml",
        help="Path to .quality-harness.yml",
    )
    parser.add_argument(
        "--report",
        default="quality-harness-report.json",
        help="Path to quality harness report output JSON",
    )
    parser.add_argument(
        "--action-log",
        default="quality-harness-action-log.json",
        help="Path to JSON action log output",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Optional baseline report JSON for regression comparison",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=2,
        help="Maximum quality-harness + autofix attempts",
    )
    return parser


def _read_field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _serialize_violation(violation: Any) -> dict[str, Any]:
    return {
        "severity": str(_read_field(violation, "severity") or ""),
        "scope": str(_read_field(violation, "scope") or ""),
        "metric": str(_read_field(violation, "metric") or ""),
        "path": _read_field(violation, "path"),
        "qualname": _read_field(violation, "qualname"),
        "value": _read_field(violation, "value"),
        "warn_threshold": _read_field(violation, "warn_threshold"),
        "fail_threshold": _read_field(violation, "fail_threshold"),
        "message": str(_read_field(violation, "message") or ""),
    }


def _violation_signature(violation: Any) -> str:
    scope = str(_read_field(violation, "scope") or "")
    metric = str(_read_field(violation, "metric") or "")
    path = str(_read_field(violation, "path") or "-")
    qualname = str(_read_field(violation, "qualname") or "-")
    return f"{scope}.{metric}:{path}:{qualname}"


def _fail_violations(violations: list[Any]) -> list[Any]:
    return [item for item in violations if str(_read_field(item, "severity")) == "fail"]


def _actions_for_violation(_violation: Any) -> tuple[ActionSpec, ...]:
    return _AUTO_FIX_ACTIONS


def _run_action(action: ActionSpec) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(action.command, check=False)
    duration_seconds = time.monotonic() - started
    exit_code = int(completed.returncode)
    return {
        "name": action.name,
        "command": list(action.command),
        "exit_code": exit_code,
        "status": "pass" if exit_code == 0 else "fail",
        "duration_seconds": duration_seconds,
    }


def _write_action_log(
    path: Path,
    *,
    status: str,
    max_attempts: int,
    attempts: list[dict[str, Any]],
    unresolved_failures: list[Any],
) -> None:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": status,
        "max_attempts": max_attempts,
        "attempt_count": len(attempts),
        "attempts": attempts,
        "unresolved_failures": [_serialize_violation(item) for item in unresolved_failures],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_enforced_checks(
    *,
    config_path: Path,
    report_path: Path,
    action_log_path: Path,
    baseline_path: Path | None,
    max_attempts: int,
) -> int:
    if max_attempts <= 0:
        raise ValueError("max_attempts must be >= 1")

    attempts: list[dict[str, Any]] = []
    unresolved_failures: list[Any] = []

    for attempt_index in range(1, max_attempts + 1):
        run_result = run_quality_harness(
            config_path=config_path,
            report_path=report_path,
            root_dir=Path.cwd(),
            baseline_path=baseline_path,
        )
        violations = list(getattr(run_result.report, "violations", []))
        fail_violations = _fail_violations(violations)

        attempt_log: dict[str, Any] = {
            "attempt": attempt_index,
            "fail_violation_count": len(fail_violations),
            "fail_violations": [_serialize_violation(item) for item in fail_violations],
            "violation_actions": [],
            "executed_actions": [],
        }

        if not fail_violations:
            attempts.append(attempt_log)
            _write_action_log(
                action_log_path,
                status="pass",
                max_attempts=max_attempts,
                attempts=attempts,
                unresolved_failures=[],
            )
            return 0

        seen_action_names: set[str] = set()
        actions_to_run: list[ActionSpec] = []
        for violation in fail_violations:
            mapped_actions = _actions_for_violation(violation)
            attempt_log["violation_actions"].append(
                {
                    "violation": _violation_signature(violation),
                    "actions": [item.name for item in mapped_actions],
                }
            )
            for action in mapped_actions:
                if action.name in seen_action_names:
                    continue
                seen_action_names.add(action.name)
                actions_to_run.append(action)

        if not actions_to_run:
            unresolved_failures = fail_violations
            attempts.append(attempt_log)
            break

        executed_actions = [_run_action(action) for action in actions_to_run]
        attempt_log["executed_actions"] = executed_actions
        attempts.append(attempt_log)

        if any(action["exit_code"] != 0 for action in executed_actions):
            unresolved_failures = fail_violations
            break

        if attempt_index == max_attempts:
            unresolved_failures = fail_violations
            break

    _write_action_log(
        action_log_path,
        status="fail",
        max_attempts=max_attempts,
        attempts=attempts,
        unresolved_failures=unresolved_failures,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run_enforced_checks(
            config_path=Path(args.config),
            report_path=Path(args.report),
            action_log_path=Path(args.action_log),
            baseline_path=Path(args.baseline) if args.baseline else None,
            max_attempts=int(args.max_attempts),
        )
    except (ConfigError, BaselineError) as exc:
        print(f"dev-checks-enforce error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(f"dev-checks-enforce error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
