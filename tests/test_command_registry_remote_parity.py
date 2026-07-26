"""Build-time parity between the CLI's command table and the Remote Script.

A mismatch here is currently caught only at runtime: `doctor` and `ping`
compare `command_set_hash` against the *installed* Remote Script, so a CLI
command pointing at a handler that does not exist ships green and fails on a
user's machine. These tests move that check to the build.

The Remote Script cannot import `src/`, so its handler tables are necessarily
a separate copy spread over `command_backend_handlers_*.py`. Merging them is
not the fix — asserting parity is.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REMOTE_DIR = Path(__file__).resolve().parents[1] / "remote_script" / "AbletonCliRemote"


def _protocol_method_names() -> set[str]:
    tree = ast.parse((_REMOTE_DIR / "command_backend_contract.py").read_text(encoding="utf-8"))
    return {
        node.name
        for cls in tree.body
        if isinstance(cls, ast.ClassDef)
        for node in cls.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _backend_attributes_used() -> set[str]:
    """Every `backend.<name>` a handler module touches."""
    used: set[str] = set()
    paths = [*sorted(_REMOTE_DIR.glob("command_backend_handlers_*.py"))]
    paths.append(_REMOTE_DIR / "command_backend_registry.py")
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "backend"
            ):
                used.add(node.attr)
    return used


def test_remote_handlers_cover_exactly_the_declared_remote_commands() -> None:
    from ableton_cli.command_specs import remote_command_names
    from remote_script.AbletonCliRemote.command_backend_registry import _HANDLERS

    declared = remote_command_names()
    served = set(_HANDLERS)

    assert not declared - served, (
        "CLI declares remote commands the Remote Script does not serve: "
        f"{sorted(declared - served)}"
    )
    assert not served - declared, (
        f"Remote Script serves commands the CLI does not declare: {sorted(served - declared)}"
    )


def test_backend_protocol_declares_every_method_handlers_call() -> None:
    declared = _protocol_method_names()
    used = _backend_attributes_used()

    assert not used - declared, (
        f"handlers call backend methods missing from CommandBackend: {sorted(used - declared)}"
    )


def test_backend_protocol_has_no_unused_methods() -> None:
    """An undialled Protocol method is a handler that was deleted and forgotten."""
    declared = _protocol_method_names()
    used = _backend_attributes_used()

    assert not declared - used, (
        f"CommandBackend declares methods no handler calls: {sorted(declared - used)}"
    )
