# ableton-cli

`ableton-cli` is a Python CLI to control and inspect Ableton Live through a local Remote Script.
It is designed for both humans and automation (Skills/agents), with stable JSON output and fixed exit codes.

## Prerequisites

- Ableton Live
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

## Quick Setup

1. Install dependencies:

```bash
uv sync
```

2. Install the Remote Script files:

```bash
uv run ableton-cli install-remote-script --yes
```

3. In Ableton Live, open Preferences and set Control Surface to `AbletonCliRemote`.

4. Run diagnostics:

```bash
uv run ableton-cli doctor
```

5. Verify connection:

```bash
uv run ableton-cli ping
```

## Core Commands

Representative commands:

```bash
uv run ableton-cli doctor
uv run ableton-cli install-remote-script --yes
uv run ableton-cli install-skill --yes
uv run ableton-cli wait-ready
uv run ableton-cli song info
uv run ableton-cli song undo
uv run ableton-cli song redo
uv run ableton-cli transport play
uv run ableton-cli transport tempo set 128
uv run ableton-cli transport position get
uv run ableton-cli transport position set 32
uv run ableton-cli transport rewind
uv run ableton-cli tracks list
uv run ableton-cli track volume get --track-index 0
uv run ableton-cli track volume set 0.7 --track-index 0
uv run ableton-cli track panning set -- -0.25 --track-index 0
uv run ableton-cli track send set 1 0.6 --track-index 0
uv run ableton-cli track routing input get --selected-track
uv run ableton-cli track routing output set --type Master --channel 3/4 --track-name "Bass"
uv run ableton-cli return-tracks list
uv run ableton-cli return-track volume set 0 0.5
uv run ableton-cli master info
uv run ableton-cli master devices list
uv run ableton-cli master device load query:Audio\ Effects#Utility --position end
uv run ableton-cli master device parameter set --device-index 0 --parameter-key gain -- -1.5
uv run ableton-cli audio loudness analyze --path ./renders/remix.wav --engine ffmpeg
uv run ableton-cli audio spectrum analyze --path ./renders/remix.wav --profile anime-club
uv run ableton-cli remix mastering target set --project ./proj/remix_project.json --profile anime-club-demo
uv run ableton-cli remix mastering analyze --project ./proj/remix_project.json --render ./renders/remix.wav
uv run ableton-cli remix mastering plan --project ./proj/remix_project.json
uv run ableton-cli remix mastering apply --project ./proj/remix_project.json --dry-run
uv run ableton-cli remix mastering qa --project ./proj/remix_project.json --render ./renders/remix.wav
uv run ableton-cli mixer crossfader set -- -0.2
uv run ableton-cli mixer cue-routing get
uv run ableton-cli clip create 0 0 --length 4
uv run ableton-cli clip notes add 0 0 --notes-json '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'
uv run ableton-cli clip cut-to-drum-rack --source-track 1 --source-clip 0 --slice-count 8 --create-trigger-clip --trigger-clip-slot 1
uv run ableton-cli arrangement clip create 0 --start 8 --length 4 --notes-json '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'
uv run ableton-cli arrangement clip notes get 0 0 --start-time 0.0 --end-time 4.0 --pitch 60
uv run ableton-cli arrangement clip notes import-browser 0 0 sounds/Bass\ Loop.alc --mode replace --import-length --import-groove
uv run ableton-cli arrangement clip delete 0 --start 0 --end 16
uv run ableton-cli arrangement from-session --scenes "0:24,1:48"
uv run ableton-cli clip fire 0 0
uv run ableton-cli scenes list
uv run ableton-cli browser search drift --item-type loadable
uv run ableton-cli browser search "Drum Rack" --path drums --item-type loadable --limit 10
uv run ableton-cli browser search "Kit" --path drums --item-type loadable --limit 10
uv run ableton-cli browser load 0 query:Synths#Operator
uv run ableton-cli browser load-drum-kit 0 <rack-uri-from-search> --kit-uri <kit-uri-from-search>
uv run ableton-cli batch run --steps-file ./steps.json
uv run ableton-cli device parameter set 0.25 --track-index 0 --device-index 0 --parameter-index 0
uv run ableton-cli synth find --type wavetable
uv run ableton-cli synth wavetable keys
uv run ableton-cli synth wavetable set 0.6 --selected-track --selected-device --parameter-key filter_cutoff
uv run ableton-cli effect find --type eq8
uv run ableton-cli effect eq8 keys
uv run ableton-cli effect eq8 set 0.6 --track-query Bass --device-query EQ --parameter-key band1_freq
```

