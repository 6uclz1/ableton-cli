from __future__ import annotations

import inspect
from pathlib import Path

from ableton_cli.client.ableton_client import AbletonClient
from ableton_cli.command_registry import CLIENT_METHOD_SPECS
from ableton_cli.command_specs import remote_command_names
from tools.generate_client_methods import _OUTPUT_PATH, render_module


def test_generated_client_module_is_up_to_date() -> None:
    """The checked-in generated file must match the generator's output.

    Regenerate with::

        uv run python tools/generate_client_methods.py
    """
    on_disk = _OUTPUT_PATH.read_text(encoding="utf-8")

    # render_module() emits unformatted source; the generator runs ruff format
    # over it. Compare on formatted text so the test does not depend on where
    # the formatter chooses to break long signatures.
    import subprocess
    import sys

    formatted = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "-"],
        input=render_module(),
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    ).stdout

    assert on_disk == formatted


def test_every_generated_method_names_a_real_remote_command() -> None:
    """A generated method that no Remote Script serves would fail only at runtime."""
    declared = remote_command_names()
    unknown = sorted(
        spec.remote_command for spec in CLIENT_METHOD_SPECS if spec.remote_command not in declared
    )

    assert unknown == []


def test_generated_methods_are_reachable_on_the_client() -> None:
    for spec in CLIENT_METHOD_SPECS:
        method = getattr(AbletonClient, spec.remote_command, None)
        assert method is not None, f"{spec.remote_command} is not on AbletonClient"

        signature = inspect.signature(method)
        parameters = [name for name in signature.parameters if name != "self"]
        assert parameters == [param.name for param in spec.params], spec.remote_command


def test_no_mixin_still_defines_a_generated_method() -> None:
    """The generated method must be the only definition, not a shadowed duplicate.

    A leftover hand-written copy in a mixin listed before the generated mixin
    would win the MRO and silently keep the old behaviour.
    """
    generated_names = {spec.remote_command for spec in CLIENT_METHOD_SPECS}
    client_dir = Path(__file__).resolve().parents[1] / "src" / "ableton_cli" / "client"

    duplicates: list[str] = []
    for path in sorted(client_dir.glob("_client_*.py")):
        if path.name == "_client_generated.py":
            continue
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in generated_names:
                duplicates.append(f"{path.name}::{node.name}")

    assert duplicates == []
