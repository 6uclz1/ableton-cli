from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.command_surface import build_command_surface_snapshot

_SNAPSHOT_PATH = Path(__file__).resolve().parent / "snapshots" / "command_surface_snapshot.json"


def test_command_surface_snapshot_matches_expected() -> None:
    """The CLI's command-line shape is a public contract.

    Option names, positional order, defaults and help text are what users and
    automation type. Regenerate with::

        uv run python tools/update_command_surface_snapshot.py

    only when the surface change is intentional.
    """
    expected = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert build_command_surface_snapshot() == expected


def test_command_surface_snapshot_is_deterministic() -> None:
    assert build_command_surface_snapshot() == build_command_surface_snapshot()


def test_update_tool_reproduces_the_checked_in_snapshot() -> None:
    """The regeneration command in the docstring above must actually work.

    Running it as a subprocess is the point: it exercises the script's own
    sys.path setup, which importing the builder directly would hide.
    """
    repo_root = Path(__file__).resolve().parents[1]
    before = _SNAPSHOT_PATH.read_bytes()
    result = subprocess.run(
        [sys.executable, "tools/update_command_surface_snapshot.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    after = _SNAPSHOT_PATH.read_bytes()
    if after != before:
        _SNAPSHOT_PATH.write_bytes(before)
    assert result.returncode == 0, result.stderr
    assert after == before