Ref-aware track, device, and parameter commands now use mutually exclusive selector flags instead of positional indexes.
Track selectors: `--track-index`, `--track-name`, `--selected-track`, `--track-query`, `--track-ref`.
Device selectors: `--device-index`, `--device-name`, `--selected-device`, `--device-query`, `--device-ref`.
Parameter selectors: `--parameter-index`, `--parameter-name`, `--parameter-query`, `--parameter-key`, `--parameter-ref`.
`tracks list`, `track info`, synth/effect device discovery, and parameter listings emit `stable_ref` fields so later commands can reuse exact session-local objects.

Complete command coverage:

- `skills/ableton-cli/SKILL.md`
- `docs/skills/skill-actions.md`
- `docs/skills/examples/*.json`

## Composition Workflow

For agent-driven composition, run a high-timeout preflight before mutating the set:

```bash
uv run ableton-cli --timeout-ms 15000 --output json wait-ready
uv run ableton-cli --timeout-ms 15000 --output json doctor
uv run ableton-cli --timeout-ms 15000 --output json tracks list
```

Discover browser targets before loading instruments or kits. Browser catalogs vary by Live version,
packs, locale, and user library state, so do not assume a fixed Drum Rack or kit URI exists:

```bash
uv run ableton-cli --timeout-ms 15000 --output json browser categories all
uv run ableton-cli --timeout-ms 15000 --output json browser search "Drum Rack" --path drums --item-type loadable --limit 10
uv run ableton-cli --timeout-ms 15000 --output json browser search "Kit" --path drums --item-type loadable --limit 10
uv run ableton-cli --timeout-ms 15000 --output json browser search "Operator" --path instruments --item-type loadable --limit 10
```

Choose exact `uri` or `path` values from those results, then pass them explicitly:

```bash
uv run ableton-cli --timeout-ms 15000 --output json browser load-drum-kit 0 <rack-uri-from-search> --kit-uri <kit-uri-from-search>
uv run ableton-cli --timeout-ms 15000 --output json browser load 1 <synth-uri-or-path-from-search>
```

## JSON Output for Automation

Use `--output json` for machine-readable output.

```bash
uv run ableton-cli --output json ping
```

Output envelope (stable):

```json
{
  "ok": true,
  "command": "ping",
  "args": {},
  "result": {},
  "error": null
}
```

## Global Options

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
- `--record <path>`
- `--replay <path>`
- `--read-only`
- `--require-confirmation`
- `--yes`
- `--plan`
- `--dry-run`
- `--compact`
- `--version`

Global options must appear before the subcommand.

```bash
# Correct
uv run ableton-cli --output json doctor

# Incorrect
uv run ableton-cli doctor --output json
```

Installer/config commands also support command-local forms:

- `--yes`
- `--dry-run`

## Protocol

`ableton-cli` uses local TCP JSONL communication on `127.0.0.1:<port>`.

## Security Model

- The Remote Script listens on 127.0.0.1 only (local loopback).
- The protocol has no authentication.
- Do not expose the port to untrusted networks.
- Treat write and destructive commands as equivalent to direct user operation in Ableton Live.
- Prefer `--read-only` for inspection and agent preflight.
- Use `--plan` or `--dry-run` to inspect the side effect and target payload before dispatch.
- Use `--require-confirmation --yes` when automation should fail closed around destructive commands.

### Request

```json
{
  "type": "command",
  "name": "song_info",
  "args": {},
  "meta": {
    "request_timeout_ms": 15000
  },
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 2
}
```

### Response (success)

```json
{
  "ok": true,
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 2,
  "result": {
    "tempo": 120.0
  },
  "error": null
}
```

### Response (failure)

```json
{
  "ok": false,
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 2,
  "result": null,
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "bpm must be between 20.0 and 999.0",
    "hint": "Fix command arguments and retry.",
    "details": null
  }
}
```

## Low-latency operation

