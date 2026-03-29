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
uv run ableton-cli track volume get 0
uv run ableton-cli track volume set 0 0.7
uv run ableton-cli track panning set 0 -- -0.25
uv run ableton-cli track send set 0 1 0.6
uv run ableton-cli track routing input get 0
uv run ableton-cli track routing output set 0 --type Master --channel 3/4
uv run ableton-cli return-tracks list
uv run ableton-cli return-track volume set 0 0.5
uv run ableton-cli master info
uv run ableton-cli master devices list
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
uv run ableton-cli browser load 0 query:Synths#Operator
uv run ableton-cli browser load-drum-kit 0 rack:drums --kit-uri kit:acoustic
uv run ableton-cli batch run --steps-file ./steps.json
uv run ableton-cli device parameter set 0 0 0 0.25
uv run ableton-cli synth find --type wavetable
uv run ableton-cli synth wavetable keys
uv run ableton-cli synth wavetable set 0 0 filter_cutoff 0.6
uv run ableton-cli effect find --type eq8
uv run ableton-cli effect eq8 keys
uv run ableton-cli effect eq8 set 0 0 band1_freq 0.6
```

Complete command coverage:

- `skills/ableton-cli/SKILL.md`
- `docs/skills/skill-actions.md`
- `docs/skills/examples/*.json`

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
- `--version`

Global options must appear before the subcommand.

```bash
# Correct
uv run ableton-cli --output json doctor

# Incorrect
uv run ableton-cli doctor --output json
```

Installers/config commands also support:

- `--yes`
- `--dry-run`

## Protocol

`ableton-cli` uses local TCP JSONL communication on `127.0.0.1:<port>`.

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
{"id":"a2","steps":[{"name":"track_volume_get","args":{"track":0}}]}
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
```

3. Confirm detailed install notes in `docs/skills/install.md`.
4. Run agent automation using `uv run ableton-cli ...` commands.

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
