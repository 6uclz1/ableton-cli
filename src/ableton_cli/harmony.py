"""Pure chord/harmony vocabulary.

Chord symbols, roman-numeral degrees, voicings and voice leading, all as
plain data plus note dicts in the same shape used by ``clip notes
get``/``update``/``add``. Like :mod:`music_theory` this module imports
nothing from ``client``, ``commands``, or ``remote_script``.

Supported inputs::

    parse_chord_symbol("Cmaj7")      -> C E G B
    parse_chord_symbol("F#m7b5")     -> F# A C E
    parse_chord_symbol("Bb13#11")    -> Bb D F Ab C E G
    parse_chord_symbol("Dm7/G")      -> D F A C over a G bass
    parse_progression("i-VI-III-VII", key="F minor")

Voicings are ``close``, ``drop2``, ``drop3``, ``shell``, ``rootless`` and
``quartal``; :func:`voice_lead` picks the octave placement closest to the
previous chord so progressions do not jump an octave per bar.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .music_theory import SCALE_INTERVALS, root_pitch_class
from .note_fields import NOTE_PITCH_MAX, NOTE_PITCH_MIN, NOTE_VELOCITY_MAX, NOTE_VELOCITY_MIN

Note = dict[str, Any]

VOICINGS: tuple[str, ...] = ("close", "drop2", "drop3", "shell", "rootless", "quartal")

#: Semitone offset of each arabic chord degree above the root.
DEGREE_SEMITONES: dict[int, int] = {
    1: 0,
    2: 2,
    3: 4,
    4: 5,
    5: 7,
    6: 9,
    7: 11,
    9: 14,
    11: 17,
    13: 21,
}

#: Chord quality suffix -> intervals in semitones above the root.
CHORD_QUALITIES: dict[str, tuple[int, ...]] = {
    "": (0, 4, 7),
    "maj": (0, 4, 7),
    "M": (0, 4, 7),
    "m": (0, 3, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "o": (0, 3, 6),
    "aug": (0, 4, 8),
    "+": (0, 4, 8),
    "5": (0, 7),
    "6": (0, 4, 7, 9),
    "m6": (0, 3, 7, 9),
    "min6": (0, 3, 7, 9),
    "69": (0, 4, 7, 9, 14),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "M7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "min7": (0, 3, 7, 10),
    "mmaj7": (0, 3, 7, 11),
    "mM7": (0, 3, 7, 11),
    "m7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9),
    "o7": (0, 3, 6, 9),
    "9": (0, 4, 7, 10, 14),
    "maj9": (0, 4, 7, 11, 14),
    "M9": (0, 4, 7, 11, 14),
    "m9": (0, 3, 7, 10, 14),
    "min9": (0, 3, 7, 10, 14),
    "11": (0, 7, 10, 14, 17),
    "m11": (0, 3, 7, 10, 14, 17),
    "13": (0, 4, 7, 10, 14, 21),
    "maj13": (0, 4, 7, 11, 14, 21),
    "m13": (0, 3, 7, 10, 14, 21),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "sus": (0, 5, 7),
    "7sus4": (0, 5, 7, 10),
    "7sus2": (0, 2, 7, 10),
}

_QUALITY_KEYS_BY_LENGTH: tuple[str, ...] = tuple(
    sorted((key for key in CHORD_QUALITIES if key), key=len, reverse=True)
)

_ROOT_RE = re.compile(r"^([A-Ga-g])([#b]?)")
_MODIFIER_RE = re.compile(r"(add|no|omit|sus|alt|[#b+])?(\d+)?")
_ROMAN_RE = re.compile(r"^([#b]?)(iii|ii|iv|i|vii|vi|v|III|II|IV|I|VII|VI|V)")

_ROMAN_DEGREES: dict[str, int] = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
}

_KEY_MODE_ALIASES: dict[str, str] = {
    "major": "major",
    "maj": "major",
    "ionian": "major",
    "minor": "natural_minor",
    "min": "natural_minor",
    "m": "natural_minor",
    "aeolian": "natural_minor",
    "natural minor": "natural_minor",
    "harmonic minor": "harmonic_minor",
    "melodic minor": "melodic_minor",
    "major pentatonic": "major_pentatonic",
    "minor pentatonic": "minor_pentatonic",
}


class HarmonyError(ValueError):
    """Raised for unparseable chord symbols, keys, or voicing requests."""


@dataclass(frozen=True, slots=True)
class Chord:
    """A chord as pitch classes plus the intervals that produced them."""

    symbol: str
    root: int
    intervals: tuple[int, ...]
    bass: int | None = None
    quality: str = ""

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        return tuple((self.root + interval) % 12 for interval in self.intervals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "root": self.root,
            "quality": self.quality,
            "intervals": list(self.intervals),
            "pitch_classes": list(self.pitch_classes),
            "bass": self.bass,
        }


@dataclass(frozen=True, slots=True)
class Key:
    root: str
    scale: str

    @property
    def root_pitch_class(self) -> int:
        return root_pitch_class(self.root)


def parse_key(text: str) -> Key:
    """Parse ``"F minor"`` / ``"Bb dorian"`` / ``"C"`` into a :class:`Key`."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        raise HarmonyError("key must not be empty")
    parts = cleaned.split(" ", 1)
    root = parts[0]
    try:
        root_pitch_class(root)
    except ValueError as exc:
        raise HarmonyError(f"unknown key root: {root!r}") from exc
    mode_text = parts[1].strip().lower() if len(parts) == 2 else "major"
    scale = _KEY_MODE_ALIASES.get(mode_text, mode_text.replace(" ", "_"))
    if scale not in SCALE_INTERVALS:
        raise HarmonyError(
            f"unknown key mode: {mode_text!r}; use one of {sorted(SCALE_INTERVALS)}",
        )
    return Key(root=root, scale=scale)


