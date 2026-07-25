"""Fan-out of Live-side events to subscribed connections.

The command protocol is strictly request/response, so anything a user does
in Live itself (moving the tempo, hitting play, selecting a track) could
only be noticed by polling. Subscribers attach a bounded queue here; the
control surface publishes onto it from Live's main thread and each
connection thread drains its own queue.

Nothing in this module touches the Live API or a socket, so the fan-out,
the bounds and the drop accounting are all testable on their own.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

#: Every event name the protocol knows about. What a given Live version can
#: actually deliver is narrower; see LiveEventSource.available_events().
EVENT_NAMES: tuple[str, ...] = (
    "tempo",
    "is_playing",
    "playing_position",
    "selected_track",
)

DEFAULT_QUEUE_SIZE = 256


class UnknownEventError(ValueError):
    """Raised when a subscription asks for an event name that does not exist."""


@dataclass(frozen=True, slots=True)
class Event:
    name: str
    data: dict[str, Any]
    ts: float

    def to_line_payload(self, *, protocol_version: int, dropped: int) -> dict[str, Any]:
        return {
            "type": "event",
            "protocol_version": protocol_version,
            "event": self.name,
            "ts": self.ts,
            "data": self.data,
            "dropped": dropped,
        }


class Subscription:
    """One connection's view of the event stream.

    The queue is bounded: a subscriber that cannot keep up loses the oldest
    events rather than growing without limit, and the count of what it lost
    rides along on the next event it does receive.
    """

    def __init__(self, events: frozenset[str], *, max_queued: int = DEFAULT_QUEUE_SIZE) -> None:
        self.events = events
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=max_queued)
        self._dropped = 0
        self._lock = threading.Lock()
        self._closed = threading.Event()

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def offer(self, event: Event) -> None:
        if self.closed or event.name not in self.events:
            return
        while True:
            try:
                self._queue.put_nowait(event)
                return
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:  # pragma: no cover - racing drain
                    continue
                with self._lock:
                    self._dropped += 1

    def get(self, timeout: float) -> tuple[Event, int] | None:
        """Next event plus the number dropped since the previous one."""
        try:
            event = self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
        with self._lock:
            dropped = self._dropped
            self._dropped = 0
        return event, dropped

    def close(self) -> None:
        self._closed.set()


class EventBroker:
    def __init__(self, *, time_fn: Callable[[], float] = time.time) -> None:
        self._time_fn = time_fn
        self._lock = threading.Lock()
        self._subscriptions: list[Subscription] = []

    @property
    def subscription_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)

    def subscribe(
        self,
        events: list[str] | tuple[str, ...],
        *,
        max_queued: int = DEFAULT_QUEUE_SIZE,
    ) -> Subscription:
        requested = tuple(events)
        unknown = [name for name in requested if name not in EVENT_NAMES]
        if unknown:
            raise UnknownEventError(
                f"unknown event names: {sorted(unknown)}; use one of {list(EVENT_NAMES)}"
            )
        subscription = Subscription(frozenset(requested or EVENT_NAMES), max_queued=max_queued)
        with self._lock:
            self._subscriptions.append(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        subscription.close()
        with self._lock:
            if subscription in self._subscriptions:
                self._subscriptions.remove(subscription)

    def publish(self, name: str, data: dict[str, Any]) -> None:
        if name not in EVENT_NAMES:
            raise UnknownEventError(f"unknown event name: {name!r}")
        event = Event(name=name, data=dict(data), ts=self._time_fn())
        with self._lock:
            subscriptions = list(self._subscriptions)
        for subscription in subscriptions:
            subscription.offer(event)

    def close(self) -> None:
        with self._lock:
            subscriptions = list(self._subscriptions)
            self._subscriptions.clear()
        for subscription in subscriptions:
            subscription.close()
