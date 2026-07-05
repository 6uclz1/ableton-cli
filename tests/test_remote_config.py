from __future__ import annotations

from pathlib import Path

import pytest

from remote_script.AbletonCliRemote.remote_config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    RemoteConfig,
    load_remote_config,
)


def test_load_remote_config_defaults_when_nothing_configured(tmp_path: Path) -> None:
    config = load_remote_config(package_dir=tmp_path)

    assert config == RemoteConfig(host=DEFAULT_HOST, port=DEFAULT_PORT, auth_token=None)


def test_load_remote_config_reads_packaged_json_file(tmp_path: Path) -> None:
    (tmp_path / "remote_config.json").write_text(
        '{"host": "0.0.0.0", "port": 9999, "auth_token": "secret"}',
        encoding="utf-8",
    )

    config = load_remote_config(package_dir=tmp_path)

    assert config == RemoteConfig(host="0.0.0.0", port=9999, auth_token="secret")


def test_load_remote_config_env_overrides_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "remote_config.json").write_text(
        '{"host": "0.0.0.0", "port": 9999, "auth_token": "file-secret"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("ABLETON_CLI_REMOTE_HOST", "192.168.1.5")
    monkeypatch.setenv("ABLETON_CLI_REMOTE_PORT", "7000")
    monkeypatch.setenv("ABLETON_CLI_REMOTE_AUTH_TOKEN", "env-secret")

    config = load_remote_config(package_dir=tmp_path)

    assert config == RemoteConfig(host="192.168.1.5", port=7000, auth_token="env-secret")


def test_load_remote_config_partial_env_overrides_only_set_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "remote_config.json").write_text(
        '{"host": "0.0.0.0", "port": 9999}',
        encoding="utf-8",
    )
    monkeypatch.setenv("ABLETON_CLI_REMOTE_PORT", "7000")

    config = load_remote_config(package_dir=tmp_path)

    assert config == RemoteConfig(host="0.0.0.0", port=7000, auth_token=None)


def test_load_remote_config_missing_file_is_ignored(tmp_path: Path) -> None:
    config = load_remote_config(package_dir=tmp_path)
    assert config == RemoteConfig()


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"host": ""}',
        '{"port": 0}',
        '{"port": 70000}',
        '{"port": "8765"}',
        '{"auth_token": 123}',
        '{"auth_token": ""}',
        '{"unexpected_key": true}',
    ],
)
def test_load_remote_config_rejects_invalid_file_values(tmp_path: Path, content: str) -> None:
    (tmp_path / "remote_config.json").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        load_remote_config(package_dir=tmp_path)


@pytest.mark.parametrize(
    ("env_var", "value"),
    [
        ("ABLETON_CLI_REMOTE_HOST", ""),
        ("ABLETON_CLI_REMOTE_PORT", "not-a-number"),
        ("ABLETON_CLI_REMOTE_PORT", "0"),
        ("ABLETON_CLI_REMOTE_AUTH_TOKEN", ""),
    ],
)
def test_load_remote_config_rejects_invalid_env_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, env_var: str, value: str
) -> None:
    monkeypatch.setenv(env_var, value)

    with pytest.raises(ValueError):
        load_remote_config(package_dir=tmp_path)
