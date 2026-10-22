"""EBU R128 / ITU-R BS.1770 loudness measurement through ffmpeg's ``ebur128`` filter.

``measure_ebur128`` takes an injected ``run`` callable so the ffmpeg invocation can be
faked in tests; ``parse_ebur128_log`` turns the filter's log into a measurement and
fails explicitly when a summary value is missing.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..errors import AppError, ErrorCode, ExitCode

FFMPEG_FILTER = "ebur128=peak=true:framelog=info"

_NUMBER = r"(-?\d+(?:\.\d+)?|-inf)"
_SUMMARY_PATTERNS = {
    "Integrated loudness": re.compile(rf"^\s+I:\s+{_NUMBER} LUFS\s*$", re.MULTILINE),
    "Loudness range": re.compile(rf"^\s+LRA:\s+{_NUMBER} LU\s*$", re.MULTILINE),
    "True peak": re.compile(rf"^\s+Peak:\s+{_NUMBER} dBFS\s*$", re.MULTILINE),
}
_FRAME_PATTERN = re.compile(rf"\bM:\s*{_NUMBER}\s+S:\s*{_NUMBER}")
_STDERR_TAIL_LINES = 5

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class Ebur128Measurement:
    integrated_lufs: float
    lra_lu: float
    true_peak_dbtp: float
    momentary_lufs_max: float
    short_term_lufs_max: float


def measure_ebur128(path: str | Path, *, run: Runner | None = None) -> Ebur128Measurement:
    command = [
        "ffmpeg",
        "-nostdin",
        "-nostats",
        "-hide_banner",
        "-i",
        str(path),
        "-af",
        FFMPEG_FILTER,
        "-f",
        "null",
        "-",
    ]
    completed = (run or _run_ffmpeg)(command)
    if completed.returncode != 0:
        raise _measurement_error(
            message=f"ffmpeg ebur128 measurement failed with exit code {completed.returncode}",
            returncode=completed.returncode,
            stderr_tail=completed.stderr.strip().splitlines()[-_STDERR_TAIL_LINES:],
        )
    return parse_ebur128_log(completed.stderr)


def parse_ebur128_log(log: str) -> Ebur128Measurement:
    summary_start = log.rfind("Summary:")
    summary = log[summary_start:] if summary_start != -1 else ""
    values: dict[str, float] = {}
    for label, pattern in _SUMMARY_PATTERNS.items():
        match = pattern.search(summary)
        if match is None:
            raise _measurement_error(message=f"ffmpeg ebur128 summary has no {label} value")
        values[label] = float(match.group(1))

    frames = [(float(m), float(s)) for m, s in _FRAME_PATTERN.findall(log[:summary_start])]
    if not frames:
        raise _measurement_error(message="ffmpeg ebur128 log has no per-frame loudness values")

    return Ebur128Measurement(
        integrated_lufs=values["Integrated loudness"],
        lra_lu=values["Loudness range"],
        true_peak_dbtp=values["True peak"],
        momentary_lufs_max=max(momentary for momentary, _ in frames),
        short_term_lufs_max=max(short_term for _, short_term in frames),
    )


def _run_ffmpeg(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _measurement_error(*, message: str, **details: object) -> AppError:
    return AppError(
        error_code=ErrorCode.INTERNAL_ERROR,
        message=message,
        hint="Check that ffmpeg provides the ebur128 filter ('ffmpeg -filters').",
        exit_code=ExitCode.INTERNAL_ERROR,
        details=dict(details),
    )
