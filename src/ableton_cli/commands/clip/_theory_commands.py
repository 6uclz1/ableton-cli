from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from ...errors import AppError, ErrorCode, ExitCode
from ...groove_apply import apply_groove
from ...music_theory import (
    ARPEGGIATE_MODES,
    SCALE_INTERVALS,
    MusicTheoryError,
    arpeggiate,
    euclidean_notes,
    ratchet_notes,
    retrograde_notes,
    transpose_in_scale,
)
from .._validation import invalid_argument
from ._shared import (
    execute_clip_command,
    notes_without_ids,
    require_float_in_range,
    require_int_in_range,
    resolve_client,
    validate_track_and_clip,
    validated_transform_filters,
)

_EUCLIDEAN_MODES = frozenset({"replace", "merge"})


def register_theory_commands(notes_app: typer.Typer) -> None:
    notes_app.command("transpose-in-scale")(clip_notes_transpose_in_scale)
    notes_app.command("arpeggiate")(clip_notes_arpeggiate)
    notes_app.command("euclidean")(clip_notes_euclidean)
    notes_app.command("ratchet")(clip_notes_ratchet)
    notes_app.command("retrograde")(clip_notes_retrograde)
    notes_app.command("apply-groove")(clip_notes_apply_groove)


def _music_theory_error(exc: MusicTheoryError, *, hint: str) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=str(exc),
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
        details={"offending_indices": exc.offending_indices},
    )


