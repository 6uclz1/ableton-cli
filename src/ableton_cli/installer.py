from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import AppError, ExitCode
from .platform_paths import PlatformPaths

REMOTE_SCRIPT_DIR_NAME = "AbletonCliRemote"
SKILL_DIR_NAME = "ableton-cli"
SKILL_FILE_NAME = "SKILL.md"
CODEX_HOME_ENV_VAR = "CODEX_HOME"


def remote_script_source_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "remote_script" / REMOTE_SCRIPT_DIR_NAME


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


def install_remote_script(
    *,
    dry_run: bool,
    yes: bool,
    platform_paths: PlatformPaths,
) -> dict[str, Any]:
    del yes  # reserved for explicit confirmation flows; command stays non-interactive.

    source = remote_script_source_dir()
    if not source.exists():
        raise AppError(
            error_code="REMOTE_SCRIPT_NOT_INSTALLED",
            message=f"Remote Script source not found: {source}",
            hint="Reinstall ableton-cli package including remote_script assets.",
            exit_code=ExitCode.REMOTE_SCRIPT_NOT_DETECTED,
        )

    candidates = platform_paths.remote_script_candidate_dirs()
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


def skill_source_file() -> Path:
    return Path(__file__).resolve().parents[2] / "skills" / SKILL_DIR_NAME / SKILL_FILE_NAME


def _resolve_codex_home(codex_home: Path | None) -> Path:
    if codex_home is not None:
        return codex_home

    raw_value = os.environ.get(CODEX_HOME_ENV_VAR)
    if raw_value is None or not raw_value.strip():
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"{CODEX_HOME_ENV_VAR} is not set",
            hint=f"Set {CODEX_HOME_ENV_VAR} before running install-skill.",
            exit_code=ExitCode.CONFIG_INVALID,
        )
    return Path(raw_value)


def _resolve_claude_home(*, claude_home: Path | None, platform_paths: PlatformPaths) -> Path:
    if claude_home is not None:
        return claude_home
    return platform_paths.claude_home_dir()


def _resolve_skill_home(
    *,
    platform_paths: PlatformPaths,
    target: str,
    codex_home: Path | None,
    claude_home: Path | None,
) -> Path:
    if target == "codex":
        return _resolve_codex_home(codex_home)
    if target == "claude":
        return _resolve_claude_home(claude_home=claude_home, platform_paths=platform_paths)
    raise AppError(
        error_code="INVALID_ARGUMENT",
        message=f"target must be one of: codex, claude (got {target!r})",
        hint="Use --target codex or --target claude.",
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def install_skill(
    *,
    dry_run: bool,
    yes: bool,
    platform_paths: PlatformPaths,
    target: str = "codex",
    codex_home: Path | None = None,
    claude_home: Path | None = None,
) -> dict[str, Any]:
    del yes  # reserved for explicit confirmation flows; command stays non-interactive.

    source = skill_source_file()
    if not source.exists():
        raise AppError(
            error_code="SKILL_SOURCE_NOT_FOUND",
            message=f"Skill source not found: {source}",
            hint="Reinstall ableton-cli package including skills assets.",
            exit_code=ExitCode.EXECUTION_FAILED,
        )

    resolved_home = _resolve_skill_home(
        platform_paths=platform_paths,
        target=target,
        codex_home=codex_home,
        claude_home=claude_home,
    )
    target_path = resolved_home / "skills" / SKILL_DIR_NAME / SKILL_FILE_NAME
    action = "update" if target_path.exists() else "install"

    if not dry_run:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target_path)

    return {
        "action": action,
        "dry_run": dry_run,
        "target_type": target,
        "source": str(source),
        "target": str(target_path),
        "home": str(resolved_home),
    }