For single commands, use existing subcommands as before.
For repeated automation commands, prefer `batch stream` to keep one process alive and avoid process startup overhead.

`batch stream` expects one JSON object per stdin line and emits one JSON response line per request:

```bash
cat <<'JSONL' | uv run ableton-cli batch stream
{"id":"a1","steps":[{"name":"song_info","args":{}}]}
{"id":"a2","steps":[{"name":"track_volume_get","args":{"track_ref":{"mode":"index","index":0}}}]}
JSONL
```

Compatibility validation is now explicit:

- `uv run ableton-cli ping` for protocol/version metadata
- `uv run ableton-cli doctor` for supported command integrity checks

## Exit Codes

- `0` success
- `2` invalid arguments
- `3` invalid configuration
- `10` Ableton not connected
- `11` Remote Script not installed/detected
- `12` timeout
- `13` protocol mismatch
- `20` execution failure
- `99` internal error

## Unsupported-by-API behavior

If a command is exposed by CLI/Remote but Live API cannot perform it, the command fails explicitly with:

- `error.code=INVALID_ARGUMENT`
- `error.details.reason=not_supported_by_live_api`

This currently applies to API-limited operations such as `song new/undo/redo/save/export`, `arrangement record start|stop`, `scenes move`, and `tracks delete` when the running Live API lacks the required primitive.

## Completion

Typer built-in completion is available:

```bash
uv run ableton-cli --install-completion
uv run ableton-cli --show-completion
```

## Man Page

Generate:

```bash
scripts/generate_man.sh
```

Install locally (optional):

```bash
scripts/install_man.sh
```

Then:

```bash
man ableton-cli
```

## Skills Integration

Use these steps to enable the `ableton-cli` skill for agent workflows:

1. Complete Quick Setup and confirm connectivity with `uv run ableton-cli ping`.
2. Install the skill:

```bash
uv run ableton-cli install-skill --yes
uv run ableton-cli install-skill --target claude --yes
uv run ableton-cli install-skill --target cursor --yes
```

3. Confirm detailed install notes in `docs/skills/install.md`.
4. Run agent automation using `uv run ableton-cli ...` commands.

Cursor users do not need any install step when working inside this repository:
`.cursor/rules/*.mdc` and `.cursor/skills/ableton-cli/SKILL.md` are committed,
so the agent picks up ableton-cli conventions automatically when the project is
opened. The `install-skill --target cursor` command only mirrors the same SKILL
file into the user-level `~/.cursor/skills/` so it is also discoverable in other
workspaces.

Skill-oriented references:

- Primary skill spec: `skills/ableton-cli/SKILL.md`
- Stable action mappings: `docs/skills/skill-actions.md`
- JSON output examples: `docs/skills/examples/*.json`

All skill command examples assume the `uv run ableton-cli ...` form.

## Contributing

Development workflows (local checks, quality gates, and merge criteria) are documented in
`CONTRIBUTING.md`.

## Troubleshooting

1. Run `uv run ableton-cli doctor`.
2. Confirm Ableton is running and `AbletonCliRemote` is selected as Control Surface.
3. Confirm host/port (`127.0.0.1:8765` by default).
4. Try a longer timeout: `--timeout-ms 30000`.
5. If protocol mismatches, use `--protocol-version <n>` or `uv run ableton-cli config set protocol_version <n>`.

### `AbletonCliRemote` not shown in Control Surface list

1. Reinstall the script files: `uv run ableton-cli install-remote-script --yes`.
2. Restart Ableton Live completely.
3. Run `uv run ableton-cli --output json doctor` and check:
   - `remote_script_files`
   - `remote_script_entrypoint`
4. Verify installed paths under:
   - `~/Music/Ableton/User Library/Remote Scripts/AbletonCliRemote`
   - `~/Documents/Ableton/User Library/Remote Scripts/AbletonCliRemote`

### Remote Script update not taking effect immediately

If behavior still looks old after `install-remote-script --yes` (for example, unchanged command errors):

1. In Ableton Live Preferences, set Control Surface to `None`.
2. Set it back to `AbletonCliRemote`.
3. Re-run `uv run ableton-cli --output json ping` and `uv run ableton-cli --output json doctor`.
4. If unchanged, restart Ableton Live and retry.
