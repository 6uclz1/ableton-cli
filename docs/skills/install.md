# Install ableton-cli Skill in Codex, Claude Code, or Cursor

Use this guide when you want to install the repository skill file into Codex, Claude Code, or Cursor.

## Install

Codex:

```bash
uv run ableton-cli install-skill --yes
```

Claude Code:

```bash
uv run ableton-cli install-skill --target claude --yes
```

Cursor:

```bash
uv run ableton-cli install-skill --target cursor --yes
```

Codex installation requires `CODEX_HOME` to be set.

For Cursor users opening this repository directly, no install step is required:
the project ships `.cursor/rules/*.mdc` and `.cursor/skills/ableton-cli/SKILL.md`,
so the agent loads ableton-cli conventions automatically. Use the `--target cursor`
command above only to mirror the same skill into the user-level Cursor skills
folder so it is available in other workspaces too.

## Verify

1. Open the relevant Skills list and confirm `ableton-cli` is shown.
2. Verify the installed file exists (Codex):

```bash
ls "$CODEX_HOME/skills/ableton-cli/SKILL.md"
```

3. Verify the installed file exists (Claude Code):

```bash
ls "$HOME/.claude/skills/ableton-cli/SKILL.md"
```

4. Verify the installed file exists (Cursor):

```bash
ls "$HOME/.cursor/skills/ableton-cli/SKILL.md"
```

5. Run a command using the documented skill command form:

```bash
uv run ableton-cli --output json ping
```
