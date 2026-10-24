from __future__ import annotations

from typing import Any

try:  # pragma: no cover - Live is only importable inside Ableton
    import Live  # type: ignore
except ImportError:
    Live = None  # type: ignore[assignment]


def midi_note_specification_class() -> Any:
    if Live is None:
        raise RuntimeError(
            "Live API is not available outside Ableton; "
            "inject a note specification factory for tests."
        )
    return Live.Clip.MidiNoteSpecification
