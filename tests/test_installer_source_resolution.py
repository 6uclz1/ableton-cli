from __future__ import annotations

from pathlib import Path

from ableton_cli import installer
from ableton_cli.installer import (
    REMOTE_SCRIPT_DIR_NAME,
    SKILL_DIR_NAME,
    SKILL_FILE_NAME,
    install_remote_script,
    remote_script_source_dir,
    skill_source_file,
)


class _PlatformPathsStub:
    def __init__(self, candidates: list[Path]) -> None:
        self._candidates = candidates

    def remote_script_candidate_dirs(self) -> list[Path]:
        return self._candidates


def test_remote_script_source_dir_resolves_repo_checkout() -> None:
    source = remote_script_source_dir()

    assert source.is_dir()
    assert (source / "__init__.py").is_file()
    assert (source / "command_backend_contract.py").is_file()


def test_skill_source_file_resolves_repo_checkout() -> None:
    source = skill_source_file()

    assert source.is_file()
    assert source.name == SKILL_FILE_NAME


def test_bundled_assets_win_over_repo_checkout(monkeypatch, tmp_path: Path) -> None:
    bundled = tmp_path / "_bundled"
    bundled_remote = bundled / "remote_script" / REMOTE_SCRIPT_DIR_NAME
    bundled_remote.mkdir(parents=True)
    bundled_skill = bundled / "skills" / SKILL_DIR_NAME / SKILL_FILE_NAME
    bundled_skill.parent.mkdir(parents=True)
    bundled_skill.write_text("# skill\n", encoding="utf-8")

    monkeypatch.setattr(installer, "_BUNDLED_DIR", bundled)

    assert remote_script_source_dir() == bundled_remote
    assert skill_source_file() == bundled_skill


def test_missing_sources_return_last_candidate_for_error_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(installer, "_BUNDLED_DIR", tmp_path / "missing_bundled")
    monkeypatch.setattr(installer, "_REPO_ROOT", tmp_path / "missing_repo")

    assert remote_script_source_dir() == (
        tmp_path / "missing_repo" / "remote_script" / REMOTE_SCRIPT_DIR_NAME
    )
    assert skill_source_file() == (
        tmp_path / "missing_repo" / "skills" / SKILL_DIR_NAME / SKILL_FILE_NAME
    )


def test_install_remote_script_skips_bytecode(monkeypatch, tmp_path: Path) -> None:
    source_root = tmp_path / "source" / REMOTE_SCRIPT_DIR_NAME
    source_root.mkdir(parents=True)
    (source_root / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    pycache = source_root / "__pycache__"
    pycache.mkdir()
    (pycache / "__init__.cpython-311.pyc").write_bytes(b"\x00")
    (source_root / "stale.pyc").write_bytes(b"\x00")

    target_root = tmp_path / "ableton" / "Remote Scripts"
    target_root.mkdir(parents=True)

    monkeypatch.setattr("ableton_cli.installer.remote_script_source_dir", lambda: source_root)
    platform_paths = _PlatformPathsStub(candidates=[target_root])

    install_remote_script(dry_run=False, yes=True, platform_paths=platform_paths)

    installed = target_root / REMOTE_SCRIPT_DIR_NAME
    assert (installed / "__init__.py").exists()
    assert not (installed / "__pycache__").exists()
    assert not (installed / "stale.pyc").exists()
