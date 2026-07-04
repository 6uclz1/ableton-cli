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
)
