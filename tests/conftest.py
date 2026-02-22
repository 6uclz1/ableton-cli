from __future__ import annotations

import pytest
from typer.testing import CliRunner

from ableton_cli.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_app():
    return app
