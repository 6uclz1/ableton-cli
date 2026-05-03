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
- Offline audio analysis commands that use the `ffmpeg` engine require both `ffmpeg`
  and `ffprobe` to be installed. If they are missing, keep the explicit
  `CONFIG_INVALID` failure; do not add fallback analyzers or silently skip metrics.

## Validation Before Handoff
- `uv run python -m ableton_cli.dev_checks`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest`

## Source Documents
Paths are repository-relative.

- `README.md`
- `CONTRIBUTING.md`
- `skills/ableton-cli/SKILL.md`
- `docs/skills/skill-actions.md`
- `.cursor/rules/ableton-cli.mdc`

## Out of Scope for This File
- No per-session skill availability lists.
- No duplicated full command references from README.
- No host/user-specific ephemeral setup notes.
