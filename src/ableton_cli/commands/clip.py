from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    parse_notes_input,
    require_non_empty_string,
    require_non_negative,
    require_positive_float,
    validate_clip_note_filters,
)

clip_app = typer.Typer(help="Clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Clip note commands", no_args_is_help=True)
name_app = typer.Typer(help="Clip naming commands", no_args_is_help=True)
active_app = typer.Typer(help="Clip active-state commands", no_args_is_help=True)


def _validate_note_filters(
    *,
    start_time: float | None,
    end_time: float | None,
    pitch: int | None,
) -> dict[str, float | int | None]:
    return validate_clip_note_filters(
        start_time=start_time,
        end_time=end_time,
        pitch=pitch,
    )


@clip_app.command("create")
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
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        require_positive_float("length", length, hint="Use a positive clip length in beats.")
        return get_client(ctx).create_clip(track, clip, length)

    execute_command(
        ctx,
        command="clip create",
        args={"track": track, "clip": clip, "length": length},
        action=_run,
    )


@notes_app.command("add")
def clip_notes_add(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    notes_json: Annotated[
        str | None,
        typer.Option("--notes-json", help="JSON array of note objects"),
    ] = None,
    notes_file: Annotated[
        str | None,
        typer.Option("--notes-file", help="Path to JSON file containing note array"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        return get_client(ctx).add_notes_to_clip(track, clip, notes)

    execute_command(
        ctx,
        command="clip notes add",
        args={"track": track, "clip": clip},
        action=_run,
    )


@notes_app.command("get")
def clip_notes_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
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
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        filters = _validate_note_filters(start_time=start_time, end_time=end_time, pitch=pitch)
        return get_client(ctx).get_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes get",
        args={
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("clear")
def clip_notes_clear(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
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
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        filters = _validate_note_filters(start_time=start_time, end_time=end_time, pitch=pitch)
        return get_client(ctx).clear_clip_notes(
            track=track,
            clip=clip,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes clear",
        args={
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@notes_app.command("replace")
def clip_notes_replace(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    notes_json: Annotated[
        str | None,
        typer.Option("--notes-json", help="JSON array of note objects"),
    ] = None,
    notes_file: Annotated[
        str | None,
        typer.Option("--notes-file", help="Path to JSON file containing note array"),
    ] = None,
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
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        filters = _validate_note_filters(start_time=start_time, end_time=end_time, pitch=pitch)
        return get_client(ctx).replace_clip_notes(
            track=track,
            clip=clip,
            notes=notes,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="clip notes replace",
        args={
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
        },
        action=_run,
    )


@name_app.command("set")
def clip_name_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    name: Annotated[str, typer.Argument(help="New clip name")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        valid_name = require_non_empty_string("name", name, hint="Pass a non-empty clip name.")
        return get_client(ctx).set_clip_name(track, clip, valid_name)

    execute_command(
        ctx,
        command="clip name set",
        args={"track": track, "clip": clip, "name": name},
        action=_run,
    )


@clip_app.command("fire")
def clip_fire(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).fire_clip(track, clip)

    execute_command(
        ctx,
        command="clip fire",
        args={"track": track, "clip": clip},
        action=_run,
    )


@clip_app.command("stop")
def clip_stop(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).stop_clip(track, clip)

    execute_command(
        ctx,
        command="clip stop",
        args={"track": track, "clip": clip},
        action=_run,
    )


@clip_app.command("duplicate")
def clip_duplicate(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    src_clip: Annotated[int, typer.Argument(help="Source clip slot index (0-based)")],
    dst_clip: Annotated[int, typer.Argument(help="Destination clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "src_clip",
            src_clip,
            hint="Use a valid source clip slot index.",
        )
        require_non_negative(
            "dst_clip",
            dst_clip,
            hint="Use a valid destination clip slot index.",
        )
        return get_client(ctx).clip_duplicate(track, src_clip, dst_clip)

    execute_command(
        ctx,
        command="clip duplicate",
        args={"track": track, "src_clip": src_clip, "dst_clip": dst_clip},
        action=_run,
    )


@active_app.command("get")
def clip_active_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).clip_active_get(track, clip)

    execute_command(
        ctx,
        command="clip active get",
        args={"track": track, "clip": clip},
        action=_run,
    )


@active_app.command("set")
def clip_active_set(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    clip: Annotated[int, typer.Argument(help="Clip slot index (0-based)")],
    value: Annotated[bool, typer.Argument(help="Active value: true|false")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative(
            "clip",
            clip,
            hint="Use a valid clip slot index.",
        )
        return get_client(ctx).clip_active_set(track, clip, value)

    execute_command(
        ctx,
        command="clip active set",
        args={"track": track, "clip": clip, "value": value},
        action=_run,
    )


clip_app.add_typer(notes_app, name="notes")
clip_app.add_typer(name_app, name="name")
clip_app.add_typer(active_app, name="active")


def register(app: typer.Typer) -> None:
    app.add_typer(clip_app, name="clip")
