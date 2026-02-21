from __future__ import annotations

from pathlib import Path

from ableton_cli.installer import REMOTE_SCRIPT_DIR_NAME, install_remote_script


def test_install_remote_script_is_idempotent_and_backs_up(monkeypatch, tmp_path: Path) -> None:
    source_root = tmp_path / "source" / REMOTE_SCRIPT_DIR_NAME
    source_root.mkdir(parents=True)
    (source_root / "__init__.py").write_text("x = 1\n", encoding="utf-8")

    target_root = tmp_path / "ableton" / "Remote Scripts"
    target_root.mkdir(parents=True)

    monkeypatch.setattr("ableton_cli.installer.remote_script_source_dir", lambda: source_root)
    monkeypatch.setattr(
        "ableton_cli.installer.remote_script_candidate_dirs", lambda home=None: [target_root]
    )

    first = install_remote_script(dry_run=False, yes=True)
    assert first["action"] == "install"
    assert (target_root / REMOTE_SCRIPT_DIR_NAME / "__init__.py").exists()

    second = install_remote_script(dry_run=False, yes=True)
    assert second["action"] == "update"
    assert second["backup"] is not None
    assert (target_root / REMOTE_SCRIPT_DIR_NAME / "__init__.py").exists()
