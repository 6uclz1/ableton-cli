---
name: ableton-cli
description: Control and inspect Ableton Live with ableton-cli in non-interactive workflows. Use when an agent or script needs deterministic setup checks, transport control, track and clip operations, browser loading, and stable JSON command mappings.
---

# Ableton Live Control with ableton-cli

## Quick start

```bash
uv run ableton-cli doctor
uv run ableton-cli ping
uv run ableton-cli song info
uv run ableton-cli transport play
uv run ableton-cli transport stop
```

## Commands

### Setup / Diagnostics

```bash
uv run ableton-cli doctor
uv run ableton-cli install-remote-script --yes
uv run ableton-cli install-remote-script --dry-run
uv run ableton-cli install-skill --yes
uv run ableton-cli install-skill --target claude --yes
uv run ableton-cli install-skill --dry-run
uv run ableton-cli ping
uv run ableton-cli wait-ready
```

After `install-remote-script --yes`, if behavior does not change immediately, reload the control surface in Ableton Preferences (`None` -> `AbletonCliRemote`) or restart Ableton Live.

To verify that the latest Remote Script is active, run `uv run ableton-cli --output json ping` and confirm:
- `result.remote_script_version` is the expected version
- `result.supported_commands` includes the newly added command names

### Song / Session

```bash
uv run ableton-cli song info
uv run ableton-cli song new
uv run ableton-cli song undo
uv run ableton-cli song redo
uv run ableton-cli song save --path /tmp/demo.als
uv run ableton-cli song export audio --path /tmp/demo.wav
uv run ableton-cli session info
uv run ableton-cli session snapshot
uv run ableton-cli session diff --from ./snapshot-before.json --to ./snapshot-after.json
uv run ableton-cli session stop-all-clips
```

### Tracks

```bash
uv run ableton-cli tracks list
uv run ableton-cli tracks create midi
uv run ableton-cli tracks create midi --index 1
uv run ableton-cli tracks create audio
uv run ableton-cli tracks create audio --index 1
uv run ableton-cli tracks delete 2
```

### Transport

```bash
uv run ableton-cli transport play
uv run ableton-cli transport stop
uv run ableton-cli transport toggle
uv run ableton-cli transport tempo get
uv run ableton-cli transport tempo set 128
uv run ableton-cli transport position get
uv run ableton-cli transport position set 32
uv run ableton-cli transport rewind
```

### Arrangement

```bash
uv run ableton-cli arrangement record start
uv run ableton-cli arrangement record stop
uv run ableton-cli arrangement clip create 0 --start 8 --length 4
uv run ableton-cli arrangement clip create 0 --start 8 --length 4 --notes-json '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'
uv run ableton-cli arrangement clip create 1 --start 16 --length 8 --audio-path /tmp/loop.wav
uv run ableton-cli arrangement clip list
uv run ableton-cli arrangement clip list --track 0
uv run ableton-cli arrangement clip notes add 0 0 --notes-file ./notes.json
uv run ableton-cli arrangement clip notes get 0 0 --start-time 0.0 --end-time 4.0 --pitch 60
uv run ableton-cli arrangement clip notes clear 0 0 --pitch 60
uv run ableton-cli arrangement clip notes replace 0 0 --notes-json '[{"pitch":65,"start_time":0.25,"duration":0.5,"velocity":100,"mute":false}]'
uv run ableton-cli arrangement clip notes import-browser 0 0 sounds/Bass\ Loop.alc --mode replace --import-length --import-groove
uv run ableton-cli arrangement clip delete 0 0
uv run ableton-cli arrangement clip delete 0 --start 8 --end 16
uv run ableton-cli arrangement clip delete 0 --all
uv run ableton-cli arrangement from-session --scenes "0:24,1:48"
```

### Track

