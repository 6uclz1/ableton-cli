"""Wiring between Live's listener API and the event broker.

Listeners are added once, on Live's main thread, when the control surface
starts, and removed on disconnect. Whether a given event is available at
all depends on the running Live version, so ``available_events`` reports
what was actually wired rather than what the protocol knows about — a
subscription for an unavailable event fails explicitly instead of going
quiet forever.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .events import EventBroker

#: playing_position fires on every Live time change; do not forward faster.
DEFAULT_POSITION_INTERVAL_S = 0.1


@dataclass(frozen=True, slots=True)
class _ListenerBinding:
    event: str
    add_attr: str
    remove_attr: str
    target: str  # "song" or "song_view"


_BINDINGS: tuple[_ListenerBinding, ...] = (
    _ListenerBinding("tempo", "add_tempo_listener", "remove_tempo_listener", "song"),
    _ListenerBinding("is_playing", "add_is_playing_listener", "remove_is_playing_listener", "song"),
    _ListenerBinding(
        "playing_position",
        "add_current_song_time_listener",
        "remove_current_song_time_listener",
        "song",
    ),
    _ListenerBinding(
        "selected_track",
        "add_selected_track_listener",
        "remove_selected_track_listener",
        "song_view",
    ),
)


class LiveEventSource:
    def __init__(
        self,
        song_getter: Callable[[], Any],
        broker: EventBroker,
        *,
        time_fn: Callable[[], float] = time.monotonic,
        position_interval_s: float = DEFAULT_POSITION_INTERVAL_S,
    ) -> None:
        self._song_getter = song_getter
        self._broker = broker
        self._time_fn = time_fn
        self._position_interval_s = position_interval_s
        self._last_position_at: float | None = None
        self._attached: list[tuple[_ListenerBinding, Any, Callable[[], None]]] = []

    def available_events(self) -> tuple[str, ...]:
        return tuple(binding.event for binding, _, _ in self._attached)

    def _target_for(self, binding: _ListenerBinding) -> Any:
        try:
            song = self._song_getter()
        except Exception:  # noqa: BLE001 - no song means no events to offer
            return None
        if binding.target == "song":
            return song
        return getattr(song, "view", None)

    def attach(self) -> tuple[str, ...]:
        """Register every listener this Live version supports.

        Returns the events that actually attached; an event that is not in
        that tuple is refused at subscribe time rather than accepted and
        then never delivered.
        """
        for binding in _BINDINGS:
            target = self._target_for(binding)
            if target is None or not callable(getattr(target, binding.add_attr, None)):
                continue
            callback = self._callback_for(binding.event)
            getattr(target, binding.add_attr)(callback)
            self._attached.append((binding, target, callback))
        return self.available_events()

    def detach(self) -> None:
        for binding, target, callback in self._attached:
            remove = getattr(target, binding.remove_attr, None)
            if callable(remove):
                try:
                    remove(callback)
                except Exception:  # noqa: BLE001 - Live may already be tearing down
                    pass
        self._attached.clear()

    def _callback_for(self, event: str) -> Callable[[], None]:
        def _fire() -> None:
            try:
                self._publish(event)
            except Exception:  # noqa: BLE001 - never let a listener break Live
                pass

        return _fire

    def _publish(self, event: str) -> None:
        if event == "playing_position" and not self._position_due():
            return
        self._broker.publish(event, self._payload_for(event))

    def _position_due(self) -> bool:
        now = self._time_fn()
        if self._last_position_at is not None and (
            now - self._last_position_at < self._position_interval_s
        ):
            return False
        self._last_position_at = now
        return True

    def _payload_for(self, event: str) -> dict[str, Any]:
        song = self._song_getter()
        if event == "tempo":
            return {"tempo": float(getattr(song, "tempo", 0.0))}
        if event == "is_playing":
            return {"is_playing": bool(getattr(song, "is_playing", False))}
        if event == "playing_position":
            return {"current_time": float(getattr(song, "current_song_time", 0.0))}
        return self._selected_track_payload(song)

    @staticmethod
    def _selected_track_payload(song: Any) -> dict[str, Any]:
        view = getattr(song, "view", None)
        selected = getattr(view, "selected_track", None) if view is not None else None
        if selected is None:
            return {"track_index": None, "name": None}
        tracks = list(getattr(song, "tracks", []))
        index = next((i for i, track in enumerate(tracks) if track is selected), None)
        return {"track_index": index, "name": str(getattr(selected, "name", ""))}
