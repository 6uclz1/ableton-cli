"""Pure grid/rate string parsing shared by music-theory and groove transforms.

Grid strings look like ``1/16`` or ``1/8T`` (a triplet). Beats follow the
convention used throughout this repo: one quarter note equals one beat, so a
whole note is 4 beats.
"""

from __future__ import annotations

_BEATS_PER_WHOLE_NOTE = 4.0
_TRIPLET_FACTOR = 2.0 / 3.0


def parse_grid_to_beats(grid: str) -> float:
    text = grid.strip()
    triplet = text.upper().endswith("T")
    core = text[:-1] if triplet else text

    parts = core.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid grid value: {grid!r}")

    try:
        numerator = float(parts[0])
        denominator = float(parts[1])
    except ValueError as exc:
        raise ValueError(f"Invalid grid value: {grid!r}") from exc

    if numerator <= 0 or denominator <= 0:
        raise ValueError(f"Invalid grid value: {grid!r}")

    beats = (numerator / denominator) * _BEATS_PER_WHOLE_NOTE
    if triplet:
        beats *= _TRIPLET_FACTOR
    return beats
