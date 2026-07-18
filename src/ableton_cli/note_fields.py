"""Single source of truth for MIDI note field validation rules.

The CLI (``src/ableton_cli``) and the Remote Script
(``remote_script/AbletonCliRemote``) run in two separate Python runtimes: the
Remote Script executes inside Ableton Live's embedded interpreter and cannot
import the ``ableton_cli`` package. Each side therefore keeps its own copy of
this module. ``tests/test_note_field_specs.py`` asserts the two copies stay
identical, so any change here must be mirrored in
``remote_script/AbletonCliRemote/note_fields.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NoteFieldKind = Literal["int", "float", "bool"]


@dataclass(frozen=True, slots=True)
class NoteFieldSpec:
    name: str
    kind: NoteFieldKind
    required: bool
    minimum: float | None = None
    maximum: float | None = None
    exclusive_minimum: bool = False


NOTE_FIELD_SPECS: tuple[NoteFieldSpec, ...] = (
    NoteFieldSpec(name="pitch", kind="int", required=True, minimum=0, maximum=127),
    NoteFieldSpec(name="start_time", kind="float", required=True, minimum=0.0),
    NoteFieldSpec(
        name="duration", kind="float", required=True, minimum=0.0, exclusive_minimum=True
    ),
    NoteFieldSpec(name="velocity", kind="int", required=True, minimum=1, maximum=127),
    NoteFieldSpec(name="mute", kind="bool", required=True),
    # Live 12+ extended note API fields. Optional on input: when omitted, Live
    # applies its own defaults (probability=1.0, velocity_deviation=0.0,
    # release_velocity=64). Always present on output.
    NoteFieldSpec(name="probability", kind="float", required=False, minimum=0.0, maximum=1.0),
    NoteFieldSpec(
        name="velocity_deviation",
        kind="float",
        required=False,
        minimum=-127.0,
        maximum=127.0,
    ),
    NoteFieldSpec(name="release_velocity", kind="int", required=False, minimum=0, maximum=127),
)


def _field_spec(name: str) -> NoteFieldSpec:
    for spec in NOTE_FIELD_SPECS:
        if spec.name == name:
            return spec
    raise KeyError(name)


NOTE_PITCH_MIN = int(_field_spec("pitch").minimum)  # type: ignore[arg-type]
NOTE_PITCH_MAX = int(_field_spec("pitch").maximum)  # type: ignore[arg-type]
NOTE_VELOCITY_MIN = int(_field_spec("velocity").minimum)  # type: ignore[arg-type]
NOTE_VELOCITY_MAX = int(_field_spec("velocity").maximum)  # type: ignore[arg-type]
