from __future__ import annotations

from pathlib import Path

import pytest

import ableton_cli.platform_detection as platform_detection
from ableton_cli.errors import AppError, ExitCode
from ableton_cli.platform_paths import PosixPlatformPaths, WindowsPlatformPaths


def test_build_platform_paths_for_windows(monkeypatch) -> None:
    home = Path("/home/test-user")

    class _PathStub:
        @staticmethod
        def home() -> Path:
            return home

    monkeypatch.setattr(platform_detection, "Path", _PathStub)
    monkeypatch.setattr(platform_detection.platform, "system", lambda: "Windows")

    result = platform_detection.build_platform_paths_for_current_os()

    assert isinstance(result, WindowsPlatformPaths)
    assert result.home == home


def test_build_platform_paths_for_macos(monkeypatch) -> None:
    home = Path("/home/test-user")

    class _PathStub:
        @staticmethod
        def home() -> Path:
            return home

    monkeypatch.setattr(platform_detection, "Path", _PathStub)
    monkeypatch.setattr(platform_detection.platform, "system", lambda: "Darwin")

    result = platform_detection.build_platform_paths_for_current_os()

    assert isinstance(result, PosixPlatformPaths)
    assert result.home == home
    assert result.remote_script_relative_dirs == (
        ("Music", "Ableton", "User Library", "Remote Scripts"),
        ("Documents", "Ableton", "User Library", "Remote Scripts"),
    )


def test_build_platform_paths_for_linux(monkeypatch) -> None:
    home = Path("/home/test-user")

    class _PathStub:
        @staticmethod
        def home() -> Path:
            return home

    monkeypatch.setattr(platform_detection, "Path", _PathStub)
    monkeypatch.setattr(platform_detection.platform, "system", lambda: "Linux")

    result = platform_detection.build_platform_paths_for_current_os()

    assert isinstance(result, PosixPlatformPaths)
    assert result.home == home
    assert result.remote_script_relative_dirs == (("Ableton", "User Library", "Remote Scripts"),)


def test_build_platform_paths_for_unsupported_os_raises_error(monkeypatch) -> None:
    monkeypatch.setattr(platform_detection.platform, "system", lambda: "Solaris")

    with pytest.raises(AppError) as exc_info:
        platform_detection.build_platform_paths_for_current_os()

    assert exc_info.value.error_code == "UNSUPPORTED_OS"
    assert exc_info.value.exit_code == ExitCode.EXECUTION_FAILED
