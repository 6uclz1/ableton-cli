from __future__ import annotations

from typing import Annotated

import typer

from ._device_family import DeviceFamily, build_device_family_app, run_find, type_filter_help

SYNTH_FAMILY = DeviceFamily(
    name="synth",
    standard_types=(("wavetable", "wavetable"), ("drift", "drift"), ("meld", "meld")),
)


def _register_find(app: typer.Typer) -> None:
    @app.command("find")
    def synth_find(
        ctx: typer.Context,
        track: Annotated[
            int | None,
            typer.Option("--track", help="Optional track index filter (0-based)"),
        ] = None,
        synth_type: Annotated[
            str | None,
            typer.Option("--type", help=type_filter_help(SYNTH_FAMILY)),
        ] = None,
    ) -> None:
        run_find(ctx, SYNTH_FAMILY, track=track, device_type=synth_type)


synth_app = build_device_family_app(SYNTH_FAMILY, _register_find)


def register(app: typer.Typer) -> None:
    app.add_typer(synth_app, name="synth")
