from __future__ import annotations

from typing import Annotated

import typer

from ._device_family import DeviceFamily, build_device_family_app, run_find, type_filter_help

EFFECT_FAMILY = DeviceFamily(
    name="effect",
    standard_types=(
        ("eq8", "eq8"),
        ("limiter", "limiter"),
        ("compressor", "compressor"),
        ("auto_filter", "auto-filter"),
        ("reverb", "reverb"),
        ("utility", "utility"),
    ),
)


def _register_find(app: typer.Typer) -> None:
    @app.command("find")
    def effect_find(
        ctx: typer.Context,
        track: Annotated[
            int | None,
            typer.Option("--track", help="Optional track index filter (0-based)"),
        ] = None,
        effect_type: Annotated[
            str | None,
            typer.Option("--type", help=type_filter_help(EFFECT_FAMILY)),
        ] = None,
    ) -> None:
        run_find(ctx, EFFECT_FAMILY, track=track, device_type=effect_type)


effect_app = build_device_family_app(EFFECT_FAMILY, _register_find)


def register(app: typer.Typer) -> None:
    app.add_typer(effect_app, name="effect")
