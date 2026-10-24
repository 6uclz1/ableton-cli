"""Helpers for testing a plugin without Ableton Live or an installed distribution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import typer

from ..app_factory import create_app
from ..plugins.host import PluginSource
from ..plugins.model import Plugin
from . import Live

Response = Mapping[str, Any] | Callable[[dict[str, Any]], Mapping[str, Any]]


class FakeLive(Live):
    """A ``Live`` that answers from canned responses and records every request.

    ``responses`` maps a Remote Script command name to its result, or to a
    function of the request args returning the result. A request for any
    other name fails the test instead of returning something plausible.
    """

    def __init__(self, responses: Mapping[str, Response] | None = None) -> None:
        self.responses = dict(responses or {})
        self.requests: list[tuple[str, dict[str, Any]]] = []
        super().__init__(self._answer)

    def _answer(self, name: str, args: dict[str, Any] | None) -> dict[str, Any]:
        payload = {} if args is None else dict(args)
        self.requests.append((name, payload))
        if name not in self.responses:
            raise AssertionError(f"FakeLive has no response for {name!r} (args={payload!r})")
        response = self.responses[name]
        return dict(response(payload) if callable(response) else response)


def create_plugin_test_app(*plugins: Plugin) -> typer.Typer:
    """The full ``ableton-cli`` app with exactly these plugins loaded, for ``CliRunner``."""
    sources = [PluginSource(name=plugin.name, load=_constant(plugin)) for plugin in plugins]
    return create_app(plugin_sources=sources, env={})


def _constant(plugin: Plugin) -> Callable[[], Plugin]:
    return lambda: plugin
