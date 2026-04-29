from __future__ import annotations

from pathlib import Path

from ableton_cli.platform_paths import PosixPlatformPaths, WindowsPlatformPaths


def test_windows_platform_paths_returns_expected_directories() -> None:
    home = Path("/home/test-user")
    platform_paths = WindowsPlatformPaths(home=home)

    assert platform_paths.remote_script_candidate_dirs() == [
        home / "Documents" / "Ableton" / "User Library" / "Remote Scripts"
    ]
    assert platform_paths.claude_home_dir() == home / ".claude"
    assert platform_paths.cursor_home_dir() == home / ".cursor"


def test_posix_platform_paths_returns_expected_directories() -> None:
    home = Path("/home/test-user")
    platform_paths = PosixPlatformPaths(
        home=home,
        remote_script_relative_dirs=(
            ("Music", "Ableton", "User Library", "Remote Scripts"),
            ("Documents", "Ableton", "User Library", "Remote Scripts"),
        ),
    )

    assert platform_paths.remote_script_candidate_dirs() == [
        home / "Music" / "Ableton" / "User Library" / "Remote Scripts",
        home / "Documents" / "Ableton" / "User Library" / "Remote Scripts",
    ]
    assert platform_paths.claude_home_dir() == home / ".claude"
    assert platform_paths.cursor_home_dir() == home / ".cursor"
