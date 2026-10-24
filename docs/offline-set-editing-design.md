# Offline Live Set editing (`set` command group): design proposal

Status: phase 1 (`set inspect`, `set lint`, `set diff`) is implemented, and so is
`set automation write` from phase 3 (with `save.py` for the shared output rules). The
rest of phases 2-4 are proposals. Every item here changes the public surface and lands through the normal
TDD + contract-update workflow in `CONTRIBUTING.md`.

## 1. Why

`ableton-cli` today drives Live exclusively through the Remote Script and the
Live Object Model (LOM). Some operations are not reachable that way at all, and
project setup is a long sequence of round trips against a running Live.

A Live Set (`.als`) is gzip-compressed XML. Editing it directly fills both gaps:

| Capability | Remote Script today | Offline `.als` editing |
| --- | --- | --- |
| Create group tracks / group existing tracks | No LOM API; no CLI command | Set `TrackGroupId` and insert a `GroupTrack` |
| Arrangement automation (mixer, sends, device params, tempo) | Clip envelopes only | Write `AutomationEnvelope` events directly |
| Curved automation segments | Not exposed | `CurveControl1X/Y`, `CurveControl2X/Y` on events |
| Locators at arbitrary positions with names | No CLI command | Write `Locators/Locators/Locator` |
| Device internal state (Simpler/Sampler sample, rack chains, plug-in state) | Only parameters the LOM exposes | Splice a device element from an `.adv` / `.adg` preset (same XML format) |
| Inspect, lint, diff without Live running | Requires Live | Pure file operation, CI-friendly |
| Large edits (thousands of notes) | One request per operation | Single in-memory pass |
| Project bootstrap | Many write commands against a running Live | One generated set from a declarative spec |

The trade-off: a set that is open in Live cannot be edited in place. Offline
commands are pre- and post-processing steps that write a new file the user then
opens. They are not live control.

### Feasibility evidence (Live 12.4.6, investigated 2026-10-20)

- Parsing and re-serialising three real sets (11 MB to 27 MB of XML) with the
  standard library gives canonical XML identical to the input.
- Edited sets (tempo, track rename, MIDI transpose + note insert, full track
  duplication) load in Live 12.4.6 with no load errors. The edits were confirmed
  through the Remote Script (`song info`, `tracks list`, `clip notes get`).
- Locators written by Python `xml.etree` load correctly (from an earlier session's
  work).
- Pitfalls found, each of which the design has to handle:
  1. **Global pointee ID space.** `Id` on `AutomationTarget`, `*ModulationTarget`,
     `Pointee` and `ControllerTargets.N` is unique across the document, must be
     `< NextPointeeId`, and is referenced by `PointeeId`. With that tag set, every
     `PointeeId` in Live-saved files resolves and none collide. Copying a subtree
     without remapping these IDs produced 131 collisions.
  2. **Automation overrides `Manual`.** Arrangement envelopes carry a default
     event at `Time="-63072000"`. Changing only `Tempo/Manual` had no effect in
     Live until that event was updated as well.
  3. **Relative media paths.** Sample references resolve against the project
     folder. A set written outside its project folder loses its project-local
     audio.
  4. **Per-clip note IDs.** New notes need `NoteIdGenerator/NextId` advanced.
  5. **Undocumented format.** Structure may change between Live versions.

## 2. Scope

In scope:

- Read-only inspection, lint and semantic diff of `.als` files.
- `set init`: generate a new set from a declarative spec.
- Write operations that the Remote Script cannot perform (groups, arrangement
  automation, locators, device import from presets).

Non-goals:

- Offline copies of operations the Remote Script already supports (note editing,
  tempo on an open set, clip properties). Per `AGENTS.md`, there is one execution
  path per operation.
- Falling back from Remote Script to file editing (or the reverse) automatically.
  The `set` group is a separate, explicitly chosen surface.
- Editing a set in place, or a set that is open in Live.
- Opening the result in Live. The user (or agent) does that explicitly.

## 3. Command surface

All commands are CLI-local (`remote_command=None` in `command_registry.py`) and
go through `runtime.execute_command`, so `--output json`, `--read-only`,
`--plan` and `--dry-run` behave as they do for every other command.

