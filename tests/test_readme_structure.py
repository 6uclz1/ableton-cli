from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_DOC = REPO_ROOT / "README.md"
CONTRIBUTING_DOC = REPO_ROOT / "CONTRIBUTING.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readme_excludes_developer_only_sections() -> None:
    markdown = _read(README_DOC)
    assert "## Commit Hook (Ruff)" not in markdown
    assert "## Quality Harness (Phase 2)" not in markdown
    assert "## Development" not in markdown
    assert "## Merge Gate" not in markdown


def test_readme_has_skill_installation_path_and_contributing_reference() -> None:
    markdown = _read(README_DOC)
    assert "## Skills Integration" in markdown
    assert "docs/skills/install.md" in markdown
    assert "CONTRIBUTING.md" in markdown


def test_contributing_collects_developer_sections() -> None:
    markdown = _read(CONTRIBUTING_DOC)
    assert "## Development" in markdown
    assert "## Commit Hook (Ruff)" in markdown
    assert "## Quality Harness (Phase 2)" in markdown
    assert "## Merge Gate" in markdown
