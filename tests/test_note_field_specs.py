from __future__ import annotations

from ableton_cli.note_fields import NOTE_FIELD_SPECS as CLI_SPECS
from remote_script.AbletonCliRemote.note_fields import NOTE_FIELD_SPECS as REMOTE_SPECS


def _as_tuples(specs):
    return [
        (spec.name, spec.kind, spec.required, spec.minimum, spec.maximum, spec.exclusive_minimum)
        for spec in specs
    ]


def test_cli_and_remote_note_field_specs_are_identical() -> None:
    assert _as_tuples(CLI_SPECS) == _as_tuples(REMOTE_SPECS)


def test_note_field_specs_cover_the_five_legacy_required_fields() -> None:
    required_names = [spec.name for spec in CLI_SPECS if spec.required]
    assert required_names == ["pitch", "start_time", "duration", "velocity", "mute"]
