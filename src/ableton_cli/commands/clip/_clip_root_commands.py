from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ...audio_analysis.transient import analyze_transients
from .._validation import invalid_argument, require_non_negative, require_positive_float
from ._parsers import (
    parse_cut_to_drum_rack_slice_spec,
    parse_cut_to_drum_rack_source,
    parse_duplicate_destinations,
    parse_place_pattern_destinations,
)
from ._shared import (
    execute_clip_command,
    execute_track_clip_command,
    resolve_client,
    validate_track_and_clip,
)


def register_clip_root_commands(clip_app: typer.Typer) -> None:
    clip_app.command("create")(clip_create)
    clip_app.command("fire")(clip_fire)
    clip_app.command("stop")(clip_stop)
    clip_app.command("duplicate")(clip_duplicate)
    clip_app.command("duplicate-many")(clip_duplicate_many)
    clip_app.command("place-pattern")(clip_place_pattern)
    clip_app.command("cut-to-drum-rack")(clip_cut_to_drum_rack)


def clip_create(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    length: Annotated[
        float,
        typer.Option("--length", help="Clip length in beats"),
    ] = 4.0,
) -> None:
    def _run() -> dict[str, object]:
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        valid_length = require_positive_float(
            "length",
            length,
            hint="Use a positive clip length in beats.",
        )
        return resolve_client(ctx).create_clip(valid_track, valid_clip, valid_length)

    execute_clip_command(
        ctx,
        command="clip create",
        args={"track": track, "clip": clip, "length": length},
        action=_run,
    )


