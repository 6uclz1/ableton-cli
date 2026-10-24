"""Mini-notation pattern compiler for note entry.

A small Strudel/TidalCycles-inspired grammar compiled to notes-json. Pure
offline compiler: zero imports from client/commands layers, feeds the
existing ``clip notes add`` / ``arrangement clip create`` notes-json paths.

Grammar (v1, EBNF)::

    pattern     = step , { WS , step } ;
    step        = element , [ "*" , int ] ;
    element     = rest | chord | group ;
    group       = "[" , pattern , "]" ;
    chord       = note , { "," , note } ;
    note        = pitch , [ "@" , int ] ;
    pitch       = note_name | midi_number ;
    note_name   = letter , [ "#" | "b" ] , octave ;
    letter      = "a" | "b" | "c" | "d" | "e" | "f" | "g" ;
    octave      = [ "-" ] , digit , { digit } ;
    midi_number = digit , { digit } ;
    rest        = "~" ;

Octave convention matches Ableton Live's own display: C3 = MIDI 60.
Nothing else is in scope for v1: no polymeter, no ``<>`` alternation, no
euclid syntax (see ``music_theory.euclidean_notes`` for that).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_NOTE_LETTER_PITCH_CLASS: dict[str, int] = {
    "c": 0,
    "d": 2,
    "e": 4,
    "f": 5,
    "g": 7,
    "a": 9,
    "b": 11,
}
_OCTAVE_OFFSET = 2  # Ableton convention: C3 == MIDI 60.


class PatternSyntaxError(ValueError):
    """Raised for malformed pattern text; ``column`` is 1-based."""

    def __init__(self, message: str, column: int) -> None:
        super().__init__(message)
        self.column = column


@dataclass(frozen=True, slots=True)
class Rest:
    pass


@dataclass(frozen=True, slots=True)
class NoteEvent:
    pitch: int
    velocity: int | None = None


@dataclass(frozen=True, slots=True)
class Chord:
    notes: tuple[NoteEvent, ...]


@dataclass(frozen=True, slots=True)
class Repeat:
    node: PatternNode
    count: int


@dataclass(frozen=True, slots=True)
class Sequence:
    steps: tuple[PatternNode, ...]


PatternNode = Rest | NoteEvent | Chord | Repeat | Sequence


class _Parser:
    def __init__(self, text: str) -> None:
        self._text = text
        self._pos = 0
        self._length = len(text)

    def parse(self) -> Sequence:
        self._skip_ws()
        steps: list[PatternNode] = []
        while self._pos < self._length:
            steps.append(self._parse_step())
            self._skip_ws()
        if not steps:
            raise PatternSyntaxError("pattern must contain at least one step", 1)
        return Sequence(tuple(steps))

    def _skip_ws(self) -> None:
        while self._pos < self._length and self._text[self._pos].isspace():
            self._pos += 1

    def _peek(self) -> str | None:
        return self._text[self._pos] if self._pos < self._length else None

    def _parse_step(self) -> PatternNode:
        element = self._parse_element()
        if self._peek() == "*":
            self._pos += 1
            column = self._pos + 1
            count = self._parse_int()
            if count < 1:
                raise PatternSyntaxError(f"repeat count must be >= 1, got {count}", column)
            return Repeat(element, count)
        return element

    def _parse_element(self) -> PatternNode:
        column = self._pos + 1
        char = self._peek()
        if char is None:
            raise PatternSyntaxError("unexpected end of pattern", column)
        if char == "~":
            self._pos += 1
            return Rest()
        if char == "[":
            return self._parse_group()
        return self._parse_chord()

    def _parse_group(self) -> Sequence:
        column = self._pos + 1
        self._pos += 1  # consume '['
        self._skip_ws()
        steps: list[PatternNode] = []
        while True:
            if self._pos >= self._length:
                raise PatternSyntaxError("unclosed '['", column)
            if self._text[self._pos] == "]":
                self._pos += 1
                break
            steps.append(self._parse_step())
            self._skip_ws()
        if not steps:
            raise PatternSyntaxError("empty group '[]'", column)
        return Sequence(tuple(steps))

    def _parse_chord(self) -> PatternNode:
        notes = [self._parse_note()]
        while self._peek() == ",":
            self._pos += 1
            notes.append(self._parse_note())
        if len(notes) == 1:
            return notes[0]
        return Chord(tuple(notes))

    def _parse_note(self) -> NoteEvent:
        pitch = self._parse_pitch()
        velocity = None
        if self._peek() == "@":
            self._pos += 1
            column = self._pos + 1
            velocity = self._parse_int()
            if not (0 <= velocity <= 127):
                raise PatternSyntaxError(f"velocity out of range: {velocity}", column)
        return NoteEvent(pitch=pitch, velocity=velocity)

    def _parse_pitch(self) -> int:
        column = self._pos + 1
        char = self._peek()
        if char is None:
            raise PatternSyntaxError("expected a pitch", column)
        if char.isdigit():
            number = self._parse_int()
            if not (0 <= number <= 127):
                raise PatternSyntaxError(f"MIDI pitch out of range: {number}", column)
            return number
        return self._parse_note_name()

    def _parse_note_name(self) -> int:
        start = self._pos
        column = self._pos + 1
        char = self._peek()
        if char is None or char.lower() not in _NOTE_LETTER_PITCH_CLASS:
            raise PatternSyntaxError(f"invalid pitch at column {column}", column)
        pitch_class = _NOTE_LETTER_PITCH_CLASS[char.lower()]
        self._pos += 1
        if self._peek() in ("#", "b"):
            pitch_class += 1 if self._text[self._pos] == "#" else -1
            self._pos += 1
        octave_start = self._pos
        if self._peek() == "-":
            self._pos += 1
        while self._pos < self._length and self._text[self._pos].isdigit():
            self._pos += 1
        if self._pos == octave_start:
            raise PatternSyntaxError(f"missing octave at column {column}", column)
        octave = int(self._text[octave_start : self._pos])
        midi = (octave + _OCTAVE_OFFSET) * 12 + pitch_class
        if not (0 <= midi <= 127):
            raise PatternSyntaxError(
                f"pitch out of MIDI range: {self._text[start : self._pos]!r}", column
            )
        return midi

    def _parse_int(self) -> int:
        start = self._pos
        column = self._pos + 1
        if self._peek() == "-":
            self._pos += 1
        digits_start = self._pos
        while self._pos < self._length and self._text[self._pos].isdigit():
            self._pos += 1
        if self._pos == digits_start:
            raise PatternSyntaxError(f"expected an integer at column {column}", column)
        return int(self._text[start : self._pos])


def parse(pattern: str) -> Sequence:
    return _Parser(pattern).parse()


def _compile_node(
    node: PatternNode,
    *,
    start: float,
    length: float,
    default_velocity: int,
    gate: float,
) -> list[dict[str, Any]]:
    if isinstance(node, Rest):
        return []
    if isinstance(node, NoteEvent):
        velocity = node.velocity if node.velocity is not None else default_velocity
        return [
            {
                "pitch": node.pitch,
                "start_time": round(start, 6),
                "duration": round(length * gate, 6),
                "velocity": velocity,
                "mute": False,
            }
        ]
    if isinstance(node, Chord):
        events: list[dict[str, Any]] = []
        for note in node.notes:
            events.extend(
                _compile_node(
                    note, start=start, length=length, default_velocity=default_velocity, gate=gate
                )
            )
        return events
    if isinstance(node, Repeat):
        step_length = length / node.count
        events = []
        for index in range(node.count):
            events.extend(
                _compile_node(
                    node.node,
                    start=start + index * step_length,
                    length=step_length,
                    default_velocity=default_velocity,
                    gate=gate,
                )
            )
        return events
    if isinstance(node, Sequence):
        step_length = length / len(node.steps)
        events = []
        for index, step in enumerate(node.steps):
            events.extend(
                _compile_node(
                    step,
                    start=start + index * step_length,
                    length=step_length,
                    default_velocity=default_velocity,
                    gate=gate,
                )
            )
        return events
    raise TypeError(f"Unknown pattern node: {node!r}")  # pragma: no cover - exhaustive above


def compile_pattern(
    node: PatternNode,
    *,
    pattern_length: float = 4.0,
    default_velocity: int = 100,
    gate: float = 1.0,
) -> list[dict[str, Any]]:
    if pattern_length <= 0:
        raise ValueError("pattern_length must be > 0")
    if not (0.0 < gate <= 1.0):
        raise ValueError("gate must be in (0.0, 1.0]")
    events = _compile_node(
        node, start=0.0, length=pattern_length, default_velocity=default_velocity, gate=gate
    )
    events.sort(key=lambda event: (event["start_time"], event["pitch"]))
    return events
