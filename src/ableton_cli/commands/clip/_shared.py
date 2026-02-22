from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

import typer

from ...runtime import execute_command as _execute_command
from .._validation import (
    invalid_argument,
    require_non_empty_string,
    require_non_negative,
    validate_clip_note_filters,
)

DEFAULT_TRACK_HINT = "Use a valid track index from 'ableton-cli tracks list'."
DEFAULT_CLIP_HINT = "Use a valid clip slot index."

TrackClipAction = Callable[[Any, int, int], dict[str, object]]


def execute_clip_command(
    ctx: typer.Context,
    *,
    command: str,
    args: dict[str, object],
    action: Callable[[], dict[str, object]],
) -> None:
    _execute_command(
        ctx,
        command=command,
        args=args,
        action=action,
    )


def resolve_client(ctx: typer.Context):  # noqa: ANN201
    package = sys.modules.get("ableton_cli.commands.clip")
    if package is None:
        raise RuntimeError("clip package is not initialized")
    package_get_client = getattr(package, "get_client", None)
    if package_get_client is None:
        raise RuntimeError("clip package get_client is not available")
    return package_get_client(ctx)


def validate_track(track: int, *, hint: str = DEFAULT_TRACK_HINT) -> int:
    return require_non_negative("track", track, hint=hint)


def validate_clip(
    value: int,
    *,
    name: str = "clip",
    hint: str = DEFAULT_CLIP_HINT,
) -> int:
    return require_non_negative(name, value, hint=hint)


def validate_track_and_clip(
    *,
    track: int,
    clip: int,
    clip_name: str = "clip",
    clip_hint: str = DEFAULT_CLIP_HINT,
) -> tuple[int, int]:
    valid_track = validate_track(track)
    valid_clip = validate_clip(clip, name=clip_name, hint=clip_hint)
    return valid_track, valid_clip


def validated_transform_filters(
    *,
    track: int,
    clip: int,
    start_time: float | None,
    end_time: float | None,
    pitch: int | None,
) -> dict[str, float | int | None]:
    validate_track_and_clip(track=track, clip=clip)
    return validate_clip_note_filters(
        start_time=start_time,
        end_time=end_time,
        pitch=pitch,
    )


def require_float_in_range(
    *,
    name: str,
    value: float,
    minimum: float,
    maximum: float,
    hint: str,
) -> float:
    if value < minimum or value > maximum:
        raise invalid_argument(
            message=f"{name} must be between {minimum} and {maximum}, got {value}",
            hint=hint,
        )
    return value


def require_int_in_range(
    *,
    name: str,
    value: int,
    minimum: int,
    maximum: int,
    hint: str,
) -> int:
    if value < minimum or value > maximum:
        raise invalid_argument(
            message=f"{name} must be between {minimum} and {maximum}, got {value}",
            hint=hint,
        )
    return value


def require_uri_or_path_target(target: str) -> str:
    parsed = require_non_empty_string(
        "target",
        target,
        hint="Pass a groove target path or URI.",
    )
    if "/" in parsed or ":" in parsed:
        return parsed
    raise invalid_argument(
        message=f"target must include '/' (path) or ':' (uri), got {parsed!r}",
        hint="Use a path like grooves/Hip Hop Boom Bap 16ths 90 bpm.agr or groove URI.",
    )


def execute_track_clip_command(
    ctx: typer.Context,
    *,
    command: str,
    args: dict[str, object],
    track_clip: tuple[int, int],
    action: TrackClipAction,
) -> None:
    def _run() -> dict[str, object]:
        track, clip = track_clip
        valid_track, valid_clip = validate_track_and_clip(
            track=track,
            clip=clip,
        )
        return action(resolve_client(ctx), valid_track, valid_clip)

    execute_clip_command(
        ctx,
        command=command,
        args=args,
        action=_run,
    )
