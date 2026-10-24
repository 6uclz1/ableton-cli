from __future__ import annotations

import json
from pathlib import Path

from ableton_cli.quality_harness.baseline import compare_against_baseline
from ableton_cli.quality_harness.models import BaselineConfig, Threshold, Violation


def test_compare_against_baseline_detects_regressions(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "summary": {"warning_count": 10, "failure_count": 0},
                "violations": [],
            }
        ),
        encoding="utf-8",
    )

    current_violations = [
        Violation(
            severity="fail",
            scope="function",
            metric="complexity",
            path="src/sample.py",
            qualname="heavy",
            value=15.0,
            warn_threshold=10.0,
            fail_threshold=15.0,
            message="function.complexity exceeded",
        )
    ]

    config = BaselineConfig(
        warning_delta=Threshold(warn=3, fail=10),
        failure_delta=Threshold(warn=1, fail=1),
        new_failures=Threshold(warn=1, fail=1),
    )

    comparison, violations, known_failures = compare_against_baseline(
        baseline_path=baseline_path,
        baseline_config=config,
        current_warning_count=14,
        current_failure_count=1,
        current_violations=current_violations,
    )

    assert comparison.warning_delta == 4
    assert comparison.failure_delta == 1
    assert comparison.new_failures == 1

    metrics = {(v.metric, v.severity) for v in violations}
    assert ("warning_delta", "warn") in metrics
    assert ("failure_delta", "fail") in metrics
    assert ("new_failures", "fail") in metrics
    assert known_failures == set()


def _violation(qualname: str, value: float) -> Violation:
    return Violation(
        severity="fail",
        scope="function",
        metric="complexity",
        path="src/sample.py",
        qualname=qualname,
        value=value,
        warn_threshold=10.0,
        fail_threshold=15.0,
        message="function.complexity exceeded",
    )


def _baseline_file(tmp_path: Path, violations: list[Violation]) -> Path:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "summary": {
                    "warning_count": 0,
                    "failure_count": len(violations),
                },
                "violations": [
                    {
                        "severity": item.severity,
                        "scope": item.scope,
                        "metric": item.metric,
                        "path": item.path,
                        "qualname": item.qualname,
                    }
                    for item in violations
                ],
            }
        ),
        encoding="utf-8",
    )
    return baseline_path


def test_known_failures_report_the_baselined_signatures(tmp_path: Path) -> None:
    known = _violation("already_bad", 20.0)
    baseline_path = _baseline_file(tmp_path, [known])

    config = BaselineConfig(
        warning_delta=Threshold(warn=3, fail=10),
        failure_delta=Threshold(warn=1, fail=1),
        new_failures=Threshold(warn=1, fail=1),
    )

    _, _, known_failures = compare_against_baseline(
        baseline_path=baseline_path,
        baseline_config=config,
        current_warning_count=0,
        current_failure_count=1,
        current_violations=[known],
    )

    assert known_failures == {("function", "complexity", "src/sample.py", "already_bad")}


def test_committed_baseline_is_readable_and_trimmed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    baseline_path = repo_root / "quality-harness-baseline.json"
    assert baseline_path.exists(), "quality-harness-baseline.json must be committed"

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert isinstance(payload["summary"]["warning_count"], int)
    assert isinstance(payload["summary"]["failure_count"], int)
    assert isinstance(payload["violations"], list)
    # Baselines carry signatures, not the full per-function metric dump.
    assert "metrics" not in payload
