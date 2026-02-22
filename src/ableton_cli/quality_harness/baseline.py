from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BaselineComparison, BaselineConfig, Threshold, Violation


class BaselineError(ValueError):
    pass


def compare_against_baseline(
    *,
    baseline_path: Path,
    baseline_config: BaselineConfig,
    current_warning_count: int,
    current_failure_count: int,
    current_violations: list[Violation],
) -> tuple[BaselineComparison, list[Violation]]:
    baseline_data = _load_baseline_report(baseline_path)
    baseline_warning_count = _read_int(baseline_data, ["summary", "warning_count"])
    baseline_failure_count = _read_int(baseline_data, ["summary", "failure_count"])
    baseline_violations = _read_baseline_violations(baseline_data)

    warning_delta = max(current_warning_count - baseline_warning_count, 0)
    failure_delta = max(current_failure_count - baseline_failure_count, 0)

    baseline_fail_signatures = {
        _violation_signature_from_dict(item)
        for item in baseline_violations
        if item.get("severity") == "fail"
    }
    current_fail_signatures = {
        _violation_signature_from_model(item)
        for item in current_violations
        if item.severity == "fail"
    }
    new_failures = len(current_fail_signatures - baseline_fail_signatures)

    comparison = BaselineComparison(
        baseline_path=baseline_path.as_posix(),
        warning_delta=warning_delta,
        failure_delta=failure_delta,
        new_failures=new_failures,
        baseline_warning_count=baseline_warning_count,
        baseline_failure_count=baseline_failure_count,
        current_warning_count=current_warning_count,
        current_failure_count=current_failure_count,
    )

    violations: list[Violation] = []
    violations.extend(
        _baseline_metric_violations(
            metric="warning_delta",
            value=warning_delta,
            threshold=baseline_config.warning_delta,
            message="warning count increased from baseline",
        )
    )
    violations.extend(
        _baseline_metric_violations(
            metric="failure_delta",
            value=failure_delta,
            threshold=baseline_config.failure_delta,
            message="failure count increased from baseline",
        )
    )
    violations.extend(
        _baseline_metric_violations(
            metric="new_failures",
            value=new_failures,
            threshold=baseline_config.new_failures,
            message="new fail-level violations not present in baseline",
        )
    )

    return comparison, violations


def _load_baseline_report(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BaselineError(f"failed to read baseline report: {path}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BaselineError(f"failed to parse baseline report json: {exc}") from exc

    if not isinstance(payload, dict):
        raise BaselineError("baseline report root must be a JSON object")
    return payload


def _read_int(data: dict[str, Any], path: list[str]) -> int:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            joined = ".".join(path)
            raise BaselineError(f"baseline report is missing required field: {joined}")
        current = current[key]

    if isinstance(current, bool) or not isinstance(current, int):
        joined = ".".join(path)
        raise BaselineError(f"baseline field must be an integer: {joined}")
    return current


def _read_baseline_violations(data: dict[str, Any]) -> list[dict[str, Any]]:
    violations = data.get("violations")
    if not isinstance(violations, list):
        raise BaselineError("baseline report is missing required field: violations")

    normalized: list[dict[str, Any]] = []
    for item in violations:
        if not isinstance(item, dict):
            continue
        normalized.append(item)
    return normalized


def _baseline_metric_violations(
    *,
    metric: str,
    value: int,
    threshold: Threshold,
    message: str,
) -> list[Violation]:
    severity = _severity_for_threshold(value=float(value), threshold=threshold)
    if severity is None:
        return []

    return [
        Violation(
            severity=severity,
            scope="baseline",
            metric=metric,
            path=None,
            qualname=None,
            value=float(value),
            warn_threshold=threshold.warn,
            fail_threshold=threshold.fail,
            message=(f"{message} ({value} >= {threshold.warn}/{threshold.fail})"),
        )
    ]


def _severity_for_threshold(*, value: float, threshold: Threshold) -> str | None:
    if value >= threshold.fail:
        return "fail"
    if value >= threshold.warn:
        return "warn"
    return None


def _violation_signature_from_dict(
    payload: dict[str, Any],
) -> tuple[str, str, str | None, str | None]:
    scope = payload.get("scope")
    metric = payload.get("metric")
    path = payload.get("path")
    qualname = payload.get("qualname")
    return str(scope), str(metric), _as_optional_str(path), _as_optional_str(qualname)


def _violation_signature_from_model(item: Violation) -> tuple[str, str, str | None, str | None]:
    return item.scope, item.metric, item.path, item.qualname


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
