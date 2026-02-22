# Install ableton-cli Skill in Codex or Claude Code

Use this guide when you want to install the repository skill file into Codex or Claude Code.

## Install

Codex:

```bash
uv run ableton-cli install-skill --yes
```

Claude Code:

```bash
uv run ableton-cli install-skill --target claude --yes
```

Codex installation requires `CODEX_HOME` to be set.

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

4. Run a command using the documented skill command form:

```bash
uv run ableton-cli --output json ping
```
