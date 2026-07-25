# Contributing to ableton-cli

This document covers developer workflows for local validation, quality gates, and pre-merge checks.

## Development

```bash
uv sync
uv run python -m ableton_cli.dev_checks
uv run ableton-cli --help
uv run ableton-cli --version
```

## Public Contract Boundary

The following are treated as public/stable contracts:

- README command surface (`song`, `transport`, `track`, `tracks`, `clip`, `arrangement`, `browser`, `device`, `synth`, `effect`, `batch`, `setup`)
- JSON output envelope shape (`ok`, `command`, `args`, `result`, `error`)
- fixed CLI exit codes and documented error codes
- TCP JSONL protocol request/response envelope and protocol versioning rules
- `tests/snapshots/public_contract_snapshot.json`

Before merge, regenerate snapshot only when you intentionally change a public contract:

```bash
uv run python tools/update_public_contract_snapshot.py
```

Internal modules (for example, `src/ableton_cli/commands/_*.py` and quality harness internals) can be refactored freely as long as public contracts and tests stay green.

## Single-Source Argument Shape Pattern

When an argument shape (for example MIDI note fields) is validated on both the CLI and the Remote Script, define it once as a data table of field specs rather than duplicating per-field checks. The CLI and the Remote Script run in separate Python runtimes and cannot share an import (the Remote Script cannot import `ableton_cli`), so each side keeps its own copy of the spec table (see `src/ableton_cli/note_fields.py` and `remote_script/AbletonCliRemote/note_fields.py`). A drift test (see `tests/test_note_field_specs.py`) asserts the two copies stay identical, so the pair behaves as a single source of truth even though the code is physically duplicated. Prefer this pattern over hand-writing the same field-by-field validation twice.

## Commit Hook (Ruff)

Enable repository-managed git hooks to run Ruff on every commit:

```bash
./scripts/install_git_hooks.sh
```

This installs `.githooks/pre-commit`, which runs:

- `uv run ruff check .`
- `uv run ruff format --check .`

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

Run with baseline comparison (this is what CI does):

```bash
uv run python tools/quality_harness.py --config .quality-harness.yml --report quality-harness-report.json --baseline quality-harness-baseline.json
```

`quality-harness-baseline.json` is committed and records the violations the
repository is currently carrying. With a baseline in play the harness gates
**regressions only**: a fail-level violation whose signature is already in the
baseline is reported with `baselined: true` and does not fail the run. That
keeps the harness useful as a ratchet instead of a wall of pre-existing debt
nobody can act on.

Regenerate the baseline only when the accepted debt genuinely changes, and say
why in the commit message:

```bash
uv run python tools/update_quality_harness_baseline.py
```

Exit codes:

- `0`: no new fail-level violations
- `1`: fail-level violations not present in the baseline
- `2`: invalid config/runtime error

Harness reports (`quality-harness-report.json`, `quality-harness-action-log.json`)
and anything under `output/` are build artifacts: CI uploads them, and they are
not committed.

Default thresholds in `.quality-harness.yml` are calibrated for this repository's current shape (warn-heavy, fail-guarded).
They are intended to keep CI fail-level guardrails active while surfacing refactoring candidates as warnings.

Detailed specification and known limits:

- `docs/quality-harness-phase2.md`

## Merge Gate

Before merge, wait until all required checks are green on the PR head commit:

```bash
gh pr checks --watch
```

`main` is protected with required status checks:

- `test (macos-latest)`
- `test (windows-latest)`
- `quality-harness`

Do not merge while any required check is pending or failing.
