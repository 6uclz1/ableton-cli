from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StableActionMapping:
    action: str
    command: str
    capability: str


STABLE_ACTION_MAPPINGS: tuple[StableActionMapping, ...] = (
    StableActionMapping(
        action="ping",
        command="uv run ableton-cli --output json ping",
        capability="Check connectivity and protocol metadata.",
    ),
    StableActionMapping(
        action="get_song_info",
        command="uv run ableton-cli --output json song info",
        capability="Read global song state such as tempo and transport status.",
    ),
    StableActionMapping(
        action="song_new",
        command="uv run ableton-cli --output json song new",
        capability="Create a new Ableton Set when supported by Live API.",
    ),
    StableActionMapping(
        action="song_undo",
        command="uv run ableton-cli --output json song undo",
        capability="Undo the most recent Ableton operation when supported by Live API.",
    ),
    StableActionMapping(
        action="song_redo",
        command="uv run ableton-cli --output json song redo",
        capability="Redo the most recently undone Ableton operation when supported by Live API.",
    ),
    StableActionMapping(
        action="song_save",
        command="uv run ableton-cli --output json song save --path <als>",
        capability="Save the current Ableton Set to a target path when supported.",
    ),
    StableActionMapping(
        action="song_export_audio",
        command="uv run ableton-cli --output json song export audio --path <wav>",
        capability="Export session audio to a target path when supported.",
    ),
    StableActionMapping(
        action="get_session_info",
        command="uv run ableton-cli --output json session info",
        capability="Read session view state and structure information.",
    ),
    StableActionMapping(
        action="get_track_info",
        command="uv run ableton-cli --output json track info --track-index <track>",
        capability="Read one track details by selector.",
    ),
    StableActionMapping(
        action="play",
        command="uv run ableton-cli --output json transport play",
        capability="Start transport playback.",
    ),
    StableActionMapping(
        action="stop",
        command="uv run ableton-cli --output json transport stop",
        capability="Stop transport playback.",
    ),
    StableActionMapping(
        action="arrangement_record_start",
        command="uv run ableton-cli --output json arrangement record start",
        capability="Start arrangement recording when supported by Live API.",
    ),
    StableActionMapping(
        action="arrangement_record_stop",
        command="uv run ableton-cli --output json arrangement record stop",
        capability="Stop arrangement recording when supported by Live API.",
    ),
    StableActionMapping(
        action="set_tempo",
        command="uv run ableton-cli --output json transport tempo set <bpm>",
        capability="Update song tempo in BPM.",
    ),
    StableActionMapping(
        action="transport_position_get",
        command="uv run ableton-cli --output json transport position get",
        capability="Read current transport beat/time position.",
    ),
    StableActionMapping(
        action="transport_position_set",
        command="uv run ableton-cli --output json transport position set <beats>",
        capability="Move transport playhead to a beat position.",
    ),
    StableActionMapping(
        action="transport_rewind",
        command="uv run ableton-cli --output json transport rewind",
        capability="Rewind transport playhead to beat 0.",
    ),
    StableActionMapping(
        action="list_tracks",
        command="uv run ableton-cli --output json tracks list",
        capability="List all tracks and their basic properties.",
    ),
    StableActionMapping(
        action="create_midi_track",
        command="uv run ableton-cli --output json tracks create midi [--index <index>]",
        capability="Insert a MIDI track at an index or append.",
    ),
    StableActionMapping(
        action="create_audio_track",
        command="uv run ableton-cli --output json tracks create audio [--index <index>]",
        capability="Insert an audio track at an index or append.",
    ),
    StableActionMapping(
        action="tracks_delete",
        command="uv run ableton-cli --output json tracks delete <track>",
        capability="Delete a track by index when supported by Live API.",
    ),
    StableActionMapping(
        action="set_track_name",
        command="uv run ableton-cli --output json track name set <name> --track-index <track>",
        capability="Rename a track.",
    ),
    StableActionMapping(
        action="set_track_volume",
        command="uv run ableton-cli --output json track volume set <value> --track-index <track>",
        capability="Set track volume in range 0.0 to 1.0.",
    ),
    StableActionMapping(
        action="get_track_mute",
        command="uv run ableton-cli --output json track mute get --track-index <track>",
        capability="Read track mute state.",
    ),
    StableActionMapping(
        action="set_track_mute",
        command="uv run ableton-cli --output json track mute set <value> --track-index <track>",
        capability="Update track mute state.",
    ),
    StableActionMapping(
        action="get_track_solo",
        command="uv run ableton-cli --output json track solo get --track-index <track>",
        capability="Read track solo state.",
    ),
    StableActionMapping(
        action="set_track_solo",
        command="uv run ableton-cli --output json track solo set <value> --track-index <track>",
        capability="Update track solo state.",
    ),
    StableActionMapping(
        action="get_track_arm",
        command="uv run ableton-cli --output json track arm get --track-index <track>",
        capability="Read track arm state.",
    ),
    StableActionMapping(
        action="set_track_arm",
        command="uv run ableton-cli --output json track arm set <value> --track-index <track>",
        capability="Update track arm state.",
    ),
    StableActionMapping(
        action="get_track_panning",
        command="uv run ableton-cli --output json track panning get --track-index <track>",
        capability="Read track panning value.",
    ),
    StableActionMapping(
        action="set_track_panning",
        command="uv run ableton-cli --output json track panning set <value> --track-index <track>",
        capability="Update track panning in range -1.0 to 1.0.",
    ),
    StableActionMapping(
        action="get_track_send",
        command="uv run ableton-cli --output json track send get <send> --track-index <track>",
        capability="Read one track send level by 0-based send index.",
    ),
    StableActionMapping(
        action="set_track_send",
        command=(
            "uv run ableton-cli --output json track send set <send> <value> --track-index <track>"
        ),
        capability="Update one track send level in range 0.0 to 1.0.",
    ),
    StableActionMapping(
        action="list_return_tracks",
        command="uv run ableton-cli --output json return-tracks list",
        capability="List all return tracks and their mixer state.",
    ),
    StableActionMapping(
        action="set_return_track_volume",
        command="uv run ableton-cli --output json return-track volume set <return-track> <value>",
        capability="Update one return-track volume in range 0.0 to 1.0.",
    ),
    StableActionMapping(
        action="get_master_info",
        command="uv run ableton-cli --output json master info",
        capability="Read master track name, volume, and panning.",
    ),
    StableActionMapping(
        action="list_master_devices",
        command="uv run ableton-cli --output json master devices list",
        capability="List master track devices and parameters.",
    ),
    StableActionMapping(
        action="set_mixer_crossfader",
        command="uv run ableton-cli --output json mixer crossfader set <value>",
        capability="Update mixer crossfader position in range -1.0 to 1.0.",
    ),
    StableActionMapping(
        action="set_mixer_cue_routing",
        command="uv run ableton-cli --output json mixer cue-routing set <routing>",
        capability="Update cue routing using an exact routing name.",
    ),
    StableActionMapping(
        action="get_track_routing_input",
        command="uv run ableton-cli --output json track routing input get --track-index <track>",
        capability="Read current and available input routing for one track.",
    ),
    StableActionMapping(
        action="set_track_routing_output",
        command=(
            "uv run ableton-cli --output json track routing output set --track-index <track> "
            "--type <routing-type> --channel <routing-channel>"
        ),
        capability="Update output routing using exact type and channel names.",
    ),
    StableActionMapping(
        action="create_clip",
        command="uv run ableton-cli --output json clip create <track> <clip> --length <beats>",
        capability="Create a clip in a slot with a target beat length.",
    ),
    StableActionMapping(
        action="add_notes_to_clip",
        command=(
            "uv run ableton-cli --output json clip notes add <track> <clip> (--notes-js"
            "on '<json-array>' | --notes-file <path>)"
        ),
        capability="Add MIDI notes to an existing clip slot.",
    ),
    StableActionMapping(
        action="get_clip_notes",
        command=(
            "uv run ableton-cli --output json clip notes get <track> <clip> [--start-ti"
            "me <beats>] [--end-time <beats>] [--pitch <midi>]"
        ),
        capability="Read clip notes with optional time/pitch filters.",
    ),
    StableActionMapping(
        action="clear_clip_notes",
        command=(
            "uv run ableton-cli --output json clip notes clear <track> <clip> [--start-"
            "time <beats>] [--end-time <beats>] [--pitch <midi>]"
        ),
        capability="Remove matching clip notes by optional time/pitch filters.",
    ),
    StableActionMapping(
        action="replace_clip_notes",
        command=(
            "uv run ableton-cli --output json clip notes replace <track> <clip> (--note"
            "s-json '<json-array>' | --notes-file <path>) [--start-time <beats>] [--end"
            "-time <beats>] [--pitch <midi>]"
        ),
        capability="Clear matching notes then add replacement notes.",
    ),
    StableActionMapping(
        action="arrangement_clip_notes_add",
        command=(
            "uv run ableton-cli --output json arrangement clip notes add <track> <index"
            "> (--notes-json '<json-array>' | --notes-file <path>)"
        ),
        capability="Add MIDI notes to an arrangement clip by list index.",
    ),
    StableActionMapping(
        action="arrangement_clip_notes_get",
        command=(
            "uv run ableton-cli --output json arrangement clip notes get <track> <index"
            "> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]"
        ),
        capability="Read arrangement clip notes with optional time/pitch filters.",
    ),
    StableActionMapping(
        action="arrangement_clip_notes_clear",
        command=(
            "uv run ableton-cli --output json arrangement clip notes clear <track> <ind"
            "ex> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]"
        ),
        capability="Remove matching arrangement clip notes by optional time/pitch filters.",
    ),
    StableActionMapping(
        action="arrangement_clip_notes_replace",
        command=(
            "uv run ableton-cli --output json arrangement clip notes replace <track> <i"
            "ndex> (--notes-json '<json-array>' | --notes-file <path>) [--start-time <b"
            "eats>] [--end-time <beats>] [--pitch <midi>]"
        ),
        capability="Clear matching arrangement notes then add replacements.",
    ),
    StableActionMapping(
        action="arrangement_clip_notes_import_browser",
        command=(
            "uv run ableton-cli --output json arrangement clip notes import-browser <tr"
            "ack> <index> <target> [--mode <replace|append>] [--import-length] [--impor"
            "t-groove]"
        ),
        capability="Import notes from a browser `.alc` item into an arrangement clip.",
    ),
    StableActionMapping(
        action="arrangement_clip_delete",
        command=(
            "uv run ableton-cli --output json arrangement clip delete <track> [index] ["
            "--start <beat> --end <beat>] [--all]"
        ),
        capability="Delete arrangement clips by index, time range, or all mode.",
    ),
    StableActionMapping(
        action="arrangement_from_session",
        command='uv run ableton-cli --output json arrangement from-session --scenes "0:24,1:48"',
        capability="Expand session scenes into Arrangement using explicit scene durations.",
    ),
    StableActionMapping(
        action="clip_duplicate",
        command="uv run ableton-cli --output json clip duplicate <track> <src_clip> <dst_clip>",
        capability="Duplicate a clip into an empty destination slot.",
    ),
    StableActionMapping(
        action="set_clip_name",
        command="uv run ableton-cli --output json clip name set <track> <clip> <name>",
        capability="Rename a clip.",
    ),
    StableActionMapping(
        action="fire_clip",
        command="uv run ableton-cli --output json clip fire <track> <clip>",
        capability="Launch a clip slot.",
    ),
    StableActionMapping(
        action="stop_clip",
        command="uv run ableton-cli --output json clip stop <track> <clip>",
        capability="Stop a playing clip slot.",
    ),
    StableActionMapping(
        action="list_scenes",
        command="uv run ableton-cli --output json scenes list",
        capability="List scene indexes and names.",
    ),
    StableActionMapping(
        action="create_scene",
        command="uv run ableton-cli --output json scenes create [--index <index>]",
        capability="Create a scene at an index or append.",
    ),
    StableActionMapping(
        action="set_scene_name",
        command="uv run ableton-cli --output json scenes name set <scene> <name>",
        capability="Rename a scene.",
    ),
    StableActionMapping(
        action="fire_scene",
        command="uv run ableton-cli --output json scenes fire <scene>",
        capability="Launch all clip slots on a scene row.",
    ),
    StableActionMapping(
        action="scenes_move",
        command="uv run ableton-cli --output json scenes move <from> <to>",
        capability="Move a scene from one index to another when supported by Live API.",
    ),
    StableActionMapping(
        action="stop_all_clips",
        command="uv run ableton-cli --output json session stop-all-clips",
        capability="Stop all currently playing clips in Session View.",
    ),
    StableActionMapping(
        action="get_browser_tree",
        command="uv run ableton-cli --output json browser tree [category_type]",
        capability="Read browser tree by category filter.",
    ),
    StableActionMapping(
        action="get_browser_items_at_path",
        command="uv run ableton-cli --output json browser items-at-path <path>",
        capability="List browser items at a specific path.",
    ),
    StableActionMapping(
        action="get_browser_item",
        command="uv run ableton-cli --output json browser item <target>",
        capability="Get one browser item by URI or path target.",
    ),
    StableActionMapping(
        action="get_browser_categories",
        command="uv run ableton-cli --output json browser categories [category_type]",
        capability="Read available browser categories.",
    ),
    StableActionMapping(
        action="get_browser_items",
        command=(
            "uv run ableton-cli --output json browser items <path> [--item-type <all,fo"
            "lder,device,loadable>] [--limit <n>] [--offset <n>]"
        ),
        capability="List browser children with pagination and optional item-type filter.",
    ),
    StableActionMapping(
        action="search_browser_items",
        command=(
            "uv run ableton-cli --output json browser search <query> [--path <path>] [-"
            "-item-type <all,folder,device,loadable>] [--limit <n>] [--offset <n>] [--e"
            "xact] [--case-sensitive]"
        ),
        capability="Search browser items by query across categories or a subtree path.",
    ),
    StableActionMapping(
        action="load_instrument_or_effect",
        command="uv run ableton-cli --output json browser load <track> <target>",
        capability="Load a browser item by URI or path target onto a track.",
    ),
    StableActionMapping(
        action="load_drum_kit",
        command=(
            "uv run ableton-cli --output json browser load-drum-kit <track> <rack_uri> "
            "(--kit-uri <uri> | --kit-path <path>)"
        ),
        capability="Load a drum rack and an explicitly selected kit onto a track.",
    ),
    StableActionMapping(
        action="set_device_parameter",
        command=(
            "uv run ableton-cli --output json device parameter set <value> --track-index <track> "
            "--device-index <device> --parameter-index <parameter>"
        ),
        capability="Set a device parameter value by selector.",
    ),
    StableActionMapping(
        action="find_synth_devices",
        command=(
            "uv run ableton-cli --output json synth find [--track <track>] [--type <wav"
            "etable|drift|meld>]"
        ),
        capability="Find supported synth devices (Wavetable, Drift, Meld).",
    ),
    StableActionMapping(
        action="list_synth_parameters",
        command=(
            "uv run ableton-cli --output json synth parameters list --track-index <track> "
            "--device-index <device>"
        ),
        capability="List synth parameters with safety metadata and stable refs.",
    ),
    StableActionMapping(
        action="set_synth_parameter_safe",
        command=(
            "uv run ableton-cli --output json synth parameter set <value> --track-index <track> "
            "--device-index <device> --parameter-index <parameter>"
        ),
        capability="Safely set a synth parameter by selector with strict range validation.",
    ),
    StableActionMapping(
        action="observe_synth_parameters",
        command=(
            "uv run ableton-cli --output json synth observe --track-index <track> "
            "--device-index <device>"
        ),
        capability="Capture one-shot synth parameter snapshot.",
    ),
    StableActionMapping(
        action="list_standard_synth_keys",
        command="uv run ableton-cli --output json synth <wavetable|drift|meld> keys",
        capability="List stable wrapper keys for a standard synth type.",
    ),
    StableActionMapping(
        action="set_standard_synth_parameter_safe",
        command=(
            "uv run ableton-cli --output json synth <wavetable|drift|meld> set <value> "
            "--track-index <track> --device-index <device> --parameter-key <key>"
        ),
        capability="Safely set a standard synth key resolved to native parameter index.",
    ),
    StableActionMapping(
        action="observe_standard_synth_state",
        command=(
            "uv run ableton-cli --output json synth <wavetable|drift|meld> observe "
            "--track-index <track> --device-index <device>"
        ),
        capability="Capture one-shot wrapper state snapshot keyed by stable synth keys.",
    ),
    StableActionMapping(
        action="find_effect_devices",
        command=(
            "uv run ableton-cli --output json effect find [--track <track>] [--type <eq"
            "8|limiter|compressor|auto_filter|reverb|utility>]"
        ),
        capability=(
            "Find supported effect devices (EQ Eight, Limiter, Compressor, Auto Filter,"
            " Reverb, Utility)."
        ),
    ),
    StableActionMapping(
        action="list_effect_parameters",
        command=(
            "uv run ableton-cli --output json effect parameters list --track-index <track> "
            "--device-index <device>"
        ),
        capability="List effect parameters with safety metadata and stable refs.",
    ),
    StableActionMapping(
        action="set_effect_parameter_safe",
        command=(
            "uv run ableton-cli --output json effect parameter set <value> --track-index <track> "
            "--device-index <device> --parameter-index <parameter>"
        ),
        capability="Safely set an effect parameter by selector with strict range validation.",
    ),
    StableActionMapping(
        action="observe_effect_parameters",
        command=(
            "uv run ableton-cli --output json effect observe --track-index <track> "
            "--device-index <device>"
        ),
        capability="Capture one-shot effect parameter snapshot.",
    ),
    StableActionMapping(
        action="list_standard_effect_keys",
        command=(
            "uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filte"
            "r|reverb|utility> keys"
        ),
        capability="List stable wrapper keys for a standard effect type.",
    ),
    StableActionMapping(
        action="set_standard_effect_parameter_safe",
        command=(
            "uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filte"
            "r|reverb|utility> set <value> --track-index <track> --device-index <device> "
            "--parameter-key <key>"
        ),
        capability="Safely set a standard effect key resolved to native parameter index.",
    ),
    StableActionMapping(
        action="observe_standard_effect_state",
        command=(
            "uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filte"
            "r|reverb|utility> observe --track-index <track> --device-index <device>"
        ),
        capability="Capture one-shot wrapper state snapshot keyed by stable effect keys.",
    ),
    StableActionMapping(
        action="execute_batch",
        command=(
            "uv run ableton-cli --output json batch run (--steps-file <path> | --steps-"
            "json '<json>' | --steps-stdin)"
        ),
        capability="Execute multiple remote commands atomically from JSON input.",
    ),
)


def stable_action_names() -> tuple[str, ...]:
    return tuple(item.action for item in STABLE_ACTION_MAPPINGS)


def stable_action_command_map() -> dict[str, str]:
    return {item.action: item.command for item in STABLE_ACTION_MAPPINGS}


def stable_action_capability_map() -> dict[str, str]:
    return {item.action: item.capability for item in STABLE_ACTION_MAPPINGS}