def _split_root(symbol: str) -> tuple[int, str]:
    match = _ROOT_RE.match(symbol)
    if match is None:
        raise HarmonyError(f"chord symbol must start with a note name: {symbol!r}")
    return root_pitch_class(match.group(1) + match.group(2)), symbol[match.end() :]


def _apply_degree(intervals: list[int], degree: int, alteration: int) -> list[int]:
    if degree not in DEGREE_SEMITONES:
        raise HarmonyError(f"unsupported chord degree: {degree}")
    base = DEGREE_SEMITONES[degree]
    target = base + alteration
    without_degree = [item for item in intervals if item % 12 != base % 12]
    return sorted({*without_degree, target})


def _remove_degree(intervals: list[int], degree: int) -> list[int]:
    if degree not in DEGREE_SEMITONES:
        raise HarmonyError(f"unsupported chord degree: {degree}")
    base = DEGREE_SEMITONES[degree] % 12
    return [item for item in intervals if item % 12 != base]


def _apply_suspension(intervals: list[int], degree: int) -> list[int]:
    without_third = [item for item in intervals if item % 12 not in (3, 4)]
    return sorted({*without_third, DEGREE_SEMITONES[degree]})


def _apply_modifier(intervals: list[int], kind: str, degree: int | None) -> list[int]:
    if kind in ("no", "omit"):
        return _remove_degree(intervals, _require_degree(kind, degree))
    if kind == "add":
        return _apply_degree(intervals, _require_degree(kind, degree), 0)
    if kind == "sus":
        return _apply_suspension(intervals, degree if degree is not None else 4)
    if kind in ("b", "#", "+"):
        alteration = -1 if kind == "b" else 1
        return _apply_degree(intervals, _require_degree(kind, degree), alteration)
    raise HarmonyError(f"unsupported chord modifier: {kind!r}")


def _require_degree(kind: str, degree: int | None) -> int:
    if degree is None:
        raise HarmonyError(f"chord modifier {kind!r} needs a degree number")
    return degree


def _parse_modifiers(intervals: tuple[int, ...], text: str) -> tuple[int, ...]:
    current = list(intervals)
    position = 0
    while position < len(text):
        match = _MODIFIER_RE.match(text, position)
        if match is None or match.end() == position:
            raise HarmonyError(f"unparseable chord modifier at {text[position:]!r}")
        kind, digits = match.group(1), match.group(2)
        if kind is None and digits is not None:
            raise HarmonyError(f"chord degree {digits!r} needs add/no/b/# before it")
        if kind == "alt":
            current = _apply_modifier(_apply_modifier(current, "b", 9), "#", 5)
        else:
            current = _apply_modifier(current, str(kind), int(digits) if digits else None)
        position = match.end()
    return tuple(current)


def parse_chord_symbol(symbol: str) -> Chord:
    """Parse a chord symbol such as ``Cmaj7``, ``F#m7b5`` or ``Dm7/G``."""
    text = symbol.strip()
    if not text:
        raise HarmonyError("chord symbol must not be empty")
    bass: int | None = None
    if "/" in text:
        text, _, bass_text = text.partition("/")
        try:
            bass = root_pitch_class(bass_text)
        except ValueError as exc:
            raise HarmonyError(f"unknown bass note in {symbol!r}") from exc
    root, remainder = _split_root(text)
    quality = ""
    for candidate in _QUALITY_KEYS_BY_LENGTH:
        if remainder.startswith(candidate):
            quality = candidate
            break
    intervals = _parse_modifiers(CHORD_QUALITIES[quality], remainder[len(quality) :])
    return Chord(symbol=symbol.strip(), root=root, intervals=intervals, bass=bass, quality=quality)


