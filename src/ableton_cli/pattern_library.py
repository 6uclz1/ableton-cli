"""Pure drum and bass pattern generators.

Style names map to step strings — ``x`` is a hit, ``o`` a ghost note, ``.``
a rest — one character per sixteenth. Everything returns notes-json in the
same shape as ``clip notes get``/``add``, and nothing here imports from
``client``, ``commands``, or ``remote_script``.

Randomness is always injected: pass an ``rng`` (a seeded
:class:`random.Random`) to get reproducible humanization, or leave it out
for a strictly deterministic pattern.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .note_fields import NOTE_PITCH_MAX, NOTE_PITCH_MIN, NOTE_VELOCITY_MAX, NOTE_VELOCITY_MIN

Note = dict[str, Any]

STEPS_PER_BAR = 16
BEATS_PER_BAR = 4.0

#: General MIDI drum-rack pitches for the voices used by the styles below.
DRUM_VOICE_PITCHES: dict[str, int] = {
    "kick": 36,
    "rim": 37,
    "snare": 38,
    "clap": 39,
    "closed_hat": 42,
    "open_hat": 46,
    "ride": 51,
}


class PatternLibraryError(ValueError):
    """Raised for unknown style names or out-of-range generator arguments."""


@dataclass(frozen=True, slots=True)
class DrumVoicePattern:
    voice: str
    steps: str
    velocity: int = 100
    ghost_velocity: int = 45


DRUM_STYLES: dict[str, tuple[DrumVoicePattern, ...]] = {
    "dnb": (
        DrumVoicePattern("kick", "x.........x....."),
        DrumVoicePattern("snare", "....x.......x..o", velocity=112),
        DrumVoicePattern("closed_hat", "x.o.x.o.x.o.x.o.", velocity=76),
        DrumVoicePattern("ride", "..x...x...x...x.", velocity=60),
    ),
    "house": (
        DrumVoicePattern("kick", "x...x...x...x..."),
        DrumVoicePattern("clap", "....x.......x...", velocity=104),
        DrumVoicePattern("closed_hat", "..x...x...x...x.", velocity=80),
        DrumVoicePattern("open_hat", "..............x.", velocity=88),
    ),
    "trap": (
        DrumVoicePattern("kick", "x.....x...x....."),
        DrumVoicePattern("snare", "........x.......", velocity=110),
        DrumVoicePattern("closed_hat", "x.xoxxx.x.xoxxx.", velocity=84),
    ),
    "boom-bap": (
        DrumVoicePattern("kick", "x.......x.x....."),
        DrumVoicePattern("snare", "....x..o....x...", velocity=108),
        DrumVoicePattern("closed_hat", "x.x.x.x.x.x.x.x.", velocity=78),
    ),
    "breakbeat": (
        DrumVoicePattern("kick", "x.......x..x...."),
        DrumVoicePattern("snare", "....x..o....x..o", velocity=106),
        DrumVoicePattern("closed_hat", "x.x.x.x.x.x.x.x.", velocity=74),
        DrumVoicePattern("open_hat", "..............x.", velocity=84),
    ),
    "four-on-floor": (
        DrumVoicePattern("kick", "x...x...x...x..."),
        DrumVoicePattern("snare", "....x.......x...", velocity=104),
        DrumVoicePattern("closed_hat", "x.x.x.x.x.x.x.x.", velocity=78),
    ),
}

#: Bass step patterns, one character per sixteenth.
BASS_PATTERNS: dict[str, str] = {
    "sustained": "x...............",
    "root-half": "x.......x.......",
    "four-floor": "x...x...x...x...",
    "offbeat": "..x...x...x...x.",
    "driving": "x.x.x.x.x.x.x.x.",
    "rolling": "x.xx..x.x.xx..x.",
    "sixteenths": "xxxxxxxxxxxxxxxx",
}


def drum_styles() -> list[str]:
    return sorted(DRUM_STYLES)


def bass_patterns() -> list[str]:
    return sorted(BASS_PATTERNS)


def _validate_steps(name: str, steps: str) -> str:
    if len(steps) != STEPS_PER_BAR:
        raise PatternLibraryError(
            f"{name} step string must be {STEPS_PER_BAR} characters, got {len(steps)}",
        )
    unknown = set(steps) - {"x", "o", "."}
    if unknown:
        raise PatternLibraryError(f"{name} step string has unknown symbols: {sorted(unknown)}")
    return steps


def _validate_common(*, bars: int, gate: float, humanize: float) -> None:
    if bars < 1:
        raise PatternLibraryError("bars must be >= 1")
    if not (0.0 < gate <= 1.0):
        raise PatternLibraryError("gate must be in (0.0, 1.0]")
    if not (0.0 <= humanize <= 1.0):
        raise PatternLibraryError("humanize must be in [0.0, 1.0]")


def _humanized(
    note: Note,
    *,
    humanize: float,
    rng: random.Random | None,
    step_beats: float,
) -> Note:
    if humanize <= 0.0 or rng is None:
        return note
    jitter = (rng.random() - 0.5) * humanize * step_beats * 0.5
    velocity_jitter = int(round((rng.random() - 0.5) * humanize * 24))
    start = max(0.0, note["start_time"] + jitter)
    velocity = min(NOTE_VELOCITY_MAX, max(NOTE_VELOCITY_MIN, note["velocity"] + velocity_jitter))
    return {**note, "start_time": round(start, 6), "velocity": velocity}


def _note(*, pitch: int, start: float, duration: float, velocity: int) -> Note:
    if not (NOTE_PITCH_MIN <= pitch <= NOTE_PITCH_MAX):
        raise PatternLibraryError(
            f"pitch {pitch} is outside [{NOTE_PITCH_MIN}, {NOTE_PITCH_MAX}]",
        )
    return {
        "pitch": pitch,
        "start_time": round(start, 6),
        "duration": round(duration, 6),
        "velocity": min(NOTE_VELOCITY_MAX, max(NOTE_VELOCITY_MIN, velocity)),
        "mute": False,
    }


def drum_pattern_notes(
    style: str,
    *,
    bars: int = 1,
    gate: float = 0.5,
    humanize: float = 0.0,
    rng: random.Random | None = None,
    pitches: dict[str, int] | None = None,
) -> list[Note]:
    """Render ``style`` as ``bars`` bars of drum notes."""
    if style not in DRUM_STYLES:
        raise PatternLibraryError(f"unknown drum style {style!r}; use one of {drum_styles()}")
    _validate_common(bars=bars, gate=gate, humanize=humanize)
    voice_pitches = {**DRUM_VOICE_PITCHES, **(pitches or {})}
    step_beats = BEATS_PER_BAR / STEPS_PER_BAR

    notes: list[Note] = []
    for voice_pattern in DRUM_STYLES[style]:
        steps = _validate_steps(
            f"drum style {style!r} voice {voice_pattern.voice!r}", voice_pattern.steps
        )
        pitch = voice_pitches[voice_pattern.voice]
        for bar in range(bars):
            for index, symbol in enumerate(steps):
                if symbol == ".":
                    continue
                velocity = voice_pattern.velocity if symbol == "x" else voice_pattern.ghost_velocity
                start = (bar * STEPS_PER_BAR + index) * step_beats
                notes.append(
                    _humanized(
                        _note(
                            pitch=pitch,
                            start=start,
                            duration=step_beats * gate,
                            velocity=velocity,
                        ),
                        humanize=humanize,
                        rng=rng,
                        step_beats=step_beats,
                    )
                )
    notes.sort(key=lambda note: (note["start_time"], note["pitch"]))
    return notes


def bass_pattern_notes(
    pattern: str,
    *,
    root_pitches: Sequence[int],
    bars: int | None = None,
    gate: float = 0.9,
    velocity: int = 100,
    humanize: float = 0.0,
    rng: random.Random | None = None,
) -> list[Note]:
    """Render ``pattern`` over ``root_pitches``, one root per bar (cycled)."""
    if pattern not in BASS_PATTERNS:
        raise PatternLibraryError(f"unknown bass pattern {pattern!r}; use one of {bass_patterns()}")
    if not root_pitches:
        raise PatternLibraryError("root_pitches must not be empty")
    bar_count = len(root_pitches) if bars is None else bars
    _validate_common(bars=bar_count, gate=gate, humanize=humanize)
    steps = _validate_steps(f"bass pattern {pattern!r}", BASS_PATTERNS[pattern])
    step_beats = BEATS_PER_BAR / STEPS_PER_BAR

    notes: list[Note] = []
    for bar in range(bar_count):
        pitch = root_pitches[bar % len(root_pitches)]
        hits = [index for index, symbol in enumerate(steps) if symbol != "."]
        for position, index in enumerate(hits):
            next_index = hits[position + 1] if position + 1 < len(hits) else STEPS_PER_BAR
            span = (next_index - index) * step_beats
            start = (bar * STEPS_PER_BAR + index) * step_beats
            notes.append(
                _humanized(
                    _note(
                        pitch=pitch,
                        start=start,
                        duration=span * gate,
                        velocity=velocity if steps[index] == "x" else int(velocity * 0.6),
                    ),
                    humanize=humanize,
                    rng=rng,
                    step_beats=step_beats,
                )
            )
    notes.sort(key=lambda note: (note["start_time"], note["pitch"]))
    return notes