| Command | Side effect | Purpose |
| --- | --- | --- |
| `set inspect --path PATH` | read | Version, effective tempo, time signature, scale, tracks (index, type, name, group, devices, clip counts), returns, scenes, locators, plug-in inventory |
| `set lint --path PATH` | read | Integrity (ID uniqueness, dangling `PointeeId`, `NextPointeeId`), missing project samples, unchecked-sample counts |
| `set diff --from A --to B` | read | Semantic diff over the `set inspect` summary, tracks matched by set-local ID |
| `set init --spec SPEC --out DIR [--template PATH]` | write | Build a new project from a spec |
| `set group create PATH --track-index ... --name NAME --out OUT` | write | Group existing tracks |
| `set locators replace PATH --locators-json JSON --out OUT` | write | Replace all locators |
| `set automation write --path PATH <selector> --target T --points-json JSON --out OUT` | write (implemented) | Write an arrangement envelope (replaces the lane) |
| `set device import PATH <selector> --preset FILE --index N --out OUT` | write | Insert a device from an `.adv` / `.adg` |

Path arguments are options (`--path`, `--from`, `--to`), matching `session diff` and
the `audio` commands.

Phase 1 findings from real sets, now part of the contract:

- Track names: Live displays `Name/UserName` when it is non-empty, otherwise the
  auto-generated `Name/EffectiveName`. Reading `EffectiveName` alone reported stale
  names for renamed tracks.
- Tempo: `set inspect` reports the effective value (the envelope's default event
  overrides `Manual`) plus `tempo_automated`.
- Samples: only `SampleRef/FileRef` is media; other `FileRef` elements record preset
  or device provenance. Project-relative samples (`RelativePathType` 3) resolve against
  the project folder only, as Live does. Library-relative types (5, 6, 7 observed) carry
  `Path` values from other machines, and Live resolves them against local libraries
  the CLI must not assume. They are reported as unchecked counts in `result.media`,
  never as missing or present.

Rules shared by every write command:

- `--out` is required, must differ from the input, and must not exist. There is
  no in-place mode and no overwrite flag, so the source file is never modified.
- Integrity validation runs on the in-memory document before writing. A failure
  aborts without creating the output file.
- Output is written atomically (temporary file in the target directory, then
  rename).
- The result reports a change summary (what was added or changed, allocated ID
  range) so the JSON output is deterministic and assertable.

Selectors reuse existing flag names (`--track-index`, `--track-name`) and shared
validation from `commands/_validation.py`. Selection is resolved against the
file, never against a running Live.

Automation targets (`--target`), as implemented: `mixer.volume`, `mixer.pan`,
`mixer.tempo` (main track only), `send.<return index>`, and
`device.<top-level device index>.<parameter XML tag>`. Selectors: `--track-index`,
`--track-name`, `--return-track-index`, `--main`. Points are
`[{"time": beats, "value": number}]` (curves stay in phase 4). Values are Live's internal
parameter values, validated against the parameter's `MidiControllerRange` (tempo against
20-999 BPM, because its `MidiControllerRange` is only the MIDI-mapping range).

Decisions taken while implementing, from Live 12.4.6 saved sets:

- Verified in Live 12.4.6: a written `Filter_Frequency` lane on Auto Filter played back
  at the written Hz values, and a send lane followed the written linear-gain values
  (internal `Send` 0.5 read back as LOM value 0.8, about -6 dB).
- Sends are addressed by return index, not return name: names are not unique and may
  contain the separator.
- Only continuous parameters are written, as `FloatEvent`s. In Live-saved sets they are
  exactly the ones with a `*ModulationTarget`; choice parameters (EQ Eight `Mode`,
  Compressor `Model`) have only `AutomationTarget` + `MidiControllerRange` and are
  automated with `EnumEvent`, and on/off parameters carry `MidiCCOnOffThresholds`. Both
  are rejected rather than written with the wrong event type.
- Device parameters use XML tags, and the error for an unknown tag lists the writable
  tags (`details.available_parameters`), which answers the naming open question for v1.

### Naming: `set init`, not top-level `init`

