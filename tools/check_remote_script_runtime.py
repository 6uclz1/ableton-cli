#!/usr/bin/env python3
"""Guard against remote_script/ using Python features newer than the
minimum interpreter bundled with the declared minimum Ableton Live version.

Ableton Live's Remote Script runs inside Live's own bundled Python
interpreter, not the interpreter used to run the `ableton-cli` CLI. The
declared floor (see README.md prerequisites) is Ableton Live 12+, which
bundles Python 3.11. This script fails when remote_script/ contains syntax
that interpreter cannot parse, catching version drift mechanically instead
of relying on someone noticing it manually.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REMOTE_SCRIPT_DIR = REPO_ROOT / "remote_script"
MIN_PYTHON_VERSION = (3, 11)
_CANDIDATE_INTERPRETER_NAMES = (
    f"python{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}",
    "python3",
    "python",
)


def _iter_source_files() -> list[Path]:
    return sorted(
        path for path in REMOTE_SCRIPT_DIR.rglob("*.py") if "__pycache__" not in path.parts
    )


def _interpreter_version(executable: str) -> tuple[int, int] | None:
    result = subprocess.run(
        [executable, "-c", "import sys; print(sys.version_info.major, sys.version_info.minor)"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        major_str, minor_str = result.stdout.strip().split()
        return (int(major_str), int(minor_str))
    except ValueError:
        return None


def _find_matching_interpreter() -> str | None:
    for name in _CANDIDATE_INTERPRETER_NAMES:
        resolved = shutil.which(name)
        if resolved is None:
            continue
        if _interpreter_version(resolved) == MIN_PYTHON_VERSION:
            return resolved
    return None


def _check_with_interpreter(interpreter: str, files: Sequence[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        result = subprocess.run(
            [interpreter, "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"{path.relative_to(REPO_ROOT)}: {result.stderr.strip()}")
    return errors


def _check_with_feature_version(files: Sequence[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=str(path), feature_version=MIN_PYTHON_VERSION)
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: {exc}")
    return errors


def run_check() -> tuple[int, str]:
    files = _iter_source_files()
    if not files:
        return 0, "No remote_script/*.py files found."

    interpreter = _find_matching_interpreter()
    if interpreter is not None:
        errors = _check_with_interpreter(interpreter, files)
        mode = f"py_compile via {interpreter}"
    else:
        errors = _check_with_feature_version(files)
        mode = (
            "ast.parse(feature_version=...) static check "
            f"(no Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} interpreter found)"
        )

    lines = [f"Checked {len(files)} file(s) under remote_script/ using {mode}."]
    if errors:
        lines.append("Runtime compatibility violations:")
        lines.extend(f"  {error}" for error in errors)
        return 1, "\n".join(lines)

    lines.append("OK: remote_script/ is compatible with the declared minimum Python version.")
    return 0, "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify remote_script/ compiles under the minimum Python version bundled "
            "with the declared minimum Ableton Live version "
            f"({MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]})."
        )
    )
    parser.parse_args(argv)
    exit_code, message = run_check()
    print(message)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
