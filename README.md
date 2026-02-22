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

### Setup / Diagnostics

```bash
uv run ableton-cli doctor
uv run ableton-cli install-remote-script --yes
uv run ableton-cli wait-ready
uv run ableton-cli config init
uv run ableton-cli config show
uv run ableton-cli config set protocol_version 2
```

### Song / Tracks

```bash
uv run ableton-cli song info
uv run ableton-cli song new
uv run ableton-cli song save --path /tmp/demo.als
uv run ableton-cli song export audio --path /tmp/demo.wav
uv run ableton-cli session info
uv run ableton-cli session snapshot
uv run ableton-cli tracks list
uv run ableton-cli tracks create midi
uv run ableton-cli tracks create audio --index 1
uv run ableton-cli tracks delete 2
uv run ableton-cli track info 0
uv run ableton-cli track name set 0 "Lead Synth"
```

### Transport

```bash
uv run ableton-cli transport play
uv run ableton-cli transport stop
uv run ableton-cli transport toggle
uv run ableton-cli transport tempo get
uv run ableton-cli transport tempo set 128
```

### Arrangement

```bash
uv run ableton-cli arrangement record start
uv run ableton-cli arrangement record stop
```

### Track Volume

```bash
uv run ableton-cli track volume get 0
uv run ableton-cli track volume set 0 0.7
uv run ableton-cli track mute get 0
uv run ableton-cli track mute set 0 true
uv run ableton-cli track solo get 0
uv run ableton-cli track solo set 0 true
uv run ableton-cli track arm get 0
uv run ableton-cli track arm set 0 false
uv run ableton-cli track panning get 0
uv run ableton-cli track panning set 0 -- -0.25
```

### Clip / Scenes / Browser / Batch / Device

```bash
uv run ableton-cli clip create 0 0 --length 4
uv run ableton-cli clip notes add 0 0 --notes-json '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'
uv run ableton-cli clip notes add 0 0 --notes-file ./notes.json
uv run ableton-cli clip notes get 0 0 --start-time 0.0 --end-time 4.0 --pitch 60
uv run ableton-cli clip notes clear 0 0 --start-time 0.0 --end-time 1.0
uv run ableton-cli clip notes replace 0 0 --notes-json '[{"pitch":65,"start_time":0.25,"duration":0.5,"velocity":100,"mute":false}]' --start-time 0.0 --end-time 1.0
uv run ableton-cli clip name set 0 0 "Hook"
uv run ableton-cli clip fire 0 0
uv run ableton-cli clip stop 0 0
uv run ableton-cli clip duplicate 0 0 1
uv run ableton-cli scenes list
uv run ableton-cli scenes create
uv run ableton-cli scenes create --index 1
uv run ableton-cli scenes name set 1 "Build"
uv run ableton-cli scenes fire 1
uv run ableton-cli scenes move 1 2
uv run ableton-cli session stop-all-clips
uv run ableton-cli browser tree all
uv run ableton-cli browser items-at-path drums/Kits
uv run ableton-cli browser item drums/Kits
uv run ableton-cli browser search drift --item-type loadable
uv run ableton-cli browser load 0 query:Synths#Operator
uv run ableton-cli browser load 0 instruments/Drift
uv run ableton-cli browser load-drum-kit 0 rack:drums --kit-uri kit:acoustic
uv run ableton-cli browser load-drum-kit 0 rack:drums --kit-path drums/Kits/Acoustic Kit
uv run ableton-cli batch run --steps-file ./steps.json
uv run ableton-cli batch run --steps-json '{"steps":[{"command":"song_info","args":{}}]}'
echo '{"steps":[{"command":"song_info","args":{}}]}' | uv run ableton-cli batch run --steps-stdin
uv run ableton-cli device parameter set 0 0 0 0.25
uv run ableton-cli synth find --type wavetable
uv run ableton-cli synth parameters list 0 0
uv run ableton-cli synth parameter set 0 0 0 0.5
uv run ableton-cli synth observe 0 0
uv run ableton-cli synth wavetable keys
uv run ableton-cli synth wavetable set 0 0 filter_cutoff 0.6
uv run ableton-cli synth wavetable observe 0 0
uv run ableton-cli synth drift keys
uv run ableton-cli synth drift set 0 0 drift_amount 0.4
uv run ableton-cli synth drift observe 0 0
uv run ableton-cli synth meld keys
uv run ableton-cli synth meld set 0 0 spread_amount 0.3
uv run ableton-cli synth meld observe 0 0
uv run ableton-cli effect find --type eq8
uv run ableton-cli effect parameters list 0 0
uv run ableton-cli effect parameter set 0 0 0 0.5
uv run ableton-cli effect observe 0 0
uv run ableton-cli effect eq8 keys
uv run ableton-cli effect eq8 set 0 0 band1_freq 0.6
uv run ableton-cli effect eq8 observe 0 0
uv run ableton-cli effect limiter keys
uv run ableton-cli effect limiter set 0 0 ceiling 0.4
uv run ableton-cli effect limiter observe 0 0
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

This currently applies to API-limited operations such as `song new/save/export`, `arrangement record start|stop`, `scenes move`, and `tracks delete` when the running Live API lacks the required primitive.

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

Skill-oriented references are in `docs/skills/`:

- Primary skill spec: `skills/ableton-cli/SKILL.md`
- Stable action mappings: `docs/skills/skill-actions.md`
- JSON output examples: `docs/skills/examples/*.json`

All skill command examples assume the `uv run ableton-cli ...` form.

## Quality Harness (Phase 2)

Phase 2 extends the AST-based quality harness with:

- baseline comparison (`--baseline`)
- internal dependency cycle detection
- layer violation detection
- existing Phase 1 metrics (complexity, nesting, args, imports, token estimate, duplication, god class risk)

Run locally:

```bash
uv run python tools/quality_harness.py --config .quality-harness.yml --report quality-harness-report.json
```

Run with baseline comparison:

```bash
uv run python tools/quality_harness.py --config .quality-harness.yml --report quality-harness-report.json --baseline ./baseline-quality-harness-report.json
```

Exit codes:

- `0`: no fail-level violations
- `1`: fail-level violations detected
- `2`: invalid config/runtime error

Default thresholds in `.quality-harness.yml` are calibrated for this repository's current shape (warn-heavy, fail-guarded).
They are intended to keep CI fail-level guardrails active while surfacing refactoring candidates as warnings.

Detailed specification and known limits:

- `docs/quality-harness-phase2.md`

## Development

```bash
uv sync
uv run python -m ableton_cli.dev_checks
uv run ableton-cli --help
uv run ableton-cli --version
```

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
