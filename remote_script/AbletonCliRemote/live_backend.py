"""Composition root for the Live-API backend.

``LiveBackend`` used to inherit from eighteen mixins, so every helper and
every command lived in one namespace and mixins depended on each other
implicitly through ``self``. It now owns a shared
:class:`LiveBackendContext` and eight domain services composed over it
(``backend.services.browser``, ``backend.services.clip_notes``, ...).

Command handlers still call a flat method surface
(``backend.create_clip(...)``), so the flat names are bound here from the
methods the services provide. The binding is checked against the
``CommandBackend`` protocol at construction: every protocol method must be
provided by exactly one service (or the context), and no two services may
export the same name. A mis-split service fails loudly at startup instead
of silently shadowing a command.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .live_backend_parts.base import LiveBackendContext
from .live_backend_parts.services import BackendServices, build_services

#: Methods the context itself provides to the command surface.
_CONTEXT_COMMAND_METHODS = (
    "ping_info",
    "resolve_track_ref",
    "resolve_device_ref",
    "resolve_parameter_ref",
)


def _protocol_method_names() -> frozenset[str]:
    names: set[str] = set()
    for klass in CommandBackend.__mro__:
        if klass is object:
            continue
        names.update(
            name
            for name, value in vars(klass).items()
            if not name.startswith("_") and callable(value)
        )
    return frozenset(names)


COMMAND_BACKEND_METHODS: frozenset[str] = _protocol_method_names()


class BackendSurfaceError(RuntimeError):
    """Raised when the services do not add up to the command surface."""


class LiveBackend:
    def __init__(self, control_surface: Any) -> None:
        self._control_surface = control_surface
        self.context = LiveBackendContext(control_surface)
        self.services: BackendServices = build_services(self.context)
        self._bind_command_surface()

    def _bind_command_surface(self) -> None:
        provided: dict[str, Callable[..., Any]] = {
            name: getattr(self.context, name) for name in _CONTEXT_COMMAND_METHODS
        }
        for service in self.services.all():
            for name, method in service.command_methods().items():
                if name in provided:
                    raise BackendSurfaceError(
                        f"{name} is exported by more than one backend service",
                    )
                provided[name] = method

        missing = COMMAND_BACKEND_METHODS - provided.keys()
        if missing:
            raise BackendSurfaceError(
                f"no backend service provides: {', '.join(sorted(missing))}",
            )
        for name, method in provided.items():
            setattr(self, name, method)


__all__ = ["COMMAND_BACKEND_METHODS", "BackendSurfaceError", "LiveBackend"]
