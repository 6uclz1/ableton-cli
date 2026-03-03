from __future__ import annotations

import hashlib
from typing import Any

from .errors import AppError, ExitCode

_REQUIRED_REMOTE_COMMANDS = frozenset(
    {
        "ping",
        "song_info",
        "song_new",
        "song_save",
        "song_export_audio",
        "get_session_info",
        "session_snapshot",
        "get_track_info",
        "tracks_list",
        "create_midi_track",
        "create_audio_track",
        "set_track_name",
        "transport_play",
        "transport_stop",
        "transport_toggle",
        "start_playback",
        "stop_playback",
        "transport_tempo_get",
        "transport_tempo_set",
        "transport_position_get",
        "transport_position_set",
        "transport_rewind",
        "set_tempo",
        "track_volume_get",
        "track_volume_set",
        "track_mute_get",
        "track_mute_set",
        "track_solo_get",
        "track_solo_set",
        "track_arm_get",
        "track_arm_set",
        "track_panning_get",
        "track_panning_set",
        "create_clip",
        "add_notes_to_clip",
        "get_clip_notes",
        "clear_clip_notes",
        "replace_clip_notes",
        "clip_notes_quantize",
        "clip_notes_humanize",
        "clip_notes_velocity_scale",
        "clip_notes_transpose",
        "clip_groove_get",
        "clip_groove_set",
        "clip_groove_amount_set",
        "clip_groove_clear",
        "set_clip_name",
        "fire_clip",
        "stop_clip",
        "clip_active_get",
        "clip_active_set",
        "clip_duplicate",
        "clip_cut_to_drum_rack",
        "load_instrument_or_effect",
        "get_browser_tree",
        "get_browser_items_at_path",
        "get_browser_item",
        "get_browser_categories",
        "get_browser_items",
        "search_browser_items",
        "load_drum_kit",
        "scenes_list",
        "create_scene",
        "set_scene_name",
        "fire_scene",
        "scenes_move",
        "stop_all_clips",
        "arrangement_record_start",
        "arrangement_record_stop",
        "arrangement_clip_create",
        "arrangement_clip_list",
        "arrangement_clip_notes_add",
        "arrangement_clip_notes_get",
        "arrangement_clip_notes_clear",
        "arrangement_clip_notes_replace",
        "arrangement_clip_notes_import_browser",
        "arrangement_clip_delete",
        "arrangement_from_session",
        "tracks_delete",
        "execute_batch",
        "set_device_parameter",
        "find_synth_devices",
        "list_synth_parameters",
        "set_synth_parameter_safe",
        "observe_synth_parameters",
        "list_standard_synth_keys",
        "set_standard_synth_parameter_safe",
        "observe_standard_synth_state",
        "find_effect_devices",
        "list_effect_parameters",
        "set_effect_parameter_safe",
        "observe_effect_parameters",
        "list_standard_effect_keys",
        "set_standard_effect_parameter_safe",
        "observe_standard_effect_state",
    }
)

_READ_ONLY_REMOTE_COMMANDS = frozenset(
    {
        "ping",
        "song_info",
        "get_session_info",
        "session_snapshot",
        "get_track_info",
        "tracks_list",
        "transport_tempo_get",
        "transport_position_get",
        "track_volume_get",
        "track_mute_get",
        "track_solo_get",
        "track_arm_get",
        "track_panning_get",
        "arrangement_clip_list",
        "arrangement_clip_notes_get",
        "get_clip_notes",
        "clip_active_get",
        "clip_groove_get",
        "get_browser_tree",
        "get_browser_items_at_path",
        "get_browser_item",
        "get_browser_categories",
        "get_browser_items",
        "search_browser_items",
        "scenes_list",
        "find_synth_devices",
        "list_synth_parameters",
        "observe_synth_parameters",
        "list_standard_synth_keys",
        "observe_standard_synth_state",
        "find_effect_devices",
        "list_effect_parameters",
        "observe_effect_parameters",
        "list_standard_effect_keys",
        "observe_standard_effect_state",
    }
)


def required_remote_commands() -> set[str]:
    return set(_REQUIRED_REMOTE_COMMANDS)


def read_only_remote_commands() -> set[str]:
    return set(_READ_ONLY_REMOTE_COMMANDS)


def compute_command_set_hash(commands: list[str] | set[str]) -> str:
    normalized = sorted(set(commands))
    digest = hashlib.sha256()
    digest.update("\n".join(normalized).encode("utf-8"))
    return digest.hexdigest()


def parse_supported_commands(ping_payload: dict[str, Any]) -> set[str]:
    raw_commands = ping_payload.get("supported_commands")
    if not isinstance(raw_commands, list):
        raise AppError(
            error_code="REMOTE_SCRIPT_INCOMPATIBLE",
            message="Remote Script ping payload is missing supported_commands",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    commands: set[str] = set()
    for index, value in enumerate(raw_commands):
        if not isinstance(value, str) or not value.strip():
            raise AppError(
                error_code="REMOTE_SCRIPT_INCOMPATIBLE",
                message=f"supported_commands[{index}] must be a non-empty string",
                hint="Reinstall Remote Script and restart Ableton Live.",
                exit_code=ExitCode.PROTOCOL_MISMATCH,
            )
        commands.add(value)

    if not commands:
        raise AppError(
            error_code="REMOTE_SCRIPT_INCOMPATIBLE",
            message="Remote Script reported no supported commands",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    remote_hash = ping_payload.get("command_set_hash")
    if not isinstance(remote_hash, str) or not remote_hash.strip():
        raise AppError(
            error_code="REMOTE_SCRIPT_INCOMPATIBLE",
            message="Remote Script ping payload is missing command_set_hash",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )
    expected_hash = compute_command_set_hash(commands)
    if remote_hash != expected_hash:
        raise AppError(
            error_code="REMOTE_SCRIPT_INCOMPATIBLE",
            message="Remote Script command_set_hash does not match supported_commands",
            hint="Reinstall Remote Script and restart Ableton Live.",
            exit_code=ExitCode.PROTOCOL_MISMATCH,
        )

    return commands


def missing_required_commands(supported_commands: set[str]) -> list[str]:
    return sorted(_REQUIRED_REMOTE_COMMANDS.difference(supported_commands))
