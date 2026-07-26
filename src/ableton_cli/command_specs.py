from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .track_facets import track_facet_command_names

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

# \b keeps these from matching inside identifiers such as "subcommand=".
_COMMAND_NAME_PATTERN = re.compile(r'\bcommand_name="([^"]+)"')
_COMMAND_PATTERN = re.compile(r'\bcommand="([^"]+)"')
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
        "audio groove extract",
        "audio loudness analyze",
        "audio reference compare",
        "audio sections import",
        "audio spectrum analyze",
        "audio stems list",
        "audio stems split",
        "audio transient analyze",
        "clip warp conform",
        "clip name set-many",
        "clip place-pattern",
        "clip notes transpose-in-scale",
        "clip notes arpeggiate",
        "clip notes euclidean",
        "clip notes ratchet",
        "clip notes retrograde",
        "clip notes apply-groove",
        "clip envelope shape",
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
        "session capture",
        "session events",
        "session diff",
        "session watch",
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
    "clip notes update": "update_clip_notes",
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


def public_command_names() -> set[str]:
    commands: set[str] = set()
    for path in sorted(_COMMANDS_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        commands.update(_COMMAND_NAME_PATTERN.findall(text))
        commands.update(_COMMAND_PATTERN.findall(text))

    commands.update(item.command_name for item in TRANSPORT_COMMAND_SPECS)
    commands.update(track_facet_command_names())
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


_READ = SideEffectSpec(kind="read", idempotent=True, requires_confirmation=False)
_WRITE = SideEffectSpec(kind="write", idempotent=False, requires_confirmation=False)
_DESTRUCTIVE = SideEffectSpec(kind="destructive", idempotent=False, requires_confirmation=True)

#: Declared side effect of every public command. There is no default: a command
#: missing from this table makes `command_specs()` raise, because a wrong guess
#: here silently widens `--read-only` or drops a confirmation prompt.
#:
#: The three shared constants are the only combinations in use. `idempotent` is
#: currently equivalent to "is a read"; individual commands that are in fact
#: idempotent writes should be promoted one at a time, with justification,
#: rather than in bulk.
#:
#: Coverage is enforced against `public_command_names()`, which collects names
#: by regex-scanning `commands/`. If that scan ever breaks, this table's
#: exhaustiveness check silently stops meaning anything — the two are expected
#: to be replaced together by per-command descriptors.
_SIDE_EFFECTS: dict[str, SideEffectSpec] = {
    "arrangement clip create": _WRITE,
    "arrangement clip delete": _DESTRUCTIVE,
    "arrangement clip file replace": _WRITE,
    "arrangement clip gain set": _WRITE,
    "arrangement clip list": _READ,
    "arrangement clip loop set": _WRITE,
    "arrangement clip marker set": _WRITE,
    "arrangement clip notes add": _WRITE,
    "arrangement clip notes clear": _DESTRUCTIVE,
    "arrangement clip notes get": _READ,
    "arrangement clip notes import-browser": _DESTRUCTIVE,
    "arrangement clip notes replace": _DESTRUCTIVE,
    "arrangement clip props get": _READ,
    "arrangement clip transpose set": _WRITE,
    "arrangement clip warp get": _READ,
    "arrangement clip warp set": _WRITE,
    "arrangement from-session": _WRITE,
    "arrangement record start": _WRITE,
    "arrangement record stop": _WRITE,
    "audio analyze": _WRITE,
    "audio asset add": _WRITE,
    "audio asset list": _READ,
    "audio asset remove": _WRITE,
    "audio beatgrid import": _WRITE,
    "audio groove extract": _WRITE,
    "audio loudness analyze": _WRITE,
    "audio reference compare": _WRITE,
    "audio sections import": _WRITE,
    "audio spectrum analyze": _WRITE,
    "audio stems list": _READ,
    "audio stems split": _WRITE,
    "audio transient analyze": _WRITE,
    "batch run": _DESTRUCTIVE,
    "batch stream": _DESTRUCTIVE,
    "browser categories": _READ,
    "browser item": _READ,
    "browser items": _READ,
    "browser items-at-path": _READ,
    "browser load": _WRITE,
    "browser load-drum-kit": _WRITE,
    "browser search": _WRITE,
    "browser tree": _WRITE,
    "clip active get": _READ,
    "clip active set": _WRITE,
    "clip create": _WRITE,
    "clip cut-to-drum-rack": _DESTRUCTIVE,
    "clip duplicate": _WRITE,
    "clip duplicate-many": _WRITE,
    "clip envelope clear": _DESTRUCTIVE,
    "clip envelope set": _DESTRUCTIVE,
    "clip envelope shape": _WRITE,
    "clip file path get": _READ,
    "clip file replace": _DESTRUCTIVE,
    "clip fire": _WRITE,
    "clip gain set": _WRITE,
    "clip groove amount set": _WRITE,
    "clip groove clear": _DESTRUCTIVE,
    "clip groove get": _READ,
    "clip groove set": _WRITE,
    "clip loop set": _WRITE,
    "clip marker set": _WRITE,
    "clip name set": _WRITE,
    "clip name set-many": _WRITE,
    "clip notes add": _WRITE,
    "clip notes apply-groove": _WRITE,
    "clip notes arpeggiate": _WRITE,
    "clip notes clear": _DESTRUCTIVE,
    "clip notes euclidean": _WRITE,
    "clip notes get": _READ,
    "clip notes humanize": _WRITE,
    "clip notes import-browser": _DESTRUCTIVE,
    "clip notes quantize": _WRITE,
    "clip notes ratchet": _WRITE,
    "clip notes replace": _DESTRUCTIVE,
    "clip notes retrograde": _WRITE,
    "clip notes transpose": _WRITE,
    "clip notes transpose-in-scale": _WRITE,
    "clip notes update": _WRITE,
    "clip notes velocity-scale": _WRITE,
    "clip place-pattern": _WRITE,
    "clip props get": _READ,
    "clip stop": _WRITE,
    "clip transpose set": _WRITE,
    "clip warp conform": _WRITE,
    "clip warp get": _READ,
    "clip warp set": _WRITE,
    "clip warp-marker add": _DESTRUCTIVE,
    "clip warp-marker list": _READ,
    "clip warp-marker move": _DESTRUCTIVE,
    "clip warp-marker remove": _DESTRUCTIVE,
    "completion": _READ,
    "config init": _DESTRUCTIVE,
    "config set": _DESTRUCTIVE,
    "config show": _READ,
    "device chains list": _READ,
    "device macro list": _READ,
    "device macro set": _WRITE,
    "device parameter set": _WRITE,
    "doctor": _READ,
    "effect auto-filter keys": _READ,
    "effect auto-filter observe": _READ,
    "effect auto-filter set": _WRITE,
    "effect compressor keys": _READ,
    "effect compressor observe": _READ,
    "effect compressor set": _WRITE,
    "effect eq8 keys": _READ,
    "effect eq8 observe": _READ,
    "effect eq8 set": _WRITE,
    "effect find": _READ,
    "effect limiter keys": _READ,
    "effect limiter observe": _READ,
    "effect limiter set": _WRITE,
    "effect observe": _READ,
    "effect parameter set": _WRITE,
    "effect parameters list": _READ,
    "effect reverb keys": _READ,
    "effect reverb observe": _READ,
    "effect reverb set": _WRITE,
    "effect utility keys": _READ,
    "effect utility observe": _READ,
    "effect utility set": _WRITE,
    "install-remote-script": _DESTRUCTIVE,
    "install-skill": _DESTRUCTIVE,
    "master device delete": _DESTRUCTIVE,
    "master device load": _WRITE,
    "master device move": _WRITE,
    "master device parameter set": _WRITE,
    "master device parameters list": _READ,
    "master devices list": _READ,
    "master effect compressor keys": _READ,
    "master effect compressor observe": _READ,
    "master effect compressor set": _WRITE,
    "master effect eq8 keys": _READ,
    "master effect eq8 observe": _READ,
    "master effect eq8 set": _WRITE,
    "master effect limiter keys": _READ,
    "master effect limiter observe": _READ,
    "master effect limiter set": _WRITE,
    "master effect utility keys": _READ,
    "master effect utility observe": _READ,
    "master effect utility set": _WRITE,
    "master info": _READ,
    "master panning get": _READ,
    "master panning set": _WRITE,
    "master volume get": _READ,
    "master volume set": _WRITE,
    "mixer crossfader get": _READ,
    "mixer crossfader set": _WRITE,
    "mixer cue-routing get": _READ,
    "mixer cue-routing set": _WRITE,
    "mixer cue-volume get": _READ,
    "mixer cue-volume set": _WRITE,
    "ping": _READ,
    "remix apply": _WRITE,
    "remix arrange": _WRITE,
    "remix device-chain apply": _WRITE,
    "remix export-plan": _WRITE,
    "remix generate bass": _WRITE,
    "remix generate chords": _WRITE,
    "remix generate drums": _WRITE,
    "remix import-assets": _WRITE,
    "remix init": _WRITE,
    "remix inspect": _WRITE,
    "remix mastering analyze": _WRITE,
    "remix mastering apply": _WRITE,
    "remix mastering plan": _WRITE,
    "remix mastering profile list": _READ,
    "remix mastering qa": _WRITE,
    "remix mastering reference add": _WRITE,
    "remix mastering reference list": _READ,
    "remix mastering reference remove": _WRITE,
    "remix mastering target set": _WRITE,
    "remix mix-macro": _WRITE,
    "remix plan": _WRITE,
    "remix qa": _WRITE,
    "remix set-target": _WRITE,
    "remix setup-mix": _WRITE,
    "remix setup-returns": _WRITE,
    "remix setup-sidechain": _WRITE,
    "remix setup-sound": _WRITE,
    "remix vocal-chop": _WRITE,
    "return-track mute get": _READ,
    "return-track mute set": _WRITE,
    "return-track solo get": _READ,
    "return-track solo set": _WRITE,
    "return-track volume get": _READ,
    "return-track volume set": _WRITE,
    "return-tracks list": _READ,
    "scenes create": _WRITE,
    "scenes fire": _WRITE,
    "scenes list": _READ,
    "scenes move": _WRITE,
    "scenes name set": _WRITE,
    "session capture": _WRITE,
    "session diff": _READ,
    "session events": _WRITE,
    "session info": _READ,
    "session snapshot": _READ,
    "session stop-all-clips": _WRITE,
    "session watch": _READ,
    "song export audio": _WRITE,
    "song info": _READ,
    "song new": _DESTRUCTIVE,
    "song redo": _DESTRUCTIVE,
    "song save": _WRITE,
    "song undo": _DESTRUCTIVE,
    "synth drift keys": _READ,
    "synth drift observe": _READ,
    "synth drift set": _WRITE,
    "synth find": _READ,
    "synth meld keys": _READ,
    "synth meld observe": _READ,
    "synth meld set": _WRITE,
    "synth observe": _READ,
    "synth parameter set": _WRITE,
    "synth parameters list": _READ,
    "synth wavetable keys": _READ,
    "synth wavetable observe": _READ,
    "synth wavetable set": _WRITE,
    "track arm get": _READ,
    "track arm set": _WRITE,
    "track info": _READ,
    "track mute get": _READ,
    "track mute set": _WRITE,
    "track name set": _WRITE,
    "track panning get": _READ,
    "track panning set": _WRITE,
    "track routing input get": _READ,
    "track routing input set": _WRITE,
    "track routing output get": _READ,
    "track routing output set": _WRITE,
    "track send get": _READ,
    "track send set": _WRITE,
    "track solo get": _READ,
    "track solo set": _WRITE,
    "track volume get": _READ,
    "track volume set": _WRITE,
    "tracks create audio": _WRITE,
    "tracks create midi": _WRITE,
    "tracks delete": _DESTRUCTIVE,
    "tracks list": _READ,
    "transport play": _WRITE,
    "transport position get": _READ,
    "transport position set": _WRITE,
    "transport rewind": _WRITE,
    "transport stop": _WRITE,
    "transport tempo get": _READ,
    "transport tempo set": _WRITE,
    "transport toggle": _WRITE,
    "wait-ready": _READ,
}


def _side_effect_spec(command_name: str) -> SideEffectSpec:
    spec = _SIDE_EFFECTS.get(command_name)
    if spec is None:
        raise KeyError(
            f"Command {command_name!r} has no declared side effect. "
            "Add an entry to _SIDE_EFFECTS in command_specs.py."
        )
    return spec


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


_SIDE_EFFECT_SEVERITY: dict[SideEffectKind, int] = {"read": 0, "write": 1, "destructive": 2}


def _merge_side_effects(left: SideEffectSpec, right: SideEffectSpec) -> SideEffectSpec:
    """Combine two declarations for the same remote command, safe side first."""
    kind = max(left.kind, right.kind, key=lambda item: _SIDE_EFFECT_SEVERITY[item])
    return SideEffectSpec(
        kind=kind,
        idempotent=left.idempotent and right.idempotent,
        requires_confirmation=left.requires_confirmation or right.requires_confirmation,
    )


def remote_command_spec_map() -> dict[str, CommandSpec]:
    """Look up a ``CommandSpec`` by remote command name.

    Batch steps name remote commands (``add_notes_to_clip``) while
    ``command_spec_map`` is keyed by CLI command names (``clip notes add``).
    The mapping is many-to-one — ``clip notes import-browser`` and
    ``browser load`` both dispatch ``load_instrument_or_effect`` — so colliding
    entries are merged on the safe side: the strongest side-effect kind wins,
    ``idempotent`` is the conjunction, and ``requires_confirmation`` the
    disjunction. ``command_name`` is left holding the first CLI name in sorted
    order and must not be used as an identity.
    """
    merged: dict[str, CommandSpec] = {}
    for spec in command_specs():
        if spec.remote_command is None:
            continue
        existing = merged.get(spec.remote_command)
        if existing is None:
            merged[spec.remote_command] = spec
            continue
        merged[spec.remote_command] = CommandSpec(
            command_name=existing.command_name,
            remote_command=spec.remote_command,
            side_effect=_merge_side_effects(existing.side_effect, spec.side_effect),
        )
    return merged


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
