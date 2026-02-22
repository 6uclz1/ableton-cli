from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from ableton_cli import dev_checks


def test_run_default_checks_runs_commands_in_order(monkeypatch) -> None:
    commands: list[tuple[str, ...]] = []

    def _run(command: tuple[str, ...], check: bool) -> SimpleNamespace:  # noqa: ANN202
        assert check is False
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(dev_checks.subprocess, "run", _run)

    result = dev_checks.run_default_checks()

    assert result == 0
    assert commands == list(dev_checks.DEFAULT_CHECK_COMMANDS)


def test_run_default_checks_runs_all_commands_and_returns_failure(monkeypatch) -> None:
    commands: list[tuple[str, ...]] = []
    exits = [0, 1, 0]

    def _run(command: tuple[str, ...], check: bool) -> SimpleNamespace:  # noqa: ANN202
        assert check is False
        commands.append(command)
        return SimpleNamespace(returncode=exits[len(commands) - 1])

    monkeypatch.setattr(dev_checks.subprocess, "run", _run)

    result = dev_checks.run_default_checks()

    assert result == 1
    assert commands == list(dev_checks.DEFAULT_CHECK_COMMANDS)


def test_run_default_checks_adds_junitxml_option_to_pytest_command(
    monkeypatch,
    tmp_path: Path,
) -> None:
    commands: list[tuple[str, ...]] = []

    def _run(command: tuple[str, ...], check: bool) -> SimpleNamespace:  # noqa: ANN202
        assert check is False
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(dev_checks.subprocess, "run", _run)

    junit_path = tmp_path / "pytest-report.xml"
    result = dev_checks.run_default_checks(pytest_junitxml_path=junit_path)

    assert result == 0
    assert commands[-1] == ("uv", "run", "pytest", f"--junitxml={junit_path}")


def test_main_writes_report_json(monkeypatch, tmp_path: Path) -> None:
    exits = [0, 0, 1]

    def _run(command: tuple[str, ...], check: bool) -> SimpleNamespace:  # noqa: ANN202
        assert check is False
        return SimpleNamespace(returncode=exits.pop(0))

    monkeypatch.setattr(dev_checks.subprocess, "run", _run)

    report_path = tmp_path / "dev-checks-report.json"
    junit_path = tmp_path / "pytest-report.xml"
    result = dev_checks.main(
        [
            "--report",
            str(report_path),
            "--pytest-junitxml",
            str(junit_path),
        ]
    )

    assert result == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["status"] == "fail"
    assert report["exit_code"] == 1
    assert len(report["commands"]) == 3
    assert report["commands"][2]["command"] == [
        "uv",
        "run",
        "pytest",
        f"--junitxml={junit_path}",
    ]