`remix init` already exists and creates a remix manifest. A top-level `init`
would read as "initialise the CLI or config". `set init` keeps the operation in
the group whose output it produces.

## 4. Init spec format

TOML, parsed with `tomli` (already a dependency, used by `config.py`), so no new
dependency is added. The spec is versioned, and `schema` is required.

```toml
schema = 1
name = "Afterglow"              # project folder "<name> Project/<name>.als"

[song]
tempo = 128
time_signature = "4/4"
scale = { root = "A", name = "Minor" }

[structure]
template = "anime-club"         # reuses remix/templates.py sections -> locators
# or: sections = [{ name = "intro", bars = 8 }, { name = "drop", bars = 32 }]

[[groups]]
name = "Rhythm"
color = 3

[[tracks]]
name = "Drums"
type = "midi"                   # midi | audio
group = "Rhythm"
color = 3
devices = [{ preset = "presets/Drums.adg" }]   # explicit paths, relative to the spec

[[tracks]]
name = "Vox"
type = "audio"

[[returns]]
name = "A-Reverb"
devices = [{ preset = "presets/Hall.adv" }]
```

Validation rules:

- Unknown keys are errors, not ignored.
- Every error reports the spec path (`tracks[1].group`), exits with
  `INVALID_ARGUMENT`, and includes a hint.
- Preset paths are explicit and must exist. There is no catalog lookup and no
  guessing of Core Library or User Library locations (`AGENTS.md`: no hard-coded
  browser or library paths).
- `structure.template` and `structure.sections` are mutually exclusive.

Template resolution: `--template PATH` if given. Otherwise, use the
`DefaultLiveSet.als` inside the installed Live application, located through the
existing `platform_paths` discovery. If neither resolves, fail with
`CONFIG_INVALID`. New tracks and returns are cloned from prototype tracks in the
template, with IDs remapped, so the tool never embeds hand-written Live XML for
whole tracks.

## 5. Module layout

New core package `src/ableton_cli/liveset/`. It must not import
`ableton_cli.commands` or the client, and `tests/test_layering.py` is extended to
enforce that.

| Module | Responsibility |
| --- | --- |
| `document.py` | Load (gzip + XML) in phase 1; atomic save and output-path rules in phase 2 |
| `schema.py` | Supported-version gate (`MajorVersion`, `MinorVersion`, `Creator`) |
| `ids.py` | Global pointee-ID tag set (phase 1); allocator and subtree remap (phase 2) |
| `integrity.py` | Validation run before every save and by `set lint` |
| `model.py` | Strict element access (`SET_SCHEMA_UNSUPPORTED` on missing structure), envelope lookup; selector resolution in phase 3 |
| `media.py` | Project-sample resolution and unchecked-sample counts |
| `findings.py` | Lint finding type with capped item lists |
| `ops/groups.py`, `ops/locators.py`, `ops/automation.py`, `ops/devices.py`, `ops/tracks.py` | One edit each: take a document, mutate it, return a change summary |
| `spec.py` | Init spec dataclasses and validation |
| `init.py` | Template plus spec, then ordered ops |
| `inspect.py`, `lint.py`, `diff.py` | Read-only reports (`diff` reuses `session_diff`) |

The CLI layer is `commands/liveset.py` (Typer wiring only) plus registry rows. Each op
is a plain function over an injected document, so it is unit-testable without
Typer or the file system. Keep functions small enough to stay inside the
`.quality-harness.yml` function thresholds.

## 6. Error contract

New error codes, no new exit codes:

| Error code | Exit code | When |
| --- | --- | --- |
| `SET_FILE_INVALID` | 2 `INVALID_ARGUMENT` | Not gzip, not XML, or root is not `<Ableton>` |
| `SET_SCHEMA_UNSUPPORTED` | 2 `INVALID_ARGUMENT` | Version outside the verified range |
| `SET_INTEGRITY_FAILED` | 20 `EXECUTION_FAILED` | Validation failed before a write (a bug or a corrupt input) |

