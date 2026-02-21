from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import invalid_argument, require_non_empty_string, require_non_negative

_SUPPORTED_EFFECT_TYPES = (
    "eq8",
    "limiter",
    "compressor",
    "auto_filter",
    "reverb",
    "utility",
)

effect_app = typer.Typer(help="Effect control commands", no_args_is_help=True)
parameters_app = typer.Typer(help="Effect parameter listing commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Effect parameter write commands", no_args_is_help=True)


def _normalize_effect_type(value: str) -> str:
    parsed = require_non_empty_string("effect_type", value, hint="Pass a non-empty effect type.")
    normalized = parsed.lower()
    if normalized not in _SUPPORTED_EFFECT_TYPES:
        raise invalid_argument(
            message=f"effect_type must be one of {', '.join(_SUPPORTED_EFFECT_TYPES)}",
            hint="Use a supported effect type.",
        )
    return normalized


@effect_app.command("find")
def effect_find(
    ctx: typer.Context,
    track: Annotated[
        int | None,
        typer.Option("--track", help="Optional track index filter (0-based)"),
    ] = None,
    effect_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Optional effect type filter: eq8|limiter|compressor|auto_filter|reverb|utility",
        ),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        if track is not None:
            require_non_negative(
                "track",
                track,
                hint="Use a valid track index from 'ableton-cli tracks list'.",
            )
        valid_type = _normalize_effect_type(effect_type) if effect_type is not None else None
        return get_client(ctx).find_effect_devices(track=track, effect_type=valid_type)

    execute_command(
        ctx,
        command="effect find",
        args={"track": track, "effect_type": effect_type},
        action=_run,
    )


@parameters_app.command("list")
def effect_parameters_list(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    device: Annotated[int, typer.Argument(help="Device index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "device",
            device,
            hint="Use a valid device index from 'ableton-cli track info'.",
        )
        return get_client(ctx).list_effect_parameters(track=track, device=device)

    execute_command(
        ctx,
        command="effect parameters list",
        args={"track": track, "device": device},
        action=_run,
    )


@parameter_app.command("set")
def effect_parameter_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    device: Annotated[int, typer.Argument(help="Device index (0-based)")],
    parameter: Annotated[int, typer.Argument(help="Parameter index (0-based)")],
    value: Annotated[float, typer.Argument(help="Target parameter value")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "device",
            device,
            hint="Use a valid device index from 'ableton-cli track info'.",
        )
        require_non_negative(
            "parameter",
            parameter,
            hint="Use a valid parameter index from 'ableton-cli effect parameters list'.",
        )
        return get_client(ctx).set_effect_parameter_safe(
            track=track,
            device=device,
            parameter=parameter,
            value=value,
        )

    execute_command(
        ctx,
        command="effect parameter set",
        args={"track": track, "device": device, "parameter": parameter, "value": value},
        action=_run,
    )


@effect_app.command("observe")
def effect_observe(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    device: Annotated[int, typer.Argument(help="Device index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "device",
            device,
            hint="Use a valid device index from 'ableton-cli track info'.",
        )
        return get_client(ctx).observe_effect_parameters(track=track, device=device)

    execute_command(
        ctx,
        command="effect observe",
        args={"track": track, "device": device},
        action=_run,
    )


def _build_standard_effect_app(effect_type: str, cli_name: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"{cli_name.title()} effect wrapper commands",
        no_args_is_help=True,
    )

    @standard_app.command("keys")
    def keys(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command=f"effect {cli_name} keys",
            args={},
            action=lambda: get_client(ctx).list_standard_effect_keys(effect_type),
        )

    @standard_app.command("set")
    def standard_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index (0-based)")],
        device: Annotated[int, typer.Argument(help="Device index (0-based)")],
        key: Annotated[str, typer.Argument(help="Stable effect key")],
        value: Annotated[float, typer.Argument(help="Target parameter value")],
    ) -> None:
        def _run() -> dict[str, object]:
            require_non_negative(
                "track",
                track,
                hint="Use a valid track index from 'ableton-cli tracks list'.",
            )
            require_non_negative(
                "device",
                device,
                hint="Use a valid device index from 'ableton-cli track info'.",
            )
            valid_key = require_non_empty_string(
                "key",
                key,
                hint="Pass a non-empty stable effect key.",
            )
            return get_client(ctx).set_standard_effect_parameter_safe(
                effect_type=effect_type,
                track=track,
                device=device,
                key=valid_key,
                value=value,
            )

        execute_command(
            ctx,
            command=f"effect {cli_name} set",
            args={"track": track, "device": device, "key": key, "value": value},
            action=_run,
        )

    @standard_app.command("observe")
    def standard_observe(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index (0-based)")],
        device: Annotated[int, typer.Argument(help="Device index (0-based)")],
    ) -> None:
        def _run() -> dict[str, object]:
            require_non_negative(
                "track",
                track,
                hint="Use a valid track index from 'ableton-cli tracks list'.",
            )
            require_non_negative(
                "device",
                device,
                hint="Use a valid device index from 'ableton-cli track info'.",
            )
            return get_client(ctx).observe_standard_effect_state(
                effect_type=effect_type,
                track=track,
                device=device,
            )

        execute_command(
            ctx,
            command=f"effect {cli_name} observe",
            args={"track": track, "device": device},
            action=_run,
        )

    return standard_app


effect_app.add_typer(parameters_app, name="parameters")
effect_app.add_typer(parameter_app, name="parameter")
effect_app.add_typer(_build_standard_effect_app("eq8", "eq8"), name="eq8")
effect_app.add_typer(_build_standard_effect_app("limiter", "limiter"), name="limiter")
effect_app.add_typer(_build_standard_effect_app("compressor", "compressor"), name="compressor")
effect_app.add_typer(_build_standard_effect_app("auto_filter", "auto-filter"), name="auto-filter")
effect_app.add_typer(_build_standard_effect_app("reverb", "reverb"), name="reverb")
effect_app.add_typer(_build_standard_effect_app("utility", "utility"), name="utility")


def register(app: typer.Typer) -> None:
    app.add_typer(effect_app, name="effect")
