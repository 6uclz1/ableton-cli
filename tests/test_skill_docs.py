from __future__ import annotations

import re
import subprocess
from pathlib import Path

from typer.main import get_command

from ableton_cli.actions import (
    STABLE_ACTION_MAPPINGS,
    stable_action_command_map,
    stable_action_names,
)
from ableton_cli.cli import app

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DOC = REPO_ROOT / "skills" / "ableton-cli" / "SKILL.md"
ACTIONS_DOC = REPO_ROOT / "docs" / "skills" / "skill-actions.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_frontmatter_keys(markdown: str) -> list[str]:
    match = re.match(r"^---\n(.*?)\n---\n", markdown, flags=re.DOTALL)
    assert match is not None, "missing YAML frontmatter"
    frontmatter = match.group(1)
    keys: list[str] = []
    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        key, separator, _value = line.partition(":")
        assert separator == ":", f"invalid frontmatter line: {raw_line!r}"
        keys.append(key.strip())
    return keys


def _extract_skill_doc_mapping(markdown: str) -> dict[str, str]:
    pattern = re.compile(
        r"^- `(?P<action>[a-z_]+)` -> `(?P<command>uv run ableton-cli [^`]+)`$",
        flags=re.MULTILINE,
    )
    matches = pattern.findall(markdown)
    return {action: command for action, command in matches}


def _extract_action_doc_mapping(markdown: str) -> dict[str, str]:
    pattern = re.compile(
        r"^\| `(?P<action>[a-z_]+)` \| `(?P<command>uv run ableton-cli [^`]+)` \| [^|]+ \|$",
        flags=re.MULTILINE,
    )
    matches = pattern.findall(markdown)
    return {action: command for action, command in matches}


def _collect_leaf_commands() -> list[str]:
    root_command = get_command(app)
    leaf_commands: list[str] = []

    def walk(group, prefix: str = "") -> None:
        for name, command in group.commands.items():
            path = f"{prefix} {name}".strip()
            children = getattr(command, "commands", None)
            if children:
                walk(command, path)
                continue
            leaf_commands.append(path)

    walk(root_command)
    return sorted(leaf_commands)


def test_skill_doc_frontmatter_is_minimal() -> None:
    keys = _extract_frontmatter_keys(_read(SKILL_DOC))
    assert keys == ["name", "description"]


def test_stable_action_names_are_complete_and_unique() -> None:
    names = stable_action_names()
    assert len(STABLE_ACTION_MAPPINGS) == 75
    assert len(names) == 75
    assert len(set(names)) == 75


def test_action_mappings_are_consistent_between_docs() -> None:
    skill_doc_mapping = _extract_skill_doc_mapping(_read(SKILL_DOC))
    action_doc_mapping = _extract_action_doc_mapping(_read(ACTIONS_DOC))
    expected_action_names = set(stable_action_names())
    expected_mapping = stable_action_command_map()

    assert set(skill_doc_mapping) == expected_action_names
    assert set(action_doc_mapping) == expected_action_names
    assert skill_doc_mapping == expected_mapping
    assert action_doc_mapping == expected_mapping
    for command in skill_doc_mapping.values():
        assert command.startswith("uv run ableton-cli ")


def test_skill_doc_covers_all_leaf_cli_commands() -> None:
    markdown = _read(SKILL_DOC)
    for command in _collect_leaf_commands():
        pattern = rf"^uv run ableton-cli {re.escape(command)}(?:\s|$)"
        assert re.search(pattern, markdown, flags=re.MULTILINE), (
            f"missing command documentation for: {command}"
        )


def test_generated_skill_docs_are_up_to_date() -> None:
    result = subprocess.run(
        ("uv", "run", "python", "tools/generate_skill_docs.py", "--check"),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
