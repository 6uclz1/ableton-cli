from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from .._client_command_runner import CommandSpec
from .._validation import (
    invalid_argument,
    require_absolute_path,
    require_non_negative_float,
    require_track_index,
)

PROPS_GET_SPEC = CommandSpec(command_name="clip props get", client_method="clip_props_get")
LOOP_SET_SPEC = CommandSpec(command_name="clip loop set", client_method="clip_loop_set")
MARKER_SET_SPEC = CommandSpec(command_name="clip marker set", client_method="clip_marker_set")
WARP_GET_SPEC = CommandSpec(command_name="clip warp get", client_method="clip_warp_get")
WARP_SET_SPEC = CommandSpec(command_name="clip warp set", client_method="clip_warp_set")
WARP_MARKER_LIST_SPEC = CommandSpec(
    command_name="clip warp-marker list",
    client_method="clip_warp_marker_list",
)
WARP_MARKER_ADD_SPEC = CommandSpec(
    command_name="clip warp-marker add",
    client_method="clip_warp_marker_add",
)
WARP_MARKER_MOVE_SPEC = CommandSpec(
    command_name="clip warp-marker move",
    client_method="clip_warp_marker_move",
)
WARP_MARKER_REMOVE_SPEC = CommandSpec(
    command_name="clip warp-marker remove",
    client_method="clip_warp_marker_remove",
)
GAIN_SET_SPEC = CommandSpec(command_name="clip gain set", client_method="clip_gain_set")
TRANSPOSE_SET_SPEC = CommandSpec(
    command_name="clip transpose set",
    client_method="clip_transpose_set",
)
FILE_REPLACE_SPEC = CommandSpec(command_name="clip file replace", client_method="clip_file_replace")
CommandRunner = Callable[..., None]


def _clip_index(value: int) -> int:
    return require_track_index(value, hint="Use a valid clip slot index.")


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


def _track_clip_kwargs(track: int, clip: int) -> dict[str, int]:
    return {"track": require_track_index(track), "clip": _clip_index(clip)}


