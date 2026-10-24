from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import LiveBackendContext

#: Names on the service base itself, never part of a service's command surface.
_INFRASTRUCTURE_NAMES = frozenset({"command_methods"})


class LiveBackendService:
    """Base for a backend domain service.

    A service holds the shared :class:`LiveBackendContext` rather than
    inheriting helpers from it, and reaches other services only through
    ``self._ctx.services``. That keeps each service's dependencies visible
    at the call site instead of hidden in a method resolution order.
    """

    def __init__(self, context: LiveBackendContext) -> None:
        self._ctx = context

    def command_methods(self) -> dict[str, Callable[..., Any]]:
        """Public methods this service contributes to the backend surface."""
        return {
            name: getattr(self, name)
            for name in dir(type(self))
            if not name.startswith("_")
            and name not in _INFRASTRUCTURE_NAMES
            and callable(getattr(type(self), name, None))
        }
