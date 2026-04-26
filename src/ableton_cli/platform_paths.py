from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

CLAUDE_HOME_DIR_NAME = ".claude"
CURSOR_HOME_DIR_NAME = ".cursor"


class PlatformPaths(Protocol):
    def remote_script_candidate_dirs(self) -> list[Path]: ...

    def claude_home_dir(self) -> Path: ...

    def cursor_home_dir(self) -> Path: ...


@dataclass(slots=True, frozen=True)
class WindowsPlatformPaths:
    home: Path

    def remote_script_candidate_dirs(self) -> list[Path]:
        return [self.home / "Documents" / "Ableton" / "User Library" / "Remote Scripts"]

    def claude_home_dir(self) -> Path:
        return self.home / CLAUDE_HOME_DIR_NAME

    def cursor_home_dir(self) -> Path:
        return self.home / CURSOR_HOME_DIR_NAME


@dataclass(slots=True, frozen=True)
class PosixPlatformPaths:
    home: Path
    remote_script_relative_dirs: tuple[tuple[str, ...], ...]

    def remote_script_candidate_dirs(self) -> list[Path]:
        return [self.home.joinpath(*path_parts) for path_parts in self.remote_script_relative_dirs]

    def claude_home_dir(self) -> Path:
        return self.home / CLAUDE_HOME_DIR_NAME

    def cursor_home_dir(self) -> Path:
        return self.home / CURSOR_HOME_DIR_NAME