```bash
uv run ableton-cli track info --track-index 0
uv run ableton-cli track volume get --track-index 0
uv run ableton-cli track volume set 0.7 --track-index 0
uv run ableton-cli track name set "Lead Synth" --track-index 0
uv run ableton-cli track mute get --track-index 0
uv run ableton-cli track mute set true --track-index 0
uv run ableton-cli track solo get --track-index 0
uv run ableton-cli track solo set true --track-index 0
uv run ableton-cli track arm get --track-index 0
uv run ableton-cli track arm set false --track-index 0
uv run ableton-cli track panning get --track-index 0
uv run ableton-cli track panning set -- -0.25 --track-index 0
uv run ableton-cli track send get 1 --track-index 0
uv run ableton-cli track send set 1 0.6 --track-index 0
uv run ableton-cli track routing input get --selected-track
uv run ableton-cli track routing input set --type Ext.\ In --channel 1/2 --track-index 0
uv run ableton-cli track routing output get --track-index 0
uv run ableton-cli track routing output set --type Master --channel 3/4 --track-index 0
```

Ref-aware commands use selector flags, not positional indexes.
Track selectors: `--track-index`, `--track-name`, `--selected-track`, `--track-query`, `--track-ref`.
Device selectors: `--device-index`, `--device-name`, `--selected-device`, `--device-query`, `--device-ref`.
Parameter selectors: `--parameter-index`, `--parameter-name`, `--parameter-query`, `--parameter-key`, `--parameter-ref`.
Reuse `stable_ref` values emitted by `tracks list`, `track info`, synth/effect finds, and parameter listings when you need an exact session-local target.

### Return Track

```bash
uv run ableton-cli return-tracks list
uv run ableton-cli return-track volume get 0
uv run ableton-cli return-track volume set 0 0.5
uv run ableton-cli return-track mute get 0
uv run ableton-cli return-track mute set 0 true
uv run ableton-cli return-track solo get 0
uv run ableton-cli return-track solo set 0 false
```

### Master / Mixer

```bash
uv run ableton-cli master info
uv run ableton-cli master volume get
uv run ableton-cli master panning get
uv run ableton-cli master devices list
uv run ableton-cli mixer crossfader get
uv run ableton-cli mixer crossfader set -- -0.2
uv run ableton-cli mixer cue-volume get
uv run ableton-cli mixer cue-volume set 0.75
uv run ableton-cli mixer cue-routing get
uv run ableton-cli mixer cue-routing set Ext.\ Out
```

### Clip

```bash
uv run ableton-cli clip create 0 0 --length 4
uv run ableton-cli clip notes add 0 0 --notes-json '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'
uv run ableton-cli clip notes add 0 0 --notes-file ./notes.json
uv run ableton-cli clip notes get 0 0 --start-time 0.0 --end-time 4.0 --pitch 60
uv run ableton-cli clip notes clear 0 0 --start-time 0.0 --end-time 1.0
uv run ableton-cli clip notes replace 0 0 --notes-json '[{"pitch":65,"start_time":0.25,"duration":0.5,"velocity":100,"mute":false}]' --start-time 0.0 --end-time 1.0
uv run ableton-cli clip notes import-browser 0 1 sounds/Bass\ Loop.alc --mode replace --import-length --import-groove
uv run ableton-cli clip notes quantize 0 0 --grid 1/16 --strength 0.8 --start-time 0.0 --end-time 4.0
uv run ableton-cli clip notes humanize 0 0 --timing 0.05 --velocity 5
uv run ableton-cli clip notes velocity-scale 0 0 --scale 1.1 --offset -3
uv run ableton-cli clip notes transpose 0 0 --semitones 2 --start-time 0.0 --end-time 4.0
uv run ableton-cli clip groove get 0 0
uv run ableton-cli clip groove set 0 0 grooves/Hip\ Hop\ Boom\ Bap\ 16ths\ 90\ bpm.agr
uv run ableton-cli clip groove amount set 0 0 0.6
uv run ableton-cli clip groove clear 0 0
uv run ableton-cli clip name set 0 0 "Hook"
uv run ableton-cli clip name set-many 0 --map "1:Main,2:Var,5:Peak"
uv run ableton-cli clip fire 0 0
uv run ableton-cli clip stop 0 0
uv run ableton-cli clip active get 0 0
uv run ableton-cli clip active set 0 0 false
uv run ableton-cli clip duplicate 0 0 1
uv run ableton-cli clip duplicate-many 0 0 --to 2,4,5,6
uv run ableton-cli clip place-pattern 0 --clip 0 --scenes Intro,Drop,Peak
uv run ableton-cli clip cut-to-drum-rack --source-track 1 --source-clip 0 --slice-count 8 --create-trigger-clip --trigger-clip-slot 1
```

