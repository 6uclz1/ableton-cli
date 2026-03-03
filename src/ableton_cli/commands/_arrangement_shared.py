from __future__ import annotations

from typing import Any

from ._validation import require_non_negative

TRACK_HINT = "Use a valid track index from 'ableton-cli tracks list'."
ARRANGEMENT_CLIP_INDEX_HINT = (
    "Use a valid arrangement clip index from 'ableton-cli arrangement clip list'."
)


def require_track_index(track: int) -> int:
    return require_non_negative(
        "track",
        track,
        hint=TRACK_HINT,
    )


def require_arrangement_clip_index(index: int, *, name: str = "index") -> int:
    return require_non_negative(
        name,
        index,
        hint=ARRANGEMENT_CLIP_INDEX_HINT,
    )


def filters_payload(
    *,
    track: int,
    index: int,
    start_time: float | None,
    end_time: float | None,
    pitch: int | None,
) -> dict[str, Any]:
    return {
        "track": track,
        "index": index,
        "start_time": start_time,
        "end_time": end_time,
        "pitch": pitch,
    }
