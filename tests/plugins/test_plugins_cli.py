from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ableton_cli.app_factory import create_app
from ableton_cli.plugin_api.testing import FakeLive, create_plugin_test_app
from ableton_cli.plugins.host import PluginSource
from ableton_cli.plugins.manifest import ManifestEntry, read_manifest, write_manifest
from tests.fixtures.plugins.demo_plugin import PLUGIN as DEMO
from tests.fixtures.plugins.fake_environment import GOOD, NEWER, SOURCE, FakeEnvironment


@pytest.fixture
def manifest_path(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "plugins.toml"
    monkeypatch.setenv("ABLETON_CLI_PLUGIN_MANIFEST", str(path))
    return path


@pytest.fixture
def environment(monkeypatch) -> FakeEnvironment:
    fake = FakeEnvironment()
    monkeypatch.setattr("ableton_cli.commands.plugins.PluginEnvironment", lambda: fake)
    monkeypatch.setattr("ableton_cli.commands.setup.PluginEnvironment", lambda: fake)
    return fake


@pytest.fixture
def git(monkeypatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(argv):
        calls.append(list(argv))
        stdout = f"{GOOD}\tHEAD\n{NEWER}\trefs/heads/next\n"
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr("ableton_cli.commands.plugins.run_subprocess", run)
    return calls


def _invoke(*args: str, app=None):
    result = CliRunner().invoke(
        app or create_app(plugin_sources=(), env={}), ["--output", "json", *args]
    )
    return result, json.loads(result.stdout)


def test_install_pins_the_default_branch_and_records_it(manifest_path, environment, git) -> None:
    result, payload = _invoke("plugins", "install", SOURCE.url)

    assert result.exit_code == 0, result.output
    assert payload["args"] == {"url": SOURCE.url, "ref": None, "source": SOURCE.url, "rev": GOOD}
    assert payload["result"]["action"] == "installed"
    assert read_manifest(manifest_path)["demo"].rev == GOOD


def test_install_plan_resolves_the_commit_without_installing(
    manifest_path, environment, git
) -> None:
    result, payload = _invoke("--plan", "plugins", "install", f"{SOURCE.url}/tree/next")

    assert result.exit_code == 0, result.output
    assert payload["args"]["rev"] == NEWER
    assert payload["result"]["side_effect"]["kind"] == "destructive"
    assert environment.calls == []
    assert not manifest_path.exists()


def test_plugin_management_writes_are_blocked_in_read_only_mode(
    manifest_path, environment, git
) -> None:
    result, payload = _invoke("--read-only", "plugins", "install", SOURCE.url)

    assert result.exit_code == 20
    assert payload["error"]["code"] == "READ_ONLY_VIOLATION"
    assert environment.calls == []


def test_install_requires_yes_under_require_confirmation(manifest_path, environment, git) -> None:
    result, payload = _invoke("--require-confirmation", "plugins", "install", SOURCE.url)

    assert result.exit_code == 20
    assert payload["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert environment.calls == []


def test_update_uninstall_and_sync_round_trip(manifest_path, environment, git) -> None:
    _invoke("plugins", "install", SOURCE.url)

    updated, update_payload = _invoke("plugins", "update", "demo", "--ref", "next")
    environment.packages.clear()
    synced, sync_payload = _invoke("plugins", "sync")
    removed, remove_payload = _invoke("plugins", "uninstall", "demo")

    assert update_payload["result"]["action"] == "updated"
    assert update_payload["args"]["rev"] == NEWER
    assert sync_payload["result"]["plugins"][0]["action"] == "installed"
    assert remove_payload["result"]["action"] == "uninstalled"
    assert (updated.exit_code, synced.exit_code, removed.exit_code) == (0, 0, 0)
    assert read_manifest(manifest_path) == {}


def test_list_merges_loaded_plugins_with_the_manifest(manifest_path, environment) -> None:
    write_manifest(
        manifest_path,
        {
            "demo": ManifestEntry(
                name="demo",
                source=SOURCE.url,
                requested_ref=None,
                rev=GOOD,
                distribution="ableton-cli-demo",
                version="0.1.0",
            )
        },
    )
    app = create_app(plugin_sources=[PluginSource(name="demo", load=lambda: DEMO)], env={})

    _, listing = _invoke("plugins", "list", app=app)
    _, info = _invoke("plugins", "info", "demo", app=app)
    missing, missing_payload = _invoke("plugins", "info", "nope", app=app)

    assert listing["result"]["api_version"] == 1
    entry = listing["result"]["plugins"][0]
    assert (entry["state"], entry["managed"], entry["in_sync"]) == ("loaded", True, False)
    assert entry["source"] == {"url": SOURCE.url, "requested_ref": None, "rev": GOOD}
    assert info["result"] == entry
    assert missing.exit_code == 2
    assert missing_payload["error"]["code"] == "INVALID_ARGUMENT"


def test_doctor_fails_the_plugin_check_when_the_environment_lost_a_plugin(
    manifest_path, environment, monkeypatch
) -> None:
    write_manifest(
        manifest_path,
        {
            "demo": ManifestEntry(
                name="demo",
                source=SOURCE.url,
                requested_ref=None,
                rev=GOOD,
                distribution="ableton-cli-demo",
                version="0.1.0",
            )
        },
    )
    monkeypatch.setattr("ableton_cli.doctor.AbletonClient", _UnreachableClient)

    _, payload = _invoke("doctor")

    check = {item["name"]: item for item in payload["result"]["checks"]}["plugins"]
    assert check["status"] == "FAIL"
    assert check["details"]["out_of_sync"] == ["demo"]
    assert "plugins sync" in check["hint"]


def test_doctor_passes_with_loaded_plugins(manifest_path, environment, monkeypatch) -> None:
    monkeypatch.setattr("ableton_cli.doctor.AbletonClient", _UnreachableClient)
    app = create_app(plugin_sources=[PluginSource(name="demo", load=lambda: DEMO)], env={})

    _, payload = _invoke("doctor", app=app)

    check = {item["name"]: item for item in payload["result"]["checks"]}["plugins"]
    assert (check["status"], check["details"]["loaded"]) == ("PASS", ["demo"])


class _UnreachableClient:
    def __init__(self, settings) -> None:
        pass

    def ping(self):
        from ableton_cli.errors import AppError, ExitCode

        raise AppError(
            error_code="ABLETON_NOT_REACHABLE",
            message="not reachable",
            hint="start ableton",
            exit_code=ExitCode.ABLETON_NOT_CONNECTED,
        )


def test_install_skill_installs_plugin_skills_next_to_the_core_skill(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    app = create_plugin_test_app(DEMO)

    result, payload = _invoke("install-skill", "--yes", app=app)

    assert result.exit_code == 0, result.output
    [plugin_skill] = payload["result"]["plugin_skills"]
    assert plugin_skill["plugin"] == "demo"
    assert plugin_skill["action"] == "install"
    assert (tmp_path / "codex" / "skills" / "demo" / "SKILL.md").is_file()


def test_fake_live_answers_canned_responses_and_records_requests() -> None:
    live = FakeLive({"tracks_list": {"tracks": []}, "echo": lambda args: {"echo": args}})

    assert live.request("tracks_list") == {"tracks": []}
    assert live.request("echo", {"a": 1}) == {"echo": {"a": 1}}
    assert live.requests == [("tracks_list", {}), ("echo", {"a": 1})]
    with pytest.raises(AssertionError):
        live.request("song_new")
