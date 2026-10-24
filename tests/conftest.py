from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

# The core suite describes ableton-cli itself; plugins installed in the dev
# environment must not change the command surface it snapshots. Plugin tests
# build their own app with explicit plugin sources.
os.environ["ABLETON_CLI_PLUGINS"] = "off"

from ableton_cli.cli import app  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_plugin_manifest(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The user's real plugins.toml lists the plugins they installed; tests see an empty one.
    monkeypatch.setenv("ABLETON_CLI_PLUGIN_MANIFEST", str(tmp_path / "plugins.toml"))


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_app():
    return app
