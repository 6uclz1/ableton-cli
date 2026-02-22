from __future__ import annotations

import subprocess
from collections.abc import Sequence

DEFAULT_CHECK_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "ruff", "format", "--check", "."),
    ("uv", "run", "pytest"),
)


def _run_command(command: Sequence[str]) -> int:
    print(f"$ {' '.join(command)}", flush=True)
    completed = subprocess.run(tuple(command), check=False)
    return int(completed.returncode)


def run_default_checks(
    *,
    commands: Sequence[Sequence[str]] = DEFAULT_CHECK_COMMANDS,
) -> int:
    for command in commands:
        exit_code = _run_command(command)
        if exit_code != 0:
            return exit_code
    return 0


def main() -> int:
    return run_default_checks()


if __name__ == "__main__":
    raise SystemExit(main())
