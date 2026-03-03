# Skill Actions Reference

Stable action names and CLI mappings for automation wrappers.

| Action | CLI command | Capability |
| --- | --- | --- |
| `ping` | `uv run ableton-cli --output json ping` | Check connectivity and protocol metadata. |
| `get_song_info` | `uv run ableton-cli --output json song info` | Read global song state such as tempo and transport status. |
| `song_new` | `uv run ableton-cli --output json song new` | Create a new Ableton Set when supported by Live API. |
| `song_save` | `uv run ableton-cli --output json song save --path <als>` | Save the current Ableton Set to a target path when supported. |
| `song_export_audio` | `uv run ableton-cli --output json song export audio --path <wav>` | Export session audio to a target path when supported. |
| `get_session_info` | `uv run ableton-cli --output json session info` | Read session view state and structure information. |
| `get_track_info` | `uv run ableton-cli --output json track info <track>` | Read one track details by index. |
| `play` | `uv run ableton-cli --output json transport play` | Start transport playback. |
| `stop` | `uv run ableton-cli --output json transport stop` | Stop transport playback. |
| `arrangement_record_start` | `uv run ableton-cli --output json arrangement record start` | Start arrangement recording when supported by Live API. |
| `arrangement_record_stop` | `uv run ableton-cli --output json arrangement record stop` | Stop arrangement recording when supported by Live API. |
| `set_tempo` | `uv run ableton-cli --output json transport tempo set <bpm>` | Update song tempo in BPM. |
| `transport_position_get` | `uv run ableton-cli --output json transport position get` | Read current transport beat/time position. |
| `transport_position_set` | `uv run ableton-cli --output json transport position set <beats>` | Move transport playhead to a beat position. |
| `transport_rewind` | `uv run ableton-cli --output json transport rewind` | Rewind transport playhead to beat 0. |
| `list_tracks` | `uv run ableton-cli --output json tracks list` | List all tracks and their basic properties. |
| `create_midi_track` | `uv run ableton-cli --output json tracks create midi [--index <index>]` | Insert a MIDI track at an index or append. |
| `create_audio_track` | `uv run ableton-cli --output json tracks create audio [--index <index>]` | Insert an audio track at an index or append. |
| `tracks_delete` | `uv run ableton-cli --output json tracks delete <track>` | Delete a track by index when supported by Live API. |
| `set_track_name` | `uv run ableton-cli --output json track name set <track> <name>` | Rename a track. |
| `set_track_volume` | `uv run ableton-cli --output json track volume set <track> <value>` | Set track volume in range 0.0 to 1.0. |
| `get_track_mute` | `uv run ableton-cli --output json track mute get <track>` | Read track mute state. |
| `set_track_mute` | `uv run ableton-cli --output json track mute set <track> <value>` | Update track mute state. |
| `get_track_solo` | `uv run ableton-cli --output json track solo get <track>` | Read track solo state. |
| `set_track_solo` | `uv run ableton-cli --output json track solo set <track> <value>` | Update track solo state. |
| `get_track_arm` | `uv run ableton-cli --output json track arm get <track>` | Read track arm state. |
| `set_track_arm` | `uv run ableton-cli --output json track arm set <track> <value>` | Update track arm state. |
| `get_track_panning` | `uv run ableton-cli --output json track panning get <track>` | Read track panning value. |
| `set_track_panning` | `uv run ableton-cli --output json track panning set <track> <value>` | Update track panning in range -1.0 to 1.0. |
| `create_clip` | `uv run ableton-cli --output json clip create <track> <clip> --length <beats>` | Create a clip in a slot with a target beat length. |
| `add_notes_to_clip` | `uv run ableton-cli --output json clip notes add <track> <clip> (--notes-json '<json-array>' | --notes-file <path>)` | Add MIDI notes to an existing clip slot. |
| `get_clip_notes` | `uv run ableton-cli --output json clip notes get <track> <clip> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]` | Read clip notes with optional time/pitch filters. |
| `clear_clip_notes` | `uv run ableton-cli --output json clip notes clear <track> <clip> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]` | Remove matching clip notes by optional time/pitch filters. |
| `replace_clip_notes` | `uv run ableton-cli --output json clip notes replace <track> <clip> (--notes-json '<json-array>' | --notes-file <path>) [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]` | Clear matching notes then add replacement notes. |
| `arrangement_clip_notes_add` | `uv run ableton-cli --output json arrangement clip notes add <track> <index> (--notes-json '<json-array>' | --notes-file <path>)` | Add MIDI notes to an arrangement clip by list index. |
| `arrangement_clip_notes_get` | `uv run ableton-cli --output json arrangement clip notes get <track> <index> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]` | Read arrangement clip notes with optional time/pitch filters. |
| `arrangement_clip_notes_clear` | `uv run ableton-cli --output json arrangement clip notes clear <track> <index> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]` | Remove matching arrangement clip notes by optional time/pitch filters. |
| `arrangement_clip_notes_replace` | `uv run ableton-cli --output json arrangement clip notes replace <track> <index> (--notes-json '<json-array>' | --notes-file <path>) [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]` | Clear matching arrangement notes then add replacements. |
| `arrangement_clip_notes_import_browser` | `uv run ableton-cli --output json arrangement clip notes import-browser <track> <index> <target> [--mode <replace|append>] [--import-length] [--import-groove]` | Import notes from a browser `.alc` item into an arrangement clip. |
| `arrangement_clip_delete` | `uv run ableton-cli --output json arrangement clip delete <track> [index] [--start <beat> --end <beat>] [--all]` | Delete arrangement clips by index, time range, or all mode. |
| `arrangement_from_session` | `uv run ableton-cli --output json arrangement from-session --scenes "0:24,1:48"` | Expand session scenes into Arrangement using explicit scene durations. |
| `clip_duplicate` | `uv run ableton-cli --output json clip duplicate <track> <src_clip> <dst_clip>` | Duplicate a clip into an empty destination slot. |
| `set_clip_name` | `uv run ableton-cli --output json clip name set <track> <clip> <name>` | Rename a clip. |
| `fire_clip` | `uv run ableton-cli --output json clip fire <track> <clip>` | Launch a clip slot. |
| `stop_clip` | `uv run ableton-cli --output json clip stop <track> <clip>` | Stop a playing clip slot. |
| `list_scenes` | `uv run ableton-cli --output json scenes list` | List scene indexes and names. |
| `create_scene` | `uv run ableton-cli --output json scenes create [--index <index>]` | Create a scene at an index or append. |
| `set_scene_name` | `uv run ableton-cli --output json scenes name set <scene> <name>` | Rename a scene. |
| `fire_scene` | `uv run ableton-cli --output json scenes fire <scene>` | Launch all clip slots on a scene row. |
| `scenes_move` | `uv run ableton-cli --output json scenes move <from> <to>` | Move a scene from one index to another when supported by Live API. |
| `stop_all_clips` | `uv run ableton-cli --output json session stop-all-clips` | Stop all currently playing clips in Session View. |
| `get_browser_tree` | `uv run ableton-cli --output json browser tree [category_type]` | Read browser tree by category filter. |
| `get_browser_items_at_path` | `uv run ableton-cli --output json browser items-at-path <path>` | List browser items at a specific path. |
| `get_browser_item` | `uv run ableton-cli --output json browser item <target>` | Get one browser item by URI or path target. |
| `get_browser_categories` | `uv run ableton-cli --output json browser categories [category_type]` | Read available browser categories. |
| `get_browser_items` | `uv run ableton-cli --output json browser items <path> [--item-type <all,folder,device,loadable>] [--limit <n>] [--offset <n>]` | List browser children with pagination and optional item-type filter. |
| `search_browser_items` | `uv run ableton-cli --output json browser search <query> [--path <path>] [--item-type <all,folder,device,loadable>] [--limit <n>] [--offset <n>] [--exact] [--case-sensitive]` | Search browser items by query across categories or a subtree path. |
| `load_instrument_or_effect` | `uv run ableton-cli --output json browser load <track> <target>` | Load a browser item by URI or path target onto a track. |
| `load_drum_kit` | `uv run ableton-cli --output json browser load-drum-kit <track> <rack_uri> (--kit-uri <uri> | --kit-path <path>)` | Load a drum rack and an explicitly selected kit onto a track. |
| `set_device_parameter` | `uv run ableton-cli --output json device parameter set <track> <device> <parameter> <value>` | Set a device parameter value by index. |
| `find_synth_devices` | `uv run ableton-cli --output json synth find [--track <track>] [--type <wavetable|drift|meld>]` | Find supported synth devices (Wavetable, Drift, Meld). |
| `list_synth_parameters` | `uv run ableton-cli --output json synth parameters list <track> <device>` | List synth parameters with safety metadata (min/max/enabled/quantized). |
| `set_synth_parameter_safe` | `uv run ableton-cli --output json synth parameter set <track> <device> <parameter> <value>` | Safely set a synth parameter by index with strict range validation. |
| `observe_synth_parameters` | `uv run ableton-cli --output json synth observe <track> <device>` | Capture one-shot synth parameter snapshot. |
| `list_standard_synth_keys` | `uv run ableton-cli --output json synth <wavetable|drift|meld> keys` | List stable wrapper keys for a standard synth type. |
| `set_standard_synth_parameter_safe` | `uv run ableton-cli --output json synth <wavetable|drift|meld> set <track> <device> <key> <value>` | Safely set a standard synth key resolved to native parameter index. |
| `observe_standard_synth_state` | `uv run ableton-cli --output json synth <wavetable|drift|meld> observe <track> <device>` | Capture one-shot wrapper state snapshot keyed by stable synth keys. |
| `find_effect_devices` | `uv run ableton-cli --output json effect find [--track <track>] [--type <eq8|limiter|compressor|auto_filter|reverb|utility>]` | Find supported effect devices (EQ Eight, Limiter, Compressor, Auto Filter, Reverb, Utility). |
| `list_effect_parameters` | `uv run ableton-cli --output json effect parameters list <track> <device>` | List effect parameters with safety metadata (min/max/enabled/quantized). |
| `set_effect_parameter_safe` | `uv run ableton-cli --output json effect parameter set <track> <device> <parameter> <value>` | Safely set an effect parameter by index with strict range validation. |
| `observe_effect_parameters` | `uv run ableton-cli --output json effect observe <track> <device>` | Capture one-shot effect parameter snapshot. |
| `list_standard_effect_keys` | `uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filter|reverb|utility> keys` | List stable wrapper keys for a standard effect type. |
| `set_standard_effect_parameter_safe` | `uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filter|reverb|utility> set <track> <device> <key> <value>` | Safely set a standard effect key resolved to native parameter index. |
| `observe_standard_effect_state` | `uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filter|reverb|utility> observe <track> <device>` | Capture one-shot wrapper state snapshot keyed by stable effect keys. |
| `execute_batch` | `uv run ableton-cli --output json batch run (--steps-file <path> | --steps-json '<json>' | --steps-stdin)` | Execute multiple remote commands atomically from JSON input. |

