from __future__ import annotations

import glob
from fnmatch import fnmatch
from pathlib import Path

from .baseline import compare_against_baseline
from .config import load_config
from .dependencies import analyze_dependencies
from .duplication import detect_duplicate_groups
from .metrics import analyze_python_files
from .models import Config, RunResult
from .reporting import build_report, write_report
from .rules import evaluate_violations, sort_violations


def run_quality_harness(
    *,
    config_path: Path,
    report_path: Path,
    root_dir: Path,
    baseline_path: Path | None,
) -> RunResult:
    config = load_config(config_path)
    target_files = _collect_target_files(config, root_dir=root_dir)

    analysis = analyze_python_files(target_files, root_dir=root_dir)
    duplicates = detect_duplicate_groups(
        analysis.duplication_candidates,
        min_lines=config.duplication.min_lines,
        min_tokens=config.duplication.min_tokens,
    )

    dependency_analysis = analyze_dependencies(
        paths=target_files,
        root_dir=root_dir,
        layers=config.layers.order,
    )

    base_violations = evaluate_violations(
        config=config,
        file_metrics=analysis.file_metrics,
        function_metrics=analysis.function_metrics,
        class_metrics=analysis.class_metrics,
        duplicates=duplicates,
        parse_errors=analysis.parse_errors,
        dependency_cycles=dependency_analysis.cycles,
        layer_violations=dependency_analysis.layer_violations,
    )

    baseline_comparison = None
    baseline_violations = []
    if baseline_path is not None:
        warning_count = sum(1 for item in base_violations if item.severity == "warn")
        failure_count = sum(1 for item in base_violations if item.severity == "fail")
        baseline_comparison, baseline_violations = compare_against_baseline(
            baseline_path=baseline_path,
            baseline_config=config.baseline,
            current_warning_count=warning_count,
            current_failure_count=failure_count,
            current_violations=base_violations,
        )

    violations = sort_violations([*base_violations, *baseline_violations])

    report = build_report(
        config=config,
        analysis=analysis,
        duplicates=duplicates,
        dependency_cycles=dependency_analysis.cycles,
        layer_violations=dependency_analysis.layer_violations,
        baseline_comparison=baseline_comparison,
        violations=violations,
    )
    write_report(report, report_path)

    exit_code = 1 if any(item.severity == "fail" for item in violations) else 0
    return RunResult(exit_code=exit_code, report=report)


def _collect_target_files(config: Config, *, root_dir: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in config.include:
        expanded_pattern = pattern
        if not Path(pattern).is_absolute():
            expanded_pattern = str(root_dir / pattern)

        for matched_path in glob.glob(expanded_pattern, recursive=True):
            path = Path(matched_path)
            if not path.is_file():
                continue
            if path.suffix != ".py":
                continue
            if _is_excluded(path, root_dir=root_dir, exclude_patterns=config.exclude):
                continue
            files.add(path.resolve())

    return sorted(files)


def _is_excluded(path: Path, *, root_dir: Path, exclude_patterns: list[str]) -> bool:
    absolute_path = path.resolve()
    absolute_root = root_dir.resolve()
    try:
        relative = absolute_path.relative_to(absolute_root).as_posix()
    except ValueError:
        relative = absolute_path.as_posix()

    for pattern in exclude_patterns:
        for variant in _expand_globstar(pattern):
            if fnmatch(relative, variant):
                return True
            if fnmatch(absolute_path.as_posix(), variant):
                return True
    return False


def _expand_globstar(pattern: str) -> set[str]:
    variants = {pattern}
    queue = [pattern]
    while queue:
        current = queue.pop()
        next_variants = {
            current.replace("/**/", "/", 1),
            current.replace("**/", "", 1),
            current.replace("/**", "", 1),
        }
        for candidate in next_variants:
            if candidate == current:
                continue
            if "**" in current and candidate not in variants:
                variants.add(candidate)
                queue.append(candidate)
    return variants