def _roman_quality(numeral: str, remainder: str) -> str:
    is_minor = numeral.islower()
    if remainder.startswith(("o7", "dim7")):
        return "dim7"
    if remainder.startswith(("o", "dim")):
        return "dim"
    if remainder.startswith(("ø", "%")):
        return "m7b5"
    if remainder.startswith(("+", "aug")):
        return "aug"
    return "m" if is_minor else ""


def _roman_suffix(remainder: str) -> str:
    for prefix in ("o7", "dim7", "o", "dim", "ø", "%", "+", "aug"):
        if remainder.startswith(prefix):
            return remainder[len(prefix) :]
    return remainder


def expand_roman_numeral(numeral: str, *, key: Key) -> Chord:
    """Expand ``VII`` / ``bII`` / ``V7`` / ``viio7`` against ``key``."""
    text = numeral.strip()
    match = _ROMAN_RE.match(text)
    if match is None:
        raise HarmonyError(f"unparseable roman numeral: {numeral!r}")
    accidental, roman = match.group(1), match.group(2)
    remainder = text[match.end() :]
    degree = _ROMAN_DEGREES[roman.lower()]
    scale_intervals = SCALE_INTERVALS[key.scale]
    if degree > len(scale_intervals):
        raise HarmonyError(
            f"scale {key.scale!r} has no degree {degree}; use a seven-note scale",
        )
    shift = {"": 0, "#": 1, "b": -1}[accidental]
    root = (key.root_pitch_class + scale_intervals[degree - 1] + shift) % 12
    quality = _roman_quality(roman, remainder)
    suffix = _roman_suffix(remainder)
    intervals = _roman_intervals(quality, suffix) if suffix else CHORD_QUALITIES[quality]
    return Chord(symbol=text, root=root, intervals=intervals, quality=quality)


def _roman_intervals(quality: str, suffix: str) -> tuple[int, ...]:
    combined = f"{quality}{suffix}"
    if combined in CHORD_QUALITIES:
        return CHORD_QUALITIES[combined]
    if suffix in CHORD_QUALITIES:
        return CHORD_QUALITIES[suffix]
    return _parse_modifiers(CHORD_QUALITIES[quality], suffix)


def _looks_like_roman(token: str) -> bool:
    stripped = token.lstrip("#b")
    return bool(stripped) and stripped[0] in "iIvV"


def parse_progression(text: str, *, key: str | Key | None = None) -> list[Chord]:
    """Parse ``"i-VI-III-VII"`` or ``"Cmaj7 A7 Dm7 G7"`` into chords.

    Tokens are separated by ``-``, ``|``, ``,`` or whitespace. Roman
    numerals require ``key``; absolute chord symbols do not.
    """
    tokens = [token for token in re.split(r"[\s,|>-]+", text.strip()) if token]
    if not tokens:
        raise HarmonyError("progression must contain at least one chord")
    parsed_key = parse_key(key) if isinstance(key, str) else key
    chords: list[Chord] = []
    for token in tokens:
        if _looks_like_roman(token):
            if parsed_key is None:
                raise HarmonyError(
                    f"roman numeral {token!r} needs a key; pass e.g. --key 'F minor'",
                )
            chords.append(expand_roman_numeral(token, key=parsed_key))
        else:
            chords.append(parse_chord_symbol(token))
    return chords


def _close_pitches(chord: Chord, *, base_pitch: int) -> list[int]:
    root = base_pitch - (base_pitch % 12) + chord.root
    if root < base_pitch - 6:
        root += 12
    return [root + interval for interval in chord.intervals]


def _drop(pitches: Sequence[int], position_from_top: int) -> list[int]:
    ordered = sorted(pitches)
    if len(ordered) < position_from_top:
        return ordered
    index = len(ordered) - position_from_top
    dropped = list(ordered)
    dropped[index] -= 12
    return sorted(dropped)


def _shell_pitches(chord: Chord, pitches: Sequence[int]) -> list[int]:
    keep = {0}
    for interval in chord.intervals:
        if interval % 12 in (2, 3, 4, 5):
            keep.add(interval)
        if interval % 12 in (10, 11):
            keep.add(interval)
    return sorted(
        pitch for pitch, interval in zip(pitches, chord.intervals, strict=True) if interval in keep
    )


