# AGENTS.md

## Purpose
- Repository-level instructions for coding agents working in `ableton-cli`.
- Operational command catalogs stay in README; this file stays stable.

## Non-Negotiable Principles
- `TDD`: implement with red -> green -> refactor.
- `DRY`: avoid duplicated logic, tests, and documentation.
- `SOLID`: keep responsibilities narrow and dependencies explicit.
- `No Fallbacks`: do not add fallback execution paths.
- `No Backward Compatibility`: do not preserve legacy behavior unless explicitly requested.

## Working Rules
- Prefer deterministic command forms: `uv run ...` and `uv run ableton-cli ...`.
- Keep changes minimal and coherent.
- Fail explicitly; do not silently degrade behavior.
- Do not add compatibility shims, deprecated aliases, or dual-path logic.

## Validation Before Handoff
- `uv run python -m ableton_cli.dev_checks`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest`

## Source Documents
- `/Users/6uclz1/ws/ableton-cli/README.md`
- `/Users/6uclz1/ws/ableton-cli/CONTRIBUTING.md`
- `/Users/6uclz1/ws/ableton-cli/skills/ableton-cli/SKILL.md`
- `/Users/6uclz1/ws/ableton-cli/docs/skills/skill-actions.md`
- `/Users/6uclz1/ws/ableton-cli/.cursor/rules/ableton-cli.mdc`

## Out of Scope for This File
- No per-session skill availability lists.
- No duplicated full command references from README.
- No host/user-specific ephemeral setup notes.
