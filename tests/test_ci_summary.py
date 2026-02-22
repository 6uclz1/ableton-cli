from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ableton_cli import ci_summary


def _write_quality_harness_report(
    path: Path,
    *,
    status: str,
    warnings: int,
    failures: int,
    violations: list[dict[str, Any]] | None = None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "summary": {
                    "status": status,
                    "warning_count": warnings,
                    "failure_count": failures,
                    "files_parsed": 12,
                    "files_total": 12,
                    "dependency_cycle_count": 0,
                    "layer_violation_count": 0,
                    "parse_error_count": 0,
                },
                "violations": violations or [],
            }
        ),
        encoding="utf-8",
    )


def _write_dev_checks_report(path: Path, *, status: str, exit_code: int) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": status,
                "exit_code": exit_code,
                "commands": [
                    {
                        "command": ["uv", "run", "ruff", "check", "."],
                        "exit_code": 0,
                        "status": "pass",
                    },
                    {
                        "command": ["uv", "run", "ruff", "format", "--check", "."],
                        "exit_code": 0,
                        "status": "pass",
                    },
                    {
                        "command": ["uv", "run", "pytest", "--junitxml=pytest-report.xml"],
                        "exit_code": exit_code,
                        "status": status,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_junit_report(path: Path, *, failing: bool) -> None:
    if failing:
        xml = (
            '<testsuite name="pytest" tests="1" failures="1" errors="0" skipped="0">'
            '<testcase classname="tests.test_transport" name="test_stop"/>'
            '<testcase classname="tests.test_transport" name="test_play">'
            '<failure message="AssertionError: expected 120">assert 110 == 120</failure>'
            "</testcase>"
            "</testsuite>"
        )
    else:
        xml = (
            '<testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="tests.test_transport" name="test_play"/>'
            "</testsuite>"
        )
    path.write_text(xml, encoding="utf-8")


def test_main_generates_summary_for_success_case(tmp_path: Path) -> None:
    quality_report = tmp_path / "quality-harness-report.json"
    dev_report = tmp_path / "dev-checks-report.json"
    junit_report = tmp_path / "pytest-report.xml"
    summary_path = tmp_path / "summary.md"
    _write_quality_harness_report(quality_report, status="pass", warnings=0, failures=0)
    _write_dev_checks_report(dev_report, status="pass", exit_code=0)
    _write_junit_report(junit_report, failing=False)

    result = ci_summary.main(
        [
            "--quality-harness-report",
            str(quality_report),
            "--dev-checks-report",
            str(dev_report),
            "--pytest-junit-report",
            str(junit_report),
            "--summary-file",
            str(summary_path),
        ]
    )

    assert result == 0
    summary = summary_path.read_text(encoding="utf-8")
    assert "## Overall Status" in summary
    assert "## Key Metrics" in summary
    assert "## Failed Tests" in summary
    assert "## Next Actions" in summary
    assert "## Quality Harness Results" not in summary
    assert "- Status: PASS" in summary


def test_main_lists_failed_tests_with_file_test_name_and_message(tmp_path: Path) -> None:
    quality_report = tmp_path / "quality-harness-report.json"
    dev_report = tmp_path / "dev-checks-report.json"
    junit_report = tmp_path / "pytest-report.xml"
    summary_path = tmp_path / "summary.md"
    _write_quality_harness_report(
        quality_report,
        status="fail",
        warnings=1,
        failures=2,
        violations=[
            {
                "severity": "fail",
                "scope": "function",
                "metric": "complexity",
                "path": "src/ableton_cli/commands/transport.py",
                "qualname": "heavy_transport",
                "value": 42,
                "warn_threshold": 10,
                "fail_threshold": 35,
                "message": "function complexity exceeded fail threshold",
            }
        ],
    )
    _write_dev_checks_report(dev_report, status="fail", exit_code=1)
    _write_junit_report(junit_report, failing=True)

    result = ci_summary.main(
        [
            "--quality-harness-report",
            str(quality_report),
            "--dev-checks-report",
            str(dev_report),
            "--pytest-junit-report",
            str(junit_report),
            "--summary-file",
            str(summary_path),
        ]
    )

    assert result == 1
    summary = summary_path.read_text(encoding="utf-8")
    assert "| tests/test_transport.py | test_play | AssertionError: expected 120 |" in summary
    assert "- Status: FAIL" in summary
    assert "## Quality Harness Results" in summary
    assert (
        "| fail | function.complexity | src/ableton_cli/commands/transport.py::heavy_transport |"
        in summary
    )
    assert "| 42 | 35 | function complexity exceeded fail threshold |" in summary
    assert "- Review the Quality Harness Results section and resolve fail-level metrics." in summary


def test_main_fails_when_required_artifact_is_missing(tmp_path: Path, capsys) -> None:
    quality_report = tmp_path / "quality-harness-report.json"
    junit_report = tmp_path / "pytest-report.xml"
    summary_path = tmp_path / "summary.md"
    _write_quality_harness_report(quality_report, status="pass", warnings=0, failures=0)
    _write_junit_report(junit_report, failing=False)
    missing_dev_report = tmp_path / "missing-dev-checks-report.json"

    result = ci_summary.main(
        [
            "--quality-harness-report",
            str(quality_report),
            "--dev-checks-report",
            str(missing_dev_report),
            "--pytest-junit-report",
            str(junit_report),
            "--summary-file",
            str(summary_path),
        ]
    )

    assert result == 2
    assert not summary_path.exists()
    assert str(missing_dev_report) in capsys.readouterr().err


def test_main_fails_when_quality_status_is_warn_but_violation_list_is_empty(tmp_path: Path) -> None:
    quality_report = tmp_path / "quality-harness-report.json"
    dev_report = tmp_path / "dev-checks-report.json"
    junit_report = tmp_path / "pytest-report.xml"
    summary_path = tmp_path / "summary.md"
    _write_quality_harness_report(
        quality_report,
        status="warn",
        warnings=1,
        failures=0,
        violations=[],
    )
    _write_dev_checks_report(dev_report, status="pass", exit_code=0)
    _write_junit_report(junit_report, failing=False)

    result = ci_summary.main(
        [
            "--quality-harness-report",
            str(quality_report),
            "--dev-checks-report",
            str(dev_report),
            "--pytest-junit-report",
            str(junit_report),
            "--summary-file",
            str(summary_path),
        ]
    )

    assert result == 2
    assert not summary_path.exists()