_QUARTAL_MAX_VOICES = 4


def _quartal_pitches(chord: Chord, pitches: Sequence[int]) -> list[int]:
    ordered = sorted(pitches)[:_QUARTAL_MAX_VOICES]
    stacked = [ordered[0]]
    for pitch in ordered[1:]:
        candidate = pitch
        while candidate - stacked[-1] < 5:
            candidate += 12
        stacked.append(candidate)
    return stacked


def voice_chord(
    chord: Chord,
    *,
    base_pitch: int = 60,
    voicing: str = "close",
) -> list[int]:
    """Render ``chord`` as concrete MIDI pitches using ``voicing``."""
    if voicing not in VOICINGS:
        raise HarmonyError(f"unknown voicing {voicing!r}; use one of {list(VOICINGS)}")
    pitches = _close_pitches(chord, base_pitch=base_pitch)
    if voicing == "drop2":
        pitches = _drop(pitches, 2)
    elif voicing == "drop3":
        pitches = _drop(pitches, 3)
    elif voicing == "shell":
        pitches = _shell_pitches(chord, pitches)
    elif voicing == "rootless":
        pitches = sorted(pitches)[1:] or sorted(pitches)
    elif voicing == "quartal":
        pitches = _quartal_pitches(chord, pitches)
    if chord.bass is not None:
        pitches = [_bass_pitch(chord.bass, min(pitches)), *pitches]
    return _clamped(sorted(pitches))


def _bass_pitch(bass_pitch_class: int, above: int) -> int:
    pitch = above - (above % 12) + bass_pitch_class
    while pitch >= above:
        pitch -= 12
    return pitch


def _clamped(pitches: Sequence[int]) -> list[int]:
    for pitch in pitches:
        if not (NOTE_PITCH_MIN <= pitch <= NOTE_PITCH_MAX):
            raise HarmonyError(
                f"voicing produced pitch {pitch} outside [{NOTE_PITCH_MIN}, {NOTE_PITCH_MAX}]",
            )
    return list(pitches)


def _movement(previous: Sequence[int], candidate: Sequence[int]) -> int:
    if not previous:
        return 0
    return sum(min(abs(pitch - other) for other in previous) for pitch in candidate)


def voice_lead(previous: Sequence[int], candidate: Sequence[int]) -> list[int]:
    """Octave-shift ``candidate`` so it moves the least from ``previous``.

    Only whole-octave transpositions of the whole voicing and rotations of
    its lowest note upward are considered, so the chord identity never
    changes — just its inversion and register.
    """
    if not previous or not candidate:
        return list(candidate)
    options: list[list[int]] = []
    for octave in (-12, 0, 12):
        shifted = [pitch + octave for pitch in candidate]
        for rotation in range(len(shifted)):
            rotated = sorted(shifted[rotation:] + [pitch + 12 for pitch in shifted[:rotation]])
            if all(NOTE_PITCH_MIN <= pitch <= NOTE_PITCH_MAX for pitch in rotated):
                options.append(rotated)
    if not options:
        return list(candidate)
    return min(options, key=lambda option: (_movement(previous, option), option))


def progression_notes(
    chords: Sequence[Chord],
    *,
    beats_per_chord: float = 4.0,
    base_pitch: int = 60,
    voicing: str = "close",
    voice_leading: bool = True,
    velocity: int = 90,
    gate: float = 0.98,
    start_time: float = 0.0,
) -> list[Note]:
    """Render ``chords`` as notes-json, one chord per ``beats_per_chord``."""
    if beats_per_chord <= 0:
        raise HarmonyError("beats_per_chord must be > 0")
    if not (0.0 < gate <= 1.0):
        raise HarmonyError("gate must be in (0.0, 1.0]")
    if not (NOTE_VELOCITY_MIN <= velocity <= NOTE_VELOCITY_MAX):
        raise HarmonyError(
            f"velocity {velocity} is outside [{NOTE_VELOCITY_MIN}, {NOTE_VELOCITY_MAX}]",
        )

    notes: list[Note] = []
    previous: list[int] = []
    for index, chord in enumerate(chords):
        pitches = voice_chord(chord, base_pitch=base_pitch, voicing=voicing)
        if voice_leading:
            pitches = voice_lead(previous, pitches)
        previous = pitches
        chord_start = start_time + index * beats_per_chord
        for pitch in pitches:
            notes.append(
                {
                    "pitch": pitch,
                    "start_time": round(chord_start, 6),
                    "duration": round(beats_per_chord * gate, 6),
                    "velocity": velocity,
                    "mute": False,
                }
            )
    return notes