Spec errors and output-path errors use the existing `INVALID_ARGUMENT`, with
`details.spec_path` or `details.out`. A missing template uses `CONFIG_INVALID`.
`set lint` reports findings in `result`, and exits non-zero (`SET_INTEGRITY_FAILED`)
only for error-severity findings.

The supported-version gate starts at Live 12.x (`MinorVersion` prefix `12.`,
verified on 12.4.5 and 12.4.6). Widening it requires a verification run (see the
test strategy).

## 7. Test strategy

- TDD per op: a failing structural test first, then the implementation.
- Fixtures: Live's bundled templates and user sets cannot be committed
  (licensing and privacy). Tests build minimal synthetic sets with
  `tests/liveset/builders.py`, modelled on the structure observed in Live-saved
  files, including `ControllerTargets.N` and the default envelope event.
- Unit tests:
  - `ids`: allocation, subtree remap (all four tag families), dangling and
    duplicate detection.
  - `io` and `schema`: invalid gzip or XML, wrong root, unsupported version, output
    exists, atomic write leaves no partial file.
  - Each op: before/after structure, change summary, integrity holds afterwards
    (one parametrized test over every op).
  - Regression tests: tempo or parameter change updates the default envelope event
    (pitfall 2), and new notes advance `NoteIdGenerator` (pitfall 4).
  - `spec`: each validation error reports the right `spec_path`, and unknown keys
    are rejected.
  - `init` end to end on a synthetic template.
- CLI and contract tests: JSON envelope per command, `--read-only` rejects write
  `set` commands, `--dry-run` and `--plan` create no file, and registry/CLI parity
  and snapshot tests pick up the new rows.
- Real-file verification is opt-in. A pytest marker `live_files` reads sets from
  a directory named by an environment variable and is skipped with an explicit
  reason when the variable is unset. A manual procedure (documented with the
  feature) opens the output in Live and checks it through the Remote Script
  (`song info`, `tracks list`, `clip notes get`), as done in the feasibility
  investigation. A new Live version enters the supported range only after this
  passes.

## 8. Public contract impact

Intentional additions, no breaking changes:

- New command rows, so both `command_surface_snapshot.json` and
  `public_contract_snapshot.json` must be regenerated.
- New `ErrorCode` values (`SET_FILE_INVALID`, `SET_SCHEMA_UNSUPPORTED`,
  `SET_INTEGRITY_FAILED`).
- The init spec `schema = 1` becomes a public contract, documented alongside the
  feature.
- README gets an "Offline set editing" section. `skills/ableton-cli/SKILL.md`,
  `docs/skills/skill-actions.md` (new actions such as `inspect_set`, `lint_set`,
  `init_set`) and `docs/skills/examples/*.json` must be updated, and the generated
  skill docs regenerated.

Unchanged: the JSON envelope fields, exit codes, the TCP JSONL protocol, and the
Remote Script.

## 9. Phases (one PR each)

1. `io`, `schema`, `ids`, `integrity`, `model` plus `set inspect`, `set lint` and
   `set diff`. Read-only, low risk, and the base everything else builds on.
2. `set init`: template, tracks, groups, returns, locators, tempo, time
   signature, scale and device presets.
3. Write ops on existing sets: `group create`, `locators replace`,
   `automation write`, `device import`.
4. Later: send levels and volumes in dB, sidechain routing, and device
   parameters by display value.

## 10. Risks and open questions

- **Group tracks are not verified in Live yet.** Only one bundled template
  contains a `GroupTrack`. Phase 2 starts by verifying a generated group in Live.
- **Parameter naming mismatch.** The Remote Script exposes parameter keys derived
  from LOM names (for example `filter_cutoff`), while the XML uses element tags.
  Should `device.<index>.<parameter>` use XML tags, which `set inspect` would
  expose, or a shared mapping? A mapping avoids two vocabularies but needs per-device
  tables.
- **Display units.** Volume and send in dB, and frequencies in Hz, need Live's
  value curves. These stay out of v1 (phase 4).
- **Project Info folder.** Whether `set init` must create `Ableton Project Info/`
  or can leave it to Live's first save needs checking.
- **Format drift.** The strict version gate plus the opt-in real-file suite are
  the mitigation. There is no best-effort parsing of unknown versions.
