# ableton-cli

`ableton-cli` is a Python CLI to control and inspect Ableton Live through a local Remote Script.
It is designed for both humans and automation (Skills/agents), with stable JSON output and fixed exit codes.

## Prerequisites

- Ableton Live 12+ (the Remote Script uses dataclass `slots=True`, which requires the
  Python 3.11 interpreter bundled with Live 12; Live 11 ships Python 3.7 and cannot
  load this Remote Script)
- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

## Install

Install as a standalone tool with uv (no checkout needed). Use this repository's
URL (shown under the GitHub "Code" button) as `<repo-url>`:

```bash
uv tool install "git+<repo-url>"
# or pin a release tag:
uv tool install "git+<repo-url>@vX.Y.Z"
```

Then use `ableton-cli` directly (no `uv run` prefix):

```bash
ableton-cli install-remote-script --yes
ableton-cli doctor
```

Release tags and prebuilt artifacts are published on this repository's GitHub
Releases page. To work from source instead, follow Quick Setup below.

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
uv run ableton-cli track meter get --track-index 0 --samples 20 --interval-ms 50
uv run ableton-cli track volume set 0.7 --track-index 0
uv run ableton-cli track panning set --track-index 0 -- -0.25
uv run ableton-cli track send set 1 0.6 --track-index 0
uv run ableton-cli track routing input get --selected-track
uv run ableton-cli track routing output set --type Master --channel 3/4 --track-name "Bass"
uv run ableton-cli return-tracks list
uv run ableton-cli return-track volume set 0 0.5
uv run ableton-cli return-track meter get 0 --samples 20
uv run ableton-cli master info
uv run ableton-cli master meter get --samples 20 --interval-ms 50
uv run ableton-cli master devices list
uv run ableton-cli device insert Utility --main
uv run ableton-cli device parameter set-display --main --device-name "Glue Compressor" --parameter-name Threshold -- -10
uv run ableton-cli session capture-tracks --track-index 0 --track-index 9 --start 304 --bars 8 --bypass-main-devices
uv run ableton-cli audio transient analyze --path ./loops/drum-break.wav --bpm 174 --max-slices 16
uv run ableton-cli remix mastering target set --project ./proj/remix_project.json --profile anime-club-demo
uv run ableton-cli remix mastering report add --project ./proj/remix_project.json --kind loudness --report ./proj/reports/remix_loudness.json
uv run ableton-cli remix mastering plan --project ./proj/remix_project.json
uv run ableton-cli remix mastering apply --project ./proj/remix_project.json --dry-run
uv run ableton-cli remix mastering qa --project ./proj/remix_project.json --render ./renders/remix.wav
uv run ableton-cli mixer crossfader set -- -0.2
uv run ableton-cli mixer cue-routing get
uv run ableton-cli clip create 0 0 --length 4
uv run ableton-cli clip notes add 0 0 --notes-json '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'
uv run ableton-cli clip notes update 0 0 --notes-json '[{"note_id":3,"velocity":90,"probability":0.75}]'
uv run ableton-cli clip cut-to-drum-rack --source-file ./loops/drum-break.wav --transient --bpm 174 --max-slices 16 --create-trigger-clip --trigger-clip-slot 1
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
uv run ableton-cli device parameters list --track-name Vox --device-name "Auto Shift"
uv run ableton-cli device parameter set-display --track-name Bass --device-name Compressor --parameter-name Threshold -- -18
uv run ableton-cli device parameter select RMS --track-name Bass --device-name Compressor --parameter-name Model
uv run ableton-cli device sidechain set --type "1-Kick" --channel "Post FX" --track-name Bass --device-name Compressor
uv run ableton-cli device insert Compressor --track-name Bass
uv run ableton-cli device parameter set-display 4.5 --return-track-index 0 --device-index 0 --parameter-name Decay
uv run ableton-cli device preset set 2 --track-name Vox --device-index 0
uv run ableton-cli return-tracks create
uv run ableton-cli song scale set --root A --name Minor --mode
uv run ableton-cli synth find --type wavetable
uv run ableton-cli synth wavetable keys
uv run ableton-cli synth wavetable set 0.6 --selected-track --selected-device --parameter-key filter_cutoff
uv run ableton-cli effect find --type eq8
uv run ableton-cli effect eq8 keys
uv run ableton-cli effect eq8 set 0.6 --track-query Bass --device-query EQ --parameter-key band1_freq
uv run ableton-cli set inspect --path ./Song\ Project/Song.als
uv run ableton-cli set lint --path ./Song\ Project/Song.als
uv run ableton-cli set diff --from ./Song\ Project/Song.als --to ./Song\ Project/Song-v2.als
uv run ableton-cli set automation write --path ./Song\ Project/Song.als --out ./Song\ Project/Song-auto.als --track-index 0 --target device.1.Frequency --points-json '[{"time":0,"value":500},{"time":64,"value":8000}]'
```

Offline loudness, spectrum, band-share and reference analysis through ffmpeg is not part of
the core: install the `analysis` plugin (the `ableton-cli-analysis` repository; see
[docs/mastering.md](docs/mastering.md) for the install command), which adds
`ableton-cli analysis loudness analyze`, `analysis spectrum analyze`, `analysis spectrum
shares` and `analysis reference compare`. Write their reports with `--report-out` and
register them with `remix mastering report add --kind loudness|spectrum|reference_compare`
so `remix mastering qa` can read them; `report add` fails with `INVALID_ARGUMENT` when a
report lacks a field QA reads. `session capture` and `session capture-tracks` return the
captured `file_path`s for the plugin to measure.

Ref-aware track, device, and parameter commands now use mutually exclusive selector flags instead of positional indexes.
Track selectors: `--track-index`, `--track-name`, `--selected-track`, `--track-query`, `--track-ref`.
`device` commands also accept `--return-track-index` and `--return-track-name`, so return-track
devices (reverbs, delays) are reachable; their results report `"track": {"kind": "return", "index": N}`.
`--main` targets the main (master) track the same way and reports `"track": {"kind": "main"}`.
Main-track devices are edited only through `device ... --main`; `master devices list` lists them
and `master effect <type>` keeps the typed wrappers.
`track meter get`, `return-track meter get` and `master meter get` read Live's output meters
(`left`, `right`, `level`) on Live's 0.0-1.0 meter scale, not dB. They take `--samples`
readings `--interval-ms` apart and report each channel's `peak` and `mean`, plus `is_playing`:
meters read 0.0 while the transport is stopped.
Device selectors: `--device-index`, `--device-name`, `--selected-device`, `--device-query`, `--device-ref`.
Parameter selectors: `--parameter-index`, `--parameter-name`, `--parameter-query`, `--parameter-key`, `--parameter-ref`.
`device parameters list` reports `value_items` for choice parameters and `step_labels` for
stepped parameters (Live reports Beat Repeat Grid or Glue Compressor Ratio as non-quantized,
but each integer raw value has its own label such as `1/32` or `4`). Set either kind by label
with `device parameter select`; use `device parameter set-display` for continuous parameters.
`set-display` takes a bare number in the parameter's display unit (`180` for 180 ms, `2000` for
2.00 s); unit text such as `180 ms` is rejected, and negative values go after `--`.
A display value Live rejects fails with `INVALID_ARGUMENT`.
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
- `--auth-token`
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

`ableton-cli` uses local TCP JSONL communication on `<host>:<port>` (`127.0.0.1:8765` by
default; see [Security Model](#security-model) for overriding host/port/auth_token).

The connection can be persistent: one line is one request, and a client may
send multiple requests over the same connection. Responses are returned in
request order. A malformed request line closes the connection; well-formed
requests that fail validation or execution return a structured error and
keep the connection open.

### Event subscriptions

Commands are strictly request/response, so anything a user does in Live itself can
only be noticed by polling — that is what `session watch` does. A connection can
instead send one `"type": "subscribe"` request and become an event stream:

```json
{"type":"subscribe","name":"events","args":{"events":["tempo","is_playing"]},"meta":{},"request_id":"...","protocol_version":3}
```

The remote answers with the usual response envelope (`result.subscribed` lists the
accepted names, `result.stream` is `true`) and then pushes one line per event:

```json
{"type":"event","protocol_version":3,"event":"tempo","ts":1730000000.0,"data":{"tempo":174.0},"dropped":0}
```

- A subscribing connection stops accepting commands, so pushed events can never
  delay a command; `ableton-cli session events` opens its own connection.
- Event names are `tempo`, `is_playing`, `playing_position` and `selected_track`.
  Which of them a given Live version can deliver depends on the listener APIs it
  exposes; subscribing to one that is unavailable fails with `INVALID_ARGUMENT`
  and a hint listing what is available, rather than accepting the subscription
  and never delivering.
- `playing_position` is throttled to at most one event per 100 ms.
- A subscriber that cannot keep up loses the oldest events instead of growing an
  unbounded queue; `dropped` reports how many were lost since the previous event.
- A Remote Script that predates subscriptions rejects `"type": "subscribe"` with
  `INVALID_ARGUMENT`, so an old install fails loudly instead of hanging.

## Security Model

- By default the Remote Script listens on 127.0.0.1 only (local loopback), port 8765, with
  no authentication: any process on the same machine can issue commands.
- Do not expose, forward, or bind the port to untrusted networks.
- Host, port, and an optional `auth_token` can be overridden via
  `remote_script/AbletonCliRemote/remote_config.json` (copied alongside the Remote Script on
  install) or environment variables read by the Remote Script process:
  `ABLETON_CLI_REMOTE_HOST`, `ABLETON_CLI_REMOTE_PORT`, `ABLETON_CLI_REMOTE_AUTH_TOKEN`.
  Invalid values (empty host, out-of-range port, non-string token) fail explicitly instead of
  falling back to defaults.

  ```json
  {
    "host": "127.0.0.1",
    "port": 8765,
    "auth_token": "replace-with-a-shared-secret"
  }
  ```

- Running multiple Ableton Live instances requires giving each Remote Script a distinct port.
- On the CLI side, set the matching token via `--auth-token`, the `ABLETON_CLI_AUTH_TOKEN`
  environment variable, or `ableton-cli config set auth_token <token>`. `config show` and
  `config set` always report `auth_token` as `***` (or `null` when unset); the raw value is
  only used on the wire and when writing the local config file.
- `auth_token` is a plain shared-secret check, not encrypted or transport-secured
  authentication. It is a deterrent against other local processes, not a security boundary
  against a hostile user on the same machine.
- `install-remote-script` copies the Remote Script directory with `copytree`; a
  `remote_config.json` already present in the installed source tree is preserved, but
  reinstalling/updating overwrites the installed `AbletonCliRemote` directory, so re-apply
  `remote_config.json` after updates if it lives only at the install target.
- Before an update, the previous `AbletonCliRemote` directory is moved to
  `User Library/Remote Script Backups/AbletonCliRemote.backup-<YYYYMMDDHHMMSS>` (reported in the
  `backup`/`backups` JSON fields). Backups are kept outside `Remote Scripts/` because Live
  tries to import every folder there as a control surface. Backups are never deleted
  automatically; remove old ones by hand. Older releases left `AbletonCliRemote.backup-*`
  folders inside `Remote Scripts/`, which log a `SyntaxError` import error in Live's `Log.txt`
  on every launch; delete or move those manually.
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
    "request_timeout_ms": 15000,
    "idempotency_key": "0f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
  },
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 3
}
```

