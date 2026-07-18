"""Pure polling helpers for ``session watch``.

Imports only client protocol types (a minimal ``session_snapshot()``
Protocol), never anything from ``commands``. The polling loop takes
injected ``sleep_fn``/``time_fn``/``emit`` callables so it is fully
testable without real sleeping or a real clock.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

from .session_diff import compute_session_diff

WATCH_SCOPES: frozenset[str] = frozenset({"song", "tracks", "transport", "all"})

_SCOPE_KEYS: dict[str, tuple[str, ...]] = {
    "song": ("song_info",),
    "tracks": ("tracks_list",),
    "transport": ("song_info",),
    "all": ("song_info", "session_info", "tracks_list", "scenes_list"),
}

_VOLATILE_SONG_INFO_KEYS = ("current_time", "beat_position")


class SessionSnapshotClient(Protocol):
    def session_snapshot(self) -> dict[str, Any]: ...


def build_watch_snapshot(client: SessionSnapshotClient, scope: str) -> dict[str, Any]:
    if scope not in WATCH_SCOPES:
        raise ValueError(f"Unknown scope: {scope!r}")
    full_snapshot = client.session_snapshot()
    keys = _SCOPE_KEYS[scope]
    return {key: full_snapshot[key] for key in keys if key in full_snapshot}


def strip_volatile(snapshot: dict[str, Any], include_position: bool) -> dict[str, Any]:
    if include_position or "song_info" not in snapshot:
        return snapshot
    song_info = snapshot["song_info"]
    if not isinstance(song_info, dict):
        return snapshot
    filtered_song_info = {
        key: value for key, value in song_info.items() if key not in _VOLATILE_SONG_INFO_KEYS
    }
    return {**snapshot, "song_info": filtered_song_info}


def run_watch_loop(
    client: SessionSnapshotClient,
    *,
    scope: str,
    interval_seconds: float,
    count: int | None,
    include_position: bool,
    emit: Callable[[dict[str, Any]], None],
    sleep_fn: Callable[[float], None] = time.sleep,
    time_fn: Callable[[], float] = time.time,
) -> None:
    """Poll ``client.session_snapshot()`` every ``interval_seconds`` and call
    ``emit({"ts": ..., "diff": ...})`` once per poll with a non-empty diff.
    Stops after ``count`` emitted diffs, or runs forever if ``count`` is
    ``None`` (until the caller interrupts, e.g. via KeyboardInterrupt).
    """
    previous = strip_volatile(build_watch_snapshot(client, scope), include_position)
    emitted = 0
    while count is None or emitted < count:
        sleep_fn(interval_seconds)
        current = strip_volatile(build_watch_snapshot(client, scope), include_position)
        diff = compute_session_diff(previous, current)
        if diff["added"] or diff["removed"] or diff["changed"]:
            emit({"ts": time_fn(), "diff": diff})
            emitted += 1
        previous = current
