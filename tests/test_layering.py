from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMMAND_SPECS_PATH = _REPO_ROOT / "src" / "ableton_cli" / "command_specs.py"
_COMMAND_REGISTRY_PATH = _REPO_ROOT / "src" / "ableton_cli" / "command_registry.py"


def _assert_no_static_import_of_commands(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("ableton_cli.commands")
                assert alias.name != "commands"
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("ableton_cli.commands")
            assert module != "commands"
            # relative "from .commands import ..." has module == "commands" and level == 1
            if module == "commands" and node.level:
                raise AssertionError(f"{path.name} must not import ableton_cli.commands")


def test_command_specs_module_has_no_static_import_of_commands() -> None:
    _assert_no_static_import_of_commands(_COMMAND_SPECS_PATH)


def test_command_registry_module_has_no_static_import_of_commands() -> None:
    # The descriptor table is read by command_specs, so it inherits the same
    # constraint: importing the commands package here would make the shared
    # Typer app's initialisation order load-bearing.
    _assert_no_static_import_of_commands(_COMMAND_REGISTRY_PATH)


def test_command_specs_imports_cleanly_with_commands_package_blocked() -> None:
    # Run in a subprocess so poisoning ableton_cli.commands in sys.modules
    # cannot leak global state (e.g. the shared Typer app) into other tests.
    script = """
import sys


class _BlockedModule:
    def __getattr__(self, name):
        raise AssertionError(
            f"command_specs.py must not touch ableton_cli.commands.{name} at import time"
        )


sys.modules["ableton_cli.commands"] = _BlockedModule()

import ableton_cli.command_specs as command_specs_module

assert command_specs_module.command_specs()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