`request_id` is fresh on every send and never identifies a retry.

`meta.idempotency_key` is optional (max 128 characters) and is what makes a
resend safe. The Remote Script keeps the response of the last 256 completed
keys; a request repeating a key it has already completed is **not executed
again** — the stored response is returned with `idempotent_replay: true` added
to `result` (or to `error.details` for a stored failure). `batch run` and
`batch stream` generate one key per step and reuse it for every retry attempt,
so a step that times out and is retried cannot be applied twice.

Protocol versions must match exactly. After upgrading the CLI, reinstall the
Remote Script and re-select the Control Surface in Live:

```bash
uv run ableton-cli install-remote-script --yes
```

### Response (success)

```json
{
  "ok": true,
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 3,
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
  "protocol_version": 3,
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

### Batch step retries

Batch steps run once unless the step opts in with a `retry` object:

```json
{"name": "tracks_list", "args": {}, "retry": {"max_attempts": 3, "backoff_ms": 200}}
```

`retry.on` defaults to `["REMOTE_BUSY"]`. `REMOTE_BUSY` is rejected by the
Remote Script before the command is queued, so a retry cannot double-apply it.

`TIMEOUT` is not retried by default, but adding it to `retry.on` is safe for
any command: a retrying step carries one `meta.idempotency_key` across all of
its attempts, so the Remote Script replays its stored response rather than
applying the command a second time. A replayed response carries
`idempotent_replay: true`.

A step that fails with `TIMEOUT` and is not retried reports
`error.details.may_have_executed`:

- `true` — Live had already started the command; inspect the set before retrying
- `false` — the command was cancelled before it ran and can be resent safely
- `null` — no structured answer reached the CLI; assume it may have been applied

### Batch step failures

By default a batch stops at the first failing step and keeps that step's error
code (and therefore its exit code). `error.details` always locates the failure:

- `step_index` / `step_name` — the step that failed
- `completed_steps` — how many steps succeeded before it
- `results` — the results of those completed steps (Live state they changed is not rolled back)

`--continue-on-error` (on both `batch run` and `batch stream`) runs every step
regardless of failures. Each `results[]` entry then carries `ok` plus either
`result` or `error`. If any step failed, the whole batch still fails with
`BATCH_STEP_FAILED` (exit code `20`), and the per-step entries are in
`error.details.results` together with `failed_step_indices`. Assertion failures
count as step failures: a failing `previous` assertion skips the step without
executing it, a failing `current` assertion marks the already-executed step as
failed, and the step after any failed step sees no `previous` payload.

```bash
uv run ableton-cli --output json batch run --continue-on-error --steps-file ./steps.json
```

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

`clip cut-to-drum-rack` builds each pad from Live 12.3+ primitives (`Track.insert_device`,
`RackDevice.insert_chain`, `Chain.insert_device("Simpler")`, `SimplerDevice.replace_sample`) and
trims every slice with the Simpler sample markers. Browser sources (`--source`) fail with
`not_supported_by_live_api` because Live's browser items do not expose the file path that
`replace_sample` needs; use `--source-file <path> --transient` or `--source-track/--source-clip`.

## Transport position

`transport play` (and `transport toggle` when it starts playback) plays from the current playhead.
Live's `start_playing` restarts from the start marker and `continue_playing` from where playback
last stopped, so the CLI re-applies a playhead moved while stopped in a follow-up request once
playback runs (Live ignores the write before then) and verifies it by read-back. Run
`transport position set <beats>` first to choose where playback and arrangement recording begin.
Live applies playhead writes after the request returns, so `transport position set` and
`transport rewind` read the position back in a second request and fail with `INVALID_ARGUMENT`
and `error.details.mismatches` when a stopped playhead did not move.

`track routing input|output set` take `--channel` as optional: omit it to keep the channel Live
selects for the routing type (for example `--type Resampling`, whose only channel is empty).

Clip and arrangement note write/edit commands (`clip notes add`, `clip notes update`,
`clip notes quantize|humanize|velocity-scale|transpose`, `arrangement clip notes add`, and
`clip cut-to-drum-rack` trigger clip creation) require the Live 12+ extended note API
(`Clip.add_new_notes` / `Clip.apply_note_modifications`, plus the `note_id`, `probability`,
`velocity_deviation`, and `release_velocity` note fields). On older Live versions these commands
fail with the `not_supported_by_live_api` reason above instead of falling back to the legacy
note API.

## Offline Live Set files

The `set` command group reads Live Set (`.als`) files directly, without Live or the
Remote Script. It is a separate surface, not a fallback: no command switches between
the Remote Script and file access on its own.

- `set inspect --path <set.als>`: tempo, time signature, scale, tracks (type, group,
  devices, clip counts), return tracks, scenes, locators, and plug-in inventory.
  Tempo is the effective value: an arrangement tempo envelope overrides the manual value.
- `set lint --path <set.als>`: integrity of the global ID space (duplicate or dangling
  IDs, `NextPointeeId`) as errors, and missing project samples as warnings. Project
  samples resolve against the nearest folder containing `Ableton Project Info`, as in
  Live. Library and other non-project samples resolve against locations the CLI does
  not assume, so they are not checked; `result.media` counts them by
  `RelativePathType`. Findings list relative paths and file names, not absolute paths.
- `set diff --from <a.als> --to <b.als>`: semantic `added` / `removed` / `changed`
  deltas, with tracks matched by their set-local ID.
- `set automation write --path <set.als> --out <new.als> <selector> --target <target>
  --points-json <json>`: write one arrangement automation lane, replacing any lane for
  the same parameter. This is the path for arrangement automation, which the Remote
  Script cannot write (the Live API only exposes session clip envelopes).
  - Choosing the path: clip-level changes go into a session clip with
    `clip envelope set|shape`. Live 12 refuses clip envelopes on arrangement clips
    ("Not a session clip"), and `arrangement from-session` copies notes into new
    clips without their envelopes. Track-wide arrangement automation needs the Set
    saved by hand in Live and then `set automation write`: `song save` and
    `song export audio` fail with `not_supported_by_live_api`, because Live exposes
    no save or export to scripts.
  - Selector: exactly one of `--track-index`, `--track-name`, `--return-track-index`,
    `--main`.
  - Target: `mixer.volume`, `mixer.pan`, `mixer.tempo` (`--main` only),
    `send.<return index>`, or `device.<top-level device index>.<parameter XML tag>`.
  - Points: `[{"time": <beats>, "value": <number>}]`, times `>= 0` and strictly
    increasing. Values are Live's internal parameter values, validated against the
    parameter's `MidiControllerRange` (tempo: 20-999 BPM). These are not the
    Remote Script's normalized values: `mixer.volume` and `send.<n>` are linear gain
    (1.0 = 0 dB, 0.5 = about -6 dB), and device frequencies are in Hz.
  - Only continuous parameters are written. On/off and choice parameters are rejected;
    the error for an unknown device parameter lists the writable tags.
  - `--out` must not exist, must differ from `--path`, and its directory must exist
    (normally the project folder, so project samples still resolve). The result is
    integrity-checked before an atomic write; the source file is never modified.
    `--read-only` blocks the command; `--dry-run` plans without reading or writing.

Failure modes:

- `error.code=SET_FILE_INVALID`, exit code `2`: not gzip, not XML, or not a Live Set.
- `error.code=SET_SCHEMA_UNSUPPORTED`, exit code `2`: not a Live 12 set, or a structure
  this version does not understand.
- `error.code=SET_INTEGRITY_FAILED`, exit code `20`: `set lint` found integrity errors,
  or a write command's result failed the integrity check; `error.details.findings`
  lists them and no file is written.

The `.als` format is undocumented. Only Live 12 sets are accepted, and widening that
range requires verifying real sets in Live. See `docs/offline-set-editing-design.md`.

## Not-implemented commands

Some commands are part of the published surface but have no working implementation behind
them, because the Live API does not expose the primitive (creating return or group tracks,
sidechain routing) or because the work happens outside this CLI (stem separation, browser
target discovery). They fail explicitly rather than returning a plan nobody executes:

- `error.code=NOT_IMPLEMENTED`
- `error.details.reason=not_implemented`
- exit code `20`
- `error.hint` names the commands that do the job

This currently applies to `remix setup-sound`, `remix mix-macro`, `remix setup-mix`,
`remix setup-returns`, `remix setup-sidechain`, `remix device-chain apply`, and
`audio stems split`. Argument validation still runs first, so a bad argument reports
`INVALID_ARGUMENT` and exit code `2`.

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

## Plugins

Features that do not belong in the core CLI (for example a local music generator or a
gating tool) ship as plugins: separate Python packages that add a top-level command group,
`ableton-cli <plugin> ...`. Plugin commands use the core JSON envelope, exit codes,
`--plan`/`--dry-run`, `--read-only` and `--require-confirmation`.

Install a plugin from its GitHub repository:

```bash
uv run ableton-cli --plan plugins install https://github.com/<owner>/<repo>
uv run ableton-cli plugins install https://github.com/<owner>/<repo>
uv run ableton-cli plugins install https://github.com/<owner>/<repo>/tree/v1.2.0
uv run ableton-cli plugins list
uv run ableton-cli plugins info <name>
uv run ableton-cli plugins update <name> --ref <branch|tag|sha>
uv run ableton-cli plugins uninstall <name>
uv run ableton-cli plugins sync
```

- Only `https://github.com/<owner>/<repo>` URLs are accepted, optionally ending in
  `/tree/<ref>` (or pass `--ref`). The ref is resolved with `git ls-remote` to a full commit
  SHA, and the install is pinned to that commit. `--plan` shows the commit without installing.
