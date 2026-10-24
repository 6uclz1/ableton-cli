"""Pure application of a groove profile (see ``audio_analysis/groove.py``)
onto a note list. No client/commands imports — testable without Live.
"""

from __future__ import annotations

from typing import Any

from .audio_analysis.groove import BEATS_PER_BAR, GrooveProfile
from .beat_grid import parse_grid_to_beats
from .note_fields import NOTE_VELOCITY_MAX, NOTE_VELOCITY_MIN

Note = dict[str, Any]


def apply_groove(
    notes: list[Note],
    profile: GrooveProfile,
    *,
    timing_amount: float = 1.0,
    velocity_amount: float = 0.0,
    beats_per_bar: float = BEATS_PER_BAR,
) -> list[Note]:
    if not (0.0 <= timing_amount <= 1.0):
        raise ValueError(f"timing_amount must be in [0.0, 1.0], got {timing_amount}")
    if not (0.0 <= velocity_amount <= 1.0):
        raise ValueError(f"velocity_amount must be in [0.0, 1.0], got {velocity_amount}")
    slots = profile["slots"]
    if not slots:
        raise ValueError("profile has no slots")
    grid_beats = parse_grid_to_beats(profile["grid"])
    slots_per_bar = len(slots)

    result: list[Note] = []
    for note in notes:
        start = note["start_time"]
        position_in_bar = start % beats_per_bar
        slot_index = round(position_in_bar / grid_beats) % slots_per_bar
        slot = slots[slot_index]

        new_note = dict(note)
        new_note["start_time"] = start + slot["timing_offset"] * timing_amount
        if "velocity" in note:
            scale = 1.0 + (slot["velocity_scale"] - 1.0) * velocity_amount
            scaled = note["velocity"] * scale
            new_note["velocity"] = int(
                round(min(max(scaled, NOTE_VELOCITY_MIN), NOTE_VELOCITY_MAX))
            )
        result.append(new_note)
    return result
