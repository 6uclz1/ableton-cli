from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SideEffectKind = Literal["read", "write", "destructive"]


@dataclass(frozen=True, slots=True)
class TransportSurfaceSpec:
    command_name: str
    client_method: str
    remote_command: str
    action_name: str | None = None
    action_command: str | None = None
    capability: str | None = None


@dataclass(frozen=True, slots=True)
class SideEffectSpec:
    kind: SideEffectKind
    idempotent: bool
    requires_confirmation: bool

    def to_contract_metadata(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "idempotent": self.idempotent,
            "requires_confirmation": self.requires_confirmation,
        }


@dataclass(frozen=True, slots=True)
class CommandSpec:
    command_name: str
    remote_command: str | None
    side_effect: SideEffectSpec


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
_LOCAL_ONLY_COMMANDS = frozenset(
    {
        "batch stream",
        "audio analyze",
        "audio asset add",
        "audio asset list",
        "audio asset remove",
        "audio beatgrid import",
        "audio loudness analyze",
        "audio reference compare",
        "audio sections import",
        "audio spectrum analyze",
        "audio stems list",
        "audio stems split",
        "clip name set-many",
        "clip place-pattern",
        "completion",
        "config init",
        "config set",
        "config show",
        "doctor",
        "install-remote-script",
        "install-skill",
        "remix apply",
        "remix arrange",
        "remix device-chain apply",
        "remix export-plan",
        "remix generate bass",
        "remix generate chords",
        "remix generate drums",
        "remix import-assets",
        "remix init",
        "remix inspect",
        "remix mix-macro",
        "remix mastering analyze",
        "remix mastering apply",
        "remix mastering plan",
        "remix mastering profile list",
        "remix mastering qa",
        "remix mastering reference add",
        "remix mastering reference list",
        "remix mastering reference remove",
        "remix mastering target set",
        "remix plan",
        "remix qa",
        "remix set-target",
        "remix setup-mix",
        "remix setup-returns",
        "remix setup-sidechain",
        "remix setup-sound",
        "remix vocal-chop",
        "session diff",
        "wait-ready",
    }
)
_REMOTE_COMMAND_EXCEPTIONS = {
    "arrangement from-session": "arrangement_from_session",
    "batch run": "execute_batch",
    "browser categories": "get_browser_categories",
    "browser item": "get_browser_item",
    "browser items": "get_browser_items",
    "browser items-at-path": "get_browser_items_at_path",
    "browser load": "load_instrument_or_effect",
    "browser load-drum-kit": "load_drum_kit",
    "browser search": "search_browser_items",
    "browser tree": "get_browser_tree",
    "clip create": "create_clip",
    "clip duplicate-many": "clip_duplicate",
    "clip fire": "fire_clip",
    "clip name set": "set_clip_name",
    "clip notes add": "add_notes_to_clip",
    "clip notes clear": "clear_clip_notes",
    "clip notes get": "get_clip_notes",
    "clip notes import-browser": "load_instrument_or_effect",
    "clip notes replace": "replace_clip_notes",
    "clip stop": "stop_clip",
    "device parameter set": "set_device_parameter",
    "effect find": "find_effect_devices",
    "effect observe": "observe_effect_parameters",
    "effect parameter set": "set_effect_parameter_safe",
    "effect parameters list": "list_effect_parameters",
    "master devices list": "master_devices_list",
    "master info": "master_info",
    "master panning get": "master_panning_get",
    "master volume get": "master_volume_get",
    "return-track mute get": "return_track_mute_get",
    "return-track mute set": "return_track_mute_set",
    "return-track solo get": "return_track_solo_get",
    "return-track solo set": "return_track_solo_set",
    "return-track volume get": "return_track_volume_get",
    "return-track volume set": "return_track_volume_set",
    "return-tracks list": "return_tracks_list",
    "scenes create": "create_scene",
    "scenes fire": "fire_scene",
    "scenes name set": "set_scene_name",
    "session info": "get_session_info",
    "session stop-all-clips": "stop_all_clips",
    "synth find": "find_synth_devices",
    "synth observe": "observe_synth_parameters",
    "synth parameter set": "set_synth_parameter_safe",
    "synth parameters list": "list_synth_parameters",
    "track info": "get_track_info",
    "track name set": "set_track_name",
    "tracks create audio": "create_audio_track",
    "tracks create midi": "create_midi_track",
}
_REMOTE_COMMAND_ALIASES = frozenset(
    {
        "master_effect_compressor_set",
        "master_effect_eq8_set",
        "master_effect_limiter_set",
        "master_effect_utility_set",
        "set_tempo",
        "start_playback",
        "stop_playback",
    }
)
_DESTRUCTIVE_COMMANDS = frozenset(
    {
        "arrangement clip delete",
        "arrangement clip notes clear",
        "arrangement clip notes import-browser",
        "arrangement clip notes replace",
        "batch run",
        "batch stream",
        "clip cut-to-drum-rack",
        "clip file replace",
        "clip groove clear",
        "clip notes clear",
        "clip notes import-browser",
        "clip notes replace",
        "clip warp-marker add",
        "config init",
        "config set",
        "install-remote-script",
        "install-skill",
        "master device delete",
        "song new",
        "song redo",
        "song undo",
        "tracks delete",
    }
)


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
    for effect_type in ("eq8", "limiter", "compressor", "utility"):
        commands.add(f"master effect {effect_type} keys")
        commands.add(f"master effect {effect_type} set")
        commands.add(f"master effect {effect_type} observe")
    return commands


