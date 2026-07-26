"""The single table that declares every public CLI command.

One row per command: its name, the remote command it dispatches (or ``None``
when it completes entirely inside the CLI), and its declared side effect.
Everything that used to be derived — by regex-scanning ``commands/`` for
command names, by string-munging a command name into a remote command name,
and by three hand-maintained exception tables — is now written down once here.

This module lives in the core layer and must not import ``ableton_cli.commands``.
``command_specs`` reads this table, and ``command_specs`` is imported during
Typer app construction, so importing the commands package from here would make
the shared Typer app's initialisation order load-bearing. ``track_facets``
carries the same constraint for the same reason; ``tests/test_layering.py``
enforces it.

Adding a command means adding a row here. There is no fallback: a Typer command
with no row (or a row with no Typer command) fails
``tests/test_command_registry_matches_cli.py`` with the exact difference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SideEffectKind = Literal["read", "write", "destructive"]


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
class CommandDescriptor:
    """One public CLI command."""

    command_name: str
    #: Remote Script command this dispatches, or ``None`` for CLI-local commands.
    remote_command: str | None
    side_effect: SideEffectSpec


#: The declared side effect of a command. There is no default: a wrong guess
#: here silently widens ``--read-only`` or drops a confirmation prompt.
#:
#: These three constants are the only combinations in use. ``idempotent`` is
#: currently equivalent to "is a read"; individual commands that are in fact
#: idempotent writes should be promoted one at a time, with justification,
#: rather than in bulk.
_READ = SideEffectSpec(kind="read", idempotent=True, requires_confirmation=False)
_WRITE = SideEffectSpec(kind="write", idempotent=False, requires_confirmation=False)
_DESTRUCTIVE = SideEffectSpec(kind="destructive", idempotent=False, requires_confirmation=True)


def _d(command_name: str, remote_command: str | None, side_effect: SideEffectSpec):
    return CommandDescriptor(
        command_name=command_name,
        remote_command=remote_command,
        side_effect=side_effect,
    )


#: Every public command, sorted by name. ``remote_command`` is spelled out even
#: where it happens to equal the command name with separators swapped, so that
#: the mapping is greppable and a rename cannot silently repoint a command at a
#: handler that does not exist.
COMMAND_DESCRIPTORS: tuple[CommandDescriptor, ...] = (
    _d("arrangement clip create", "arrangement_clip_create", _WRITE),
    _d("arrangement clip delete", "arrangement_clip_delete", _DESTRUCTIVE),
    _d("arrangement clip file replace", "arrangement_clip_file_replace", _WRITE),
    _d("arrangement clip gain set", "arrangement_clip_gain_set", _WRITE),
    _d("arrangement clip list", "arrangement_clip_list", _READ),
    _d("arrangement clip loop set", "arrangement_clip_loop_set", _WRITE),
    _d("arrangement clip marker set", "arrangement_clip_marker_set", _WRITE),
    _d("arrangement clip notes add", "arrangement_clip_notes_add", _WRITE),
    _d("arrangement clip notes clear", "arrangement_clip_notes_clear", _DESTRUCTIVE),
    _d("arrangement clip notes get", "arrangement_clip_notes_get", _READ),
    _d(
        "arrangement clip notes import-browser",
        "arrangement_clip_notes_import_browser",
        _DESTRUCTIVE,
    ),
    _d("arrangement clip notes replace", "arrangement_clip_notes_replace", _DESTRUCTIVE),
    _d("arrangement clip props get", "arrangement_clip_props_get", _READ),
    _d("arrangement clip transpose set", "arrangement_clip_transpose_set", _WRITE),
    _d("arrangement clip warp get", "arrangement_clip_warp_get", _READ),
    _d("arrangement clip warp set", "arrangement_clip_warp_set", _WRITE),
    _d("arrangement from-session", "arrangement_from_session", _WRITE),
    _d("arrangement record start", "arrangement_record_start", _WRITE),
    _d("arrangement record stop", "arrangement_record_stop", _WRITE),
    _d("audio analyze", None, _WRITE),
    _d("audio asset add", None, _WRITE),
    _d("audio asset list", None, _READ),
    _d("audio asset remove", None, _WRITE),
    _d("audio beatgrid import", None, _WRITE),
    _d("audio groove extract", None, _WRITE),
    _d("audio loudness analyze", None, _WRITE),
    _d("audio reference compare", None, _WRITE),
    _d("audio sections import", None, _WRITE),
    _d("audio spectrum analyze", None, _WRITE),
    _d("audio stems list", None, _READ),
    _d("audio stems split", None, _WRITE),
    _d("audio transient analyze", None, _WRITE),
    _d("batch run", "execute_batch", _DESTRUCTIVE),
    _d("batch stream", None, _DESTRUCTIVE),
    _d("browser categories", "get_browser_categories", _READ),
    _d("browser item", "get_browser_item", _READ),
    _d("browser items", "get_browser_items", _READ),
    _d("browser items-at-path", "get_browser_items_at_path", _READ),
    _d("browser load", "load_instrument_or_effect", _WRITE),
    _d("browser load-drum-kit", "load_drum_kit", _WRITE),
    _d("browser search", "search_browser_items", _WRITE),
    _d("browser tree", "get_browser_tree", _WRITE),
    _d("clip active get", "clip_active_get", _READ),
    _d("clip active set", "clip_active_set", _WRITE),
    _d("clip create", "create_clip", _WRITE),
    _d("clip cut-to-drum-rack", "clip_cut_to_drum_rack", _DESTRUCTIVE),
    _d("clip duplicate", "clip_duplicate", _WRITE),
    _d("clip duplicate-many", "clip_duplicate", _WRITE),
    _d("clip envelope clear", "clip_envelope_clear", _DESTRUCTIVE),
    _d("clip envelope set", "clip_envelope_set", _DESTRUCTIVE),
    _d("clip envelope shape", None, _WRITE),
    _d("clip file path get", "clip_file_path_get", _READ),
    _d("clip file replace", "clip_file_replace", _DESTRUCTIVE),
    _d("clip fire", "fire_clip", _WRITE),
    _d("clip gain set", "clip_gain_set", _WRITE),
    _d("clip groove amount set", "clip_groove_amount_set", _WRITE),
    _d("clip groove clear", "clip_groove_clear", _DESTRUCTIVE),
    _d("clip groove get", "clip_groove_get", _READ),
    _d("clip groove set", "clip_groove_set", _WRITE),
    _d("clip loop set", "clip_loop_set", _WRITE),
    _d("clip marker set", "clip_marker_set", _WRITE),
    _d("clip name set", "set_clip_name", _WRITE),
    _d("clip name set-many", None, _WRITE),
    _d("clip notes add", "add_notes_to_clip", _WRITE),
    _d("clip notes apply-groove", None, _WRITE),
    _d("clip notes arpeggiate", None, _WRITE),
    _d("clip notes clear", "clear_clip_notes", _DESTRUCTIVE),
    _d("clip notes euclidean", None, _WRITE),
    _d("clip notes get", "get_clip_notes", _READ),
    _d("clip notes humanize", "clip_notes_humanize", _WRITE),
    _d("clip notes import-browser", "load_instrument_or_effect", _DESTRUCTIVE),
    _d("clip notes quantize", "clip_notes_quantize", _WRITE),
    _d("clip notes ratchet", None, _WRITE),
    _d("clip notes replace", "replace_clip_notes", _DESTRUCTIVE),
    _d("clip notes retrograde", None, _WRITE),
    _d("clip notes transpose", "clip_notes_transpose", _WRITE),
    _d("clip notes transpose-in-scale", None, _WRITE),
    _d("clip notes update", "update_clip_notes", _WRITE),
    _d("clip notes velocity-scale", "clip_notes_velocity_scale", _WRITE),
    _d("clip place-pattern", None, _WRITE),
    _d("clip props get", "clip_props_get", _READ),
    _d("clip stop", "stop_clip", _WRITE),
    _d("clip transpose set", "clip_transpose_set", _WRITE),
    _d("clip warp conform", None, _WRITE),
    _d("clip warp get", "clip_warp_get", _READ),
    _d("clip warp set", "clip_warp_set", _WRITE),
    _d("clip warp-marker add", "clip_warp_marker_add", _DESTRUCTIVE),
    _d("clip warp-marker list", "clip_warp_marker_list", _READ),
    _d("clip warp-marker move", "clip_warp_marker_move", _DESTRUCTIVE),
    _d("clip warp-marker remove", "clip_warp_marker_remove", _DESTRUCTIVE),
    _d("completion", None, _READ),
    _d("config init", None, _DESTRUCTIVE),
    _d("config set", None, _DESTRUCTIVE),
    _d("config show", None, _READ),
    _d("device chains list", "device_chains_list", _READ),
    _d("device macro list", "device_macro_list", _READ),
    _d("device macro set", "device_macro_set", _WRITE),
    _d("device parameter set", "set_device_parameter", _WRITE),
    _d("doctor", None, _READ),
    _d("effect auto-filter keys", "list_standard_effect_keys", _READ),
    _d("effect auto-filter observe", "observe_standard_effect_state", _READ),
    _d("effect auto-filter set", "set_standard_effect_parameter_safe", _WRITE),
    _d("effect compressor keys", "list_standard_effect_keys", _READ),
    _d("effect compressor observe", "observe_standard_effect_state", _READ),
    _d("effect compressor set", "set_standard_effect_parameter_safe", _WRITE),
    _d("effect eq8 keys", "list_standard_effect_keys", _READ),
    _d("effect eq8 observe", "observe_standard_effect_state", _READ),
    _d("effect eq8 set", "set_standard_effect_parameter_safe", _WRITE),
    _d("effect find", "find_effect_devices", _READ),
    _d("effect limiter keys", "list_standard_effect_keys", _READ),
    _d("effect limiter observe", "observe_standard_effect_state", _READ),
    _d("effect limiter set", "set_standard_effect_parameter_safe", _WRITE),
    _d("effect observe", "observe_effect_parameters", _READ),
    _d("effect parameter set", "set_effect_parameter_safe", _WRITE),
    _d("effect parameters list", "list_effect_parameters", _READ),
    _d("effect reverb keys", "list_standard_effect_keys", _READ),
    _d("effect reverb observe", "observe_standard_effect_state", _READ),
    _d("effect reverb set", "set_standard_effect_parameter_safe", _WRITE),
    _d("effect utility keys", "list_standard_effect_keys", _READ),
    _d("effect utility observe", "observe_standard_effect_state", _READ),
    _d("effect utility set", "set_standard_effect_parameter_safe", _WRITE),
    _d("install-remote-script", None, _DESTRUCTIVE),
    _d("install-skill", None, _DESTRUCTIVE),
    _d("master device delete", "master_device_delete", _DESTRUCTIVE),
    _d("master device load", "master_device_load", _WRITE),
    _d("master device move", "master_device_move", _WRITE),
    _d("master device parameter set", "master_device_parameter_set", _WRITE),
    _d("master device parameters list", "master_device_parameters_list", _READ),
    _d("master devices list", "master_devices_list", _READ),
    _d("master effect compressor keys", "master_effect_keys", _READ),
    _d("master effect compressor observe", "master_effect_observe", _READ),
    _d("master effect compressor set", "master_effect_set", _WRITE),
    _d("master effect eq8 keys", "master_effect_keys", _READ),
    _d("master effect eq8 observe", "master_effect_observe", _READ),
    _d("master effect eq8 set", "master_effect_set", _WRITE),
    _d("master effect limiter keys", "master_effect_keys", _READ),
    _d("master effect limiter observe", "master_effect_observe", _READ),
    _d("master effect limiter set", "master_effect_set", _WRITE),
    _d("master effect utility keys", "master_effect_keys", _READ),
    _d("master effect utility observe", "master_effect_observe", _READ),
    _d("master effect utility set", "master_effect_set", _WRITE),
    _d("master info", "master_info", _READ),
    _d("master panning get", "master_panning_get", _READ),
    _d("master panning set", "master_panning_set", _WRITE),
    _d("master volume get", "master_volume_get", _READ),
    _d("master volume set", "master_volume_set", _WRITE),
    _d("mixer crossfader get", "mixer_crossfader_get", _READ),
    _d("mixer crossfader set", "mixer_crossfader_set", _WRITE),
    _d("mixer cue-routing get", "mixer_cue_routing_get", _READ),
    _d("mixer cue-routing set", "mixer_cue_routing_set", _WRITE),
    _d("mixer cue-volume get", "mixer_cue_volume_get", _READ),
    _d("mixer cue-volume set", "mixer_cue_volume_set", _WRITE),
    _d("ping", "ping", _READ),
    _d("remix apply", None, _WRITE),
    _d("remix arrange", None, _WRITE),
    _d("remix device-chain apply", None, _WRITE),
    _d("remix export-plan", None, _WRITE),
    _d("remix generate bass", None, _WRITE),
    _d("remix generate chords", None, _WRITE),
    _d("remix generate drums", None, _WRITE),
    _d("remix import-assets", None, _WRITE),
    _d("remix init", None, _WRITE),
    _d("remix inspect", None, _WRITE),
    _d("remix mastering analyze", None, _WRITE),
    _d("remix mastering apply", None, _WRITE),
    _d("remix mastering plan", None, _WRITE),
    _d("remix mastering profile list", None, _READ),
    _d("remix mastering qa", None, _WRITE),
    _d("remix mastering reference add", None, _WRITE),
    _d("remix mastering reference list", None, _READ),
    _d("remix mastering reference remove", None, _WRITE),
    _d("remix mastering target set", None, _WRITE),
    _d("remix mix-macro", None, _WRITE),
    _d("remix plan", None, _WRITE),
    _d("remix qa", None, _WRITE),
    _d("remix set-target", None, _WRITE),
    _d("remix setup-mix", None, _WRITE),
    _d("remix setup-returns", None, _WRITE),
    _d("remix setup-sidechain", None, _WRITE),
    _d("remix setup-sound", None, _WRITE),
    _d("remix vocal-chop", None, _WRITE),
    _d("return-track mute get", "return_track_mute_get", _READ),
    _d("return-track mute set", "return_track_mute_set", _WRITE),
    _d("return-track solo get", "return_track_solo_get", _READ),
    _d("return-track solo set", "return_track_solo_set", _WRITE),
    _d("return-track volume get", "return_track_volume_get", _READ),
    _d("return-track volume set", "return_track_volume_set", _WRITE),
    _d("return-tracks list", "return_tracks_list", _READ),
    _d("scenes create", "create_scene", _WRITE),
    _d("scenes fire", "fire_scene", _WRITE),
    _d("scenes list", "scenes_list", _READ),
    _d("scenes move", "scenes_move", _WRITE),
    _d("scenes name set", "set_scene_name", _WRITE),
    _d("session capture", None, _WRITE),
    _d("session diff", None, _READ),
    _d("session events", None, _WRITE),
    _d("session info", "get_session_info", _READ),
    _d("session snapshot", "session_snapshot", _READ),
    _d("session stop-all-clips", "stop_all_clips", _WRITE),
    _d("session watch", None, _READ),
    _d("song export audio", "song_export_audio", _WRITE),
    _d("song info", "song_info", _READ),
    _d("song new", "song_new", _DESTRUCTIVE),
    _d("song redo", "song_redo", _DESTRUCTIVE),
    _d("song save", "song_save", _WRITE),
    _d("song undo", "song_undo", _DESTRUCTIVE),
    _d("synth drift keys", "list_standard_synth_keys", _READ),
    _d("synth drift observe", "observe_standard_synth_state", _READ),
    _d("synth drift set", "set_standard_synth_parameter_safe", _WRITE),
    _d("synth find", "find_synth_devices", _READ),
    _d("synth meld keys", "list_standard_synth_keys", _READ),
    _d("synth meld observe", "observe_standard_synth_state", _READ),
    _d("synth meld set", "set_standard_synth_parameter_safe", _WRITE),
    _d("synth observe", "observe_synth_parameters", _READ),
    _d("synth parameter set", "set_synth_parameter_safe", _WRITE),
    _d("synth parameters list", "list_synth_parameters", _READ),
    _d("synth wavetable keys", "list_standard_synth_keys", _READ),
    _d("synth wavetable observe", "observe_standard_synth_state", _READ),
    _d("synth wavetable set", "set_standard_synth_parameter_safe", _WRITE),
    _d("track arm get", "track_arm_get", _READ),
    _d("track arm set", "track_arm_set", _WRITE),
    _d("track info", "get_track_info", _READ),
    _d("track mute get", "track_mute_get", _READ),
    _d("track mute set", "track_mute_set", _WRITE),
    _d("track name set", "set_track_name", _WRITE),
    _d("track panning get", "track_panning_get", _READ),
    _d("track panning set", "track_panning_set", _WRITE),
    _d("track routing input get", "track_routing_input_get", _READ),
    _d("track routing input set", "track_routing_input_set", _WRITE),
    _d("track routing output get", "track_routing_output_get", _READ),
    _d("track routing output set", "track_routing_output_set", _WRITE),
    _d("track send get", "track_send_get", _READ),
    _d("track send set", "track_send_set", _WRITE),
    _d("track solo get", "track_solo_get", _READ),
    _d("track solo set", "track_solo_set", _WRITE),
    _d("track volume get", "track_volume_get", _READ),
    _d("track volume set", "track_volume_set", _WRITE),
    _d("tracks create audio", "create_audio_track", _WRITE),
    _d("tracks create midi", "create_midi_track", _WRITE),
    _d("tracks delete", "tracks_delete", _DESTRUCTIVE),
    _d("tracks list", "tracks_list", _READ),
    _d("transport play", "transport_play", _WRITE),
    _d("transport position get", "transport_position_get", _READ),
    _d("transport position set", "transport_position_set", _WRITE),
    _d("transport rewind", "transport_rewind", _WRITE),
    _d("transport stop", "transport_stop", _WRITE),
    _d("transport tempo get", "transport_tempo_get", _READ),
    _d("transport tempo set", "transport_tempo_set", _WRITE),
    _d("transport toggle", "transport_toggle", _WRITE),
    _d("wait-ready", None, _READ),
)

#: Remote commands the Remote Script serves that no CLI command dispatches.
#: They are part of the command set (and therefore of ``command_set_hash``)
#: because the Remote Script registers handlers for them: stable action aliases
#: kept for batch scripts, and the master-effect variants.
REMOTE_COMMAND_ALIASES: frozenset[str] = frozenset(
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


def _build_descriptor_map() -> dict[str, CommandDescriptor]:
    by_name: dict[str, CommandDescriptor] = {}
    for descriptor in COMMAND_DESCRIPTORS:
        if descriptor.command_name in by_name:
            raise AssertionError(
                f"duplicate command descriptor for {descriptor.command_name!r} "
                "in COMMAND_DESCRIPTORS"
            )
        by_name[descriptor.command_name] = descriptor
    return by_name


DESCRIPTOR_BY_COMMAND_NAME: dict[str, CommandDescriptor] = _build_descriptor_map()


def public_command_names() -> set[str]:
    return set(DESCRIPTOR_BY_COMMAND_NAME)


def descriptor_for(command_name: str) -> CommandDescriptor:
    descriptor = DESCRIPTOR_BY_COMMAND_NAME.get(command_name)
    if descriptor is None:
        raise KeyError(
            f"Command {command_name!r} is not declared. "
            "Add a row to COMMAND_DESCRIPTORS in command_registry.py."
        )
    return descriptor


@dataclass(frozen=True, slots=True)
class ClientParamSpec:
    """One parameter of a generated client method."""

    name: str
    #: Type annotation, as source text, copied verbatim into the generated file.
    annotation: str
    #: Default value as source text, or ``None`` when the parameter is required.
    default: str | None = None
    #: Key this parameter takes in the request payload, when it differs from
    #: the Python parameter name (``scenes_move`` sends ``from``/``to``, which
    #: are not usable as Python identifiers).
    key: str | None = None

    @property
    def payload_key(self) -> str:
        return self.key if self.key is not None else self.name


@dataclass(frozen=True, slots=True)
class ClientMethodSpec:
    """A client method whose whole body is one ``self._call``.

    Keyed by remote command because that is the real cardinality: several CLI
    commands can share one client method (all four ``master effect <type> keys``
    commands call ``master_effect_keys``), so this cannot hang off
    ``CommandDescriptor`` without duplicating a row per sharing command.

    Client methods that assemble arguments, branch, or post-process stay
    hand-written in the mixins; only the pass-through ones are described here.
    """

    #: Both the remote command name and the generated Python method name.
    remote_command: str
    params: tuple[ClientParamSpec, ...] = ()
    returns: str = "dict[str, Any]"


def _p(
    name: str, annotation: str, default: str | None = None, key: str | None = None
) -> ClientParamSpec:
    return ClientParamSpec(name=name, annotation=annotation, default=default, key=key)


def _m(
    remote_command: str,
    params: tuple[ClientParamSpec, ...] = (),
    returns: str = "dict[str, Any]",
) -> ClientMethodSpec:
    return ClientMethodSpec(remote_command=remote_command, params=params, returns=returns)


#: Every pass-through client method, sorted by name. Transcribed from the
#: hand-written mixins by AST, not by hand. ``tools/generate_client_methods.py``
#: turns this into ``client/_client_generated.py``.
CLIENT_METHOD_SPECS: tuple[ClientMethodSpec, ...] = (
    _m(
        "arrangement_clip_file_replace",
        (_p("track", "int"), _p("index", "int"), _p("audio_path", "str")),
    ),
    _m("arrangement_clip_gain_set", (_p("track", "int"), _p("index", "int"), _p("db", "float"))),
    _m(
        "arrangement_clip_loop_set",
        (
            _p("track", "int"),
            _p("index", "int"),
            _p("start", "float"),
            _p("end", "float"),
            _p("enabled", "bool"),
        ),
    ),
    _m(
        "arrangement_clip_marker_set",
        (
            _p("track", "int"),
            _p("index", "int"),
            _p("start_marker", "float"),
            _p("end_marker", "float"),
        ),
    ),
    _m("arrangement_clip_props_get", (_p("track", "int"), _p("index", "int"))),
    _m(
        "arrangement_clip_transpose_set",
        (_p("track", "int"), _p("index", "int"), _p("semitones", "int")),
    ),
    _m("arrangement_clip_warp_get", (_p("track", "int"), _p("index", "int"))),
    _m("arrangement_from_session", (_p("scenes", "list[dict[str, float]]"),)),
    _m("arrangement_record_start", ()),
    _m("arrangement_record_stop", ()),
    _m("clip_active_get", (_p("track", "int"), _p("clip", "int"))),
    _m("clip_active_set", (_p("track", "int"), _p("clip", "int"), _p("value", "bool"))),
    _m(
        "clip_envelope_set",
        (
            _p("track", "int"),
            _p("clip", "int"),
            _p("device_ref", "RefPayload"),
            _p("parameter_ref", "RefPayload"),
            _p("points", "list[dict[str, float]]"),
            _p("mode", "str", default="'replace'"),
        ),
    ),
    _m("clip_file_path_get", (_p("track", "int"), _p("clip", "int"))),
    _m("clip_file_replace", (_p("track", "int"), _p("clip", "int"), _p("audio_path", "str"))),
    _m("clip_gain_set", (_p("track", "int"), _p("clip", "int"), _p("db", "float"))),
    _m("clip_groove_amount_set", (_p("track", "int"), _p("clip", "int"), _p("value", "float"))),
    _m("clip_groove_clear", (_p("track", "int"), _p("clip", "int"))),
    _m("clip_groove_get", (_p("track", "int"), _p("clip", "int"))),
    _m("clip_groove_set", (_p("track", "int"), _p("clip", "int"), _p("target", "str"))),
    _m(
        "clip_loop_set",
        (
            _p("track", "int"),
            _p("clip", "int"),
            _p("start", "float"),
            _p("end", "float"),
            _p("enabled", "bool"),
        ),
    ),
    _m(
        "clip_marker_set",
        (
            _p("track", "int"),
            _p("clip", "int"),
            _p("start_marker", "float"),
            _p("end_marker", "float"),
        ),
    ),
    _m("clip_props_get", (_p("track", "int"), _p("clip", "int"))),
    _m("clip_transpose_set", (_p("track", "int"), _p("clip", "int"), _p("semitones", "int"))),
    _m("clip_warp_get", (_p("track", "int"), _p("clip", "int"))),
    _m("clip_warp_marker_list", (_p("track", "int"), _p("clip", "int"))),
    _m(
        "clip_warp_marker_move",
        (_p("track", "int"), _p("clip", "int"), _p("beat_time", "float"), _p("distance", "float")),
    ),
    _m(
        "clip_warp_marker_remove", (_p("track", "int"), _p("clip", "int"), _p("beat_time", "float"))
    ),
    _m("create_audio_track", (_p("index", "int", default="-1"),)),
    _m("create_clip", (_p("track", "int"), _p("clip", "int"), _p("length", "float"))),
    _m("create_midi_track", (_p("index", "int", default="-1"),)),
    _m("create_scene", (_p("index", "int"),)),
    _m("device_chains_list", (_p("track_ref", "RefPayload"), _p("device_ref", "RefPayload"))),
    _m("device_macro_list", (_p("track_ref", "RefPayload"), _p("device_ref", "RefPayload"))),
    _m(
        "device_macro_set",
        (
            _p("track_ref", "RefPayload"),
            _p("device_ref", "RefPayload"),
            _p("macro_index", "int"),
            _p("value", "float"),
        ),
    ),
    _m("execute_batch", (_p("steps", "list[dict[str, Any]]"),)),
    _m("fire_clip", (_p("track", "int"), _p("clip", "int"))),
    _m("fire_scene", (_p("scene", "int"),)),
    _m("get_browser_categories", (_p("category_type", "str", default="'all'"),)),
    _m(
        "get_browser_items",
        (
            _p("path", "str"),
            _p("item_type", "str", default="'all'"),
            _p("limit", "int", default="100"),
            _p("offset", "int", default="0"),
        ),
    ),
    _m("get_browser_items_at_path", (_p("path", "str"),)),
    _m("get_browser_tree", (_p("category_type", "str", default="'all'"),)),
    _m("get_session_info", (), returns="dict[str, object]"),
    _m("get_track_info", (_p("track_ref", "RefPayload"),)),
    _m("list_effect_parameters", (_p("track_ref", "RefPayload"), _p("device_ref", "RefPayload"))),
    _m("list_standard_effect_keys", (_p("effect_type", "str"),)),
    _m("list_standard_synth_keys", (_p("synth_type", "str"),)),
    _m("list_synth_parameters", (_p("track_ref", "RefPayload"), _p("device_ref", "RefPayload"))),
    _m("master_device_delete", (_p("device_index", "int"),)),
    _m("master_device_load", (_p("target", "str"), _p("position", "str"))),
    _m("master_device_move", (_p("device_index", "int"), _p("to_index", "int"))),
    _m(
        "master_device_parameter_set",
        (
            _p("device_ref", "dict[str, Any]"),
            _p("parameter_ref", "dict[str, Any]"),
            _p("value", "float"),
        ),
    ),
    _m("master_device_parameters_list", (_p("device_ref", "dict[str, Any]"),)),
    _m("master_devices_list", ()),
    _m("master_effect_keys", (_p("effect_type", "str"),)),
    _m("master_effect_observe", (_p("effect_type", "str"), _p("device_ref", "dict[str, Any]"))),
    _m(
        "master_effect_set",
        (
            _p("effect_type", "str"),
            _p("device_ref", "dict[str, Any]"),
            _p("parameter_ref", "dict[str, Any]"),
            _p("value", "float"),
        ),
    ),
    _m("master_info", ()),
    _m("master_panning_get", ()),
    _m("master_panning_set", (_p("value", "float"),)),
    _m("master_volume_get", ()),
    _m("master_volume_set", (_p("value", "float"),)),
    _m("mixer_crossfader_get", ()),
    _m("mixer_crossfader_set", (_p("value", "float"),)),
    _m("mixer_cue_routing_get", ()),
    _m("mixer_cue_routing_set", (_p("routing", "str"),)),
    _m("mixer_cue_volume_get", ()),
    _m("mixer_cue_volume_set", (_p("value", "float"),)),
    _m(
        "observe_effect_parameters", (_p("track_ref", "RefPayload"), _p("device_ref", "RefPayload"))
    ),
    _m(
        "observe_standard_effect_state",
        (_p("effect_type", "str"), _p("track_ref", "RefPayload"), _p("device_ref", "RefPayload")),
    ),
    _m(
        "observe_standard_synth_state",
        (_p("synth_type", "str"), _p("track_ref", "RefPayload"), _p("device_ref", "RefPayload")),
    ),
    _m("observe_synth_parameters", (_p("track_ref", "RefPayload"), _p("device_ref", "RefPayload"))),
    _m("ping", (), returns="dict[str, object]"),
    _m("return_track_mute_get", (_p("return_track", "int"),)),
    _m("return_track_mute_set", (_p("return_track", "int"), _p("value", "bool"))),
    _m("return_track_solo_get", (_p("return_track", "int"),)),
    _m("return_track_solo_set", (_p("return_track", "int"), _p("value", "bool"))),
    _m("return_track_volume_get", (_p("return_track", "int"),)),
    _m("return_track_volume_set", (_p("return_track", "int"), _p("value", "float"))),
    _m("return_tracks_list", ()),
    _m("scenes_list", ()),
    _m("scenes_move", (_p("from_index", "int", key="from"), _p("to_index", "int", key="to"))),
    _m("session_snapshot", (), returns="dict[str, object]"),
    _m("set_clip_name", (_p("track", "int"), _p("clip", "int"), _p("name", "str"))),
    _m("set_scene_name", (_p("scene", "int"), _p("name", "str"))),
    _m("set_tempo", (_p("tempo", "float"),), returns="dict[str, object]"),
    _m("set_track_name", (_p("track_ref", "RefPayload"), _p("name", "str"))),
    _m("song_export_audio", (_p("path", "str"),), returns="dict[str, object]"),
    _m("song_info", (), returns="dict[str, object]"),
    _m("song_new", (), returns="dict[str, object]"),
    _m("song_redo", (), returns="dict[str, object]"),
    _m("song_save", (_p("path", "str"),), returns="dict[str, object]"),
    _m("song_undo", (), returns="dict[str, object]"),
    _m("start_playback", (), returns="dict[str, object]"),
    _m("stop_all_clips", ()),
    _m("stop_clip", (_p("track", "int"), _p("clip", "int"))),
    _m("stop_playback", (), returns="dict[str, object]"),
    _m("track_arm_get", (_p("track_ref", "RefPayload"),)),
    _m("track_arm_set", (_p("track_ref", "RefPayload"), _p("value", "bool"))),
    _m("track_mute_get", (_p("track_ref", "RefPayload"),)),
    _m("track_mute_set", (_p("track_ref", "RefPayload"), _p("value", "bool"))),
    _m("track_panning_get", (_p("track_ref", "RefPayload"),)),
    _m("track_panning_set", (_p("track_ref", "RefPayload"), _p("value", "float"))),
    _m("track_routing_input_get", (_p("track_ref", "RefPayload"),)),
    _m(
        "track_routing_input_set",
        (
            _p("track_ref", "RefPayload"),
            _p("routing_type", "str"),
            _p("routing_channel", "str | None"),
        ),
    ),
    _m("track_routing_output_get", (_p("track_ref", "RefPayload"),)),
    _m(
        "track_routing_output_set",
        (_p("track_ref", "RefPayload"), _p("routing_type", "str"), _p("routing_channel", "str")),
    ),
    _m("track_send_get", (_p("track_ref", "RefPayload"), _p("send", "int"))),
    _m("track_send_set", (_p("track_ref", "RefPayload"), _p("send", "int"), _p("value", "float"))),
    _m("track_solo_get", (_p("track_ref", "RefPayload"),)),
    _m("track_solo_set", (_p("track_ref", "RefPayload"), _p("value", "bool"))),
    _m("track_volume_get", (_p("track_ref", "RefPayload"),)),
    _m("track_volume_set", (_p("track_ref", "RefPayload"), _p("value", "float"))),
    _m("tracks_delete", (_p("track", "int"),)),
    _m("tracks_list", ()),
    _m("transport_play", (), returns="dict[str, object]"),
    _m("transport_position_get", (), returns="dict[str, object]"),
    _m("transport_position_set", (_p("beats", "float"),), returns="dict[str, object]"),
    _m("transport_rewind", (), returns="dict[str, object]"),
    _m("transport_stop", (), returns="dict[str, object]"),
    _m("transport_tempo_get", (), returns="dict[str, object]"),
    _m("transport_tempo_set", (_p("bpm", "float"),), returns="dict[str, object]"),
    _m("transport_toggle", (), returns="dict[str, object]"),
)


def _build_client_method_map() -> dict[str, ClientMethodSpec]:
    by_name: dict[str, ClientMethodSpec] = {}
    for spec in CLIENT_METHOD_SPECS:
        if spec.remote_command in by_name:
            raise AssertionError(
                f"duplicate client method spec for {spec.remote_command!r} in CLIENT_METHOD_SPECS"
            )
        by_name[spec.remote_command] = spec
    return by_name


CLIENT_METHOD_SPEC_BY_NAME: dict[str, ClientMethodSpec] = _build_client_method_map()
