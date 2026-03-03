from __future__ import annotations

from pathlib import Path

import pytest

import ableton_cli.bootstrap as bootstrap
from ableton_cli.config import Settings
from ableton_cli.errors import AppError, ExitCode
from ableton_cli.output import OutputMode
from ableton_cli.platform_paths import PosixPlatformPaths


def test_build_runtime_context_resolves_dependencies_and_configures_logging(
    monkeypatch, tmp_path
) -> None:
    settings = Settings(
        host="10.0.0.20",
        port=12345,
        timeout_ms=2500,
        log_level="INFO",
        log_file="/tmp/resolved.log",
        protocol_version=7,
        config_path="/tmp/config.toml",
    )
    platform_paths = PosixPlatformPaths(
        home=Path("/home/test-user"),
        remote_script_relative_dirs=(("Ableton", "User Library", "Remote Scripts"),),
    )
    seen: dict[str, object] = {}

    def _resolve_settings_stub(*, cli_overrides, config_path):  # noqa: ANN001, ANN202
        seen["cli_overrides"] = cli_overrides
        seen["config_path"] = config_path
        return settings

    monkeypatch.setattr(bootstrap, "resolve_settings", _resolve_settings_stub)
    monkeypatch.setattr(bootstrap, "build_platform_paths_for_current_os", lambda: platform_paths)
    monkeypatch.setattr(
        bootstrap,
        "configure_logging",
        lambda *, verbose, quiet, log_file: seen.update(
            {"verbose": verbose, "quiet": quiet, "log_file": log_file}
        ),
    )

    config_path = tmp_path / "config.toml"
    runtime = bootstrap.build_runtime_context(
        host="127.0.0.1",
        port=8765,
        timeout_ms=15000,
        protocol_version=11,
        output=OutputMode.JSON,
        verbose=True,
        log_file="/tmp/cli-override.log",
        config=config_path,
        no_color=True,
        quiet=False,
        record="/tmp/session-record.jsonl",
        replay=None,
        read_only=True,
        compact=True,
    )

    assert runtime.settings is settings
    assert runtime.platform_paths is platform_paths
    assert runtime.output_mode is OutputMode.JSON
    assert runtime.quiet is False
    assert runtime.no_color is True
    assert runtime.record_path == "/tmp/session-record.jsonl"
    assert runtime.replay_path is None
    assert runtime.read_only is True
    assert runtime.compact is True
    assert seen["config_path"] == config_path
    assert seen["cli_overrides"] == {
        "host": "127.0.0.1",
        "port": 8765,
        "timeout_ms": 15000,
        "log_file": "/tmp/cli-override.log",
        "protocol_version": 11,
    }
    assert seen["verbose"] is True
    assert seen["quiet"] is False
    assert seen["log_file"] == "/tmp/resolved.log"


def test_build_runtime_context_propagates_bootstrap_errors(monkeypatch) -> None:
    expected = AppError(
        error_code="CONFIG_INVALID",
        message="boom",
        hint="fix",
        exit_code=ExitCode.CONFIG_INVALID,
    )

    def _raise_error(*, cli_overrides, config_path):  # noqa: ANN001, ANN202
        del cli_overrides, config_path
        raise expected

    monkeypatch.setattr(bootstrap, "resolve_settings", _raise_error)

    with pytest.raises(AppError) as exc_info:
        bootstrap.build_runtime_context(
            host=None,
            port=None,
            timeout_ms=None,
            protocol_version=None,
            output=OutputMode.HUMAN,
            verbose=False,
            log_file=None,
            config=None,
            no_color=False,
            quiet=False,
            record=None,
            replay=None,
            read_only=False,
            compact=False,
        )

    assert exc_info.value is expected