def _register_props_get(props_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @props_app.command("get")
    def clip_props_get(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=PROPS_GET_SPEC,
            args={"track": track, "clip": clip},
            method_kwargs=lambda: _track_clip_kwargs(track, clip),
        )


def _register_loop_set(loop_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @loop_app.command("set")
    def clip_loop_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        start: Annotated[float, typer.Option("--start", help="Loop start in beats")],
        end: Annotated[float, typer.Option("--end", help="Loop end in beats")],
        enabled: Annotated[str, typer.Option("--enabled", help="Loop enabled")],
    ) -> None:
        def _kwargs() -> dict[str, object]:
            valid_start = require_non_negative_float(
                "start", start, hint="Use a non-negative --start."
            )
            valid_end = require_non_negative_float("end", end, hint="Use a non-negative --end.")
            if valid_end <= valid_start:
                raise typer.BadParameter("end must be greater than start")
            return {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "start": valid_start,
                "end": valid_end,
                "enabled": _bool_option("enabled", enabled),
            }

        run_client_command_spec(
            ctx,
            spec=LOOP_SET_SPEC,
            args={"track": track, "clip": clip, "start": start, "end": end, "enabled": enabled},
            method_kwargs=_kwargs,
        )


def _register_marker_set(marker_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @marker_app.command("set")
    def clip_marker_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        start_marker: Annotated[float, typer.Option("--start-marker")],
        end_marker: Annotated[float, typer.Option("--end-marker")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=MARKER_SET_SPEC,
            args={
                "track": track,
                "clip": clip,
                "start_marker": start_marker,
                "end_marker": end_marker,
            },
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
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
    def clip_warp_get(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_GET_SPEC,
            args={"track": track, "clip": clip},
            method_kwargs=lambda: _track_clip_kwargs(track, clip),
        )


def _register_warp_set(warp_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @warp_app.command("set")
    def clip_warp_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        enabled: Annotated[str, typer.Option("--enabled")],
        mode: Annotated[str | None, typer.Option("--mode")] = None,
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_SET_SPEC,
            args={"track": track, "clip": clip, "enabled": enabled, "mode": mode},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "enabled": _bool_option("enabled", enabled),
                "mode": mode,
            },
        )


def _register_warp_marker_list(
    warp_marker_app: typer.Typer,
    run_client_command_spec: CommandRunner,
) -> None:
    @warp_marker_app.command("list")
    def clip_warp_marker_list(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_MARKER_LIST_SPEC,
            args={"track": track, "clip": clip},
            method_kwargs=lambda: _track_clip_kwargs(track, clip),
        )


def _register_warp_marker_add(
    warp_marker_app: typer.Typer,
    run_client_command_spec: CommandRunner,
) -> None:
    @warp_marker_app.command("add")
    def clip_warp_marker_add(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        beat_time: Annotated[float, typer.Option("--beat-time")],
        sample_time: Annotated[float | None, typer.Option("--sample-time")] = None,
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_MARKER_ADD_SPEC,
            args={"track": track, "clip": clip, "sample_time": sample_time, "beat_time": beat_time},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "beat_time": require_non_negative_float(
                    "beat_time",
                    beat_time,
                    hint="Use a non-negative --beat-time.",
                ),
                "sample_time": (
                    require_non_negative_float(
                        "sample_time",
                        sample_time,
                        hint="Use a non-negative --sample-time.",
                    )
                    if sample_time is not None
                    else None
                ),
            },
        )


def _register_warp_marker_move(
    warp_marker_app: typer.Typer,
    run_client_command_spec: CommandRunner,
) -> None:
    @warp_marker_app.command("move")
    def clip_warp_marker_move(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        beat_time: Annotated[float, typer.Option("--beat-time")],
        distance: Annotated[float, typer.Option("--distance")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_MARKER_MOVE_SPEC,
            args={"track": track, "clip": clip, "beat_time": beat_time, "distance": distance},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "beat_time": require_non_negative_float(
                    "beat_time",
                    beat_time,
                    hint="Use a non-negative --beat-time.",
                ),
                "distance": distance,
            },
        )


def _register_warp_marker_remove(
    warp_marker_app: typer.Typer,
    run_client_command_spec: CommandRunner,
) -> None:
    @warp_marker_app.command("remove")
    def clip_warp_marker_remove(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        beat_time: Annotated[float, typer.Option("--beat-time")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=WARP_MARKER_REMOVE_SPEC,
            args={"track": track, "clip": clip, "beat_time": beat_time},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "beat_time": require_non_negative_float(
                    "beat_time",
                    beat_time,
                    hint="Use a non-negative --beat-time.",
                ),
            },
        )


def _register_gain_set(gain_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @gain_app.command("set")
    def clip_gain_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        db: Annotated[float, typer.Option("--db", help="Gain in dB")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=GAIN_SET_SPEC,
            args={"track": track, "clip": clip, "db": db},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "db": db,
            },
        )


def _register_transpose_set(
    transpose_app: typer.Typer,
    run_client_command_spec: CommandRunner,
) -> None:
    @transpose_app.command("set")
    def clip_transpose_set(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        semitones: Annotated[int, typer.Option("--semitones")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=TRANSPOSE_SET_SPEC,
            args={"track": track, "clip": clip, "semitones": semitones},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "semitones": semitones,
            },
        )


def _register_file_replace(file_app: typer.Typer, run_client_command_spec: CommandRunner) -> None:
    @file_app.command("replace")
    def clip_file_replace(
        ctx: typer.Context,
        track: Annotated[int, typer.Argument(help="Track index")],
        clip: Annotated[int, typer.Argument(help="Clip slot index")],
        audio_path: Annotated[str, typer.Option("--audio-path", help="Absolute replacement path")],
    ) -> None:
        run_client_command_spec(
            ctx,
            spec=FILE_REPLACE_SPEC,
            args={"track": track, "clip": clip, "audio_path": audio_path},
            method_kwargs=lambda: {
                "track": require_track_index(track),
                "clip": _clip_index(clip),
                "audio_path": require_absolute_path(
                    "audio_path",
                    audio_path,
                    hint="Pass an absolute path to --audio-path.",
                ),
            },
        )


def register_prop_commands(
    *,
    props_app: typer.Typer,
    loop_app: typer.Typer,
    marker_app: typer.Typer,
    warp_app: typer.Typer,
    warp_marker_app: typer.Typer,
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
    _register_warp_marker_list(warp_marker_app, run_client_command_spec)
    _register_warp_marker_add(warp_marker_app, run_client_command_spec)
    _register_warp_marker_move(warp_marker_app, run_client_command_spec)
    _register_warp_marker_remove(warp_marker_app, run_client_command_spec)
    _register_gain_set(gain_app, run_client_command_spec)
    _register_transpose_set(transpose_app, run_client_command_spec)
    _register_file_replace(file_app, run_client_command_spec)
