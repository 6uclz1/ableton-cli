# Command-definition refactor: findings

Things noticed while consolidating command definitions into
`src/ableton_cli/command_registry.py`. Nothing here is fixed as part of the
refactor: the refactor's contract is that the public surface does not move by a
single byte, and every item below would move it. Each needs its own change, its
own justification, and its own snapshot update.

## Pre-existing, not caused by the refactor

### quality harness baseline is stale on `main`

`quality-harness-baseline.json` records 0 failures and 395 warnings. On `main`,
before any refactor commit, `dev_checks_enforce` reports 1 failure and 419
warnings and exits 1. The failure is:

    src/ableton_cli/commands/_arrangement_clip_commands.py::register_commands
    function.estimated_tokens 951.0 >= 950.0

Verified by running the harness on a clean stash of `main` — the numbers are
identical with and without the Phase 0/1 changes. Phase 1 brings warnings down
by one (419 → 418) and adds no new violations.

Phase 5 covers baseline regeneration. The `register_commands` size violation
should be fixed rather than baselined.

## Deviations from the plan

### Client argument specs are keyed by remote command, not hung off `CommandDescriptor`

The plan sketched `ClientArgSpec` as a field on `CommandDescriptor`. That does
not fit the data: the mapping from CLI command to client method is many-to-one.
All four `master effect <type> keys` commands call one `master_effect_keys`
client method, and the six `effect <type> keys` commands call one
`list_standard_effect_keys`. Putting the argument spec on the descriptor would
duplicate the same parameter list across every sharing command and let the
copies drift.

`CLIENT_METHOD_SPECS` is therefore a second table in the same module, keyed by
remote command name — which for all 123 generated methods is also the Python
method name. `tests/test_client_method_generation.py` asserts every key is a
declared remote command, so the two tables cannot drift apart.

Everything else about the plan's Phase 2 is unchanged: the table lives in the
core layer, the generated file is checked in, and CI regenerates it and fails
on a diff.

### The other generator tools write with the platform's line ending

`tools/update_command_surface_snapshot.py` now passes `newline="\n"` to
`write_text`, because a byte-level test caught it rewriting every line ending
when run on Windows. The same latent inconsistency exists in
`tools/update_public_contract_snapshot.py`, `tools/generate_skill_docs.py` and
`tools/update_quality_harness_baseline.py`, which all call `write_text` without
it.

It is currently harmless: `.gitattributes` pins the repo to `eol=lf`, so `git
diff --exit-code` normalises the difference away and CI stays green. It only
surfaces if something compares bytes without going through git. Left alone
here rather than swept into a refactor PR.

## Observations to revisit after the refactor

### The plan's command counts were stale

The plan quotes 191 public commands and 159 remote handler entries. The actual
figures at the start of the work were 250 and 161. This changes no decision —
it makes the descriptor table larger, not different — but any effort estimate
derived from those numbers is low by ~30%.

### `remote_command_spec_map()` merges names it cannot distinguish

Several CLI commands share one remote command (`clip notes import-browser` and
`browser load` both dispatch `load_instrument_or_effect`). The merged entry
keeps the first CLI name in sorted order, which is not an identity, and merges
side effects on the safe side. This is deliberate and documented at the
function, but it means a batch step naming `load_instrument_or_effect` is
governed by the *strictest* of the sharing commands rather than by the one the
caller meant. Worth revisiting if batch steps ever need per-command policy.

### `idempotent` is currently a synonym for `kind == "read"`

Every row in the table uses one of three shared side-effect constants, and in
all three `idempotent` is exactly `kind == "read"`. Several writes are in fact
idempotent (`track volume set` with the same value, `clip name set`). Promoting
them one at a time would make `--dry-run`/retry policy more useful, but each
promotion is a public contract change.
