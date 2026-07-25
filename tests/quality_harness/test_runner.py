from __future__ import annotations

import json
from pathlib import Path

from ableton_cli.quality_harness.runner import run_quality_harness

from .helpers import write_config

_COMPLEX_FUNCTION = """
def {name}(value):
    total = 0
    for index in range(value):
        if index % 2 == 0 and index % 3 == 0:
            total += index
        elif index % 5 == 0 or index % 7 == 0:
            total -= index
        elif index > 10 and index < 20:
            total *= 2
        elif index > 30 and index < 40:
            total //= 2
        elif index > 50 and index < 60:
            total += 1
        elif index > 70 and index < 80:
            total -= 1
        elif index > 90 and index < 100:
            total += 3
        else:
            total += 1
    while total > 100 and total < 1000:
        total -= 7
    return total
"""


def _project(tmp_path: Path, functions: list[str]) -> Path:
    source_dir = tmp_path / "src"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "sample.py").write_text(
        "".join(_COMPLEX_FUNCTION.format(name=name) for name in functions),
        encoding="utf-8",
    )
    return write_config(tmp_path / ".quality-harness.yml", include=["src/**/*.py"])


def _run(tmp_path: Path, config_path: Path, baseline_path: Path | None):  # noqa: ANN202
    return run_quality_harness(
        config_path=config_path,
        report_path=tmp_path / "report.json",
        root_dir=tmp_path,
        baseline_path=baseline_path,
    )


def _write_baseline(path: Path, report) -> Path:  # noqa: ANN001
    path.write_text(
        json.dumps(
            {
                "summary": {
                    "warning_count": report.summary["warning_count"],
                    "failure_count": report.summary["failure_count"],
                },
                "violations": [
                    {
                        "severity": item.severity,
                        "scope": item.scope,
                        "metric": item.metric,
                        "path": item.path,
                        "qualname": item.qualname,
                    }
                    for item in report.violations
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_without_a_baseline_existing_failures_fail_the_run(tmp_path: Path) -> None:
    config_path = _project(tmp_path, ["already_bad"])
    result = _run(tmp_path, config_path, None)

    assert result.exit_code == 1
    assert result.report.summary["failure_count"] >= 1
    assert result.report.summary["baselined_failure_count"] == 0
    assert result.report.summary["status"] == "fail"


def test_baselined_failures_are_reported_but_do_not_fail_the_run(tmp_path: Path) -> None:
    config_path = _project(tmp_path, ["already_bad"])
    first = _run(tmp_path, config_path, None)
    baseline_path = _write_baseline(tmp_path / "baseline.json", first.report)

    result = _run(tmp_path, config_path, baseline_path)

    assert result.exit_code == 0
    assert result.report.summary["failure_count"] >= 1
    assert (
        result.report.summary["baselined_failure_count"] == result.report.summary["failure_count"]
    )
    assert result.report.summary["regression_count"] == 0
    assert result.report.summary["status"] != "fail"
    assert all(item.baselined for item in result.report.violations if item.severity == "fail")


def test_a_new_failure_still_fails_against_the_baseline(tmp_path: Path) -> None:
    config_path = _project(tmp_path, ["already_bad"])
    first = _run(tmp_path, config_path, None)
    baseline_path = _write_baseline(tmp_path / "baseline.json", first.report)

    _project(tmp_path, ["already_bad", "newly_bad"])
    result = _run(tmp_path, config_path, baseline_path)

    assert result.exit_code == 1
    regressions = [
        item for item in result.report.violations if item.severity == "fail" and not item.baselined
    ]
    assert any(item.qualname == "newly_bad" for item in regressions)
    assert not any(item.qualname == "already_bad" for item in regressions)
