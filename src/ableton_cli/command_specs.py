from __future__ import annotations

from dataclasses import dataclass

from .command_registry import (
    COMMAND_DESCRIPTORS,
    DESCRIPTOR_BY_COMMAND_NAME,
    REMOTE_COMMAND_ALIASES,
    CommandDescriptor,
    SideEffectKind,
    SideEffectSpec,
)
from .command_registry import public_command_names as registry_public_command_names


@dataclass(frozen=True, slots=True)
class TransportSurfaceSpec:
    command_name: str
    client_method: str
    remote_command: str
    action_name: str | None = None
    action_command: str | None = None
    capability: str | None = None


TRANSPORT_COMMAND_SPECS: tuple[TransportSurfaceSpec, ...] = (
    TransportSurfaceSpec(
        command_name="transport play",
        client_method="transport_play",
        remote_command="transport_play",
        action_name="play",
        action_command="uv run ableton-cli --output json transport play",
        capability="Start transport playback.",
    ),
    TransportSurfaceSpec(
        command_name="transport stop",
        client_method="transport_stop",
        remote_command="transport_stop",
        action_name="stop",
        action_command="uv run ableton-cli --output json transport stop",
        capability="Stop transport playback.",
    ),
    TransportSurfaceSpec(
        command_name="transport toggle",
        client_method="transport_toggle",
        remote_command="transport_toggle",
    ),
    TransportSurfaceSpec(
        command_name="transport tempo get",
        client_method="transport_tempo_get",
        remote_command="transport_tempo_get",
    ),
    TransportSurfaceSpec(
        command_name="transport tempo set",
        client_method="transport_tempo_set",
        remote_command="transport_tempo_set",
        action_name="set_tempo",
        action_command="uv run ableton-cli --output json transport tempo set <bpm>",
        capability="Update song tempo in BPM.",
    ),
    TransportSurfaceSpec(
        command_name="transport position get",
        client_method="transport_position_get",
        remote_command="transport_position_get",
        action_name="transport_position_get",
        action_command="uv run ableton-cli --output json transport position get",
        capability="Read current transport beat/time position.",
    ),
    TransportSurfaceSpec(
        command_name="transport position set",
        client_method="transport_position_set",
        remote_command="transport_position_set",
        action_name="transport_position_set",
        action_command="uv run ableton-cli --output json transport position set <beats>",
        capability="Move transport playhead to a beat position.",
    ),
    TransportSurfaceSpec(
        command_name="transport rewind",
        client_method="transport_rewind",
        remote_command="transport_rewind",
        action_name="transport_rewind",
        action_command="uv run ableton-cli --output json transport rewind",
        capability="Rewind transport playhead to beat 0.",
    ),
)


def public_command_names() -> set[str]:
    return registry_public_command_names()


def command_specs() -> tuple[CommandDescriptor, ...]:
    return tuple(sorted(COMMAND_DESCRIPTORS, key=lambda item: item.command_name))


def command_spec_map() -> dict[str, CommandDescriptor]:
    return dict(DESCRIPTOR_BY_COMMAND_NAME)


_SIDE_EFFECT_SEVERITY: dict[SideEffectKind, int] = {"read": 0, "write": 1, "destructive": 2}


def _merge_side_effects(left: SideEffectSpec, right: SideEffectSpec) -> SideEffectSpec:
    """Combine two declarations for the same remote command, safe side first."""
    kind = max(left.kind, right.kind, key=lambda item: _SIDE_EFFECT_SEVERITY[item])
    return SideEffectSpec(
        kind=kind,
        idempotent=left.idempotent and right.idempotent,
        requires_confirmation=left.requires_confirmation or right.requires_confirmation,
    )


def remote_command_spec_map() -> dict[str, CommandDescriptor]:
    """Look up a ``CommandDescriptor`` by remote command name.

    Batch steps name remote commands (``add_notes_to_clip``) while
    ``command_spec_map`` is keyed by CLI command names (``clip notes add``).
    The mapping is many-to-one — ``clip notes import-browser`` and
    ``browser load`` both dispatch ``load_instrument_or_effect`` — so colliding
    entries are merged on the safe side: the strongest side-effect kind wins,
    ``idempotent`` is the conjunction, and ``requires_confirmation`` the
    disjunction. ``command_name`` is left holding the first CLI name in sorted
    order and must not be used as an identity.
    """
    merged: dict[str, CommandDescriptor] = {}
    for spec in command_specs():
        if spec.remote_command is None:
            continue
        existing = merged.get(spec.remote_command)
        if existing is None:
            merged[spec.remote_command] = spec
            continue
        merged[spec.remote_command] = CommandDescriptor(
            command_name=existing.command_name,
            remote_command=spec.remote_command,
            side_effect=_merge_side_effects(existing.side_effect, spec.side_effect),
        )
    return merged


def remote_command_names() -> set[str]:
    return {
        spec.remote_command for spec in command_specs() if spec.remote_command is not None
    }.union(REMOTE_COMMAND_ALIASES)


def read_only_remote_command_names() -> set[str]:
    return {
        spec.remote_command
        for spec in command_specs()
        if spec.remote_command is not None and spec.side_effect.kind == "read"
    }
