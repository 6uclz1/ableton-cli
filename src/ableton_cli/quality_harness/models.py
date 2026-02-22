from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["warn", "fail"]


@dataclass(frozen=True)
class Threshold:
    warn: float
    fail: float


@dataclass(frozen=True)
class DuplicationConfig:
    min_lines: int
    min_tokens: int


@dataclass(frozen=True)
class BaselineConfig:
    warning_delta: Threshold
    failure_delta: Threshold
    new_failures: Threshold


@dataclass(frozen=True)
class DependenciesConfig:
    cycle_count: Threshold


@dataclass(frozen=True)
class LayerRule:
    name: str
    include: list[str]


@dataclass(frozen=True)
class LayersConfig:
    violation_count: Threshold
    order: list[LayerRule]


@dataclass(frozen=True)
class ThresholdGroups:
    file: dict[str, Threshold]
    function: dict[str, Threshold]
    class_: dict[str, Threshold]
    duplicates: dict[str, Threshold]


@dataclass(frozen=True)
class Config:
    version: int
    phase: int
    include: list[str]
    exclude: list[str]
    duplication: DuplicationConfig
    thresholds: ThresholdGroups
    parse_errors_mode: Severity
    baseline: BaselineConfig
    dependencies: DependenciesConfig
    layers: LayersConfig


@dataclass(frozen=True)
class FileMetric:
    path: str
    complexity: int
    nesting: int
    args: int
    imports: int
    estimated_tokens: int
    line_count: int


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    qualname: str
    lineno: int
    end_lineno: int
    parent_class: str | None
    complexity: int
    nesting: int
    args: int
    imports: int
    estimated_tokens: int
    line_count: int


@dataclass(frozen=True)
class ClassMetric:
    path: str
    qualname: str
    lineno: int
    end_lineno: int
    complexity: int
    nesting: int
    args: int
    imports: int
    estimated_tokens: int
    line_count: int
    method_count: int
    public_method_count: int
    god_class_risk: float


@dataclass(frozen=True)
class DuplicationCandidate:
    path: str
    qualname: str
    lineno: int
    end_lineno: int
    line_count: int
    estimated_tokens: int
    source: str


@dataclass(frozen=True)
class DuplicateLocation:
    path: str
    qualname: str
    lineno: int
    end_lineno: int
    line_count: int
    estimated_tokens: int


@dataclass(frozen=True)
class DuplicateGroup:
    fingerprint: str
    occurrences: int
    line_count: int
    estimated_tokens: int
    locations: list[DuplicateLocation]


@dataclass(frozen=True)
class ParseErrorRecord:
    path: str
    error_type: str
    message: str


@dataclass(frozen=True)
class DependencyEdge:
    importer_module: str
    importer_path: str
    imported_module: str
    imported_path: str


@dataclass(frozen=True)
class DependencyCycle:
    modules: list[str]
    paths: list[str]


@dataclass(frozen=True)
class LayerViolationRecord:
    importer_module: str
    importer_path: str
    imported_module: str
    imported_path: str
    from_layer: str
    to_layer: str


@dataclass(frozen=True)
class BaselineComparison:
    baseline_path: str
    warning_delta: int
    failure_delta: int
    new_failures: int
    baseline_warning_count: int
    baseline_failure_count: int
    current_warning_count: int
    current_failure_count: int


@dataclass(frozen=True)
class Violation:
    severity: Severity
    scope: str
    metric: str
    path: str | None
    qualname: str | None
    value: float
    warn_threshold: float | None
    fail_threshold: float | None
    message: str


@dataclass(frozen=True)
class AnalysisResult:
    files_total: int
    file_metrics: list[FileMetric]
    function_metrics: list[FunctionMetric]
    class_metrics: list[ClassMetric]
    duplication_candidates: list[DuplicationCandidate]
    parse_errors: list[ParseErrorRecord]


@dataclass(frozen=True)
class DependencyAnalysis:
    edges: list[DependencyEdge]
    cycles: list[DependencyCycle]
    layer_violations: list[LayerViolationRecord]


@dataclass(frozen=True)
class MetricBundle:
    files: list[FileMetric]
    functions: list[FunctionMetric]
    classes: list[ClassMetric]
    duplicates: list[DuplicateGroup]


@dataclass(frozen=True)
class Report:
    schema_version: int
    phase: int
    summary: dict[str, Any]
    metrics: MetricBundle
    violations: list[Violation]
    parse_errors: list[ParseErrorRecord]
    dependency_cycles: list[DependencyCycle]
    layer_violations: list[LayerViolationRecord]
    baseline_comparison: BaselineComparison | None
    effective_config: dict[str, Any]


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    report: Report
