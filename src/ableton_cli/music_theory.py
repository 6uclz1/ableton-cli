"""Pure music-theory note transforms.

Every transform here operates on plain note dicts (the same shape used by
``clip notes get``/``update``/``add``) and returns new note dicts. Nothing in
this module imports from ``client``, ``commands``, or ``remote_script`` —
the remote surface keeps receiving/sending plain note lists via the existing
notes get/update/add commands.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Any

from .beat_grid import parse_grid_to_beats
from .note_fields import NOTE_PITCH_MAX, NOTE_PITCH_MIN, NOTE_VELOCITY_MAX, NOTE_VELOCITY_MIN

Note = dict[str, Any]

SCALE_INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "natural_minor": (0, 2, 3, 5, 7, 8, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "locrian": (0, 1, 3, 5, 6, 8, 10),
    "major_pentatonic": (0, 2, 4, 7, 9),
    "minor_pentatonic": (0, 3, 5, 7, 10),
}

_ROOT_PITCH_CLASSES: dict[str, int] = {
    "c": 0,
    "c#": 1,
    "db": 1,
    "d": 2,
    "d#": 3,
    "eb": 3,
    "e": 4,
    "f": 5,
    "f#": 6,
    "gb": 6,
    "g": 7,
    "g#": 8,
    "ab": 8,
    "a": 9,
    "a#": 10,
    "bb": 10,
    "b": 11,
}

ARPEGGIATE_MODES = frozenset({"up", "down", "updown", "random"})
_CHORD_EPSILON = 1e-9


class MusicTheoryError(ValueError):
    """Raised when a transform would exceed pitch/velocity bounds."""

    def __init__(self, message: str, *, offending_indices: Sequence[int]) -> None:
        super().__init__(message)
        self.offending_indices = list(offending_indices)


def root_pitch_class(root: str) -> int:
    key = root.strip().lower()
    if key not in _ROOT_PITCH_CLASSES:
        raise ValueError(f"Unknown root note: {root!r}")
    return _ROOT_PITCH_CLASSES[key]


def scale_pitches(
    root: str,
    scale: str,
    *,
    low: int = NOTE_PITCH_MIN,
    high: int = NOTE_PITCH_MAX,
) -> list[int]:
    if scale not in SCALE_INTERVALS:
        raise ValueError(f"Unknown scale: {scale!r}")
    pitch_class = root_pitch_class(root)
    intervals = SCALE_INTERVALS[scale]
    pitches: set[int] = set()
    octave_base = low - (low % 12) - 12
    while octave_base <= high + 12:
        for interval in intervals:
            pitch = octave_base + pitch_class + interval
            if low <= pitch <= high:
                pitches.add(pitch)
        octave_base += 12
    return sorted(pitches)


def transpose_in_scale(
    notes: Sequence[Note],
    *,
    root: str,
    scale: str,
    degrees: int,
) -> list[Note]:
    pitches = scale_pitches(root, scale)
    if not pitches:
        raise ValueError("Scale produced no pitches in the valid MIDI range")

    result: list[Note] = []
    offending: list[int] = []
    for index, note in enumerate(notes):
        pitch = note["pitch"]
        nearest_index = min(
            range(len(pitches)),
            key=lambda idx: (abs(pitches[idx] - pitch), pitches[idx]),
        )
        new_index = nearest_index + degrees
        if new_index < 0 or new_index >= len(pitches):
            offending.append(index)
            result.append(dict(note))
            continue
        new_note = dict(note)
        new_note["pitch"] = pitches[new_index]
        result.append(new_note)

    if offending:
        raise MusicTheoryError(
            f"transpose-in-scale would move notes out of range at indices: {offending}",
            offending_indices=offending,
        )
    return result


def _group_into_chords(notes: Sequence[Note]) -> list[list[Note]]:
    groups: list[list[Note]] = []
    group_starts: list[float] = []
    for note in notes:
        start = note["start_time"]
        matched = False
        for group_index, group_start in enumerate(group_starts):
            if abs(group_start - start) <= _CHORD_EPSILON:
                groups[group_index].append(note)
                matched = True
                break
        if not matched:
            group_starts.append(start)
            groups.append([note])
    return groups


def arpeggiate(
    notes: Sequence[Note],
    *,
    mode: str,
    rate: str | float,
    gate: float = 0.9,
    rng: random.Random | None = None,
) -> list[Note]:
    if mode not in ARPEGGIATE_MODES:
        raise ValueError(f"Unknown arpeggiate mode: {mode!r}")
    rate_beats = parse_grid_to_beats(rate) if isinstance(rate, str) else float(rate)
    if rng is None:
        rng = random.Random()

    result: list[Note] = []
    for chord in _group_into_chords(notes):
        start = chord[0]["start_time"]
        if mode == "up":
            ordered = sorted(chord, key=lambda note: note["pitch"])
        elif mode == "down":
            ordered = sorted(chord, key=lambda note: note["pitch"], reverse=True)
        elif mode == "updown":
            ascending = sorted(chord, key=lambda note: note["pitch"])
            descending = list(reversed(ascending))[1:-1] if len(ascending) > 2 else []
            ordered = ascending + descending
        else:  # random
            ordered = list(chord)
            rng.shuffle(ordered)

        for step, note in enumerate(ordered):
            new_note = dict(note)
            new_note["start_time"] = start + step * rate_beats
            new_note["duration"] = rate_beats * gate
            result.append(new_note)
    return result


def bjorklund(steps: int, pulses: int) -> list[bool]:
    """Compute a Euclidean rhythm pattern using Bjorklund's algorithm.

    Returns a list of length ``steps`` with exactly ``pulses`` ``True``
    entries, maximally evenly distributed, starting on a pulse.
    """
    if steps <= 0:
        raise ValueError("steps must be > 0")
    if pulses < 0 or pulses > steps:
        raise ValueError("pulses must be between 0 and steps")
    if pulses == 0:
        return [False] * steps
    if pulses == steps:
        return [True] * steps

    counts: list[int] = []
    remainders: list[int] = [pulses]
    divisor = steps - pulses
    level = 0
    while True:
        counts.append(divisor // remainders[level])
        remainders.append(divisor % remainders[level])
        divisor = remainders[level]
        level += 1
        if remainders[level] <= 1:
            break
    counts.append(divisor)

    pattern: list[bool] = []

    def build(level_index: int) -> None:
        if level_index == -1:
            pattern.append(False)
        elif level_index == -2:
            pattern.append(True)
        else:
            for _ in range(counts[level_index]):
                build(level_index - 1)
            if remainders[level_index] != 0:
                build(level_index - 2)

    build(level)
    first_pulse = pattern.index(True)
    return pattern[first_pulse:] + pattern[:first_pulse]


def rotate_pattern(pattern: Sequence[bool], rotate: int) -> list[bool]:
    if not pattern:
        return list(pattern)
    rotate %= len(pattern)
    return list(pattern[rotate:]) + list(pattern[:rotate])


def euclidean_notes(
    *,
    pitch: int,
    steps: int,
    pulses: int,
    rotate: int = 0,
    length: float,
    velocity: int = 100,
) -> list[Note]:
    if not (NOTE_PITCH_MIN <= pitch <= NOTE_PITCH_MAX):
        raise MusicTheoryError(
            f"pitch {pitch} is outside [{NOTE_PITCH_MIN}, {NOTE_PITCH_MAX}]",
            offending_indices=[],
        )
    if not (NOTE_VELOCITY_MIN <= velocity <= NOTE_VELOCITY_MAX):
        raise MusicTheoryError(
            f"velocity {velocity} is outside [{NOTE_VELOCITY_MIN}, {NOTE_VELOCITY_MAX}]",
            offending_indices=[],
        )
    if length <= 0:
        raise ValueError("length must be > 0")

    pattern = rotate_pattern(bjorklund(steps, pulses), rotate)
    step_beats = length / steps
    notes: list[Note] = []
    for index, hit in enumerate(pattern):
        if not hit:
            continue
        notes.append(
            {
                "pitch": pitch,
                "start_time": index * step_beats,
                "duration": step_beats,
                "velocity": velocity,
                "mute": False,
            }
        )
    return notes


def ratchet_notes(
    notes: Sequence[Note],
    *,
    division: int,
    probability: float = 1.0,
    rng: random.Random | None = None,
) -> list[Note]:
    if division < 1:
        raise ValueError("division must be >= 1")
    if rng is None:
        rng = random.Random()

    result: list[Note] = []
    for note in notes:
        sub_duration = note["duration"] / division
        for step in range(division):
            if step > 0 and rng.random() >= probability:
                continue
            new_note = dict(note)
            new_note["start_time"] = note["start_time"] + step * sub_duration
            new_note["duration"] = sub_duration
            result.append(new_note)
    return result


def retrograde_notes(notes: Sequence[Note], *, loop_length: float) -> list[Note]:
    result: list[Note] = []
    for note in notes:
        end_time = note["start_time"] + note["duration"]
        if end_time > loop_length:
            raise ValueError(f"note ending at {end_time} extends beyond loop_length {loop_length}")
        new_note = dict(note)
        new_note["start_time"] = loop_length - end_time
        result.append(new_note)
    result.sort(key=lambda note: note["start_time"])
    return result
