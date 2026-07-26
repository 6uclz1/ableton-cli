from __future__ import annotations

import click
from typer.main import get_command

from ableton_cli.cli import app
from ableton_cli.command_registry import COMMAND_DESCRIPTORS


def _cli_command_names() -> set[str]:
    """Every leaf command actually reachable on the command line."""

    def walk(command: click.Command, path: tuple[str, ...]) -> set[str]:
        if isinstance(command, click.Group):
            found: set[str] = set()
            for name, child in command.commands.items():
                found |= walk(child, (*path, name))
            return found
        return {" ".join(path)}

    return walk(get_command(app), ())


def test_every_cli_command_has_a_descriptor_and_vice_versa() -> None:
    """The table and the CLI must name exactly the same commands.

    This replaces the old regex scan of ``commands/**/*.py``. That scan could
    only ever miss quietly: a command spelled in a way the pattern did not
    match simply vanished from ``public_command_names()``, and with it from
    the side-effect exhaustiveness check and the contract registry. Walking
    the real Typer app cannot miss anything.
    """
    cli_names = _cli_command_names()
    table_names = {descriptor.command_name for descriptor in COMMAND_DESCRIPTORS}

    missing_from_table = sorted(cli_names - table_names)
    missing_from_cli = sorted(table_names - cli_names)

    assert not missing_from_table and not missing_from_cli, (
        "command_registry.COMMAND_DESCRIPTORS is out of sync with the CLI.\n"
        f"  add to COMMAND_DESCRIPTORS ({len(missing_from_table)}): {missing_from_table}\n"
        f"  remove from COMMAND_DESCRIPTORS ({len(missing_from_cli)}): {missing_from_cli}"
    )


def test_descriptor_table_is_sorted_and_unique() -> None:
    names = [descriptor.command_name for descriptor in COMMAND_DESCRIPTORS]

    assert names == sorted(names)
    assert len(names) == len(set(names))
