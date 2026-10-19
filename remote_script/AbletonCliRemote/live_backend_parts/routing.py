"""Routing type/channel selection shared by tracks and sidechain-capable devices.

Live exposes the same four properties wherever a routing chooser exists:
``available_<direction>_routing_types``/``_channels`` and the current
``<direction>_routing_type``/``_channel``. Tracks have ``input`` and
``output``; ``CompressorDevice`` has ``input`` for its sidechain source. The
helpers here operate on any such owner so both use one implementation.
"""

from __future__ import annotations

from typing import Any

from .base import _invalid_argument, _not_supported_by_live_api


def routing_display_name(value: object) -> str:
    # Live 12 routing targets are RoutingType/RoutingChannel objects whose
    # str() is an opaque repr; display_name carries the user-facing name.
    return str(getattr(value, "display_name", value))


def string_choices(values: list[object]) -> list[str]:
    return [routing_display_name(value) for value in values]


def require_routing_support(
    owner: Any,
    direction: str,
    *,
    subject: str,
) -> tuple[list[str], list[str]]:
    types_attr = f"available_{direction}_routing_types"
    channels_attr = f"available_{direction}_routing_channels"
    current_type_attr = f"{direction}_routing_type"
    current_channel_attr = f"{direction}_routing_channel"
    if not all(
        hasattr(owner, attribute)
        for attribute in (types_attr, channels_attr, current_type_attr, current_channel_attr)
    ):
        raise _not_supported_by_live_api(
            message=f"{direction} routing API is not available in Live API",
            hint=f"Use a Live version exposing {subject} {direction} routing properties.",
        )
    return (
        string_choices(list(getattr(owner, types_attr))),
        string_choices(list(getattr(owner, channels_attr))),
    )


def routing_state(owner: Any, direction: str, *, subject: str) -> dict[str, Any]:
    available_types, available_channels = require_routing_support(owner, direction, subject=subject)
    return {
        "current": {
            "type": routing_display_name(getattr(owner, f"{direction}_routing_type")),
            "channel": routing_display_name(getattr(owner, f"{direction}_routing_channel")),
        },
        "available": {
            "types": available_types,
            "channels": available_channels,
        },
    }


def apply_routing(
    owner: Any,
    direction: str,
    *,
    subject: str,
    routing_type: str,
    routing_channel: str | None,
) -> None:
    available_types, _ = require_routing_support(owner, direction, subject=subject)
    if routing_type not in available_types:
        raise _invalid_argument(
            message=f"Unsupported {direction} routing type: {routing_type}",
            hint="Use one of the exact routing types reported by the get command.",
        )
    # Assign the Live routing objects themselves; Live rejects plain strings.
    type_choices = list(getattr(owner, f"available_{direction}_routing_types"))
    setattr(
        owner,
        f"{direction}_routing_type",
        type_choices[available_types.index(routing_type)],
    )
    # Valid channels depend on the routing type, so resolve them only after
    # the type is applied. A None channel keeps Live's auto-selected default.
    if routing_channel is None:
        return
    channel_choices = list(getattr(owner, f"available_{direction}_routing_channels"))
    available_channels = string_choices(channel_choices)
    if routing_channel not in available_channels:
        raise _invalid_argument(
            message=(
                f"Unsupported {direction} routing channel for {routing_type!r}: {routing_channel}"
            ),
            hint=(
                "The routing type was applied; pick a channel from "
                f"{available_channels} or omit the channel to keep Live's default."
            ),
        )
    setattr(
        owner,
        f"{direction}_routing_channel",
        channel_choices[available_channels.index(routing_channel)],
    )
