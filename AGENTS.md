# AGENTS.md

## Purpose

Repository-level instructions for coding agents working on `ableton-cli`.

Keep this file stable and operational. Do not duplicate the full command catalog here. Use the source documents listed below for command coverage, action mappings, examples, and contributor workflow details.

## Project Context

`ableton-cli` is a Python CLI for controlling and inspecting Ableton Live through a local Remote Script. The project is intended for both humans and automation, so deterministic CLI behavior, stable JSON output, fixed exit codes, and explicit failures are part of the product surface.

## Non-Negotiable Principles

- **TDD:** use red -> green -> refactor for behavioral changes.
- **DRY:** do not duplicate command logic, validation, tests, fixtures, or documentation.
- **SOLID:** keep modules focused; make dependencies explicit and injectable where practical.
- **No silent degradation:** fail explicitly with the correct error code and hint.
- **No fallback execution paths:** do not add alternate analyzers, alternate transports, or best-effort branches that hide missing prerequisites.
- **No compatibility shims:** do not add deprecated aliases, dual-path behavior, or legacy adapters unless explicitly requested. If a public contract changes, update the contract artifacts instead of preserving both behaviors.

## Source of Truth

Use these repository-relative documents before changing behavior:

- `README.md` — user-facing setup, command examples, global option placement, protocol, security model, exit codes.
- `CONTRIBUTING.md` — developer workflow, public contract boundary, quality harness, merge gates.
- `skills/ableton-cli/SKILL.md` — agent-facing command catalog.
- `docs/skills/skill-actions.md` — stable automation action names and CLI mappings.
- `docs/skills/examples/*.json` — machine-oriented examples.
- `.cursor/rules/ableton-cli.mdc` — Cursor-specific conventions mirroring this file.
- `.quality-harness.yml` and `docs/quality-harness-phase2.md` — quality harness thresholds and limits.

## Repository Map

- `src/ableton_cli/` — CLI, command specs, client/runtime code, contracts, output formatting, quality harness, remix/audio modules.
- `src/ableton_cli/commands/` — command implementations and command grouping.
- `remote_script/AbletonCliRemote/` — Ableton Live Remote Script server, handlers, validators, backend registry, Live API integration.
- `tests/` — unit, contract, CLI, remote backend, docs, quality harness, and snapshot tests.
- `tests/snapshots/public_contract_snapshot.json` — public contract snapshot; update only for intentional public contract changes.
- `tools/` — generators and maintenance scripts, including public contract snapshot and skill-doc generation.
- `skills/ableton-cli/` and `docs/skills/` — automation-facing skill docs and action mappings.

## Working Rules

- Prefer deterministic command forms: `uv run ...` and `uv run ableton-cli ...`.
- Global CLI options must appear before the subcommand: `uv run ableton-cli --output json doctor`, not `uv run ableton-cli doctor --output json`.
- Use `--output json` for automation-facing command output and tests.
- Keep changes minimal, coherent, and scoped to the requested behavior.
- Preserve the JSON envelope shape unless the task explicitly changes a public contract.
- Preserve fixed exit-code behavior unless the task explicitly changes a public contract.
- Do not hide invalid configuration, unsupported Live API behavior, missing tools, or protocol mismatches behind permissive defaults.
- Do not hard-code Ableton browser catalog URIs, pack names, locale-dependent paths, or user-library assumptions. Discover browser targets first and use returned `uri` or `path` values.
- Prefer stable selectors and refs over ambiguous positional assumptions when a command supports them.
- Keep generated documentation and snapshots in sync with source changes.

## Public Contract Changes

Treat these as public/stable contracts:

- README command surface and documented command behavior.
- JSON output envelope fields: `ok`, `command`, `args`, `result`, `error`.
- CLI exit codes and documented error codes.
- TCP JSONL protocol request/response envelope and protocol-version behavior.
- `tests/snapshots/public_contract_snapshot.json`.
- Stable action names and CLI mappings in `docs/skills/skill-actions.md`.

