from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


@dataclass(frozen=True)
class DevChecksMetrics:
    total_reports: int
    failed_reports: int
    total_commands: int
    failed_commands: int


@dataclass(frozen=True)
class PytestTotals:
    tests: int
    failures: int
    errors: int
    skipped: int


@dataclass(frozen=True)
class FailedTest:
    file: str
    name: str
    message: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate GitHub Actions summary from quality harness and pytest artifacts.",
    )
    parser.add_argument("--quality-harness-report", required=True)
    parser.add_argument("--dev-checks-report", required=True, action="append")
    parser.add_argument("--pytest-junit-report", required=True, action="append")
    parser.add_argument("--summary-file", required=True)
    return parser


def _ensure_artifact(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"required artifact missing: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"required artifact is empty: {path}")


def _read_json(path: Path) -> dict[str, Any]:
    _ensure_artifact(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in artifact: {path}")
    return payload


def _read_quality_harness_report(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"quality harness artifact has invalid summary object: {path}")
    required_keys = (
        "status",
        "warning_count",
        "failure_count",
        "files_parsed",
        "files_total",
        "dependency_cycle_count",
        "layer_violation_count",
        "parse_error_count",
    )
    for key in required_keys:
        if key not in summary:
            raise ValueError(f"quality harness artifact missing summary key '{key}': {path}")
    return summary


def _read_dev_checks_reports(paths: list[Path]) -> DevChecksMetrics:
    failed_reports = 0
    total_commands = 0
    failed_commands = 0
    for path in paths:
        payload = _read_json(path)
        status = payload.get("status")
        if status not in {"pass", "fail"}:
            raise ValueError(f"dev checks artifact has invalid status: {path}")
        if status == "fail":
            failed_reports += 1
        commands = payload.get("commands")
        if not isinstance(commands, list):
            raise ValueError(f"dev checks artifact has invalid commands list: {path}")
        total_commands += len(commands)
        failed_commands += sum(1 for command in commands if int(command.get("exit_code", 1)) != 0)

    return DevChecksMetrics(
        total_reports=len(paths),
        failed_reports=failed_reports,
        total_commands=total_commands,
        failed_commands=failed_commands,
    )


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid integer value in junit report: {value!r}") from exc


def _classname_to_file(classname: str | None) -> str:
    if not classname:
        return "-"
    return f"{classname.replace('.', '/')}.py"


def _message_from_element(element: ElementTree.Element | None) -> str:
    if element is None:
        return "-"
    message = (element.attrib.get("message") or "").strip()
    if message:
        return message.replace("\n", " ")
    text = (element.text or "").strip()
    if not text:
        return "-"
    return text.splitlines()[0].strip()


def _parse_junit_report(path: Path) -> tuple[PytestTotals, list[FailedTest]]:
    _ensure_artifact(path)
    tree = ElementTree.parse(path)
    root = tree.getroot()
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root.findall("testsuite"))
    else:
        raise ValueError(f"unsupported junit root tag '{root.tag}': {path}")

    tests = 0
    failures = 0
    errors = 0
    skipped = 0
    failed_tests: list[FailedTest] = []
    for suite in suites:
        tests += _to_int(suite.attrib.get("tests", 0))
        failures += _to_int(suite.attrib.get("failures", 0))
        errors += _to_int(suite.attrib.get("errors", 0))
        skipped += _to_int(suite.attrib.get("skipped", 0))
        for testcase in suite.findall("testcase"):
            failure = testcase.find("failure")
            error = testcase.find("error")
            if failure is None and error is None:
                continue
            file_name = testcase.attrib.get("file") or _classname_to_file(
                testcase.attrib.get("classname")
            )
            failed_tests.append(
                FailedTest(
                    file=file_name,
                    name=testcase.attrib.get("name", "-"),
                    message=_message_from_element(failure if failure is not None else error),
                )
            )
    return PytestTotals(
        tests=tests, failures=failures, errors=errors, skipped=skipped
    ), failed_tests


def _merge_pytest_reports(paths: list[Path]) -> tuple[PytestTotals, list[FailedTest]]:
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    failed_tests: list[FailedTest] = []

    for path in paths:
        totals, report_failed_tests = _parse_junit_report(path)
        total_tests += totals.tests
        total_failures += totals.failures
        total_errors += totals.errors
        total_skipped += totals.skipped
        failed_tests.extend(report_failed_tests)

    return (
        PytestTotals(
            tests=total_tests,
            failures=total_failures,
            errors=total_errors,
            skipped=total_skipped,
        ),
        failed_tests,
    )


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _build_summary_markdown(
    *,
    quality_summary: dict[str, Any],
    dev_metrics: DevChecksMetrics,
    pytest_totals: PytestTotals,
    failed_tests: list[FailedTest],
) -> tuple[str, int]:
    quality_status = str(quality_summary["status"])
    has_fail = (
        quality_status == "fail"
        or dev_metrics.failed_reports > 0
        or pytest_totals.failures > 0
        or pytest_totals.errors > 0
    )
    overall_status = "FAIL" if has_fail else "WARN" if quality_status == "warn" else "PASS"
    exit_code = 1 if has_fail else 0

    test_status = "FAIL" if (pytest_totals.failures > 0 or pytest_totals.errors > 0) else "PASS"
    dev_status = "FAIL" if dev_metrics.failed_reports > 0 else "PASS"
    quality_warnings = quality_summary["warning_count"]
    quality_failures = quality_summary["failure_count"]
    quality_files_parsed = quality_summary["files_parsed"]
    quality_files_total = quality_summary["files_total"]

    lines: list[str] = []
    lines.append("## Overall Status")
    lines.append(f"- Status: {overall_status}")
    lines.append(
        "- Quality Harness: "
        f"{quality_status.upper()} "
        f"(warnings={quality_warnings}, failures={quality_failures})"
    )
    lines.append(
        f"- Dev Checks: {dev_status} "
        f"(failed_reports={dev_metrics.failed_reports}/{dev_metrics.total_reports}, "
        f"failed_commands={dev_metrics.failed_commands}/{dev_metrics.total_commands})"
    )
    lines.append(
        f"- Pytest: {test_status} "
        f"(tests={pytest_totals.tests}, failures={pytest_totals.failures}, "
        f"errors={pytest_totals.errors}, skipped={pytest_totals.skipped})"
    )
    lines.append("")
    lines.append("## Key Metrics")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Quality files parsed | {quality_files_parsed}/{quality_files_total} |")
    lines.append(f"| Quality warnings | {quality_warnings} |")
    lines.append(f"| Quality failures | {quality_failures} |")
    lines.append(f"| Dependency cycles | {quality_summary['dependency_cycle_count']} |")
    lines.append(f"| Layer violations | {quality_summary['layer_violation_count']} |")
    lines.append(f"| Parse errors | {quality_summary['parse_error_count']} |")
    lines.append(f"| Dev check reports | {dev_metrics.total_reports} |")
    lines.append(f"| Dev check failed reports | {dev_metrics.failed_reports} |")
    lines.append(f"| Dev check failed commands | {dev_metrics.failed_commands} |")
    lines.append(f"| Pytest reports | {pytest_totals.tests} tests total |")
    lines.append("")
    lines.append("## Failed Tests")
    lines.append("| File | Test | Message |")
    lines.append("| --- | --- | --- |")
    if failed_tests:
        for failure in failed_tests:
            lines.append(
                f"| {_escape_cell(failure.file)} | {_escape_cell(failure.name)} | "
                f"{_escape_cell(failure.message)} |"
            )
    else:
        lines.append("| - | - | No failed tests |")
    lines.append("")
    lines.append("## Next Actions")
    if overall_status == "PASS":
        lines.append("- No action required.")
    else:
        if quality_status in {"warn", "fail"}:
            lines.append("- Review quality harness violations and resolve fail-level metrics.")
        if dev_metrics.failed_reports > 0:
            lines.append("- Re-run failed dev check commands locally and fix lint/test issues.")
        if pytest_totals.failures > 0 or pytest_totals.errors > 0:
            lines.append("- Fix the failed tests listed above.")
    lines.append("")
    return "\n".join(lines), exit_code


def generate_summary(
    *,
    quality_harness_report: Path,
    dev_checks_reports: list[Path],
    pytest_junit_reports: list[Path],
    summary_file: Path,
) -> int:
    quality_summary = _read_quality_harness_report(quality_harness_report)
    dev_metrics = _read_dev_checks_reports(dev_checks_reports)
    pytest_totals, failed_tests = _merge_pytest_reports(pytest_junit_reports)
    summary, exit_code = _build_summary_markdown(
        quality_summary=quality_summary,
        dev_metrics=dev_metrics,
        pytest_totals=pytest_totals,
        failed_tests=failed_tests,
    )
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(summary, encoding="utf-8")
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return generate_summary(
            quality_harness_report=Path(args.quality_harness_report),
            dev_checks_reports=[Path(item) for item in args.dev_checks_report],
            pytest_junit_reports=[Path(item) for item in args.pytest_junit_report],
            summary_file=Path(args.summary_file),
        )
    except (OSError, ValueError, json.JSONDecodeError, ElementTree.ParseError) as exc:
        print(f"ci-summary error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
