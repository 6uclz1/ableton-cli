#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ableton_cli.quality_harness.baseline import BaselineError
from ableton_cli.quality_harness.config import ConfigError
from ableton_cli.quality_harness.runner import run_quality_harness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quality harness for Python projects")
    parser.add_argument(
        "--config",
        default=".quality-harness.yml",
        help="Path to .quality-harness.yml",
    )
    parser.add_argument(
        "--report",
        default="quality-harness-report.json",
        help="Path to JSON report output",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Optional baseline report JSON for regression comparison",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    report_path = Path(args.report)
    baseline_path = Path(args.baseline) if args.baseline else None

    try:
        result = run_quality_harness(
            config_path=config_path,
            report_path=report_path,
            root_dir=Path.cwd(),
            baseline_path=baseline_path,
        )
    except (ConfigError, BaselineError) as exc:
        print(f"quality-harness error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(f"quality-harness error: {exc}", file=sys.stderr)
        return 2

    summary = result.report.summary
    print(
        "quality-harness "
        f"status={summary['status']} "
        f"warnings={summary['warning_count']} "
        f"failures={summary['failure_count']} "
        f"files={summary['files_parsed']}/{summary['files_total']} "
        f"cycles={summary['dependency_cycle_count']} "
        f"layer_violations={summary['layer_violation_count']} "
        f"parse_errors={summary['parse_error_count']} "
        f"baseline_used={summary['baseline_used']} "
        f"report={report_path}"
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
