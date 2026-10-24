from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

# The core suite describes ableton-cli itself; plugins installed in the dev
# environment must not change the command surface it snapshots. Plugin tests
# build their own app with explicit plugin sources.
os.environ["ABLETON_CLI_PLUGINS"] = "off"

from ableton_cli.cli import app  # noqa: E402


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_app():
    return app