### Scenes

```bash
uv run ableton-cli scenes list
uv run ableton-cli scenes create
uv run ableton-cli scenes create --index 1
uv run ableton-cli scenes name set 1 "Build"
uv run ableton-cli scenes fire 1
uv run ableton-cli scenes move 1 2
```

### Browser

```bash
uv run ableton-cli browser tree all
uv run ableton-cli browser items-at-path drums/Kits
uv run ableton-cli browser item drums/Kits
uv run ableton-cli browser item query:Synths#Operator
uv run ableton-cli browser categories all
uv run ableton-cli browser items drums/Kits --item-type loadable --limit 100 --offset 0
uv run ableton-cli browser search drift --item-type loadable
uv run ableton-cli browser load 0 query:Synths#Operator
uv run ableton-cli browser load 0 instruments/Drift
uv run ableton-cli browser load-drum-kit 0 rack:drums --kit-uri kit:acoustic
uv run ableton-cli browser load-drum-kit 0 rack:drums --kit-path drums/Kits/Acoustic Kit
```

### Batch

```bash
uv run ableton-cli batch run --steps-file ./steps.json
uv run ableton-cli batch run --steps-json '{"steps":[{"name":"song_info","args":{}}]}'
echo '{"steps":[{"name":"song_info","args":{}}]}' | uv run ableton-cli batch run --steps-stdin
uv run ableton-cli batch stream
echo '{"id":"req-1","steps":[{"name":"song_info","args":{}}]}' | uv run ableton-cli batch stream
```

### Device

```bash
uv run ableton-cli device parameter set 0.25 --track-index 0 --device-index 0 --parameter-index 0
```

### Synth

```bash
uv run ableton-cli synth find
uv run ableton-cli synth find --track 0 --type wavetable
uv run ableton-cli synth parameters list --track-index 0 --device-index 0
uv run ableton-cli synth parameter set 0.5 --track-index 0 --device-index 0 --parameter-index 0
uv run ableton-cli synth observe --track-index 0 --device-index 0
uv run ableton-cli synth wavetable keys
uv run ableton-cli synth wavetable set 0.6 --track-index 0 --device-index 0 --parameter-key filter_cutoff
uv run ableton-cli synth wavetable observe --track-index 0 --device-index 0
uv run ableton-cli synth drift keys
uv run ableton-cli synth drift set 0.4 --track-index 0 --device-index 0 --parameter-key drift_amount
uv run ableton-cli synth drift observe --track-index 0 --device-index 0
uv run ableton-cli synth meld keys
uv run ableton-cli synth meld set 0.3 --track-index 0 --device-index 0 --parameter-key spread_amount
uv run ableton-cli synth meld observe --track-index 0 --device-index 0
```

### Effect

```bash
uv run ableton-cli effect find
uv run ableton-cli effect find --track 0 --type eq8
uv run ableton-cli effect parameters list --track-index 0 --device-index 0
uv run ableton-cli effect parameter set 0.5 --track-index 0 --device-index 0 --parameter-index 0
uv run ableton-cli effect parameter set -- -2.0 --track-index 0 --device-index 0 --parameter-index 7
uv run ableton-cli effect observe --track-index 0 --device-index 0
uv run ableton-cli effect eq8 keys
uv run ableton-cli effect eq8 set 0.6 --track-index 0 --device-index 0 --parameter-key band1_freq
uv run ableton-cli effect eq8 observe --track-index 0 --device-index 0
uv run ableton-cli effect limiter keys
uv run ableton-cli effect limiter set 0.4 --track-index 0 --device-index 0 --parameter-key ceiling
uv run ableton-cli effect limiter observe --track-index 0 --device-index 0
uv run ableton-cli effect compressor keys
uv run ableton-cli effect compressor set 0 0 ratio 0.5
uv run ableton-cli effect compressor observe 0 0
uv run ableton-cli effect auto-filter keys
uv run ableton-cli effect auto-filter set 0 0 lfo_rate 0.25
uv run ableton-cli effect auto-filter observe 0 0
uv run ableton-cli effect reverb keys
uv run ableton-cli effect reverb set 0 0 size 0.55
uv run ableton-cli effect reverb observe 0 0
uv run ableton-cli effect utility keys
uv run ableton-cli effect utility set 0 0 width 0.75
uv run ableton-cli effect utility observe 0 0
```

