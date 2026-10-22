"""Session capture workflow: compose existing primitives (routing, arm,
record, transport, analysis) into one "hear what you composed" command.

``capture_tracks`` repeats that capture once per track with the track soloed,
into a temporary audio track, so each track's contribution to a section can be
measured on its own (``spectrum_shares``). Every solo, temporary track, and
bypassed main device it touches is restored even when a capture fails.

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

from .audio_analysis import analyze_loudness, analyze_spectrum, spectrum_shares
from .audio_analysis.io import wav_duration_sec
from .audio_analysis.spectrum import RESOLUTIONS
from .errors import AppError, ErrorCode, ExitCode
from .remix.mastering import run_mastering_qa

_WAIT_PAD_SECONDS = 1.0
# Commands reach Live a fraction of a beat apart, so the measured start is never exact.
_RECORDED_START_TOLERANCE_BEATS = 0.5


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
    start: float,
    set_routing: bool = False,
    analyze: bool = False,
    qa_project: str | None = None,
    wait_fn: Callable[[float], None] | None = None,
    recorded_seconds_fn: Callable[[str], float] | None = None,
) -> dict[str, Any]:
    if wait_fn is None:
        wait_fn = time.sleep
    if recorded_seconds_fn is None:
        recorded_seconds_fn = wav_duration_sec
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
        # Omit the channel: valid channels change with the routing type, so
        # let Live auto-select its default for Resampling.
        client.track_routing_input_set(track_ref, "Resampling", None)

    song = client.song_info()
    tempo = float(song.get("tempo", 0.0))
    if tempo <= 0:
        raise _invalid_argument(
            message=f"invalid tempo read from song info: {tempo}",
            hint="Ensure Ableton Live reports a valid tempo before capturing.",
            step="read_tempo",
        )
    signature = song.get("signature", {})
    beats_per_bar = (
        float(signature.get("numerator", 4)) * 4.0 / float(signature.get("denominator", 4))
    )
    if start < beats_per_bar:
        raise _invalid_argument(
            message=f"start must leave one bar of pre-roll, got {start} beats",
            hint=f"Use --start >= {beats_per_bar:g} (one bar); recording begins exactly there.",
            step="validate_start",
        )

    # Live ignores a playhead moved while stopped, and firing a clip from a stopped
    # transport restarts the song at 0. So start playback, then move the playhead one
    # bar before start and fire: launch quantization begins the recording at start.
    client.track_arm_set(track_ref, True)
    client.transport_play()
    client.transport_position_set(start - beats_per_bar)
    client.fire_clip(track, slot)

    seconds_per_bar = beats_per_bar * 60.0 / tempo
    wait_seconds = bars * seconds_per_bar
    wait_fn(seconds_per_bar + wait_seconds + _WAIT_PAD_SECONDS)

    client.stop_clip(track, slot)
    client.transport_stop()
    stop_beat = float(client.song_info().get("current_time", 0.0))

    file_info = client.clip_file_path_get(track, slot)
    file_path = file_info.get("file_path")
    if not file_path:
        raise _invalid_argument(
            message="Recording produced no file path",
            hint="Confirm the track was armed, routed to Resampling, and recording started.",
            step="read_file_path",
        )

    recorded_start = round(stop_beat - recorded_seconds_fn(file_path) * tempo / 60.0, 3)
    if abs(recorded_start - start) > _RECORDED_START_TOLERANCE_BEATS:
        raise _invalid_argument(
            message=f"recording began at beat {recorded_start}, not at start beat {start}",
            hint="Set Live's global launch quantization to 1 Bar, then capture again.",
            step="verify_recorded_start",
            recorded_start_beat=recorded_start,
            requested_start_beat=start,
            file_path=file_path,
        )

    result: dict[str, Any] = {
        "track": track,
        "slot": slot,
        "bars": bars,
        "tempo": tempo,
        "wait_seconds": wait_seconds,
        "recorded_start_beat": recorded_start,
        "file_path": file_path,
    }

    if analyze:
        result["loudness"] = analyze_loudness(file_path)
        result["spectrum"] = analyze_spectrum(file_path)

    if qa_project is not None:
        result["qa"] = run_mastering_qa(qa_project, render=file_path)

    return result


_MAIN_TRACK = {"mode": "main"}


def capture_tracks(
    client: Any,
    *,
    tracks: list[int],
    bars: float,
    start: float = 0.0,
    bypass_main_devices: bool = False,
    analyze: bool = False,
    resolution: str = "bands",
    focus: str | None = None,
    wait_fn: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    if focus is not None and not analyze:
        raise _invalid_argument(
            message="--focus requires --analyze",
            hint="Add --analyze, or drop --focus.",
            step="validate_focus",
        )
    if analyze and resolution not in RESOLUTIONS:
        raise _invalid_argument(
            message=f"unsupported spectrum resolution: {resolution}",
            hint=f"Use one of: {', '.join(RESOLUTIONS)}.",
            step="validate_resolution",
        )
    names = _validate_capture_tracks(client, tracks)
    labels = _track_labels(tracks, names)

    bypassed: list[int] = []
    captures: list[dict[str, Any]] = []
    try:
        if bypass_main_devices:
            _bypass_active_main_devices(client, bypassed)
        for track in tracks:
            captures.append(
                {
                    "track_index": track,
                    "track_name": names[track],
                    "label": labels[track],
                    "file_path": _capture_soloed(
                        client, track=track, bars=bars, start=start, wait_fn=wait_fn
                    ),
                }
            )
    finally:
        for index in bypassed:
            client.device_active_set(_MAIN_TRACK, {"mode": "index", "index": index}, True)

    result: dict[str, Any] = {
        "start": start,
        "bars": bars,
        "bypassed_main_devices": bypassed,
        "captures": captures,
    }
    if analyze:
        result["shares"] = spectrum_shares(
            [(capture["label"], capture["file_path"]) for capture in captures],
            resolution=resolution,
            focus=focus,
        )
    return result


def _bypass_active_main_devices(client: Any, bypassed: list[int]) -> None:
    """Turn off each active main device, recording it in ``bypassed`` as soon as it is off."""
    for device in client.master_devices_list().get("devices", []):
        device_ref = {"mode": "index", "index": device["index"]}
        if client.device_active_get(_MAIN_TRACK, device_ref).get("active"):
            client.device_active_set(_MAIN_TRACK, device_ref, False)
            bypassed.append(device["index"])


def _validate_capture_tracks(client: Any, tracks: list[int]) -> dict[int, str]:
    if not tracks:
        raise _invalid_argument(
            message="capture-tracks needs at least one --track-index",
            hint="Pass --track-index once per track to capture.",
            step="validate_tracks",
        )
    for track in tracks:
        if tracks.count(track) > 1:
            raise _invalid_argument(
                message=f"duplicate track index: {track}",
                hint="Pass each --track-index once.",
                step="validate_tracks",
            )
    listing = client.tracks_list().get("tracks", [])
    names = {int(item["index"]): str(item["name"]) for item in listing}
    for track in tracks:
        if track not in names:
            raise _invalid_argument(
                message=f"track index {track} does not exist",
                hint="Use 'tracks list' to find track indexes.",
                step="validate_tracks",
            )
    soloed = [str(item["name"]) for item in listing if item.get("solo")]
    if soloed:
        raise _invalid_argument(
            message="tracks are already soloed; a solo capture would include them",
            hint="Unsolo every track, then run capture-tracks again.",
            step="check_solo",
            soloed_tracks=soloed,
        )
    return names


def _track_labels(tracks: list[int], names: dict[int, str]) -> dict[int, str]:
    chosen = [names[track] for track in tracks]
    return {
        track: names[track] if chosen.count(names[track]) == 1 else f"{track}:{names[track]}"
        for track in tracks
    }


def _capture_soloed(
    client: Any,
    *,
    track: int,
    bars: float,
    start: float,
    wait_fn: Callable[[float], None] | None,
) -> str:
    track_ref = {"mode": "index", "index": track}
    client.track_solo_set(track_ref, True)
    try:
        temporary = int(client.create_audio_track(-1)["index"])
        try:
            # The capture track's own output stays silent so it never feeds the resample.
            client.track_volume_set({"mode": "index", "index": temporary}, 0.0)
            capture = capture_session(
                client,
                track=temporary,
                slot=0,
                bars=bars,
                start=start,
                set_routing=True,
                wait_fn=wait_fn,
            )
        finally:
            client.tracks_delete(temporary)
    finally:
        client.track_solo_set(track_ref, False)
    return str(capture["file_path"])