def _remote_command_name(command_name: str) -> str | None:
    synth_match = re.fullmatch(r"synth (wavetable|drift|meld) (keys|set|observe)", command_name)
    if synth_match:
        suffix = synth_match.group(2)
        if suffix == "keys":
            return "list_standard_synth_keys"
        if suffix == "set":
            return "set_standard_synth_parameter_safe"
        return "observe_standard_synth_state"

    effect_match = re.fullmatch(
        r"effect (eq8|limiter|compressor|auto-filter|reverb|utility) (keys|set|observe)",
        command_name,
    )
    if effect_match:
        suffix = effect_match.group(2)
        if suffix == "keys":
            return "list_standard_effect_keys"
        if suffix == "set":
            return "set_standard_effect_parameter_safe"
        return "observe_standard_effect_state"

    master_effect_match = re.fullmatch(
        r"master effect (eq8|limiter|compressor|utility) (keys|set|observe)",
        command_name,
    )
    if master_effect_match:
        suffix = master_effect_match.group(2)
        if suffix == "keys":
            return "master_effect_keys"
        if suffix == "set":
            return "master_effect_set"
        return "master_effect_observe"

    if command_name in _LOCAL_ONLY_COMMANDS:
        return None
    if command_name in _REMOTE_COMMAND_EXCEPTIONS:
        return _REMOTE_COMMAND_EXCEPTIONS[command_name]
    return command_name.replace(" ", "_").replace("-", "_")


def _is_read_command(command_name: str) -> bool:
    if command_name in {
        "completion",
        "config show",
        "doctor",
        "ping",
        "session diff",
        "session info",
        "session snapshot",
        "wait-ready",
    }:
        return True

    read_suffixes = (" get", " info", " list", " find", " observe", " keys")
    if command_name.endswith(read_suffixes):
        return True

    return command_name.startswith(("browser categories", "browser item", "browser items"))


def _side_effect_spec(command_name: str) -> SideEffectSpec:
    if _is_read_command(command_name):
        return SideEffectSpec(kind="read", idempotent=True, requires_confirmation=False)

    kind: SideEffectKind = "destructive" if command_name in _DESTRUCTIVE_COMMANDS else "write"
    return SideEffectSpec(
        kind=kind,
        idempotent=False,
        requires_confirmation=kind == "destructive",
    )


def command_specs() -> tuple[CommandSpec, ...]:
    return tuple(
        CommandSpec(
            command_name=command_name,
            remote_command=_remote_command_name(command_name),
            side_effect=_side_effect_spec(command_name),
        )
        for command_name in sorted(public_command_names())
    )


def command_spec_map() -> dict[str, CommandSpec]:
    return {spec.command_name: spec for spec in command_specs()}


def remote_command_names() -> set[str]:
    return {
        spec.remote_command for spec in command_specs() if spec.remote_command is not None
    }.union(_REMOTE_COMMAND_ALIASES)


def read_only_remote_command_names() -> set[str]:
    return {
        spec.remote_command
        for spec in command_specs()
        if spec.remote_command is not None and spec.side_effect.kind == "read"
    }


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
