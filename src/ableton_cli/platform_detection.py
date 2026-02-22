from __future__ import annotations

import platform
from pathlib import Path

from .errors import AppError, ExitCode
from .platform_paths import PlatformPaths, PosixPlatformPaths, WindowsPlatformPaths


def build_platform_paths_for_current_os() -> PlatformPaths:
    detected_os = platform.system().lower()
    home = Path.home()

    if detected_os == "windows":
        return WindowsPlatformPaths(home=home)
    if detected_os == "darwin":
        return PosixPlatformPaths(
            home=home,
            remote_script_relative_dirs=(
                ("Music", "Ableton", "User Library", "Remote Scripts"),
                ("Documents", "Ableton", "User Library", "Remote Scripts"),
            ),
        )
    if detected_os == "linux":
        return PosixPlatformPaths(
            home=home,
            remote_script_relative_dirs=(("Ableton", "User Library", "Remote Scripts"),),
        )

    raise AppError(
        error_code="UNSUPPORTED_OS",
        message=f"Unsupported operating system: {detected_os}",
        hint="Use Windows, macOS, or Linux.",
        exit_code=ExitCode.EXECUTION_FAILED,
    )
