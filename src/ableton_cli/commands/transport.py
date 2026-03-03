from __future__ import annotations

from typing import Annotated

import typer

from ..errors import AppError, ExitCode
from ..runtime import execute_command, get_client
from ._validation import require_non_negative_float

transport_app = typer.Typer(help="Transport control commands", no_args_is_help=True)
tempo_app = typer.Typer(help="Tempo controls", no_args_is_help=True)
position_app = typer.Typer(help="Playhead position controls", no_args_is_help=True)


@transport_app.command("play")
def transport_play(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="transport play",
        args={},
        action=lambda: get_client(ctx).transport_play(),
    )


@transport_app.command("stop")
def transport_stop(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="transport stop",
        args={},
        action=lambda: get_client(ctx).transport_stop(),
    )


@transport_app.command("toggle")
def transport_toggle(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="transport toggle",
        args={},
        action=lambda: get_client(ctx).transport_toggle(),
    )


@tempo_app.command("get")
def tempo_get(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="transport tempo get",
        args={},
        action=lambda: get_client(ctx).transport_tempo_get(),
    )


@tempo_app.command("set")
def tempo_set(
    ctx: typer.Context,
    bpm: Annotated[float, typer.Argument(help="Target BPM. Allowed range: 20.0 to 999.0")],
) -> None:
    def _run() -> dict[str, float]:
        if bpm < 20.0 or bpm > 999.0:
            raise AppError(
                error_code="INVALID_ARGUMENT",
                message=f"bpm must be between 20.0 and 999.0, got {bpm}",
                hint="Use a valid tempo value such as 120.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )
        return get_client(ctx).transport_tempo_set(bpm)

    execute_command(
        ctx,
        command="transport tempo set",
        args={"bpm": bpm},
        action=_run,
    )


@position_app.command("get")
def transport_position_get(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="transport position get",
        args={},
        action=lambda: get_client(ctx).transport_position_get(),
    )


@position_app.command("set")
def transport_position_set(
    ctx: typer.Context,
    beats: Annotated[float, typer.Argument(help="Target beat position (>= 0)")],
) -> None:
    def _run() -> dict[str, object]:
        valid_beats = require_non_negative_float(
            "beats",
            beats,
            hint="Use a non-negative beat position such as 0 or 32.",
        )
        return get_client(ctx).transport_position_set(valid_beats)

    execute_command(
        ctx,
        command="transport position set",
        args={"beats": beats},
        action=_run,
    )


@transport_app.command("rewind")
def transport_rewind(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="transport rewind",
        args={},
        action=lambda: get_client(ctx).transport_rewind(),
    )


transport_app.add_typer(tempo_app, name="tempo")
transport_app.add_typer(position_app, name="position")


def register(app: typer.Typer) -> None:
    app.add_typer(transport_app, name="transport")
