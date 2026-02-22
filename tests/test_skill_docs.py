from __future__ import annotations

import re
from pathlib import Path

from typer.main import get_command

from ableton_cli.cli import app

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DOC = REPO_ROOT / "skills" / "ableton-cli" / "SKILL.md"
ACTIONS_DOC = REPO_ROOT / "docs" / "skills" / "skill-actions.md"

STABLE_ACTIONS = (
    "ping",
    "get_song_info",
    "song_new",
    "song_save",
    "song_export_audio",
    "get_session_info",
    "get_track_info",
    "play",
    "stop",
    "arrangement_record_start",
    "arrangement_record_stop",
    "set_tempo",
    "list_tracks",
    "create_midi_track",
    "create_audio_track",
    "tracks_delete",
    "set_track_name",
    "set_track_volume",
    "get_track_mute",
    "set_track_mute",
    "get_track_solo",
    "set_track_solo",
    "get_track_arm",
    "set_track_arm",
    "get_track_panning",
    "set_track_panning",
    "create_clip",
    "add_notes_to_clip",
    "get_clip_notes",
    "clear_clip_notes",
    "replace_clip_notes",
    "clip_duplicate",
    "set_clip_name",
    "fire_clip",
    "stop_clip",
    "list_scenes",
    "create_scene",
    "set_scene_name",
    "fire_scene",
    "scenes_move",
    "stop_all_clips",
    "get_browser_tree",
    "get_browser_items_at_path",
    "get_browser_item",
    "get_browser_categories",
    "get_browser_items",
    "search_browser_items",
    "load_instrument_or_effect",
    "load_drum_kit",
    "set_device_parameter",
    "find_synth_devices",
    "list_synth_parameters",
    "set_synth_parameter_safe",
    "observe_synth_parameters",
    "list_standard_synth_keys",
    "set_standard_synth_parameter_safe",
    "observe_standard_synth_state",
    "find_effect_devices",
    "list_effect_parameters",
    "set_effect_parameter_safe",
    "observe_effect_parameters",
    "list_standard_effect_keys",
    "set_standard_effect_parameter_safe",
    "observe_standard_effect_state",
    "execute_batch",
)


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
    assert len(STABLE_ACTIONS) == 65
    assert len(set(STABLE_ACTIONS)) == 65


def test_action_mappings_are_consistent_between_docs() -> None:
    skill_doc_mapping = _extract_skill_doc_mapping(_read(SKILL_DOC))
    action_doc_mapping = _extract_action_doc_mapping(_read(ACTIONS_DOC))

    assert set(skill_doc_mapping) == set(STABLE_ACTIONS)
    assert set(action_doc_mapping) == set(STABLE_ACTIONS)
    assert skill_doc_mapping == action_doc_mapping
    for command in skill_doc_mapping.values():
        assert command.startswith("uv run ableton-cli ")


def test_skill_doc_covers_all_leaf_cli_commands() -> None:
    markdown = _read(SKILL_DOC)
    for command in _collect_leaf_commands():
        pattern = rf"^uv run ableton-cli {re.escape(command)}(?:\s|$)"
        assert re.search(pattern, markdown, flags=re.MULTILINE), (
            f"missing command documentation for: {command}"
        )