When a public contract intentionally changes:

1. Add or update tests that fail before the implementation change.
2. Update the implementation.
3. Update user-facing docs and skill/action docs.
4. Regenerate the public contract snapshot:

       uv run python tools/update_public_contract_snapshot.py

5. Regenerate generated skill docs when command docs or mappings change:

       uv run python tools/generate_skill_docs.py
       git diff --exit-code

Do not update snapshots or generated docs to mask accidental API drift.

## Remote Script and Protocol Rules

- Keep the CLI/client and Remote Script protocol behavior explicit and version-aware.
- Validate request arguments before mutating Ableton state.
- Return structured errors with actionable hints rather than raising opaque exceptions through the protocol boundary.
- Keep Remote Script handlers small; put reusable selection, validation, and Live-object access logic in shared helper modules.
- Do not assume Ableton Live is running in tests unless the test explicitly targets integration behavior.
- For new Remote Script commands, update command registry/capability exposure, CLI command specs, protocol tests, backend tests, and public contract artifacts as applicable.

## Ableton Operation Safety

Commands can mutate a user's Live Set. For agent-driven operation or manual verification against a running Ableton instance:

- Run high-timeout preflight before mutating state:

       uv run ableton-cli --timeout-ms 15000 --output json wait-ready
       uv run ableton-cli --timeout-ms 15000 --output json doctor
       uv run ableton-cli --timeout-ms 15000 --output json tracks list

- Prefer `--read-only` for inspection.
- Use `--plan` or `--dry-run` where supported before write/destructive operations.
- Use explicit selectors such as `--track-index`, `--track-name`, `--selected-track`, `--track-query`, or `--track-ref`; do not rely on the current selection unless the task requires it.
- Treat `song new`, `tracks delete`, clip deletion, file replacement, routing changes, export, save, and mastering apply operations as destructive or user-visible.

## Audio Analysis Rules

- Offline audio analysis with the `ffmpeg` engine requires both `ffmpeg` and `ffprobe` on `PATH`.
- If either tool is missing, preserve the explicit `CONFIG_INVALID` failure.
- Do not add fallback analyzers, silently skip metrics, or reinterpret missing analysis data as success.

## Security Rules

- The Remote Script protocol is local TCP JSONL on `127.0.0.1:<port>` and has no authentication.
- Never expose, forward, or bind the Remote Script port to untrusted networks.
- Treat write commands as equivalent to direct user operation in Ableton Live.
- Do not log secrets, absolute private paths, or large user payloads unless required for a test fixture or explicit diagnostic output.
- Avoid network access in tests and tools unless the task explicitly requires it.

## Validation Before Handoff

Run the smallest meaningful checks during iteration, then the full gate before handoff when feasible.

Baseline validation:

    uv run python -m ableton_cli.dev_checks
    uv run ruff check .
    uv run ruff format --check .
    uv run pytest

Quality harness enforcement:

    uv run python -m ableton_cli.dev_checks_enforce --config .quality-harness.yml --report quality-harness-report.json --action-log quality-harness-action-log.json

For packaging or CI-parity changes, also verify:

    uv run ableton-cli --help
    uv run ableton-cli --version
    uv run python -m build

For command docs or generated skill docs:

    uv run python tools/generate_skill_docs.py
    git diff --exit-code

If a check cannot be run, state exactly why and list the narrower checks that were run.

## Handoff Format

When finishing a task, report:

- changed files and the reason for each change;
- public contract impact: none, intentional change, or uncertain;
- validation commands run and results;
- validation not run and the reason;
- any follow-up needed for Ableton Live manual verification.

## Out of Scope for This File

- Full command catalogs.
- Per-session skill availability lists.
- Host/user-specific setup notes.
- Long troubleshooting guides that belong in docs.
- Generated output snapshots or command examples beyond minimal workflow snippets.
