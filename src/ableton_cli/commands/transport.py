from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..errors import AppError, ErrorCode, ExitCode
from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._validation import require_non_negative_float

transport_app = typer.Typer(help="Transport control commands", no_args_is_help=True)
tempo_app = typer.Typer(help="Tempo controls", no_args_is_help=True)
position_app = typer.Typer(help="Playhead position controls", no_args_is_help=True)


TransportCommandSpec = CommandSpec


TRANSPORT_PLAY_SPEC = TransportCommandSpec(
    command_name="transport play",
    client_method="transport_play",
)
TRANSPORT_STOP_SPEC = TransportCommandSpec(
    command_name="transport stop",
    client_method="transport_stop",
)
TRANSPORT_TOGGLE_SPEC = TransportCommandSpec(
    command_name="transport toggle",
    client_method="transport_toggle",
)
TRANSPORT_TEMPO_GET_SPEC = TransportCommandSpec(
    command_name="transport tempo get",
    client_method="transport_tempo_get",
)
TRANSPORT_TEMPO_SET_SPEC = TransportCommandSpec(
    command_name="transport tempo set",
    client_method="transport_tempo_set",
)
TRANSPORT_POSITION_GET_SPEC = TransportCommandSpec(
    command_name="transport position get",
    client_method="transport_position_get",
)
TRANSPORT_POSITION_SET_SPEC = TransportCommandSpec(
    command_name="transport position set",
    client_method="transport_position_set",
)
TRANSPORT_REWIND_SPEC = TransportCommandSpec(
    command_name="transport rewind",
    client_method="transport_rewind",
)


def run_client_command(
    ctx: typer.Context,
    *,
    command_name: str,
    args: dict[str, object],
    fn: Callable[[object], dict[str, object]],
) -> None:
    run_client_command_shared(
        ctx,
        command_name=command_name,
        args=args,
        fn=fn,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: TransportCommandSpec,
    args: dict[str, object],
    method_kwargs: dict[str, object] | Callable[[], dict[str, object]] | None = None,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
        method_kwargs=method_kwargs,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


@transport_app.command("play")
def transport_play(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=TRANSPORT_PLAY_SPEC,
        args={},
    )


@transport_app.command("stop")
def transport_stop(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=TRANSPORT_STOP_SPEC,
        args={},
    )


@transport_app.command("toggle")
def transport_toggle(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=TRANSPORT_TOGGLE_SPEC,
        args={},
    )


@tempo_app.command("get")
def tempo_get(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=TRANSPORT_TEMPO_GET_SPEC,
        args={},
    )


@tempo_app.command("set")
def tempo_set(
    ctx: typer.Context,
    bpm: Annotated[float, typer.Argument(help="Target BPM. Allowed range: 20.0 to 999.0")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        if bpm < 20.0 or bpm > 999.0:
            raise AppError(
                error_code=ErrorCode.INVALID_ARGUMENT,
                message=f"bpm must be between 20.0 and 999.0, got {bpm}",
                hint="Use a valid tempo value such as 120.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )
        return {"bpm": bpm}

    run_client_command_spec(
        ctx,
        spec=TRANSPORT_TEMPO_SET_SPEC,
        args={"bpm": bpm},
        method_kwargs=_method_kwargs,
    )


@position_app.command("get")
def transport_position_get(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=TRANSPORT_POSITION_GET_SPEC,
        args={},
    )


@position_app.command("set")
def transport_position_set(
    ctx: typer.Context,
    beats: Annotated[float, typer.Argument(help="Target beat position (>= 0)")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_beats = require_non_negative_float(
            "beats",
            beats,
            hint="Use a non-negative beat position such as 0 or 32.",
        )
        return {"beats": valid_beats}

    run_client_command_spec(
        ctx,
        spec=TRANSPORT_POSITION_SET_SPEC,
        args={"beats": beats},
        method_kwargs=_method_kwargs,
    )


@transport_app.command("rewind")
def transport_rewind(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=TRANSPORT_REWIND_SPEC,
        args={},
    )


transport_app.add_typer(tempo_app, name="tempo")
transport_app.add_typer(position_app, name="position")


def register(app: typer.Typer) -> None:
    app.add_typer(transport_app, name="transport")
