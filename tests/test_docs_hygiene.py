from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_DOC = REPO_ROOT / "README.md"
PROTOCOL_DOC = REPO_ROOT / "docs" / "protocol.md"
QUALITY_HARNESS_TODO_DOC = REPO_ROOT / "docs" / "quality-harness-todo.md"
GENERATED_MAN_DOC = REPO_ROOT / "docs" / "man" / "generated" / "ableton-cli.1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_removed_docs_do_not_exist() -> None:
    assert not PROTOCOL_DOC.exists()
    assert not QUALITY_HARNESS_TODO_DOC.exists()


def test_readme_includes_protocol_section() -> None:
    markdown = _read(README_DOC)
    assert "## Protocol" in markdown


def test_generated_man_uses_stable_command_name() -> None:
    man_page = _read(GENERATED_MAN_DOC)
    assert "tmp." not in man_page
    assert "TMP." not in man_page
    assert "ableton-cli" in man_page
