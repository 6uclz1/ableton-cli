from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._arrangement_shared import require_arrangement_clip_index, require_track_index
from ._arrangement_specs import ArrangementCommandSpec
from ._validation import invalid_argument, require_absolute_path, require_non_negative_float

PROPS_GET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip props get",
    client_method="arrangement_clip_props_get",
)
LOOP_SET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip loop set",
    client_method="arrangement_clip_loop_set",
)
MARKER_SET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip marker set",
    client_method="arrangement_clip_marker_set",
)
WARP_GET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip warp get",
    client_method="arrangement_clip_warp_get",
)
WARP_SET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip warp set",
    client_method="arrangement_clip_warp_set",
)
GAIN_SET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip gain set",
    client_method="arrangement_clip_gain_set",
)
TRANSPOSE_SET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip transpose set",
    client_method="arrangement_clip_transpose_set",
)
FILE_REPLACE_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip file replace",
    client_method="arrangement_clip_file_replace",
)
CommandRunner = Callable[..., None]


def _bool_option(name: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise invalid_argument(
        message=f"{name} must be true or false, got {value!r}",
        hint=f"Pass --{name} true or --{name} false.",
    )


def _track_index_kwargs(track: int, index: int) -> dict[str, int]:
    return {
        "track": require_track_index(track),
        "index": require_arrangement_clip_index(index),
    }


def _register_props_get(props_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @props_app.command("get")
    def arrangement_clip_props_get(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=PROPS_GET_SPEC,
            args={"track": track, "index": index},
            method_kwargs=lambda: _track_index_kwargs(track, index),
        )


def _register_loop_set(loop_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @loop_app.command("set")
    def arrangement_clip_loop_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
        start: Annotated[float, typer.Option("--start")],
        end: Annotated[float, typer.Option("--end")],
        enabled: Annotated[str, typer.Option("--enabled")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=LOOP_SET_SPEC,
            args={"track": track, "index": index, "start": start, "end": end, "enabled": enabled},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "start": require_non_negative_float(
                    "start", start, hint="Use a non-negative --start."
                ),
                "end": require_non_negative_float("end", end, hint="Use a non-negative --end."),
                "enabled": _bool_option("enabled", enabled),
            },
        )


def _register_marker_set(marker_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @marker_app.command("set")
    def arrangement_clip_marker_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
        start_marker: Annotated[float, typer.Option("--start-marker")],
        end_marker: Annotated[float, typer.Option("--end-marker")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=MARKER_SET_SPEC,
            args={
                "track": track,
                "index": index,
                "start_marker": start_marker,
                "end_marker": end_marker,
            },
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "start_marker": require_non_negative_float(
                    "start_marker",
                    start_marker,
                    hint="Use a non-negative --start-marker.",
                ),
                "end_marker": require_non_negative_float(
                    "end_marker",
                    end_marker,
                    hint="Use a non-negative --end-marker.",
                ),
            },
        )


def _register_warp_get(warp_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @warp_app.command("get")
    def arrangement_clip_warp_get(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_GET_SPEC,
            args={"track": track, "index": index},
            method_kwargs=lambda: _track_index_kwargs(track, index),
        )


def _register_warp_set(warp_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @warp_app.command("set")
    def arrangement_clip_warp_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
        enabled: Annotated[str, typer.Option("--enabled")],
        mode: Annotated[str | None, typer.Option("--mode")] = None,
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_SET_SPEC,
            args={"track": track, "index": index, "enabled": enabled, "mode": mode},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "enabled": _bool_option("enabled", enabled),
                "mode": mode,
            },
        )


def _register_gain_set(gain_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @gain_app.command("set")
    def arrangement_clip_gain_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
        db: Annotated[float, typer.Option("--db")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=GAIN_SET_SPEC,
            args={"track": track, "index": index, "db": db},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "db": db,
            },
        )


def _register_transpose_set(
    transpose_app: typer.Typer,
    run_client_command_spec: CommandRunner,
) -> None:
    @transpose_app.command("set")
    def arrangement_clip_transpose_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
        semitones: Annotated[int, typer.Option("--semitones")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=TRANSPOSE_SET_SPEC,
            args={"track": track, "index": index, "semitones": semitones},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "semitones": semitones,
            },
        )


def _register_file_replace(file_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @file_app.command("replace")
    def arrangement_clip_file_replace(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        index: Annotated[int, typer.Argument(help="Arrangement clip index")],
        audio_path: Annotated[str, typer.Option("--audio-path")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=FILE_REPLACE_SPEC,
            args={"track": track, "index": index, "audio_path": audio_path},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "audio_path": require_absolute_path(
                    "audio_path",
                    audio_path,
                    hint="Pass an absolute path to --audio-path.",
                ),
            },
        )


def register_commands(
    *,
    props_app: typer.Typer,
    loop_app: typer.Typer,
    marker_app: typer.Typer,
    warp_app: typer.Typer,
    gain_app: typer.Typer,
    transpose_app: typer.Typer,
    file_app: typer.Typer,
    run_client_command_spec: Callable[..., None],
) -> None:
    _register_props_get(props_app, run_client_command_spec)
    _register_loop_set(loop_app, run_client_command_spec)
    _register_marker_set(marker_app, run_client_command_spec)
    _register_warp_get(warp_app, run_client_command_spec)
    _register_warp_set(warp_app, run_client_command_spec)
    _register_gain_set(gain_app, run_client_command_spec)
    _register_transpose_set(transpose_app, run_client_command_spec)
    _register_file_replace(file_app, run_client_command_spec)
