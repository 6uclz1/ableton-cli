from __future__ import annotations

import platform
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import AppError, ExitCode

REMOTE_SCRIPT_DIR_NAME = "AbletonCliRemote"


def remote_script_source_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "remote_script" / REMOTE_SCRIPT_DIR_NAME


def remote_script_candidate_dirs(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    system = platform.system().lower()

    if system == "darwin":
        return [
            home / "Music" / "Ableton" / "User Library" / "Remote Scripts",
            home / "Documents" / "Ableton" / "User Library" / "Remote Scripts",
        ]
    if system == "windows":
        return [
            home / "Documents" / "Ableton" / "User Library" / "Remote Scripts",
        ]

    return [home / "Ableton" / "User Library" / "Remote Scripts"]


def _select_target_roots(candidates: list[Path]) -> list[Path]:
    existing = [candidate for candidate in candidates if candidate.exists()]
    if existing:
        return existing

    for candidate in candidates:
        if candidate.parent.exists():
            return [candidate]

    joined = "\n".join(str(candidate) for candidate in candidates)
    raise AppError(
        error_code="INSTALL_TARGET_NOT_FOUND",
        message="Could not locate Ableton Remote Scripts directory",
        hint=f"Create one of these directories or set up Ableton User Library:\n{joined}",
        exit_code=ExitCode.EXECUTION_FAILED,
    )


def install_remote_script(*, dry_run: bool, yes: bool) -> dict[str, Any]:
    del yes  # reserved for explicit confirmation flows; command stays non-interactive.

    source = remote_script_source_dir()
    if not source.exists():
        raise AppError(
            error_code="REMOTE_SCRIPT_NOT_INSTALLED",
            message=f"Remote Script source not found: {source}",
            hint="Reinstall ableton-cli package including remote_script assets.",
            exit_code=ExitCode.REMOTE_SCRIPT_NOT_DETECTED,
        )

    candidates = remote_script_candidate_dirs()
    target_roots = _select_target_roots(candidates)

    targets: list[str] = []
    backups: list[str] = []
    action = "install"

    for target_root in target_roots:
        target = target_root / REMOTE_SCRIPT_DIR_NAME
        backup_path: Path | None = None
        if target.exists():
            action = "update"
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            backup_path = target_root / f"{REMOTE_SCRIPT_DIR_NAME}.backup-{timestamp}"
            backups.append(str(backup_path))

        if not dry_run:
            target_root.mkdir(parents=True, exist_ok=True)
            if target.exists() and backup_path is not None:
                shutil.move(str(target), str(backup_path))
            shutil.copytree(source, target)

        targets.append(str(target))

    return {
        "action": action,
        "dry_run": dry_run,
        "target": targets[0],
        "targets": targets,
        "backup": backups[0] if backups else None,
        "backups": backups,
        "candidates": [str(path) for path in candidates],
    }
