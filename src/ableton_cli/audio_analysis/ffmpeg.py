"""Shared ffmpeg invocation for the analyzers that measure through ffmpeg filters.

Analyzers take a ``Runner`` so tests can fake the ffmpeg process; ``run_ffmpeg`` fails
explicitly on a non-zero exit, and ``ffmpeg_output_error`` reports output that does not
carry the expected measurement.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable

from ..errors import AppError, ErrorCode, ExitCode

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]

_STDERR_TAIL_LINES = 5


def run_ffmpeg(command: list[str], *, run: Runner | None, hint: str) -> str:
    completed = (run or _run_subprocess)(command)
    if completed.returncode != 0:
        raise ffmpeg_output_error(
            message=f"ffmpeg measurement failed with exit code {completed.returncode}",
            hint=hint,
            returncode=completed.returncode,
            stderr_tail=completed.stderr.strip().splitlines()[-_STDERR_TAIL_LINES:],
        )
    return completed.stderr


def ffmpeg_output_error(*, message: str, hint: str, **details: object) -> AppError:
    return AppError(
        error_code=ErrorCode.INTERNAL_ERROR,
        message=message,
        hint=hint,
        exit_code=ExitCode.INTERNAL_ERROR,
        details=dict(details),
    )


def _run_subprocess(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)
