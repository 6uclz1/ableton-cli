from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


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

_COMMAND_NAME_PATTERN = re.compile(r'command_name="([^"]+)"')
_COMMAND_PATTERN = re.compile(r'command="([^"]+)"')
_COMMANDS_DIR = Path(__file__).resolve().parent / "commands"
_STANDARD_SYNTH_TYPES = ("wavetable", "drift", "meld")
_STANDARD_EFFECT_TYPES = ("eq8", "limiter", "compressor", "auto-filter", "reverb", "utility")


def public_command_names() -> set[str]:
    commands: set[str] = set()
    for path in sorted(_COMMANDS_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        commands.update(_COMMAND_NAME_PATTERN.findall(text))
        commands.update(_COMMAND_PATTERN.findall(text))

    commands.update(item.command_name for item in TRANSPORT_COMMAND_SPECS)
    commands.add("batch stream")
    for synth_type in _STANDARD_SYNTH_TYPES:
        commands.add(f"synth {synth_type} keys")
        commands.add(f"synth {synth_type} set")
        commands.add(f"synth {synth_type} observe")
    for effect_type in _STANDARD_EFFECT_TYPES:
        commands.add(f"effect {effect_type} keys")
        commands.add(f"effect {effect_type} set")
        commands.add(f"effect {effect_type} observe")
    return commands


def validate_transport_command_specs() -> None:
    from .actions import stable_action_capability_map, stable_action_command_map
    from .capabilities import required_remote_commands
    from .commands import transport
    from .contracts.registry import get_registered_contracts

    contracts = get_registered_contracts()
    action_commands = stable_action_command_map()
    action_capabilities = stable_action_capability_map()
    required = required_remote_commands()
    public_commands = public_command_names()
    module_specs = {
        item.command_name: item.client_method
        for item in (
            transport.TRANSPORT_PLAY_SPEC,
            transport.TRANSPORT_STOP_SPEC,
            transport.TRANSPORT_TOGGLE_SPEC,
            transport.TRANSPORT_TEMPO_GET_SPEC,
            transport.TRANSPORT_TEMPO_SET_SPEC,
            transport.TRANSPORT_POSITION_GET_SPEC,
            transport.TRANSPORT_POSITION_SET_SPEC,
            transport.TRANSPORT_REWIND_SPEC,
        )
    }

    for spec in TRANSPORT_COMMAND_SPECS:
        assert spec.command_name in public_commands
        assert module_specs[spec.command_name] == spec.client_method
        assert spec.remote_command in required
        assert spec.command_name in contracts
        if spec.action_name is None:
            continue
        assert action_commands[spec.action_name] == spec.action_command
        assert action_capabilities[spec.action_name] == spec.capability
