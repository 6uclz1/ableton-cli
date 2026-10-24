from __future__ import annotations

from remote_script.AbletonCliRemote.command_backend_handlers_arrangement import (
    ARRANGEMENT_HANDLERS,
)
from remote_script.AbletonCliRemote.command_backend_handlers_tracks_clips import (
    TRACKS_CLIPS_HANDLERS,
)
from remote_script.AbletonCliRemote.command_backend_registry import _HANDLERS


def test_arrangement_handlers_moved_out_of_tracks_clips_handlers() -> None:
    assert not any(name.startswith("arrangement_") for name in TRACKS_CLIPS_HANDLERS)
    assert all(name.startswith("arrangement_") for name in ARRANGEMENT_HANDLERS)


def test_arrangement_handlers_are_registered_in_dispatch_table() -> None:
    for name in ARRANGEMENT_HANDLERS:
        assert name in _HANDLERS
        assert _HANDLERS[name] is ARRANGEMENT_HANDLERS[name]


def test_tracks_clips_handlers_still_owns_session_clip_commands() -> None:
    assert "fire_clip" in TRACKS_CLIPS_HANDLERS
    assert "clip_notes_quantize" in TRACKS_CLIPS_HANDLERS
    assert "tracks_delete" in TRACKS_CLIPS_HANDLERS