- The package is installed with `uv pip install` into the Python environment that runs
  `ableton-cli`. Every package already installed is pinned through a constraints file, so a
  plugin can add dependencies but never change ableton-cli's or another plugin's. `git` and
  `uv` must be on `PATH` (`CONFIG_INVALID` otherwise).
- After installing, the plugin is loaded in a fresh interpreter. If it does not load (wrong
  plugin API version, name clash, import error, ...) the install is rolled back and the command
  fails with `PLUGIN_INVALID`.
- Installed plugins are recorded in `plugins.toml` next to the config file (override the path
  with `ABLETON_CLI_PLUGIN_MANIFEST`). Recreating the environment (reinstalling ableton-cli,
  `uv sync`) removes plugin packages; `doctor` then fails its `plugins` check and
  `plugins sync` reinstalls the recorded commits.
- Installing a plugin runs its code with the same access as `ableton-cli`, including write
  access to the Live Set. Only install repositories you trust; `plugins install`,
  `update`, `uninstall` and `sync` are destructive commands, so `--require-confirmation`
  makes them require `--yes`.
- A plugin that fails to load answers every call with `PLUGIN_LOAD_FAILED` and the reason in
  `error.details.load_failure`; core commands keep working. `ABLETON_CLI_PLUGINS=off`
  disables all plugins (`on` is the default; any other value is `CONFIG_INVALID`).
- Plugin error codes are prefixed with the plugin name, for example
  `ACE_STEP_GENERATION_FAILED`.
- `install-skill` also installs the skills of loaded plugins (`result.plugin_skills`).

Writing a plugin: see `docs/plugins.md`.

## Contributing

Development workflows (local checks, quality gates, and merge criteria) are documented in
`CONTRIBUTING.md`.

## Troubleshooting

1. Run `uv run ableton-cli doctor`.
2. Confirm Ableton is running and `AbletonCliRemote` is selected as Control Surface.
3. Confirm host/port (`127.0.0.1:8765` by default).
4. Try a longer timeout: `--timeout-ms 30000`.
5. If protocol mismatches, the installed Remote Script is from a different release:
   run `uv run ableton-cli install-remote-script --yes`, restart Ableton Live, and re-select
   `AbletonCliRemote` as Control Surface. Use `--protocol-version <n>` or
   `uv run ableton-cli config set protocol_version <n>` only to talk to a deliberately pinned
   Remote Script version.

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