### Config / Completion

```bash
uv run ableton-cli config init
uv run ableton-cli config init --dry-run
uv run ableton-cli config show
uv run ableton-cli config set protocol_version 2
uv run ableton-cli completion
uv run ableton-cli --install-completion
uv run ableton-cli --show-completion
```

## Operational notes

- For positional numeric arguments that begin with `-`, insert `--` before the value.
  - Example: `uv run ableton-cli track panning set -- -0.25 --track-index 0`
  - Example: `uv run ableton-cli effect parameter set -- -2.0 --track-index 0 --device-index 0 --parameter-index 7`
- For low-latency repeated automation operations, prefer `uv run ableton-cli batch stream`.
- Capability and compatibility checks are explicit through `uv run ableton-cli ping` and `uv run ableton-cli doctor`.
- Standard wrapper commands (`synth <type> ...`, `effect <type> ...`) are strict and intentionally fail if required parameter names are missing.
  - If you get `Missing required standard ... keys`, use generic commands instead:
    - `uv run ableton-cli --output json effect parameters list --track-index <track> --device-index <device>`
    - `uv run ableton-cli --output json effect parameter set <value> --track-index <track> --device-index <device> --parameter-index <parameter>`
  - Use this path for locale/device-variant differences to avoid workflow stalls.

## Global options

- `--host`
- `--port`
- `--timeout-ms`
- `--protocol-version`
- `--output [human|json]`
- `--verbose`
- `--log-file`
- `--config <path>`
- `--no-color`
- `--quiet`
- `--version`

Global options must appear before subcommands, e.g. `uv run ableton-cli --output json doctor`.

## JSON output envelope

Use `--output json` for machine-readable responses.

```bash
uv run ableton-cli --output json ping
```

```json
{
  "ok": true,
  "command": "ping",
  "args": {},
    "result": {
      "host": "127.0.0.1",
      "port": 8765,
      "protocol_version": 2,
      "remote_script_version": "0.4.0",
      "rtt_ms": 2.31
    },
  "error": null
}
```

## Exit codes

- `0` success
- `2` invalid arguments
- `3` invalid configuration
- `10` Ableton not connected
- `11` Remote Script not installed or not detected
- `12` timeout
- `13` protocol mismatch
- `20` execution failure
- `99` internal error

## Stable action names and mappings

