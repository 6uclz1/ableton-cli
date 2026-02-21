from __future__ import annotations

from pathlib import Path

from ableton_cli.config import resolve_settings


def test_config_priority_cli_over_env_over_file_over_default(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                'host = "10.1.1.1"',
                "port = 7777",
                "timeout_ms = 3000",
                'log_level = "DEBUG"',
                "protocol_version = 2",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ABLETON_CLI_HOST", "10.2.2.2")
    monkeypatch.setenv("ABLETON_CLI_PORT", "8888")
    monkeypatch.setenv("ABLETON_CLI_PROTOCOL_VERSION", "3")

    settings = resolve_settings(
        cli_overrides={"host": "127.0.0.1", "port": 8765, "protocol_version": 4},
        config_path=config_path,
    )

    assert settings.host == "127.0.0.1"  # CLI wins
    assert settings.port == 8765  # CLI wins
    assert settings.timeout_ms == 3000  # file wins over default
    assert settings.log_level == "DEBUG"
    assert settings.protocol_version == 4  # CLI wins over env/file


def test_config_defaults_use_protocol_v2_and_longer_timeout(tmp_path: Path) -> None:
    settings = resolve_settings(cli_overrides={}, config_path=tmp_path / "missing.toml")

    assert settings.timeout_ms == 15000
    assert settings.protocol_version == 2
