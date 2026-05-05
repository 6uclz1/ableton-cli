from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _load_ci_workflow() -> dict[str, object]:
    return yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_ci_workflow_limits_default_token_permissions() -> None:
    workflow = _load_ci_workflow()

    assert workflow["permissions"] == {"contents": "read"}


def test_ci_workflow_configures_dev_checks_reports() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    test_job = jobs["test"]
    steps = test_job["steps"]

    verify_generated_docs = next(
        step for step in steps if step.get("name") == "Verify generated skill docs"
    )
    assert "python tools/generate_skill_docs.py" in verify_generated_docs["run"]
    assert "git diff --exit-code" in verify_generated_docs["run"]

    run_lint_and_tests = next(step for step in steps if step.get("name") == "Run lint and tests")
    assert run_lint_and_tests["run"] == (
        "uv run python -m ableton_cli.dev_checks "
        "--report dev-checks-report.json "
        "--pytest-junitxml pytest-report.xml"
    )

    assert any(step.get("name") == "Upload dev checks report" for step in steps)
    assert any(step.get("name") == "Upload pytest report" for step in steps)


def test_ci_workflow_uses_dev_checks_enforce_for_quality_harness_job() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    quality_job = jobs["quality-harness"]
    steps = quality_job["steps"]

    run_enforce = next(step for step in steps if step.get("name") == "Run dev checks enforce")
    assert run_enforce["run"] == (
        "uv run python -m ableton_cli.dev_checks_enforce "
        "--config .quality-harness.yml "
        "--report quality-harness-report.json "
        "--action-log quality-harness-action-log.json"
    )

    assert any(step.get("name") == "Upload quality harness report" for step in steps)
    assert any(step.get("name") == "Upload quality harness action log" for step in steps)


def test_ci_workflow_has_summary_job() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    summary_job = jobs["summary"]
    steps = summary_job["steps"]
    generate_summary = next(step for step in steps if step.get("name") == "Generate CI summary")

    run = generate_summary["run"]
    assert "python -m ableton_cli.ci_summary" in run
    assert "--quality-harness-report" in run
    assert "--dev-checks-report" in run
    assert "--pytest-junit-report" in run
    assert '--summary-file "$GITHUB_STEP_SUMMARY"' in run

    download_steps = [step for step in steps if step.get("uses") == "actions/download-artifact@v4"]
    assert len(download_steps) >= 1
    assert all("if-no-files-found" not in step.get("with", {}) for step in download_steps)
