"""Regenerate the committed quality-harness baseline.

The baseline records the violations the repository is currently carrying so
CI can fail on regressions only. Keep it trimmed: a full report is ~1 MB of
per-function metrics, none of which the comparison reads.

Run this only when the accepted debt genuinely changes, and say why in the
commit message:

    uv run python tools/update_quality_harness_baseline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from ableton_cli.quality_harness.runner import run_quality_harness

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / ".quality-harness.yml"
BASELINE_PATH = REPO_ROOT / "quality-harness-baseline.json"


def build_baseline() -> dict[str, object]:
    with_report = REPO_ROOT / "quality-harness-baseline.full.json"
    try:
        result = run_quality_harness(
            config_path=CONFIG_PATH,
            report_path=with_report,
            root_dir=REPO_ROOT,
            baseline_path=None,
        )
    finally:
        with_report.unlink(missing_ok=True)

    summary = result.report.summary
    return {
        "schema_version": result.report.schema_version,
        "summary": {
            "warning_count": summary["warning_count"],
            "failure_count": summary["failure_count"],
        },
        "violations": [
            {
                "severity": item.severity,
                "scope": item.scope,
                "metric": item.metric,
                "path": item.path,
                "qualname": item.qualname,
                "message": item.message,
            }
            for item in result.report.violations
        ],
    }


def main() -> int:
    baseline = build_baseline()
    BASELINE_PATH.write_text(
        json.dumps(baseline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = baseline["summary"]
    print(f"wrote {BASELINE_PATH.relative_to(REPO_ROOT)}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