def clip_notes_transpose_in_scale(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    root: Annotated[str, typer.Option("--root", help="Scale root note, e.g. C, F#, Bb")],
    scale: Annotated[
        str,
        typer.Option(
            "--scale",
            help=f"Scale name: one of {', '.join(sorted(SCALE_INTERVALS))}",
        ),
    ],
    degrees: Annotated[
        int,
        typer.Option("--degrees", help="Number of scale degrees to shift (can be negative)"),
    ],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = validated_transform_filters(
            track=track, clip=clip, start_time=start_time, end_time=end_time, pitch=pitch
        )
        if scale not in SCALE_INTERVALS:
            raise invalid_argument(
                message=f"scale must be one of {sorted(SCALE_INTERVALS)}, got {scale!r}",
                hint="Use --scale with one of the supported scale names.",
            )
        client = resolve_client(ctx)
        existing = client.get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )
        try:
            transformed = transpose_in_scale(
                notes_without_ids(existing["notes"]), root=root, scale=scale, degrees=degrees
            )
        except MusicTheoryError as exc:
            raise _music_theory_error(
                exc, hint="Reduce --degrees or narrow the filter to keep pitches in range."
            ) from exc
        except ValueError as exc:
            raise invalid_argument(message=str(exc), hint="Use a valid --root note name.") from exc
        return client.replace_clip_notes(
            track=track,
            clip=clip,
            notes=transformed,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
        ctx,
        command="clip notes transpose-in-scale",
        args={
            "track": track,
            "clip": clip,
            "root": root,
            "scale": scale,
            "degrees": degrees,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


def clip_notes_arpeggiate(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    mode: Annotated[
        str,
        typer.Option("--mode", help="Arpeggio order: up|down|updown|random"),
    ] = "up",
    rate: Annotated[
        str,
        typer.Option("--rate", help="Step spacing as a grid fraction, e.g. 1/16"),
    ] = "1/16",
    gate: Annotated[
        float,
        typer.Option("--gate", help="Per-step duration as a fraction of rate, in (0.0, 1.0]"),
    ] = 0.9,
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = validated_transform_filters(
            track=track, clip=clip, start_time=start_time, end_time=end_time, pitch=pitch
        )
        if mode not in ARPEGGIATE_MODES:
            raise invalid_argument(
                message=f"mode must be one of {sorted(ARPEGGIATE_MODES)}, got {mode!r}",
                hint="Use --mode up, down, updown, or random.",
            )
        valid_gate = require_float_in_range(
            name="gate", value=gate, minimum=0.0, maximum=1.0, hint="Use --gate in (0.0, 1.0]."
        )
        client = resolve_client(ctx)
        existing = client.get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )
        try:
            transformed = arpeggiate(
                notes_without_ids(existing["notes"]), mode=mode, rate=rate, gate=valid_gate
            )
        except ValueError as exc:
            raise invalid_argument(message=str(exc), hint="Use a grid string like '1/16'.") from exc
        return client.replace_clip_notes(
            track=track,
            clip=clip,
            notes=transformed,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
        ctx,
        command="clip notes arpeggiate",
        args={
            "track": track,
            "clip": clip,
            "mode": mode,
            "rate": rate,
            "gate": gate,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


def clip_notes_euclidean(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    pitch: Annotated[int, typer.Option("--pitch", help="MIDI pitch for generated notes")],
    steps: Annotated[int, typer.Option("--steps", help="Total number of grid steps")],
    pulses: Annotated[int, typer.Option("--pulses", help="Number of hits distributed over steps")],
    length: Annotated[float, typer.Option("--length", help="Total pattern length in beats")],
    rotate: Annotated[
        int, typer.Option("--rotate", help="Rotate the generated pattern by N steps")
    ] = 0,
    velocity: Annotated[
        int, typer.Option("--velocity", help="Velocity for generated notes (1-127)")
    ] = 100,
    mode: Annotated[
        str,
        typer.Option("--mode", help="replace clears pitch/range first; merge adds on top"),
    ] = "replace",
) -> None:
    def _run() -> dict[str, object]:
        if mode not in _EUCLIDEAN_MODES:
            raise invalid_argument(
                message=f"mode must be one of {sorted(_EUCLIDEAN_MODES)}, got {mode!r}",
                hint="Use --mode replace or merge.",
            )
        require_int_in_range(
            name="steps", value=steps, minimum=1, maximum=512, hint="Use --steps >= 1."
        )
        require_int_in_range(
            name="pulses",
            value=pulses,
            minimum=0,
            maximum=steps,
            hint="Use 0 <= --pulses <= steps.",
        )
        valid_track, valid_clip = validate_track_and_clip(track=track, clip=clip)
        try:
            notes = euclidean_notes(
                pitch=pitch,
                steps=steps,
                pulses=pulses,
                rotate=rotate,
                length=length,
                velocity=velocity,
            )
        except MusicTheoryError as exc:
            raise _music_theory_error(
                exc, hint="Use --pitch and --velocity within the valid MIDI ranges."
            ) from exc
        except ValueError as exc:
            raise invalid_argument(message=str(exc), hint="Use --length > 0.") from exc

        client = resolve_client(ctx)
        if mode == "merge":
            return client.add_notes_to_clip(valid_track, valid_clip, notes)
        return client.replace_clip_notes(
            track=valid_track,
            clip=valid_clip,
            notes=notes,
            start_time=0.0,
            end_time=length,
            pitch=pitch,
        )

    execute_clip_command(
        ctx,
        command="clip notes euclidean",
        args={
            "track": track,
            "clip": clip,
            "pitch": pitch,
            "steps": steps,
            "pulses": pulses,
            "rotate": rotate,
            "length": length,
            "velocity": velocity,
            "mode": mode,
        },
        action=_run,
    )


def clip_notes_ratchet(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    division: Annotated[
        int, typer.Option("--division", help="Number of equal repeats per matching note")
    ],
    probability: Annotated[
        float,
        typer.Option(
            "--probability", help="Chance each repeat after the first survives, in [0.0, 1.0]"
        ),
    ] = 1.0,
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = validated_transform_filters(
            track=track, clip=clip, start_time=start_time, end_time=end_time, pitch=pitch
        )
        require_int_in_range(
            name="division", value=division, minimum=1, maximum=64, hint="Use --division >= 1."
        )
        valid_probability = require_float_in_range(
            name="probability",
            value=probability,
            minimum=0.0,
            maximum=1.0,
            hint="Use --probability in [0.0, 1.0].",
        )
        client = resolve_client(ctx)
        existing = client.get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )
        transformed = ratchet_notes(
            notes_without_ids(existing["notes"]), division=division, probability=valid_probability
        )
        return client.replace_clip_notes(
            track=track,
            clip=clip,
            notes=transformed,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
        ctx,
        command="clip notes ratchet",
        args={
            "track": track,
            "clip": clip,
            "division": division,
            "probability": probability,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


def clip_notes_retrograde(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    loop_length: Annotated[
        float,
        typer.Option("--loop-length", help="Clip loop length in beats to reverse notes within"),
    ],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = validated_transform_filters(
            track=track, clip=clip, start_time=start_time, end_time=end_time, pitch=pitch
        )
        if loop_length <= 0:
            raise invalid_argument(
                message=f"loop_length must be > 0, got {loop_length}",
                hint="Use --loop-length > 0.",
            )
        client = resolve_client(ctx)
        existing = client.get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )
        try:
            transformed = retrograde_notes(
                notes_without_ids(existing["notes"]), loop_length=loop_length
            )
        except ValueError as exc:
            raise invalid_argument(
                message=str(exc), hint="Use a --loop-length covering every filtered note."
            ) from exc
        return client.replace_clip_notes(
            track=track,
            clip=clip,
            notes=transformed,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
        ctx,
        command="clip notes retrograde",
        args={
            "track": track,
            "clip": clip,
            "loop_length": loop_length,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


def _load_groove_profile(groove_file: Path) -> dict[str, Any]:
    try:
        payload = json.loads(groove_file.read_text(encoding="utf-8"))
    except OSError as exc:
        raise invalid_argument(
            message=f"groove_file could not be read: {groove_file}",
            hint="Pass a path produced by 'audio groove extract --out'.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise invalid_argument(
            message=f"groove_file must be valid JSON: {exc.msg}",
            hint="Pass a path produced by 'audio groove extract --out'.",
        ) from exc

    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("grid"), str)
        or not isinstance(payload.get("slots"), list)
    ):
        raise invalid_argument(
            message="groove_file must contain a {grid, slots} groove profile object",
            hint="Pass a path produced by 'audio groove extract --out'.",
        )
    return payload


def clip_notes_apply_groove(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    groove_file: Annotated[
        Path, typer.Option("--groove-file", help="Groove profile JSON from 'audio groove extract'")
    ],
    timing_amount: Annotated[
        float, typer.Option("--timing-amount", help="Timing shift strength in [0.0, 1.0]")
    ] = 1.0,
    velocity_amount: Annotated[
        float, typer.Option("--velocity-amount", help="Velocity scaling strength in [0.0, 1.0]")
    ] = 0.0,
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[
        int | None,
        typer.Option("--pitch", help="Exact MIDI pitch filter"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        filters = validated_transform_filters(
            track=track, clip=clip, start_time=start_time, end_time=end_time, pitch=pitch
        )
        valid_timing_amount = require_float_in_range(
            name="timing_amount",
            value=timing_amount,
            minimum=0.0,
            maximum=1.0,
            hint="Use --timing-amount in [0.0, 1.0].",
        )
        valid_velocity_amount = require_float_in_range(
            name="velocity_amount",
            value=velocity_amount,
            minimum=0.0,
            maximum=1.0,
            hint="Use --velocity-amount in [0.0, 1.0].",
        )
        profile = _load_groove_profile(groove_file)
        client = resolve_client(ctx)
        existing = client.get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )
        try:
            transformed = apply_groove(
                notes_without_ids(existing["notes"]),
                profile,
                timing_amount=valid_timing_amount,
                velocity_amount=valid_velocity_amount,
            )
        except ValueError as exc:
            raise invalid_argument(
                message=str(exc),
                hint="Use a groove profile produced by 'audio groove extract'.",
            ) from exc
        return client.replace_clip_notes(
            track=track,
            clip=clip,
            notes=transformed,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_clip_command(
        ctx,
        command="clip notes apply-groove",
        args={
            "track": track,
            "clip": clip,
            "groove_file": str(groove_file),
            "timing_amount": timing_amount,
            "velocity_amount": velocity_amount,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )
