from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..command_specs import TRANSPORT_COMMAND_SPECS
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

_TRANSPORT_SPEC_BY_NAME = {item.command_name: item for item in TRANSPORT_COMMAND_SPECS}

TRANSPORT_PLAY_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport play"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport play"].client_method,
)
TRANSPORT_STOP_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport stop"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport stop"].client_method,
)
TRANSPORT_TOGGLE_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport toggle"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport toggle"].client_method,
)
TRANSPORT_TEMPO_GET_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport tempo get"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport tempo get"].client_method,
)
TRANSPORT_TEMPO_SET_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport tempo set"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport tempo set"].client_method,
)
TRANSPORT_POSITION_GET_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport position get"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport position get"].client_method,
)
TRANSPORT_POSITION_SET_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport position set"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport position set"].client_method,
)
TRANSPORT_REWIND_SPEC = TransportCommandSpec(
    command_name=_TRANSPORT_SPEC_BY_NAME["transport rewind"].command_name,
    client_method=_TRANSPORT_SPEC_BY_NAME["transport rewind"].client_method,
)


_POSITION_TOLERANCE_BEATS = 1e-6


def _read_back_position(client: object, *, requested: float) -> dict[str, object]:
    """Read the playhead back in a separate request and return that song state.

    Live applies ``current_song_time`` writes after the Remote Script handler
    returns, so the write response still carries the previous position.
    """
    song = client.song_info()  # type: ignore[attr-defined]
    actual = float(song["current_time"])
    if song["is_playing"]:
        moved = actual >= requested - _POSITION_TOLERANCE_BEATS
    else:
        moved = abs(actual - requested) <= _POSITION_TOLERANCE_BEATS
    if not moved:
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=f"Live did not move the playhead to beat {requested}",
            hint="Read the position with 'transport position get' and retry.",
            exit_code=ExitCode.INVALID_ARGUMENT,
            details={
                "mismatches": [
                    {"attribute": "current_song_time", "requested": requested, "actual": actual}
                ]
            },
        )
    return song


def _verified_position(client: object, *, requested: float) -> dict[str, object]:
    actual = float(_read_back_position(client, requested=requested)["current_time"])
    return {"current_time": actual, "beat_position": actual}


def _start_from_playhead(client: object, client_method: str) -> dict[str, object]:
    """Run a transport start command so playback begins at the stopped playhead.

    Live restarts from its start marker or the last stop point and ignores a
    playhead moved while stopped, but honours a playhead write once playback
    runs, so the stopped position is re-applied in a follow-up request.
    """
    before = client.song_info()  # type: ignore[attr-defined]
    getattr(client, client_method)()
    if before["is_playing"]:
        return {"is_playing": bool(client.song_info()["is_playing"])}  # type: ignore[attr-defined]
    playhead = float(before["current_time"])
    client.transport_position_set(beats=playhead)  # type: ignore[attr-defined]
    song = _read_back_position(client, requested=playhead)
    return {"is_playing": bool(song["is_playing"])}


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
    run_client_command(
        ctx,
        command_name=TRANSPORT_PLAY_SPEC.command_name,
        args={},
        fn=lambda client: _start_from_playhead(client, TRANSPORT_PLAY_SPEC.client_method),
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
    run_client_command(
        ctx,
        command_name=TRANSPORT_TOGGLE_SPEC.command_name,
        args={},
        fn=lambda client: _start_from_playhead(client, TRANSPORT_TOGGLE_SPEC.client_method),
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
    def _run(client: object) -> dict[str, object]:
        valid_beats = require_non_negative_float(
            "beats",
            beats,
            hint="Use a non-negative beat position such as 0 or 32.",
        )
        getattr(client, TRANSPORT_POSITION_SET_SPEC.client_method)(beats=valid_beats)
        return _verified_position(client, requested=valid_beats)

    run_client_command(
        ctx,
        command_name=TRANSPORT_POSITION_SET_SPEC.command_name,
        args={"beats": beats},
        fn=_run,
    )


@transport_app.command("rewind")
def transport_rewind(ctx: typer.Context) -> None:
    def _run(client: object) -> dict[str, object]:
        getattr(client, TRANSPORT_REWIND_SPEC.client_method)()
        return _verified_position(client, requested=0.0)

    run_client_command(
        ctx,
        command_name=TRANSPORT_REWIND_SPEC.command_name,
        args={},
        fn=_run,
    )


transport_app.add_typer(tempo_app, name="tempo")
transport_app.add_typer(position_app, name="position")


def register(app: typer.Typer) -> None:
    app.add_typer(transport_app, name="transport")
