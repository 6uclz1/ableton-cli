# Computer Use Playbooks

Agent-facing procedures for the Ableton Live work that `ableton-cli` cannot do because the Live API
does not expose it. Use these only after confirming that no CLI command covers the step.

## When to fall back

1. Try the CLI first (`skills/ableton-cli/SKILL.md`). Native Live devices are fully readable and
   writable through `device parameters list`, `device parameter set-display`, and
   `device parameter select`. Leaving a native device at its defaults is a choice, not an API limit.
2. If the CLI fails with `not_supported_by_live_api`, or the target is not exposed at all (for
   example a plug-in that lists only `Device On`), check [cli-gaps.md](cli-gaps.md).
3. If the gap is listed there, do that step with Computer Use following the linked playbook,
   then return to the CLI for everything else.
4. If the gap is new, do it with Computer Use, then add it to `cli-gaps.md` and the matching
   playbook.

A Computer Use fallback is an explicit, reported step. It never replaces a CLI failure silently:
report which steps ran through the GUI and why.

## Rules

- Run the CLI preflight (`wait-ready`, `doctor`, `tracks list`) before any GUI work.
- Request access to Ableton Live only. Plug-in windows belong to Live's process.
- Verify each GUI change, either with a zoomed screenshot or by reading it back through the CLI
  (for example `device parameters list` after Configure).
- Prefer making a parameter CLI-reachable over repeating GUI edits. Configure a plug-in parameter
  once, then drive it from the CLI.
- Saving, overwriting, and file dialogs are user-visible. Save only a new or agent-created set
  unless the user asks you to save theirs.

## Pages

- [cli-gaps.md](cli-gaps.md): which operations need Computer Use, and why.
- [ableton-live.md](ableton-live.md): Live 12 GUI procedures (Configure, modulator mapping,
  arrangement automation, saving) and input tips.
- [plugins/serum-2.md](plugins/serum-2.md): Serum 2 presets, macros, and FX.

## Adding a page

- Use one page per application area or plug-in, and put plug-in pages under `plugins/`.
- Link every page from this index. `tests/test_docs_hygiene.py` enforces this.
- Write procedures in terms of on-screen labels, not screen coordinates. Coordinates change with
  window layout.
- Record the Live and plug-in versions you verified against.
- Keep host-specific paths and user names out of these pages.
