from __future__ import annotations

from pathlib import Path

import pytest

from ableton_cli.errors import AppError, ExitCode
from ableton_cli.installer import SKILL_DIR_NAME, install_skill


class _PlatformPathsStub:
    def __init__(self, *, claude_home_dir: Path) -> None:
        self._claude_home_dir = claude_home_dir

    def remote_script_candidate_dirs(self) -> list[Path]:
        return []

    def claude_home_dir(self) -> Path:
        return self._claude_home_dir


def test_install_skill_installs_and_updates_for_codex(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source" / SKILL_DIR_NAME / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text("name: first\n", encoding="utf-8")

    codex_home = tmp_path / ".codex"
    platform_paths = _PlatformPathsStub(claude_home_dir=tmp_path / ".claude")
    monkeypatch.setattr("ableton_cli.installer.skill_source_file", lambda: source)

    first = install_skill(
        dry_run=False,
        yes=True,
        platform_paths=platform_paths,
        target="codex",
        codex_home=codex_home,
    )
    assert first["action"] == "install"
    target = codex_home / "skills" / SKILL_DIR_NAME / "SKILL.md"
    assert target.read_text(encoding="utf-8") == "name: first\n"

    source.write_text("name: second\n", encoding="utf-8")
    second = install_skill(
        dry_run=False,
        yes=True,
        platform_paths=platform_paths,
        target="codex",
        codex_home=codex_home,
    )
    assert second["action"] == "update"
    assert target.read_text(encoding="utf-8") == "name: second\n"


def test_install_skill_installs_for_claude(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source" / SKILL_DIR_NAME / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text("name: first\n", encoding="utf-8")

    claude_home = tmp_path / ".claude"
    platform_paths = _PlatformPathsStub(claude_home_dir=claude_home)
    monkeypatch.setattr("ableton_cli.installer.skill_source_file", lambda: source)

    result = install_skill(
        dry_run=False,
        yes=True,
        platform_paths=platform_paths,
        target="claude",
    )

    assert result["action"] == "install"
    target = claude_home / "skills" / SKILL_DIR_NAME / "SKILL.md"
    assert target.read_text(encoding="utf-8") == "name: first\n"


def test_install_skill_requires_codex_home_env_for_codex_target(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "source" / SKILL_DIR_NAME / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text("name: first\n", encoding="utf-8")

    platform_paths = _PlatformPathsStub(claude_home_dir=tmp_path / ".claude")
    monkeypatch.setattr("ableton_cli.installer.skill_source_file", lambda: source)
    monkeypatch.delenv("CODEX_HOME", raising=False)

    with pytest.raises(AppError) as exc_info:
        install_skill(dry_run=False, yes=True, platform_paths=platform_paths, target="codex")

    assert exc_info.value.error_code == "CONFIG_INVALID"
    assert exc_info.value.exit_code == ExitCode.CONFIG_INVALID


def test_install_skill_rejects_unknown_target(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source" / SKILL_DIR_NAME / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text("name: first\n", encoding="utf-8")

    platform_paths = _PlatformPathsStub(claude_home_dir=tmp_path / ".claude")
    monkeypatch.setattr("ableton_cli.installer.skill_source_file", lambda: source)

    with pytest.raises(AppError) as exc_info:
        install_skill(dry_run=False, yes=True, platform_paths=platform_paths, target="unknown")

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert exc_info.value.exit_code == ExitCode.INVALID_ARGUMENT
