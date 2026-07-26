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
