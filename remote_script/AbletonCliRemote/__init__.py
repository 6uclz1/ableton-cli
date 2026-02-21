from __future__ import annotations

from .control_surface import AbletonCliRemoteSurface


def create_instance(c_instance):  # noqa: ANN001, ANN201
    """Ableton Live entrypoint for Control Surface scripts."""
    return AbletonCliRemoteSurface(c_instance)


__all__ = ["create_instance", "AbletonCliRemoteSurface"]
