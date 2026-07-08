"""Pure groove extraction: snap transients to a grid and aggregate feel.

Decoupled from audio decoding on purpose — this module only consumes the
``(position_beats, strength)`` pairs already produced by
``ableton_cli.audio_analysis.transient.analyze_transients`` (its
``onset_points_beats``/``onset_strengths`` fields), so it is testable with
synthetic transient lists and has no I/O of its own.
"""

from __future__ import annotations

from statistics import median
from typing import TypedDict

from ..beat_grid import parse_grid_to_beats

BEATS_PER_BAR = 4.0


class GrooveSlot(TypedDict):
    position: float
    timing_offset: float
    velocity_scale: float


class GrooveProfile(TypedDict):
    grid: str
    slots: list[GrooveSlot]


def extract_groove(
    transients: list[tuple[float, float]],
    *,
    grid: str = "1/16",
    beats_per_bar: float = BEATS_PER_BAR,
    round_digits: int = 6,
) -> GrooveProfile:
    """Snap transients onto ``grid`` and aggregate per-slot feel across bars.

    ``transients`` is a list of ``(position_beats, strength)`` pairs, where
    ``strength`` is already normalized to ``[0.0, 1.0]``. Returns one slot
    per grid position within a single bar (median timing offset and median
    velocity scale across every bar in the input); slots with no transients
    default to ``timing_offset=0.0``, ``velocity_scale=1.0`` (play as-is).
    """
    grid_beats = parse_grid_to_beats(grid)
    if beats_per_bar <= 0:
        raise ValueError("beats_per_bar must be > 0")
    slots_per_bar = round(beats_per_bar / grid_beats)
    if slots_per_bar < 1:
        raise ValueError("grid must divide beats_per_bar into at least one slot")

    offsets_by_slot: dict[int, list[float]] = {index: [] for index in range(slots_per_bar)}
    velocities_by_slot: dict[int, list[float]] = {index: [] for index in range(slots_per_bar)}

    for position, strength in transients:
        if position < 0:
            raise ValueError(f"transient position must be >= 0, got {position}")
        absolute_slot = round(position / grid_beats)
        within_bar_slot = absolute_slot % slots_per_bar
        timing_offset = position - (absolute_slot * grid_beats)
        offsets_by_slot[within_bar_slot].append(timing_offset)
        velocities_by_slot[within_bar_slot].append(strength)

    slots: list[GrooveSlot] = []
    for index in range(slots_per_bar):
        offsets = offsets_by_slot[index]
        velocities = velocities_by_slot[index]
        slots.append(
            {
                "position": round(index * grid_beats, round_digits),
                "timing_offset": round(median(offsets), round_digits) if offsets else 0.0,
                "velocity_scale": round(median(velocities), round_digits) if velocities else 1.0,
            }
        )

    return {"grid": grid, "slots": slots}
