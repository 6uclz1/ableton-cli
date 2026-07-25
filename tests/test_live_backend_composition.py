from __future__ import annotations

import inspect
from typing import Any

import pytest

from remote_script.AbletonCliRemote.live_backend import (
    COMMAND_BACKEND_METHODS,
    BackendSurfaceError,
    LiveBackend,
)
from remote_script.AbletonCliRemote.live_backend_parts.base import LiveBackendContext
from remote_script.AbletonCliRemote.live_backend_parts.service import LiveBackendService
from remote_script.AbletonCliRemote.live_backend_parts.services import (
    BackendServices,
    build_services,
)


class _SurfaceStub:
    def song(self) -> Any:
        return self

    def application(self) -> Any:
        return self

    tracks: list[Any] = []
    return_tracks: list[Any] = []
    scenes: list[Any] = []


def test_live_backend_is_not_a_mixin_pile() -> None:
    assert LiveBackend.__bases__ == (object,)


def test_backend_exposes_context_and_services() -> None:
    backend = LiveBackend(_SurfaceStub())
    assert isinstance(backend.context, LiveBackendContext)
    assert isinstance(backend.services, BackendServices)
    assert len(backend.services.all()) == 8
    for service in backend.services.all():
        assert isinstance(service, LiveBackendService)
        assert service._ctx is backend.context  # noqa: SLF001


def test_services_are_reachable_from_the_context() -> None:
    backend = LiveBackend(_SurfaceStub())
    assert backend.context.services is backend.services


def test_every_protocol_method_is_bound_from_exactly_one_service() -> None:
    backend = LiveBackend(_SurfaceStub())
    assert COMMAND_BACKEND_METHODS
    for name in COMMAND_BACKEND_METHODS:
        assert callable(getattr(backend, name)), name


def test_no_two_services_export_the_same_command_name() -> None:
    context = LiveBackendContext(_SurfaceStub())
    services = build_services(context)
    seen: dict[str, str] = {}
    for service in services.all():
        for name in service.command_methods():
            assert name not in seen, f"{name} exported by {seen.get(name)} and {type(service)}"
            seen[name] = type(service).__name__


def test_a_service_missing_a_protocol_method_fails_loudly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = BackendServices.all

    def _without_browser(self: BackendServices) -> tuple[LiveBackendService, ...]:
        return tuple(item for item in original(self) if item is not self.browser)

    monkeypatch.setattr(BackendServices, "all", _without_browser)
    with pytest.raises(BackendSurfaceError, match="no backend service provides"):
        LiveBackend(_SurfaceStub())


def test_command_methods_exclude_service_infrastructure() -> None:
    context = LiveBackendContext(_SurfaceStub())
    services = build_services(context)
    for service in services.all():
        assert "command_methods" not in service.command_methods()


def test_services_reach_each_other_only_through_the_context() -> None:
    """No service may hold a direct reference to another service."""
    context = LiveBackendContext(_SurfaceStub())
    services = build_services(context)
    others = set(map(id, services.all()))
    for service in services.all():
        for _, value in inspect.getmembers(service, lambda item: not callable(item)):
            assert id(value) not in others or value is service
