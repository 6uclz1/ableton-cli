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

    comparison, violations = compare_against_baseline(
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