## CLI-only commands (not stable actions)

- `uv run ableton-cli doctor`: Validate host, port, and Remote Script installation state.
- `uv run ableton-cli install-remote-script --yes`: Install Remote Script files non-interactively.
- `uv run ableton-cli completion`: Print shell completion guidance.
- `uv run ableton-cli wait-ready`: Poll ping until Ableton Live becomes reachable.
- `uv run ableton-cli config init`: Create or update local config defaults.
- `uv run ableton-cli config show`: Print effective runtime configuration.
- `uv run ableton-cli config set <key> <value>`: Update one config key (`host`, `port`, `timeout_ms`, `protocol_version`).
- `uv run ableton-cli --protocol-version <n> ...`: Override config protocol version for one invocation.
- `uv run ableton-cli transport toggle`: Toggle play and stop state.
- `uv run ableton-cli transport tempo get`: Read current tempo only.
- `uv run ableton-cli track volume get <track>`: Read current track volume only.
- `uv run ableton-cli session snapshot`: Fetch song/session/tracks/scenes in one call.
- `uv run ableton-cli batch stream`: Execute one JSON request per stdin line and receive one JSON response line for low-latency repeated automation.
- `uv run ableton-cli clip notes quantize <track> <clip> --grid <fraction-or-beats> --strength <0.0-1.0>`: Quantize matching note start times.
- `uv run ableton-cli clip notes humanize <track> <clip> --timing <beats> --velocity <0-127>`: Humanize timing and velocity for matching notes.
- `uv run ableton-cli clip notes velocity-scale <track> <clip> --scale <float> --offset <int>`: Scale and offset note velocities for matching notes.
- `uv run ableton-cli clip notes transpose <track> <clip> --semitones <int>`: Transpose matching note pitches.
- `uv run ableton-cli clip groove get <track> <clip>`: Read groove assignment and amount from a clip.
- `uv run ableton-cli clip groove set <track> <clip> <target>`: Assign a `.agr` groove by browser path or URI.
- `uv run ableton-cli clip groove amount set <track> <clip> <0.0-1.0>`: Set groove amount on a clip.
- `uv run ableton-cli clip groove clear <track> <clip>`: Clear groove assignment from a clip.
- `uv run ableton-cli clip cut-to-drum-rack (--source-track <track> --source-clip <clip> | --source <uri-or-path>) (--grid <fraction-or-beats> | --slice-count <n>) [--target-track <track>] [--start-pad <pad>] [--create-trigger-clip --trigger-clip-slot <clip>]`: Slice audio source and map slices into Drum Rack pads.

Operational note: after `install-remote-script --yes`, reload Ableton's Control Surface assignment (`None` -> `AbletonCliRemote`) or restart Ableton Live to apply updated Remote Script code.

Operational note: verify the active Remote Script via `uv run ableton-cli --output json ping` (`result.remote_script_version`, `result.supported_commands`) before troubleshooting command behavior.

Operational note: run `uv run ableton-cli doctor` to validate protocol/capability integrity when compatibility issues are suspected.

Operational note: when passing a negative positional number, use `--` before the value (for example, `track panning set 0 -- -0.25`, `effect parameter set 0 0 7 -- -2.0`).

Operational note: standard wrapper commands (`synth <type> ...`, `effect <type> ...`) intentionally fail if required parameter-name keys are missing. If you see `Missing required standard ... keys`, switch to generic indexed commands:
- `uv run ableton-cli --output json effect parameters list <track> <device>`
- `uv run ableton-cli --output json effect parameter set <track> <device> <parameter> <value>`
