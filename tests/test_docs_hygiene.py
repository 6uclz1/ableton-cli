from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_DOC = REPO_ROOT / "README.md"
PROTOCOL_DOC = REPO_ROOT / "docs" / "protocol.md"
QUALITY_HARNESS_TODO_DOC = REPO_ROOT / "docs" / "quality-harness-todo.md"
GENERATED_MAN_DOC = REPO_ROOT / "docs" / "man" / "generated" / "ableton-cli.1"
SKILL_DOC = REPO_ROOT / "skills" / "ableton-cli" / "SKILL.md"
AGENTS_DOC = REPO_ROOT / "AGENTS.md"
CURSOR_RULE_DOC = REPO_ROOT / ".cursor" / "rules" / "ableton-cli.mdc"
COMPUTER_USE_INDEX = "docs/computer-use/README.md"
ENVIRONMENT_INDEPENDENT_DOC_GLOBS = (
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "skills/ableton-cli/SKILL.md",
    "docs/skills/**/*.md",
    "docs/computer-use/**/*.md",
    ".cursor/rules/**/*.mdc",
    ".cursor/skills/**/*.md",
)
HOST_SPECIFIC_MARKERS = ("".join(("6uc", "lz1")), "/" + "Users/")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _environment_independent_docs() -> tuple[Path, ...]:
    paths: set[Path] = set()
    for pattern in ENVIRONMENT_INDEPENDENT_DOC_GLOBS:
        paths.update(path for path in REPO_ROOT.glob(pattern) if path.is_file())
    return tuple(sorted(paths))


def test_removed_docs_do_not_exist() -> None:
    assert not PROTOCOL_DOC.exists()
    assert not QUALITY_HARNESS_TODO_DOC.exists()


def test_agent_docs_do_not_reference_host_specific_paths() -> None:
    violations = [
        f"{path.relative_to(REPO_ROOT)} contains {marker!r}"
        for path in _environment_independent_docs()
        for marker in HOST_SPECIFIC_MARKERS
        if marker in _read(path)
    ]

    assert violations == []


def test_readme_includes_protocol_section() -> None:
    markdown = _read(README_DOC)
    assert "## Protocol" in markdown


def test_readme_documents_security_model() -> None:
    markdown = _read(README_DOC)
    assert "## Security Model" in markdown
    assert "127.0.0.1 only" in markdown
    assert "no authentication" in markdown
    assert "--read-only" in markdown


def test_generated_man_uses_stable_command_name() -> None:
    man_page = _read(GENERATED_MAN_DOC)
    assert "tmp." not in man_page
    assert "TMP." not in man_page
    assert "ableton-cli" in man_page


def test_no_outdated_live_11_version_floor_references() -> None:
    outdated_marker = "Live 11+"
    scan_globs = (
        "README.md",
        "docs/**/*.md",
        "skills/ableton-cli/SKILL.md",
        "remote_script/**/*.py",
        "src/**/*.py",
    )
    violations = []
    for pattern in scan_globs:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if outdated_marker in _read(path):
                violations.append(str(path.relative_to(REPO_ROOT)))

    assert violations == []


def test_composition_docs_use_browser_discovery_before_drum_kit_loading() -> None:
    docs = "\n".join(
        [
            _read(README_DOC),
            _read(SKILL_DOC),
            _read(GENERATED_MAN_DOC),
        ]
    )

    assert 'browser search "Drum Rack"' in docs
    assert 'browser search "Kit"' in docs
    assert "browser load-drum-kit 0 rack:drums --kit-uri kit:acoustic" not in docs


def test_agent_docs_route_cli_gaps_to_computer_use_docs() -> None:
    assert (REPO_ROOT / COMPUTER_USE_INDEX).is_file()
    for path in (AGENTS_DOC, CURSOR_RULE_DOC, SKILL_DOC):
        markdown = _read(path)
        assert COMPUTER_USE_INDEX in markdown, path.name
        assert "Computer Use" in markdown, path.name


def test_computer_use_docs_are_linked_from_index() -> None:
    index = _read(REPO_ROOT / COMPUTER_USE_INDEX)
    pages = sorted((REPO_ROOT / "docs" / "computer-use").rglob("*.md"))
    unlinked = [
        page.relative_to(REPO_ROOT).as_posix()
        for page in pages
        if page.name != "README.md"
        and page.relative_to(REPO_ROOT / "docs" / "computer-use").as_posix() not in index
    ]

    assert unlinked == []
