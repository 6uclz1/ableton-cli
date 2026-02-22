from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import config_to_dict
from .models import (
    AnalysisResult,
    BaselineComparison,
    Config,
    DependencyCycle,
    DuplicateGroup,
    LayerViolationRecord,
    MetricBundle,
    Report,
    Violation,
)


def build_report(
    *,
    config: Config,
    analysis: AnalysisResult,
    duplicates: list[DuplicateGroup],
    dependency_cycles: list[DependencyCycle],
    layer_violations: list[LayerViolationRecord],
    baseline_comparison: BaselineComparison | None,
    violations: list[Violation],
) -> Report:
    warning_count = sum(1 for item in violations if item.severity == "warn")
    failure_count = sum(1 for item in violations if item.severity == "fail")
    status = "fail" if failure_count > 0 else "warn" if warning_count > 0 else "pass"

    summary = {
        "files_total": analysis.files_total,
        "files_parsed": len(analysis.file_metrics),
        "parse_error_count": len(analysis.parse_errors),
        "function_count": len(analysis.function_metrics),
        "class_count": len(analysis.class_metrics),
        "duplicate_group_count": len(duplicates),
        "dependency_cycle_count": len(dependency_cycles),
        "layer_violation_count": len(layer_violations),
        "baseline_used": baseline_comparison is not None,
        "warning_count": warning_count,
        "failure_count": failure_count,
        "status": status,
    }

    return Report(
        schema_version=1,
        phase=config.phase,
        summary=summary,
        metrics=MetricBundle(
            files=analysis.file_metrics,
            functions=analysis.function_metrics,
            classes=analysis.class_metrics,
            duplicates=duplicates,
        ),
        violations=violations,
        parse_errors=analysis.parse_errors,
        dependency_cycles=dependency_cycles,
        layer_violations=layer_violations,
        baseline_comparison=baseline_comparison,
        effective_config=config_to_dict(config),
    )


def write_report(report: Report, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
