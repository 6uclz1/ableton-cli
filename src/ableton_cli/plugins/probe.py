"""``python -m ableton_cli.plugins.probe``: load every installed plugin, print a JSON report.

``plugins install`` runs this in a fresh interpreter to validate what it just
installed. It ignores ``ABLETON_CLI_PLUGINS`` because its whole job is to load
plugins. Anything a plugin prints while loading is swallowed so stdout stays
one JSON document.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from collections.abc import Iterable
from typing import TextIO

import typer

from ..command_registry import command_roots
from .host import PluginSource, discover_plugin_sources, mount_plugins
from .model import PLUGIN_API_VERSION


def probe_report(sources: Iterable[PluginSource]) -> dict[str, object]:
    with contextlib.redirect_stdout(io.StringIO()):
        report = mount_plugins(typer.Typer(), sources, reserved_names=command_roots())
    return {"api_version": PLUGIN_API_VERSION, "plugins": report.entries()}


def main(stdout: TextIO = sys.stdout) -> int:
    json.dump(probe_report(discover_plugin_sources()), stdout, sort_keys=True)
    stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
