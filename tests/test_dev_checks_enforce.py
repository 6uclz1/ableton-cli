from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class _FakeViolation:
    severity: str
    scope: str
    metric: str
    path: str | None
    qualname: str | None
    value: float
    warn_threshold: float | None
    fail_threshold: float | None
    message: str


@dataclass(frozen=True)
class _FakeReport:
    violations: list[_FakeViolation]


@dataclass(frozen=True)
class _FakeRunResult:
    report: _FakeReport


class _CompletedProcess:
    def __init__(self, returncode: int) -> None:
        self.returncode = int(returncode)


def _fail_violation() -> _FakeViolation:
    return _FakeViolation(
        severity="fail",
        scope="file",
        metric="complexity",
        path="src/example.py",
        qualname=None,
        value=300.0,
        warn_threshold=180.0,
        fail_threshold=260.0,
        message="complexity exceeds fail threshold",
    )


def test_dev_checks_enforce_passes_without_actions(monkeypatch, tmp_path: Path) -> None:
    from ableton_cli import dev_checks_enforce

    report_path = tmp_path / "quality-harness-report.json"
    action_log_path = tmp_path / "quality-harness-action-log.json"

    monkeypatch.setattr(
        dev_checks_enforce,
        "run_quality_harness",
        lambda **_kwargs: _FakeRunResult(report=_FakeReport(violations=[])),
    )

    def _unexpected_action(*_args, **_kwargs):  # noqa: ANN202
        raise AssertionError("actions should not run when there are no fail violations")

    monkeypatch.setattr(dev_checks_enforce.subprocess, "run", _unexpected_action)

    exit_code = dev_checks_enforce.main(
        [
            "--report",
            str(report_path),
            "--action-log",
            str(action_log_path),
            "--max-attempts",
            "2",
        ]
    )

    assert exit_code == 0
    payload = json.loads(action_log_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["attempt_count"] == 1
    assert payload["unresolved_failures"] == []


def test_dev_checks_enforce_retries_after_actions_and_converges(
    monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli import dev_checks_enforce

    report_path = tmp_path / "quality-harness-report.json"
    action_log_path = tmp_path / "quality-harness-action-log.json"
    state = {"calls": 0, "commands": []}

    def _run_quality_harness(**_kwargs):  # noqa: ANN202
        state["calls"] += 1
        if state["calls"] == 1:
            return _FakeRunResult(report=_FakeReport(violations=[_fail_violation()]))
        return _FakeRunResult(report=_FakeReport(violations=[]))

    def _run_action(command, check=False):  # noqa: ANN202
        state["commands"].append(tuple(command))
        return _CompletedProcess(returncode=0)

    monkeypatch.setattr(dev_checks_enforce, "run_quality_harness", _run_quality_harness)
    monkeypatch.setattr(dev_checks_enforce.subprocess, "run", _run_action)

    exit_code = dev_checks_enforce.main(
        [
            "--report",
            str(report_path),
            "--action-log",
            str(action_log_path),
            "--max-attempts",
            "2",
        ]
    )

    assert exit_code == 0
    assert state["calls"] == 2
    assert state["commands"] == [
        ("uv", "run", "ruff", "check", "--fix", "."),
        ("uv", "run", "ruff", "format", "."),
    ]
    payload = json.loads(action_log_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["attempt_count"] == 2


def test_dev_checks_enforce_fails_when_unresolved_after_max_attempts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from ableton_cli import dev_checks_enforce

    report_path = tmp_path / "quality-harness-report.json"
    action_log_path = tmp_path / "quality-harness-action-log.json"

    monkeypatch.setattr(
        dev_checks_enforce,
        "run_quality_harness",
        lambda **_kwargs: _FakeRunResult(report=_FakeReport(violations=[_fail_violation()])),
    )
    monkeypatch.setattr(
        dev_checks_enforce.subprocess,
        "run",
        lambda *args, **kwargs: _CompletedProcess(returncode=0),
    )

    exit_code = dev_checks_enforce.main(
        [
            "--report",
            str(report_path),
            "--action-log",
            str(action_log_path),
            "--max-attempts",
            "2",
        ]
    )

    assert exit_code == 1
    payload = json.loads(action_log_path.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert payload["attempt_count"] == 2
    assert payload["unresolved_failures"]
