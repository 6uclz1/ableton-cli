from __future__ import annotations

from pathlib import Path


def build_config_text(
    *,
    include: list[str],
    exclude: list[str] | None = None,
    function_complexity_warn: int = 10,
    function_complexity_fail: int = 15,
    parse_errors_mode: str = "warn",
) -> str:
    exclude = exclude or ["**/__pycache__/**", "tests/**"]
    include_lines = "\n".join(f'  - "{pattern}"' for pattern in include)
    exclude_lines = "\n".join(f'  - "{pattern}"' for pattern in exclude)

    function_complexity_line = (
        "    complexity: { warn: "
        f"{function_complexity_warn}, fail: {function_complexity_fail} "
        "}\n"
    )

    return (
        "version: 1\n"
        "phase: 2\n"
        "include:\n"
        f"{include_lines}\n"
        "exclude:\n"
        f"{exclude_lines}\n"
        "duplication:\n"
        "  min_lines: 6\n"
        "  min_tokens: 40\n"
        "thresholds:\n"
        "  file:\n"
        "    complexity: { warn: 120, fail: 180 }\n"
        "    imports: { warn: 20, fail: 30 }\n"
        "    estimated_tokens: { warn: 2800, fail: 4000 }\n"
        "  function:\n"
        f"{function_complexity_line}"
        "    nesting: { warn: 3, fail: 5 }\n"
        "    args: { warn: 5, fail: 8 }\n"
        "    estimated_tokens: { warn: 220, fail: 320 }\n"
        "  class:\n"
        "    complexity: { warn: 60, fail: 90 }\n"
        "    nesting: { warn: 3, fail: 5 }\n"
        "    args: { warn: 8, fail: 12 }\n"
        "    imports: { warn: 8, fail: 12 }\n"
        "    estimated_tokens: { warn: 1200, fail: 1800 }\n"
        "    god_class_risk: { warn: 60, fail: 80 }\n"
        "  duplicates:\n"
        "    occurrences: { warn: 2, fail: 3 }\n"
        "parse_errors:\n"
        f"  mode: {parse_errors_mode}\n"
        "baseline:\n"
        "  warning_delta: { warn: 5, fail: 15 }\n"
        "  failure_delta: { warn: 0.5, fail: 1 }\n"
        "  new_failures: { warn: 0.5, fail: 1 }\n"
        "dependencies:\n"
        "  cycle_count: { warn: 1, fail: 3 }\n"
        "layers:\n"
        "  violation_count: { warn: 1, fail: 3 }\n"
        "  order:\n"
        "    - name: app\n"
        "      include:\n"
        '        - "src/**/*.py"\n'
        "    - name: remote\n"
        "      include:\n"
        '        - "remote_script/**/*.py"\n'
    )


def write_config(
    path: Path,
    *,
    include: list[str],
    exclude: list[str] | None = None,
    function_complexity_warn: int = 10,
    function_complexity_fail: int = 15,
    parse_errors_mode: str = "warn",
) -> Path:
    path.write_text(
        build_config_text(
            include=include,
            exclude=exclude,
            function_complexity_warn=function_complexity_warn,
            function_complexity_fail=function_complexity_fail,
            parse_errors_mode=parse_errors_mode,
        ),
        encoding="utf-8",
    )
    return path
