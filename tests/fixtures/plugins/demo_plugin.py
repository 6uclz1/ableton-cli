"""A minimal plugin for the plugin host tests; it uses only ableton_cli.plugin_api."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ableton_cli.plugin_api import DESTRUCTIVE, READ, WRITE, Live, Plugin, PluginApi


def register(api: PluginApi) -> None:
    @api.command("echo", side_effect=READ, help="Echo a message")
    def echo(ctx: typer.Context, message: Annotated[str, typer.Option("--message")]) -> None:
        api.run(ctx, args={"message": message}, action=lambda live: {"message": message})

    @api.command("tempo set", side_effect=WRITE, help="Set the tempo through Live")
    def tempo_set(ctx: typer.Context, bpm: Annotated[float, typer.Argument()]) -> None:
        def _action(live: Live) -> dict[str, object]:
            return live.request("transport_tempo_set", {"bpm": bpm})

        api.run(ctx, args={"bpm": bpm}, action=_action)

    @api.command("reset", side_effect=DESTRUCTIVE, help="Pretend to delete something")
    def reset(ctx: typer.Context) -> None:
        api.run(ctx, args={}, action=lambda live: {"reset": True})

    @api.command("fail", side_effect=READ, help="Always fail")
    def fail(ctx: typer.Context) -> None:
        def _action(live: Live) -> dict[str, object]:
            raise api.error("BROKEN", "Demo failure", hint="Fix the demo.")

        api.run(ctx, args={}, action=_action)


PLUGIN = Plugin(
    name="demo",
    api_version=1,
    register=register,
    description="Demo plugin for tests",
    skills=(Path(__file__).resolve().parent / "skills" / "demo",),
)
