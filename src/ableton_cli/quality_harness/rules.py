from __future__ import annotations

from .models import (
    ClassMetric,
    Config,
    DependencyCycle,
    DuplicateGroup,
    FileMetric,
    FunctionMetric,
    LayerViolationRecord,
    ParseErrorRecord,
    Threshold,
    Violation,
)


def evaluate_violations(
    *,
    config: Config,
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    class_metrics: list[ClassMetric],
    duplicates: list[DuplicateGroup],
    parse_errors: list[ParseErrorRecord],
    dependency_cycles: list[DependencyCycle],
    layer_violations: list[LayerViolationRecord],
) -> list[Violation]:
    violations: list[Violation] = []

    violations.extend(
        _evaluate_scope_metrics(
            scope="file",
            metrics=file_metrics,
            thresholds=config.thresholds.file,
        )
    )
    violations.extend(
        _evaluate_scope_metrics(
            scope="function",
            metrics=function_metrics,
            thresholds=config.thresholds.function,
        )
    )
    violations.extend(
        _evaluate_scope_metrics(
            scope="class",
            metrics=class_metrics,
            thresholds=config.thresholds.class_,
        )
    )

    duplicate_threshold = config.thresholds.duplicates["occurrences"]
    for group in duplicates:
        severity = _severity_for_threshold(group.occurrences, duplicate_threshold)
        if severity is None:
            continue
        duplicate_threshold_text = (
            f"{group.occurrences} >= {duplicate_threshold.warn}/{duplicate_threshold.fail}"
        )
        violations.append(
            Violation(
                severity=severity,
                scope="duplicates",
                metric="occurrences",
                path=group.locations[0].path if group.locations else None,
                qualname=group.locations[0].qualname if group.locations else None,
                value=float(group.occurrences),
                warn_threshold=duplicate_threshold.warn,
                fail_threshold=duplicate_threshold.fail,
                message=(
                    f"duplicate block occurrences exceeded threshold ({duplicate_threshold_text})"
                ),
            )
        )

    dependency_cycle_threshold = config.dependencies.cycle_count
    dependency_cycle_count = len(dependency_cycles)
    dependency_severity = _severity_for_threshold(
        dependency_cycle_count,
        dependency_cycle_threshold,
    )
    if dependency_severity is not None:
        violations.append(
            Violation(
                severity=dependency_severity,
                scope="dependencies",
                metric="cycle_count",
                path=None,
                qualname=None,
                value=float(dependency_cycle_count),
                warn_threshold=dependency_cycle_threshold.warn,
                fail_threshold=dependency_cycle_threshold.fail,
                message=(
                    "dependency cycle count exceeded threshold "
                    f"({dependency_cycle_count} >= "
                    f"{dependency_cycle_threshold.warn}/{dependency_cycle_threshold.fail})"
                ),
            )
        )

    layer_violation_threshold = config.layers.violation_count
    layer_violation_count = len(layer_violations)
    layer_severity = _severity_for_threshold(layer_violation_count, layer_violation_threshold)
    if layer_severity is not None:
        violations.append(
            Violation(
                severity=layer_severity,
                scope="layers",
                metric="violation_count",
                path=None,
                qualname=None,
                value=float(layer_violation_count),
                warn_threshold=layer_violation_threshold.warn,
                fail_threshold=layer_violation_threshold.fail,
                message=(
                    "layer violation count exceeded threshold "
                    f"({layer_violation_count} >= "
                    f"{layer_violation_threshold.warn}/{layer_violation_threshold.fail})"
                ),
            )
        )

    parse_severity = config.parse_errors_mode
    for parse_error in parse_errors:
        violations.append(
            Violation(
                severity=parse_severity,
                scope="parse_errors",
                metric="count",
                path=parse_error.path,
                qualname=None,
                value=1.0,
                warn_threshold=None,
                fail_threshold=None,
                message=f"{parse_error.error_type}: {parse_error.message}",
            )
        )

    return _sort_violations(violations)


def sort_violations(violations: list[Violation]) -> list[Violation]:
    return _sort_violations(violations)


def _sort_violations(violations: list[Violation]) -> list[Violation]:
    return sorted(
        violations,
        key=lambda item: (
            0 if item.severity == "fail" else 1,
            item.scope,
            item.metric,
            item.path or "",
            item.qualname or "",
        ),
    )


def _evaluate_scope_metrics(
    *,
    scope: str,
    metrics: list[FileMetric] | list[FunctionMetric] | list[ClassMetric],
    thresholds: dict[str, Threshold],
) -> list[Violation]:
    violations: list[Violation] = []
    for metric_record in metrics:
        for metric_name, threshold in thresholds.items():
            value = float(getattr(metric_record, metric_name))
            severity = _severity_for_threshold(value, threshold)
            if severity is None:
                continue

            path = getattr(metric_record, "path", None)
            qualname = getattr(metric_record, "qualname", None)
            violations.append(
                Violation(
                    severity=severity,
                    scope=scope,
                    metric=metric_name,
                    path=path,
                    qualname=qualname,
                    value=value,
                    warn_threshold=threshold.warn,
                    fail_threshold=threshold.fail,
                    message=(
                        f"{scope}.{metric_name} exceeded threshold "
                        f"({value} >= {threshold.warn}/{threshold.fail})"
                    ),
                )
            )
    return violations


def _severity_for_threshold(value: float, threshold: Threshold) -> str | None:
    if value >= threshold.fail:
        return "fail"
    if value >= threshold.warn:
        return "warn"
    return None
