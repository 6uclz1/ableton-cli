from __future__ import annotations

from pathlib import Path

import pytest

from ableton_cli.errors import AppError
from ableton_cli.plugins.github import PinnedSource
from ableton_cli.plugins.installer import (
    install_plugin,
    sync_plugins,
    uninstall_plugin,
    update_plugin,
)
from ableton_cli.plugins.manifest import read_manifest
from tests.fixtures.plugins.fake_environment import (
    BROKEN,
    GOOD,
    NEWER,
    RENAMED,
    SOURCE,
    TWO_ENTRY_POINTS,
    FakeEnvironment,
)


def _pinned(rev: str, ref: str | None = None) -> PinnedSource:
    return PinnedSource(source=SOURCE, requested_ref=ref, rev=rev)


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    return tmp_path / "plugins.toml"


def test_install_pins_the_commit_and_records_it(manifest_path: Path) -> None:
    environment = FakeEnvironment()

    result = install_plugin(
        _pinned(GOOD, "main"), manifest_path=manifest_path, environment=environment
    )

    assert result["action"] == "installed"
    entry = read_manifest(manifest_path)["demo"]
    assert (entry.source, entry.requested_ref, entry.rev) == (SOURCE.url, "main", GOOD)
    assert (entry.distribution, entry.version) == ("ableton-cli-demo", "0.1.0")
    assert environment.calls == [("install", f"git+{SOURCE.url}@{GOOD}")]


@pytest.mark.parametrize("rev", [BROKEN, TWO_ENTRY_POINTS])
def test_an_install_that_does_not_validate_is_removed_again(manifest_path: Path, rev: str) -> None:
    environment = FakeEnvironment()

    with pytest.raises(AppError) as exc_info:
        install_plugin(_pinned(rev), manifest_path=manifest_path, environment=environment)

    assert exc_info.value.error_code == "PLUGIN_INVALID"
    assert environment.packages == {}
    assert read_manifest(manifest_path) == {}


def test_installing_the_same_repository_twice_is_refused(manifest_path: Path) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)

    with pytest.raises(AppError) as exc_info:
        install_plugin(_pinned(NEWER), manifest_path=manifest_path, environment=environment)

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert "plugins update demo" in exc_info.value.hint


def test_update_moves_the_pin_and_reports_the_previous_commit(manifest_path: Path) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)

    result = update_plugin(
        "demo", _pinned(NEWER), manifest_path=manifest_path, environment=environment
    )

    assert (result["action"], result["previous_rev"]) == ("updated", GOOD)
    assert read_manifest(manifest_path)["demo"].rev == NEWER
    assert environment.packages["ableton-cli-demo"].version == "0.2.0"


def test_update_to_the_installed_commit_changes_nothing(manifest_path: Path) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)

    result = update_plugin(
        "demo", _pinned(GOOD), manifest_path=manifest_path, environment=environment
    )

    assert result["action"] == "unchanged"
    assert len(environment.calls) == 1


@pytest.mark.parametrize("rev", [BROKEN, RENAMED])
def test_a_failed_update_reinstalls_the_previous_commit(manifest_path: Path, rev: str) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)

    with pytest.raises(AppError) as exc_info:
        update_plugin("demo", _pinned(rev), manifest_path=manifest_path, environment=environment)

    assert exc_info.value.error_code == "PLUGIN_INVALID"
    assert environment.packages["ableton-cli-demo"].commit == GOOD
    assert read_manifest(manifest_path)["demo"].rev == GOOD


def test_a_failed_rollback_is_reported_with_the_original_error(manifest_path: Path) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)
    environment.calls.clear()
    environment.fail_rollback = True  # the update installs, the rollback install fails

    with pytest.raises(AppError) as exc_info:
        update_plugin("demo", _pinned(BROKEN), manifest_path=manifest_path, environment=environment)

    assert exc_info.value.error_code == "PLUGIN_INVALID"
    assert exc_info.value.details["rollback_error"]["code"] == "PLUGIN_INSTALL_FAILED"


def test_update_and_uninstall_refuse_plugins_not_in_the_manifest(manifest_path: Path) -> None:
    environment = FakeEnvironment(installed_rev=GOOD)

    for operation in (
        lambda: update_plugin(
            "demo", _pinned(NEWER), manifest_path=manifest_path, environment=environment
        ),
        lambda: uninstall_plugin("demo", manifest_path=manifest_path, environment=environment),
    ):
        with pytest.raises(AppError) as exc_info:
            operation()
        assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert environment.calls == []


def test_uninstall_removes_the_package_and_the_entry(manifest_path: Path) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)

    result = uninstall_plugin("demo", manifest_path=manifest_path, environment=environment)

    assert result["action"] == "uninstalled"
    assert environment.packages == {}
    assert read_manifest(manifest_path) == {}


def test_uninstall_of_a_missing_package_only_cleans_the_manifest(manifest_path: Path) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)
    environment.packages.clear()

    result = uninstall_plugin("demo", manifest_path=manifest_path, environment=environment)

    assert result["action"] == "removed_from_manifest"
    assert read_manifest(manifest_path) == {}


def test_sync_reinstalls_what_the_environment_lost(manifest_path: Path) -> None:
    environment = FakeEnvironment()
    install_plugin(_pinned(GOOD), manifest_path=manifest_path, environment=environment)
    environment.packages.clear()

    first = sync_plugins(manifest_path=manifest_path, environment=environment)
    second = sync_plugins(manifest_path=manifest_path, environment=environment)

    assert first == {"plugins": [{"name": "demo", "action": "installed", "rev": GOOD}]}
    assert second == {"plugins": [{"name": "demo", "action": "unchanged", "rev": GOOD}]}
    assert environment.packages["ableton-cli-demo"].commit == GOOD