def clip_fire(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    execute_track_clip_command(
        ctx,
        command="clip fire",
        args={"track": track, "clip": clip},
        track_clip=(track, clip),
        action=lambda client, valid_track, valid_clip: client.fire_clip(valid_track, valid_clip),
    )


def clip_stop(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    execute_track_clip_command(
        ctx,
        command="clip stop",
        args={"track": track, "clip": clip},
        track_clip=(track, clip),
        action=lambda client, valid_track, valid_clip: client.stop_clip(valid_track, valid_clip),
    )


def clip_duplicate(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    src_clip: Annotated[int, typer.Argument(help="Source clip slot index (0-based)")],
    dst_clip: Annotated[
        int | None,
        typer.Argument(help="Destination clip slot index (0-based)"),
    ] = None,
    to: Annotated[
        str | None,
        typer.Option("--to", help="Comma-separated destination clip slot indexes (0-based)"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_src_clip = require_non_negative(
            "src_clip",
            src_clip,
            hint="Use a valid source clip slot index.",
        )
        single_dst_clip, many_dst_clips = parse_duplicate_destinations(
            src_clip=valid_src_clip,
            dst_clip=dst_clip,
            to=to,
        )
        return resolve_client(ctx).clip_duplicate(
            track=valid_track,
            src_clip=valid_src_clip,
            dst_clip=single_dst_clip,
            dst_clips=many_dst_clips,
        )

    execute_clip_command(
        ctx,
        command="clip duplicate",
        args={"track": track, "src_clip": src_clip, "dst_clip": dst_clip, "to": to},
        action=_run,
    )


def clip_duplicate_many(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    src_clip: Annotated[int, typer.Argument(help="Source clip slot index (0-based)")],
    to: Annotated[
        str,
        typer.Option("--to", help="Comma-separated destination clip slot indexes (0-based)"),
    ],
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_src_clip = require_non_negative(
            "src_clip",
            src_clip,
            hint="Use a valid source clip slot index.",
        )
        _single_dst_clip, many_dst_clips = parse_duplicate_destinations(
            src_clip=valid_src_clip,
            dst_clip=None,
            to=to,
        )
        assert many_dst_clips is not None
        return resolve_client(ctx).clip_duplicate(
            track=valid_track,
            src_clip=valid_src_clip,
            dst_clips=many_dst_clips,
        )

    execute_clip_command(
        ctx,
        command="clip duplicate-many",
        args={"track": track, "src_clip": src_clip, "to": to},
        action=_run,
    )


def clip_place_pattern(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[
        int,
        typer.Option("--clip", help="Source clip slot index to place (0-based)"),
    ],
    scenes: Annotated[
        str,
        typer.Option(
            "--scenes",
            help=(
                "Scene selectors: comma-separated indexes/ranges/names "
                "(e.g. 2,4,6 or 2-6 or Intro,Drop)"
            ),
        ),
    ],
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        src_clip = require_non_negative(
            "clip",
            clip,
            hint="Use a valid source clip slot index.",
        )
        client = resolve_client(ctx)
        dst_clips = parse_place_pattern_destinations(
            src_clip=src_clip,
            scenes=scenes,
            load_scenes=client.scenes_list,
        )
        return client.clip_duplicate(
            track=valid_track,
            src_clip=src_clip,
            dst_clips=dst_clips,
        )

    execute_clip_command(
        ctx,
        command="clip place-pattern",
        args={"track": track, "clip": clip, "scenes": scenes},
        action=_run,
    )


def clip_cut_to_drum_rack(
    ctx: typer.Context,
    source_track: Annotated[
        int | None,
        typer.Option("--source-track", help="Source session track index (0-based)"),
    ] = None,
    source_clip: Annotated[
        int | None,
        typer.Option("--source-clip", help="Source session clip slot index (0-based)"),
    ] = None,
    source: Annotated[
        str | None,
        typer.Option("--source", help="Source browser target (URI or path)"),
    ] = None,
    source_file: Annotated[
        Path | None,
        typer.Option("--source-file", help="Local PCM WAV file for transient slicing"),
    ] = None,
    target_track: Annotated[
        int | None,
        typer.Option("--target-track", help="Destination track index (0-based)"),
    ] = None,
    grid: Annotated[
        str | None,
        typer.Option("--grid", help="Slice grid (fraction or beats, e.g. 1/16 or 0.25)"),
    ] = None,
    slice_count: Annotated[
        int | None,
        typer.Option("--slice-count", help="Number of equal slices"),
    ] = None,
    transient: Annotated[
        bool,
        typer.Option("--transient", help="Analyze --source-file transients and slice by onsets"),
    ] = False,
    bpm: Annotated[
        float | None,
        typer.Option("--bpm", help="Source tempo for transient analysis"),
    ] = None,
    max_slices: Annotated[
        int,
        typer.Option("--max-slices", help="Maximum transient slices"),
    ] = 32,
    start_pad: Annotated[
        int,
        typer.Option("--start-pad", help="Destination start pad index (0-based)"),
    ] = 0,
    create_trigger_clip: Annotated[
        bool,
        typer.Option("--create-trigger-clip", help="Create trigger MIDI clip on destination track"),
    ] = False,
    trigger_clip_slot: Annotated[
        int | None,
        typer.Option("--trigger-clip-slot", help="Trigger clip slot index (0-based)"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        client = resolve_client(ctx)
        valid_target_track = (
            require_non_negative(
                "target_track",
                target_track,
                hint="Use a valid target track index from 'ableton-cli tracks list'.",
            )
            if target_track is not None
            else None
        )
        valid_start_pad = require_non_negative(
            "start_pad",
            start_pad,
            hint="Use a non-negative --start-pad value.",
        )
        valid_trigger_clip_slot = (
            require_non_negative(
                "trigger_clip_slot",
                trigger_clip_slot,
                hint="Use a non-negative --trigger-clip-slot value.",
            )
            if trigger_clip_slot is not None
            else None
        )
        if not create_trigger_clip and valid_trigger_clip_slot is not None:
            raise invalid_argument(
                message="--trigger-clip-slot requires --create-trigger-clip",
                hint="Use --create-trigger-clip with --trigger-clip-slot.",
            )
        if create_trigger_clip and valid_trigger_clip_slot is None:
            valid_trigger_clip_slot = 0

        if transient:
            if source_file is None:
                raise invalid_argument(
                    message="--transient requires --source-file",
                    hint="Use --source-file with --transient slicing.",
                )
            if source is not None or source_track is not None or source_clip is not None:
                raise invalid_argument(
                    message="--source-file is mutually exclusive with session/browser sources",
                    hint="Use only --source-file for transient slicing.",
                )
            if grid is not None or slice_count is not None:
                raise invalid_argument(
                    message="--transient is mutually exclusive with --grid/--slice-count",
                    hint="Transient slicing derives slice ranges from detected onsets.",
                )
            valid_bpm = _resolve_transient_bpm(client, bpm)
            analysis = analyze_transients(source_file, bpm=valid_bpm, max_slices=max_slices)
            source_file_path = str(analysis["path"])
            slice_ranges = [
                {
                    "slice_start": float(item["slice_start"]),
                    "slice_end": float(item["slice_end"]),
                }
                for item in analysis["slice_ranges"]  # type: ignore[union-attr]
            ]
            remote_result = client.clip_cut_to_drum_rack(
                source_track=None,
                source_clip=None,
                source_uri=None,
                source_path=None,
                target_track=valid_target_track,
                grid=None,
                slice_count=None,
                start_pad=valid_start_pad,
                create_trigger_clip=create_trigger_clip,
                trigger_clip_slot=valid_trigger_clip_slot,
                source_file=source_file_path,
                source_file_duration_beats=float(analysis["duration_beats"]),
                slice_ranges=slice_ranges,
            )
            return {
                **remote_result,
                "source_mode": remote_result.get("source_mode", "file"),
                "source_file": source_file_path,
                "bpm": valid_bpm,
                "duration_beats": analysis["duration_beats"],
                "slice_count": remote_result.get("slice_count", len(slice_ranges)),
                "transient_analysis": {
                    "analysis_version": analysis["analysis_version"],
                    "confidence": analysis["confidence"],
                    "warnings": analysis["warnings"],
                },
            }

        if source_file is not None:
            raise invalid_argument(
                message="--source-file requires --transient",
                hint="Use --source-file with --transient slicing.",
            )
        (
            valid_source_track,
            valid_source_clip,
            source_uri,
            source_path,
        ) = parse_cut_to_drum_rack_source(
            source_track=source_track,
            source_clip=source_clip,
            source=source,
        )
        valid_grid, valid_slice_count = parse_cut_to_drum_rack_slice_spec(
            grid=grid,
            slice_count=slice_count,
        )

        return client.clip_cut_to_drum_rack(
            source_track=valid_source_track,
            source_clip=valid_source_clip,
            source_uri=source_uri,
            source_path=source_path,
            target_track=valid_target_track,
            grid=valid_grid,
            slice_count=valid_slice_count,
            start_pad=valid_start_pad,
            create_trigger_clip=create_trigger_clip,
            trigger_clip_slot=valid_trigger_clip_slot,
        )

    execute_clip_command(
        ctx,
        command="clip cut-to-drum-rack",
        args={
            "source_track": source_track,
            "source_clip": source_clip,
            "source": source,
            "source_file": str(source_file) if source_file is not None else None,
            "target_track": target_track,
            "grid": grid,
            "slice_count": slice_count,
            "transient": transient,
            "bpm": bpm,
            "max_slices": max_slices,
            "start_pad": start_pad,
            "create_trigger_clip": create_trigger_clip,
            "trigger_clip_slot": trigger_clip_slot,
        },
        action=_run,
    )


def _resolve_transient_bpm(client: object, bpm: float | None) -> float:
    if bpm is not None:
        return _validate_transient_bpm(bpm)
    song_info = client.song_info()  # type: ignore[attr-defined]
    tempo = song_info.get("tempo") if isinstance(song_info, dict) else None
    if not isinstance(tempo, (int, float)):
        raise invalid_argument(
            message="song_info did not return a numeric tempo",
            hint="Pass --bpm explicitly for transient slicing.",
        )
    return _validate_transient_bpm(float(tempo))


def _validate_transient_bpm(value: float) -> float:
    if value < 20.0 or value > 999.0:
        raise invalid_argument(
            message=f"bpm must be between 20.0 and 999.0, got {value}",
            hint="Use a realistic tempo between 20.0 and 999.0 BPM.",
        )
    return float(value)
