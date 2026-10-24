from __future__ import annotations

import pytest
import typer

import ableton_cli.version as version_module
from ableton_cli import __version__
from ableton_cli.errors import ExitCode
from remote_script.AbletonCliRemote.command_backend_contract import REMOTE_SCRIPT_VERSION


def test_version_callback_prints_and_exits(monkeypatch) -> None:
    seen: dict[str, str] = {}
    monkeypatch.setattr(version_module.typer, "echo", lambda value: seen.setdefault("value", value))

    with pytest.raises(typer.Exit) as exc_info:
        version_module.version_callback(True)

    assert seen["value"] == __version__
    assert exc_info.value.exit_code == ExitCode.SUCCESS.value


def test_version_callback_ignores_false() -> None:
    version_module.version_callback(False)


def test_remote_script_version_matches_package_version() -> None:
    assert REMOTE_SCRIPT_VERSION == __version__
