from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .helpers import build_config_text

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SCRIPT = REPO_ROOT / "tools" / "quality_harness.py"


def _run_cli(tmp_path: Path, config_text: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    config_path = tmp_path / ".quality-harness.yml"
    report_path = tmp_path / "quality-harness-report.json"
    config_path.write_text(config_text, encoding="utf-8")

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = (
        src_path if not existing_pythonpath else f"{src_path}{os.pathsep}{existing_pythonpath}"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(CLI_SCRIPT),
            "--config",
            str(config_path),
            "--report",
            str(report_path),
        ],
        cwd=tmp_path,
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    return result, report_path


def _run_cli_with_baseline(
    tmp_path: Path,
    config_text: str,
    baseline_path: Path,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    config_path = tmp_path / ".quality-harness.yml"
    report_path = tmp_path / "quality-harness-report.json"
    config_path.write_text(config_text, encoding="utf-8")

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = (
        src_path if not existing_pythonpath else f"{src_path}{os.pathsep}{existing_pythonpath}"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(CLI_SCRIPT),
            "--config",
            str(config_path),
            "--report",
            str(report_path),
            "--baseline",
            str(baseline_path),
        ],
        cwd=tmp_path,
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    return result, report_path


def test_cli_outputs_json_report_and_exit_code_zero_on_pass(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "sample.py").write_text("def ok(a):\n    return a\n", encoding="utf-8")

    result, report_path = _run_cli(
        tmp_path,
        build_config_text(include=["src/**/*.py"]),
    )

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["phase"] == 2
    assert report["summary"]["status"] in {"pass", "warn"}


def test_cli_returns_exit_code_one_when_fail_violations_exist(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "sample.py").write_text(
        "\n".join(
            [
                "def heavy(a, b):",
                "    if a and b:",
                "        for i in range(3):",
                "            if i:",
                "                return i",
                "    return 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result, report_path = _run_cli(
        tmp_path,
        build_config_text(
            include=["src/**/*.py"],
            function_complexity_warn=1,
            function_complexity_fail=2,
        ),
    )

    assert result.returncode == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["failure_count"] >= 1
    assert report["summary"]["status"] == "fail"


def test_cli_returns_exit_code_two_for_invalid_config(tmp_path: Path) -> None:
    result, _report_path = _run_cli(tmp_path, "version: 1\nphase: 1\n")

    assert result.returncode == 2
    assert "error" in result.stderr.lower()


def test_cli_supports_optional_baseline_comparison(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "sample.py").write_text("def ok(a):\n    return a\n", encoding="utf-8")

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "summary": {"warning_count": 0, "failure_count": 0},
                "violations": [],
            }
        ),
        encoding="utf-8",
    )

    result, report_path = _run_cli_with_baseline(
        tmp_path,
        build_config_text(include=["src/**/*.py"]),
        baseline_path,
    )

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["baseline_used"] is True
    assert report["baseline_comparison"]["baseline_path"].endswith("baseline.json")
