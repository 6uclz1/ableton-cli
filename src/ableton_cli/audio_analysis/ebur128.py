"""EBU R128 / ITU-R BS.1770 loudness measurement through ffmpeg's ``ebur128`` filter.

``measure_ebur128`` takes an injected ``run`` callable so the ffmpeg invocation can be
faked in tests; ``parse_ebur128_log`` turns the filter's log into a measurement and
fails explicitly when a summary value is missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import Runner, ffmpeg_output_error, run_ffmpeg

FFMPEG_FILTER = "ebur128=peak=true:framelog=info"

_NUMBER = r"(-?\d+(?:\.\d+)?|-inf)"
_SUMMARY_PATTERNS = {
    "Integrated loudness": re.compile(rf"^\s+I:\s+{_NUMBER} LUFS\s*$", re.MULTILINE),
    "Loudness range": re.compile(rf"^\s+LRA:\s+{_NUMBER} LU\s*$", re.MULTILINE),
    "True peak": re.compile(rf"^\s+Peak:\s+{_NUMBER} dBFS\s*$", re.MULTILINE),
}
_FRAME_PATTERN = re.compile(rf"\bM:\s*{_NUMBER}\s+S:\s*{_NUMBER}")
_HINT = "Check that ffmpeg provides the ebur128 filter ('ffmpeg -filters')."


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
    return parse_ebur128_log(run_ffmpeg(command, run=run, hint=_HINT))


def parse_ebur128_log(log: str) -> Ebur128Measurement:
    summary_start = log.rfind("Summary:")
    summary = log[summary_start:] if summary_start != -1 else ""
    values: dict[str, float] = {}
    for label, pattern in _SUMMARY_PATTERNS.items():
        match = pattern.search(summary)
        if match is None:
            raise ffmpeg_output_error(
                hint=_HINT, message=f"ffmpeg ebur128 summary has no {label} value"
            )
        values[label] = float(match.group(1))

    frames = [(float(m), float(s)) for m, s in _FRAME_PATTERN.findall(log[:summary_start])]
    if not frames:
        raise ffmpeg_output_error(
            hint=_HINT, message="ffmpeg ebur128 log has no per-frame loudness values"
        )

    return Ebur128Measurement(
        integrated_lufs=values["Integrated loudness"],
        lra_lu=values["Loudness range"],
        true_peak_dbtp=values["True peak"],
        momentary_lufs_max=max(momentary for momentary, _ in frames),
        short_term_lufs_max=max(short_term for _, short_term in frames),
    )
