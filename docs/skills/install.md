# Install ableton-cli Skill in Codex

Use this guide when you want to install the repository skill file into your local Codex skills directory.

## Install

```bash
mkdir -p "$CODEX_HOME/skills/ableton-cli"
cp /Users/6uclz1/ws/ableton-cli/skills/ableton-cli/SKILL.md "$CODEX_HOME/skills/ableton-cli/SKILL.md"
```

## Verify

1. Open the Codex Skills list and confirm `ableton-cli` is shown.
2. Verify the installed file exists:

```bash
ls "$CODEX_HOME/skills/ableton-cli/SKILL.md"
```

3. Run a command using the documented skill command form:

```bash
uv run ableton-cli --output json ping
```
