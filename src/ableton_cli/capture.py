"""Session capture workflow: compose existing primitives (routing, arm,
record, transport, analysis) into one "hear what you composed" command.

``capture_session`` takes an injected ``client`` so it is unit-testable
with fakes (see ``tests/test_capture.py``), per the dependency-injection
style used by ``warp_conform.conform_session_clip_warp``. Each step is a
single existing client call; any step failure aborts immediately with the
step name in the error details (no fallback paths, no partial retries).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .audio_analysis import analyze_loudness, analyze_spectrum
from .errors import AppError, ErrorCode, ExitCode
from .remix.mastering import run_mastering_qa

_WAIT_PAD_SECONDS = 1.0
_BEATS_PER_BAR = 4.0


def _invalid_argument(message: str, hint: str, *, step: str, **details: Any) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
        details={"step": step, **details},
    )


def capture_session(
    client: Any,
    *,
    track: int,
    slot: int,
    bars: float,
    start: float = 0.0,
    set_routing: bool = False,
    analyze: bool = False,
    qa_project: str | None = None,
    wait_fn: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    if wait_fn is None:
        wait_fn = time.sleep
    if bars <= 0:
        raise _invalid_argument(
            message=f"bars must be > 0, got {bars}",
            hint="Use --bars > 0.",
            step="validate_bars",
        )

    track_ref = {"mode": "index", "index": track}

    track_info = client.get_track_info(track_ref)
    if not bool(track_info.get("is_audio_track")):
        raise _invalid_argument(
            message=f"track {track} is not an audio track",
            hint="Target an audio track for resampling capture.",
            step="validate_track_is_audio",
        )

    routing = client.track_routing_input_get(track_ref)
    current_type = routing.get("current", {}).get("type")
    if current_type != "Resampling":
        if not set_routing:
            raise _invalid_argument(
                message=f"track {track} input routing is {current_type!r}, not 'Resampling'",
                hint=(
                    "Pass --set-routing to set it automatically, or run: "
                    f"uv run ableton-cli track routing input set Resampling <channel> "
                    f"--track-index {track}"
                ),
                step="check_routing",
            )
        available_types = routing.get("available", {}).get("types", [])
        if "Resampling" not in available_types:
            raise _invalid_argument(
                message="'Resampling' is not an available input routing type for this track",
                hint="Resampling routing requires another track/bus to resample from.",
                step="set_routing",
                available_types=available_types,
            )
        available_channels = routing.get("available", {}).get("channels", [])
        channel = available_channels[0] if available_channels else "Resampling"
        client.track_routing_input_set(track_ref, "Resampling", channel)

    client.track_arm_set(track_ref, True)
    client.transport_position_set(start)
    client.fire_clip(track, slot)
    client.transport_play()

    song = client.song_info()
    tempo = float(song.get("tempo", 0.0))
    if tempo <= 0:
        raise _invalid_argument(
            message=f"invalid tempo read from song info: {tempo}",
            hint="Ensure Ableton Live reports a valid tempo before capturing.",
            step="read_tempo",
        )
    wait_seconds = bars * _BEATS_PER_BAR * 60.0 / tempo
    wait_fn(wait_seconds + _WAIT_PAD_SECONDS)

    client.stop_clip(track, slot)
    client.transport_stop()

    file_info = client.clip_file_path_get(track, slot)
    file_path = file_info.get("file_path")
    if not file_path:
        raise _invalid_argument(
            message="Recording produced no file path",
            hint="Confirm the track was armed, routed to Resampling, and recording started.",
            step="read_file_path",
        )

    result: dict[str, Any] = {
        "track": track,
        "slot": slot,
        "bars": bars,
        "tempo": tempo,
        "wait_seconds": wait_seconds,
        "file_path": file_path,
    }

    if analyze:
        result["loudness"] = analyze_loudness(file_path)
        result["spectrum"] = analyze_spectrum(file_path)

    if qa_project is not None:
        result["qa"] = run_mastering_qa(qa_project, render=file_path)

    return result
