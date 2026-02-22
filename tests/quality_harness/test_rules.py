from __future__ import annotations

from pathlib import Path

from ableton_cli.quality_harness.config import load_config
from ableton_cli.quality_harness.models import (
    ClassMetric,
    DuplicateGroup,
    DuplicateLocation,
    FileMetric,
    FunctionMetric,
    ParseErrorRecord,
)
from ableton_cli.quality_harness.rules import evaluate_violations

from .helpers import write_config


def test_evaluate_violations_supports_warn_and_fail_thresholds(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path / ".quality-harness.yml", include=["src/**/*.py"]))

    file_metrics = [
        FileMetric(
            path="src/sample.py",
            complexity=190,
            nesting=2,
            args=0,
            imports=1,
            estimated_tokens=100,
            line_count=20,
        )
    ]
    function_metrics = [
        FunctionMetric(
            path="src/sample.py",
            qualname="sample_fn",
            lineno=1,
            end_lineno=6,
            parent_class=None,
            complexity=10,
            nesting=3,
            args=8,
            imports=0,
            estimated_tokens=100,
            line_count=6,
        )
    ]
    class_metrics = [
        ClassMetric(
            path="src/sample.py",
            qualname="Big",
            lineno=10,
            end_lineno=50,
            complexity=20,
            nesting=2,
            args=8,
            imports=1,
            estimated_tokens=200,
            line_count=40,
            method_count=3,
            public_method_count=2,
            god_class_risk=85.0,
        )
    ]
    duplicates = [
        DuplicateGroup(
            fingerprint="abc",
            occurrences=2,
            line_count=8,
            estimated_tokens=60,
            locations=[
                DuplicateLocation(
                    path="src/sample.py",
                    qualname="one",
                    lineno=1,
                    end_lineno=8,
                    line_count=8,
                    estimated_tokens=60,
                ),
                DuplicateLocation(
                    path="src/other.py",
                    qualname="two",
                    lineno=1,
                    end_lineno=8,
                    line_count=8,
                    estimated_tokens=60,
                ),
            ],
        )
    ]
    parse_errors = [
        ParseErrorRecord(path="src/broken.py", error_type="SyntaxError", message="invalid syntax")
    ]

    violations = evaluate_violations(
        config=config,
        file_metrics=file_metrics,
        function_metrics=function_metrics,
        class_metrics=class_metrics,
        duplicates=duplicates,
        parse_errors=parse_errors,
        dependency_cycles=[],
        layer_violations=[],
    )

    fail_metrics = {(item.scope, item.metric) for item in violations if item.severity == "fail"}
    warn_metrics = {(item.scope, item.metric) for item in violations if item.severity == "warn"}

    assert ("file", "complexity") in fail_metrics
    assert ("function", "args") in fail_metrics
    assert ("class", "god_class_risk") in fail_metrics
    assert ("duplicates", "occurrences") in warn_metrics
    assert ("parse_errors", "count") in warn_metrics


def test_evaluate_violations_treats_warn_boundary_as_warn(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path / ".quality-harness.yml", include=["src/**/*.py"]))

    violations = evaluate_violations(
        config=config,
        file_metrics=[
            FileMetric(
                path="src/sample.py",
                complexity=120,
                nesting=0,
                args=0,
                imports=0,
                estimated_tokens=10,
                line_count=1,
            )
        ],
        function_metrics=[],
        class_metrics=[],
        duplicates=[],
        parse_errors=[],
        dependency_cycles=[],
        layer_violations=[],
    )

    assert len(violations) == 1
    assert violations[0].severity == "warn"
    assert violations[0].scope == "file"
    assert violations[0].metric == "complexity"
