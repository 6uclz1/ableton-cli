from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import invalid_argument, require_non_empty_string, require_non_negative

_SUPPORTED_SYNTH_TYPES = ("wavetable", "drift", "meld")

synth_app = typer.Typer(help="Synth control commands", no_args_is_help=True)
parameters_app = typer.Typer(help="Synth parameter listing commands", no_args_is_help=True)
parameter_app = typer.Typer(help="Synth parameter write commands", no_args_is_help=True)


def _normalize_synth_type(value: str) -> str:
    parsed = require_non_empty_string("synth_type", value, hint="Pass a non-empty synth type.")
    normalized = parsed.lower()
    if normalized not in _SUPPORTED_SYNTH_TYPES:
        raise invalid_argument(
            message=f"synth_type must be one of {', '.join(_SUPPORTED_SYNTH_TYPES)}",
            hint="Use a supported synth type.",
        )
    return normalized


@synth_app.command("find")
def synth_find(
    ctx: typer.Context,
    track: Annotated[
        int | None,
        typer.Option("--track", help="Optional track index filter (0-based)"),
    ] = None,
    synth_type: Annotated[
        str | None,
        typer.Option("--type", help="Optional synth type filter: wavetable|drift|meld"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        if track is not None:
            require_non_negative(
                "track",
                track,
                hint="Use a valid track index from 'ableton-cli tracks list'.",
            )
        valid_type = _normalize_synth_type(synth_type) if synth_type is not None else None
        return get_client(ctx).find_synth_devices(track=track, synth_type=valid_type)

    execute_command(
        ctx,
        command="synth find",
        args={"track": track, "synth_type": synth_type},
        action=_run,
    )


@parameters_app.command("list")
def synth_parameters_list(
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
        return get_client(ctx).list_synth_parameters(track=track, device=device)

    execute_command(
        ctx,
        command="synth parameters list",
        args={"track": track, "device": device},
        action=_run,
    )


@parameter_app.command("set")
def synth_parameter_set(
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
            hint="Use a valid parameter index from 'ableton-cli synth parameters list'.",
        )
        return get_client(ctx).set_synth_parameter_safe(
            track=track,
            device=device,
            parameter=parameter,
            value=value,
        )

    execute_command(
        ctx,
        command="synth parameter set",
        args={"track": track, "device": device, "parameter": parameter, "value": value},
        action=_run,
    )


@synth_app.command("observe")
def synth_observe(
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
        return get_client(ctx).observe_synth_parameters(track=track, device=device)

    execute_command(
        ctx,
        command="synth observe",
        args={"track": track, "device": device},
        action=_run,
    )


def _build_standard_synth_app(synth_type: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"{synth_type.title()} synth wrapper commands",
        no_args_is_help=True,
    )

    @standard_app.command("keys")
    def keys(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command=f"synth {synth_type} keys",
            args={},
            action=lambda: get_client(ctx).list_standard_synth_keys(synth_type),
        )

    @standard_app.command("set")
    def standard_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index (0-based)")],
        device: Annotated[int, typer.Argument(help="Device index (0-based)")],
        key: Annotated[str, typer.Argument(help="Stable synth key")],
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
                hint="Pass a non-empty stable synth key.",
            )
            return get_client(ctx).set_standard_synth_parameter_safe(
                synth_type=synth_type,
                track=track,
                device=device,
                key=valid_key,
                value=value,
            )

        execute_command(
            ctx,
            command=f"synth {synth_type} set",
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
            return get_client(ctx).observe_standard_synth_state(
                synth_type=synth_type,
                track=track,
                device=device,
            )

        execute_command(
            ctx,
            command=f"synth {synth_type} observe",
            args={"track": track, "device": device},
            action=_run,
        )

    return standard_app


synth_app.add_typer(parameters_app, name="parameters")
synth_app.add_typer(parameter_app, name="parameter")
synth_app.add_typer(_build_standard_synth_app("wavetable"), name="wavetable")
synth_app.add_typer(_build_standard_synth_app("drift"), name="drift")
synth_app.add_typer(_build_standard_synth_app("meld"), name="meld")


def register(app: typer.Typer) -> None:
    app.add_typer(synth_app, name="synth")
