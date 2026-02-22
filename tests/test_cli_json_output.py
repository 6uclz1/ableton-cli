from __future__ import annotations

import json


def test_config_show_outputs_json_envelope(runner, cli_app, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('host = "127.0.0.1"\nport = 8765\n', encoding="utf-8")

    result = runner.invoke(
        cli_app,
        [
            "--config",
            str(config_path),
            "--output",
            "json",
            "config",
            "show",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "config show"
    assert payload["error"] is None
    assert payload["result"]["host"] == "127.0.0.1"


def test_ping_unreachable_outputs_json_error(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--host",
            "127.0.0.1",
            "--port",
            "65534",
            "--timeout-ms",
            "100",
            "--output",
            "json",
            "ping",
        ],
    )

    assert result.exit_code in (10, 12)
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "ping"
    assert payload["error"]["code"] in {"ABLETON_NOT_REACHABLE", "TIMEOUT"}


def test_install_remote_script_verify_includes_doctor_result(runner, cli_app, monkeypatch) -> None:
    import ableton_cli.bootstrap as bootstrap_module
    from ableton_cli.commands import setup

    class _PlatformPathsSentinel:
        pass

    platform_paths = _PlatformPathsSentinel()
    seen: dict[str, object] = {}

    def _install_remote_script_stub(
        *, yes: bool, dry_run: bool, platform_paths
    ) -> dict[str, object]:
        del yes
        seen["install"] = platform_paths
        return {
            "action": "install",
            "dry_run": dry_run,
            "target": "/tmp/AbletonCliRemote",
            "targets": ["/tmp/AbletonCliRemote"],
            "backup": None,
            "backups": [],
            "candidates": ["/tmp"],
        }

    def _run_doctor_stub(settings, *, platform_paths) -> dict[str, object]:
        del settings
        seen["doctor"] = platform_paths
        return {
            "summary": {"pass": 1, "warn": 0, "fail": 0},
            "checks": [],
        }

    monkeypatch.setattr(
        setup,
        "install_remote_script",
        _install_remote_script_stub,
    )
    monkeypatch.setattr(
        setup,
        "run_doctor",
        _run_doctor_stub,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "build_platform_paths_for_current_os",
        lambda: platform_paths,
    )

    result = runner.invoke(
        cli_app,
        ["--output", "json", "install-remote-script", "--dry-run", "--verify"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "install-remote-script"
    assert payload["result"]["dry_run"] is True
    assert payload["result"]["verification"]["summary"]["pass"] == 1
    assert seen["install"] is platform_paths
    assert seen["doctor"] is platform_paths


def test_install_skill_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    monkeypatch.setattr(
        setup,
        "install_skill",
        lambda yes, dry_run, platform_paths, target: {
            "action": "install",
            "dry_run": dry_run,
            "target_type": target,
            "source": "/tmp/repo/skills/ableton-cli/SKILL.md",
            "target": "/tmp/.claude/skills/ableton-cli/SKILL.md",
            "home": "/tmp/.claude",
        },
    )

    result = runner.invoke(
        cli_app,
        ["--output", "json", "install-skill", "--target", "claude", "--dry-run"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "install-skill"
    assert payload["args"]["target"] == "claude"
    assert payload["result"]["dry_run"] is True
    assert payload["result"]["target_type"] == "claude"
    assert payload["result"]["target"] == "/tmp/.claude/skills/ableton-cli/SKILL.md"


def test_bootstrap_fails_for_unsupported_os(runner, cli_app, monkeypatch) -> None:
    import ableton_cli.platform_detection as platform_detection_module

    monkeypatch.setattr(platform_detection_module.platform, "system", lambda: "Solaris")

    result = runner.invoke(
        cli_app,
        ["--output", "json", "config", "show"],
    )

    assert result.exit_code == 20
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "bootstrap"
    assert payload["error"]["code"] == "UNSUPPORTED_OS"


def test_ping_includes_capabilities_when_remote_reports_them(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    class _ClientStub:
        def ping(self):  # noqa: ANN201
            return {
                "protocol_version": 2,
                "remote_script_version": "0.2.0",
                "supported_commands": ["ping", "song_info"],
                "command_set_hash": "abc123",
                "api_support": {
                    "song_save_supported": False,
                    "song_export_audio_supported": False,
                    "arrangement_record_supported": False,
                },
            }

    monkeypatch.setattr(setup, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "ping"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["supported_commands"] == ["ping", "song_info"]
    assert payload["result"]["command_set_hash"] == "abc123"
    assert payload["result"]["api_support"]["song_save_supported"] is False
    assert payload["result"]["api_support"]["song_export_audio_supported"] is False
    assert payload["result"]["api_support"]["arrangement_record_supported"] is False


def test_config_set_updates_key_and_returns_json_envelope(runner, cli_app, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                'host = "127.0.0.1"',
                "port = 8765",
                "timeout_ms = 15000",
                "protocol_version = 2",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        [
            "--config",
            str(config_path),
            "--output",
            "json",
            "config",
            "set",
            "protocol_version",
            "7",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "config set"
    assert payload["result"]["key"] == "protocol_version"
    assert payload["result"]["value"] == 7
    text = config_path.read_text(encoding="utf-8")
    assert "protocol_version = 7" in text


def test_config_set_rejects_invalid_key_or_value(runner, cli_app, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('host = "127.0.0.1"\nport = 8765\n', encoding="utf-8")

    invalid_key = runner.invoke(
        cli_app,
        [
            "--config",
            str(config_path),
            "--output",
            "json",
            "config",
            "set",
            "unsupported_key",
            "1",
        ],
    )
    invalid_value = runner.invoke(
        cli_app,
        [
            "--config",
            str(config_path),
            "--output",
            "json",
            "config",
            "set",
            "port",
            "not-an-int",
        ],
    )

    assert invalid_key.exit_code == 2
    assert invalid_value.exit_code == 2
    invalid_key_payload = json.loads(invalid_key.stdout)
    invalid_value_payload = json.loads(invalid_value.stdout)
    assert invalid_key_payload["error"]["code"] == "INVALID_ARGUMENT"
    assert invalid_value_payload["error"]["code"] == "INVALID_ARGUMENT"


def test_protocol_version_global_option_overrides_config(runner, cli_app, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("protocol_version = 2\n", encoding="utf-8")

    result = runner.invoke(
        cli_app,
        [
            "--config",
            str(config_path),
            "--protocol-version",
            "11",
            "--output",
            "json",
            "config",
            "show",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["protocol_version"] == 11