- `ping` -> `uv run ableton-cli --output json ping`
- `get_song_info` -> `uv run ableton-cli --output json song info`
- `song_new` -> `uv run ableton-cli --output json song new`
- `song_undo` -> `uv run ableton-cli --output json song undo`
- `song_redo` -> `uv run ableton-cli --output json song redo`
- `song_save` -> `uv run ableton-cli --output json song save --path <als>`
- `song_export_audio` -> `uv run ableton-cli --output json song export audio --path <wav>`
- `get_session_info` -> `uv run ableton-cli --output json session info`
- `get_track_info` -> `uv run ableton-cli --output json track info --track-index <track>`
- `play` -> `uv run ableton-cli --output json transport play`
- `stop` -> `uv run ableton-cli --output json transport stop`
- `arrangement_record_start` -> `uv run ableton-cli --output json arrangement record start`
- `arrangement_record_stop` -> `uv run ableton-cli --output json arrangement record stop`
- `set_tempo` -> `uv run ableton-cli --output json transport tempo set <bpm>`
- `transport_position_get` -> `uv run ableton-cli --output json transport position get`
- `transport_position_set` -> `uv run ableton-cli --output json transport position set <beats>`
- `transport_rewind` -> `uv run ableton-cli --output json transport rewind`
- `list_tracks` -> `uv run ableton-cli --output json tracks list`
- `create_midi_track` -> `uv run ableton-cli --output json tracks create midi [--index <index>]`
- `create_audio_track` -> `uv run ableton-cli --output json tracks create audio [--index <index>]`
- `tracks_delete` -> `uv run ableton-cli --output json tracks delete <track>`
- `set_track_name` -> `uv run ableton-cli --output json track name set <name> --track-index <track>`
- `set_track_volume` -> `uv run ableton-cli --output json track volume set <value> --track-index <track>`
- `get_track_mute` -> `uv run ableton-cli --output json track mute get --track-index <track>`
- `set_track_mute` -> `uv run ableton-cli --output json track mute set <value> --track-index <track>`
- `get_track_solo` -> `uv run ableton-cli --output json track solo get --track-index <track>`
- `set_track_solo` -> `uv run ableton-cli --output json track solo set <value> --track-index <track>`
- `get_track_arm` -> `uv run ableton-cli --output json track arm get --track-index <track>`
- `set_track_arm` -> `uv run ableton-cli --output json track arm set <value> --track-index <track>`
- `get_track_panning` -> `uv run ableton-cli --output json track panning get --track-index <track>`
- `set_track_panning` -> `uv run ableton-cli --output json track panning set <value> --track-index <track>`
- `get_track_send` -> `uv run ableton-cli --output json track send get <send> --track-index <track>`
- `set_track_send` -> `uv run ableton-cli --output json track send set <send> <value> --track-index <track>`
- `list_return_tracks` -> `uv run ableton-cli --output json return-tracks list`
- `set_return_track_volume` -> `uv run ableton-cli --output json return-track volume set <return-track> <value>`
- `get_master_info` -> `uv run ableton-cli --output json master info`
- `list_master_devices` -> `uv run ableton-cli --output json master devices list`
- `set_mixer_crossfader` -> `uv run ableton-cli --output json mixer crossfader set <value>`
- `set_mixer_cue_routing` -> `uv run ableton-cli --output json mixer cue-routing set <routing>`
- `get_track_routing_input` -> `uv run ableton-cli --output json track routing input get --track-index <track>`
- `set_track_routing_output` -> `uv run ableton-cli --output json track routing output set --track-index <track> --type <routing-type> --channel <routing-channel>`
- `create_clip` -> `uv run ableton-cli --output json clip create <track> <clip> --length <beats>`
- `add_notes_to_clip` -> `uv run ableton-cli --output json clip notes add <track> <clip> (--notes-json '<json-array>' | --notes-file <path>)`
- `get_clip_notes` -> `uv run ableton-cli --output json clip notes get <track> <clip> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]`
- `clear_clip_notes` -> `uv run ableton-cli --output json clip notes clear <track> <clip> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]`
- `replace_clip_notes` -> `uv run ableton-cli --output json clip notes replace <track> <clip> (--notes-json '<json-array>' | --notes-file <path>) [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]`
- `arrangement_clip_notes_add` -> `uv run ableton-cli --output json arrangement clip notes add <track> <index> (--notes-json '<json-array>' | --notes-file <path>)`
- `arrangement_clip_notes_get` -> `uv run ableton-cli --output json arrangement clip notes get <track> <index> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]`
- `arrangement_clip_notes_clear` -> `uv run ableton-cli --output json arrangement clip notes clear <track> <index> [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]`
- `arrangement_clip_notes_replace` -> `uv run ableton-cli --output json arrangement clip notes replace <track> <index> (--notes-json '<json-array>' | --notes-file <path>) [--start-time <beats>] [--end-time <beats>] [--pitch <midi>]`
- `arrangement_clip_notes_import_browser` -> `uv run ableton-cli --output json arrangement clip notes import-browser <track> <index> <target> [--mode <replace|append>] [--import-length] [--import-groove]`
- `arrangement_clip_delete` -> `uv run ableton-cli --output json arrangement clip delete <track> [index] [--start <beat> --end <beat>] [--all]`
- `arrangement_from_session` -> `uv run ableton-cli --output json arrangement from-session --scenes "0:24,1:48"`
- `clip_duplicate` -> `uv run ableton-cli --output json clip duplicate <track> <src_clip> <dst_clip>`
- `set_clip_name` -> `uv run ableton-cli --output json clip name set <track> <clip> <name>`
- `fire_clip` -> `uv run ableton-cli --output json clip fire <track> <clip>`
- `stop_clip` -> `uv run ableton-cli --output json clip stop <track> <clip>`
- `list_scenes` -> `uv run ableton-cli --output json scenes list`
- `create_scene` -> `uv run ableton-cli --output json scenes create [--index <index>]`
- `set_scene_name` -> `uv run ableton-cli --output json scenes name set <scene> <name>`
- `fire_scene` -> `uv run ableton-cli --output json scenes fire <scene>`
- `scenes_move` -> `uv run ableton-cli --output json scenes move <from> <to>`
- `stop_all_clips` -> `uv run ableton-cli --output json session stop-all-clips`
- `get_browser_tree` -> `uv run ableton-cli --output json browser tree [category_type]`
- `get_browser_items_at_path` -> `uv run ableton-cli --output json browser items-at-path <path>`
- `get_browser_item` -> `uv run ableton-cli --output json browser item <target>`
- `get_browser_categories` -> `uv run ableton-cli --output json browser categories [category_type]`
- `get_browser_items` -> `uv run ableton-cli --output json browser items <path> [--item-type <all,folder,device,loadable>] [--limit <n>] [--offset <n>]`
- `search_browser_items` -> `uv run ableton-cli --output json browser search <query> [--path <path>] [--item-type <all,folder,device,loadable>] [--limit <n>] [--offset <n>] [--exact] [--case-sensitive]`
- `load_instrument_or_effect` -> `uv run ableton-cli --output json browser load <track> <target>`
- `load_drum_kit` -> `uv run ableton-cli --output json browser load-drum-kit <track> <rack_uri> (--kit-uri <uri> | --kit-path <path>)`
- `set_device_parameter` -> `uv run ableton-cli --output json device parameter set <value> --track-index <track> --device-index <device> --parameter-index <parameter>`
- `find_synth_devices` -> `uv run ableton-cli --output json synth find [--track <track>] [--type <wavetable|drift|meld>]`
- `list_synth_parameters` -> `uv run ableton-cli --output json synth parameters list --track-index <track> --device-index <device>`
- `set_synth_parameter_safe` -> `uv run ableton-cli --output json synth parameter set <value> --track-index <track> --device-index <device> --parameter-index <parameter>`
- `observe_synth_parameters` -> `uv run ableton-cli --output json synth observe --track-index <track> --device-index <device>`
- `list_standard_synth_keys` -> `uv run ableton-cli --output json synth <wavetable|drift|meld> keys`
- `set_standard_synth_parameter_safe` -> `uv run ableton-cli --output json synth <wavetable|drift|meld> set <value> --track-index <track> --device-index <device> --parameter-key <key>`
- `observe_standard_synth_state` -> `uv run ableton-cli --output json synth <wavetable|drift|meld> observe --track-index <track> --device-index <device>`
- `find_effect_devices` -> `uv run ableton-cli --output json effect find [--track <track>] [--type <eq8|limiter|compressor|auto_filter|reverb|utility>]`
- `list_effect_parameters` -> `uv run ableton-cli --output json effect parameters list --track-index <track> --device-index <device>`
- `set_effect_parameter_safe` -> `uv run ableton-cli --output json effect parameter set <value> --track-index <track> --device-index <device> --parameter-index <parameter>`
- `observe_effect_parameters` -> `uv run ableton-cli --output json effect observe --track-index <track> --device-index <device>`
- `list_standard_effect_keys` -> `uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filter|reverb|utility> keys`
- `set_standard_effect_parameter_safe` -> `uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filter|reverb|utility> set <value> --track-index <track> --device-index <device> --parameter-key <key>`
- `observe_standard_effect_state` -> `uv run ableton-cli --output json effect <eq8|limiter|compressor|auto-filter|reverb|utility> observe --track-index <track> --device-index <device>`
- `execute_batch` -> `uv run ableton-cli --output json batch run (--steps-file <path> | --steps-json '<json>' | --steps-stdin)`

## Examples

- `ping`: `docs/skills/examples/ping.json`
- `song info`: `docs/skills/examples/song-info.json`
- `tempo set`: `docs/skills/examples/set-tempo.json`
- `tracks list`: `docs/skills/examples/list-tracks.json`
- `track volume set`: `docs/skills/examples/set-track-volume.json`
- `browser search`: `docs/skills/examples/browser-search.json`
