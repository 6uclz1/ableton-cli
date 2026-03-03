from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    invalid_argument,
    parse_notes_input,
    require_absolute_path,
    require_non_empty_string,
    require_non_negative,
    require_non_negative_float,
    require_positive_float,
    resolve_uri_or_path_target,
    validate_clip_note_filters,
)
from .clip._parsers import parse_arrangement_scene_durations

arrangement_app = typer.Typer(help="Arrangement commands", no_args_is_help=True)
record_app = typer.Typer(help="Arrangement recording commands", no_args_is_help=True)
clip_app = typer.Typer(help="Arrangement clip commands", no_args_is_help=True)
notes_app = typer.Typer(help="Arrangement clip note commands", no_args_is_help=True)


@record_app.command("start")
def arrangement_record_start(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="arrangement record start",
        args={},
        action=lambda: get_client(ctx).arrangement_record_start(),
    )


@record_app.command("stop")
def arrangement_record_stop(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="arrangement record stop",
        args={},
        action=lambda: get_client(ctx).arrangement_record_stop(),
    )


@clip_app.command("create")
def arrangement_clip_create(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    start: Annotated[
        float,
        typer.Option(
            "--start",
            help="Arrangement start time in beats",
        ),
    ],
    length: Annotated[
        float,
        typer.Option(
            "--length",
            help="Arrangement clip length in beats",
        ),
    ],
    audio_path: Annotated[
        str | None,
        typer.Option(
            "--audio-path",
            help="Absolute audio file path for audio tracks",
        ),
    ] = None,
    notes_json: Annotated[
        str | None,
        typer.Option("--notes-json", help="JSON array of note objects for MIDI clips"),
    ] = None,
    notes_file: Annotated[
        str | None,
        typer.Option("--notes-file", help="Path to JSON file containing note array for MIDI clips"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        require_non_negative_float(
            "start",
            start,
            hint="Use a non-negative --start value in beats.",
        )
        require_positive_float(
            "length",
            length,
            hint="Use a positive --length value in beats.",
        )
        normalized_audio_path = (
            require_absolute_path(
                "audio_path",
                audio_path,
                hint="Pass an absolute file path for --audio-path.",
            )
            if audio_path is not None
            else None
        )
        notes = (
            parse_notes_input(notes_json=notes_json, notes_file=notes_file)
            if notes_json is not None or notes_file is not None
            else None
        )
        if normalized_audio_path is not None and notes is not None:
            raise invalid_argument(
                message="--audio-path and --notes-json/--notes-file are mutually exclusive",
                hint="Use notes options for MIDI clips or --audio-path for audio clips.",
            )
        return get_client(ctx).arrangement_clip_create(
            track=track,
            start_time=start,
            length=length,
            audio_path=normalized_audio_path,
            notes=notes,
        )

    execute_command(
        ctx,
        command="arrangement clip create",
        args={
            "track": track,
            "start_time": start,
            "length": length,
            "audio_path": audio_path,
            "notes": notes_json is not None or notes_file is not None,
        },
        action=_run,
    )


@clip_app.command("list")
def arrangement_clip_list(
    ctx: typer.Context,
    track: Annotated[
        int | None,
        typer.Option(
            "--track",
            help="Optional track index filter (0-based)",
        ),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        if track is not None:
            require_non_negative(
                "track",
                track,
                hint="Use a valid track index from 'ableton-cli tracks list'.",
            )
        return get_client(ctx).arrangement_clip_list(track=track)

    execute_command(
        ctx,
        command="arrangement clip list",
        args={"track": track},
        action=_run,
    )


@notes_app.command("add")
def arrangement_clip_notes_add(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    index: Annotated[int, typer.Argument(help="Arrangement clip index from list output")],
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
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_index = require_non_negative(
            "index",
            index,
            hint="Use a valid arrangement clip index from 'ableton-cli arrangement clip list'.",
        )
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        return get_client(ctx).arrangement_clip_notes_add(
            track=valid_track,
            index=valid_index,
            notes=notes,
        )

    execute_command(
        ctx,
        command="arrangement clip notes add",
        args={"track": track, "index": index},
        action=_run,
    )


@notes_app.command("get")
def arrangement_clip_notes_get(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    index: Annotated[int, typer.Argument(help="Arrangement clip index from list output")],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[int | None, typer.Option("--pitch", help="Exact MIDI pitch filter")] = None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_index = require_non_negative(
            "index",
            index,
            hint="Use a valid arrangement clip index from 'ableton-cli arrangement clip list'.",
        )
        filters = validate_clip_note_filters(
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return get_client(ctx).arrangement_clip_notes_get(
            track=valid_track,
            index=valid_index,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="arrangement clip notes get",
        args={"track": track, "index": index, "start_time": start_time, "end_time": end_time},
        action=_run,
    )


@notes_app.command("clear")
def arrangement_clip_notes_clear(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    index: Annotated[int, typer.Argument(help="Arrangement clip index from list output")],
    start_time: Annotated[
        float | None,
        typer.Option("--start-time", help="Inclusive start time filter in beats"),
    ] = None,
    end_time: Annotated[
        float | None,
        typer.Option("--end-time", help="Exclusive end time filter in beats"),
    ] = None,
    pitch: Annotated[int | None, typer.Option("--pitch", help="Exact MIDI pitch filter")] = None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_index = require_non_negative(
            "index",
            index,
            hint="Use a valid arrangement clip index from 'ableton-cli arrangement clip list'.",
        )
        filters = validate_clip_note_filters(
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return get_client(ctx).arrangement_clip_notes_clear(
            track=valid_track,
            index=valid_index,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="arrangement clip notes clear",
        args={"track": track, "index": index, "start_time": start_time, "end_time": end_time},
        action=_run,
    )


@notes_app.command("replace")
def arrangement_clip_notes_replace(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    index: Annotated[int, typer.Argument(help="Arrangement clip index from list output")],
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
    pitch: Annotated[int | None, typer.Option("--pitch", help="Exact MIDI pitch filter")] = None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_index = require_non_negative(
            "index",
            index,
            hint="Use a valid arrangement clip index from 'ableton-cli arrangement clip list'.",
        )
        notes = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
        filters = validate_clip_note_filters(
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return get_client(ctx).arrangement_clip_notes_replace(
            track=valid_track,
            index=valid_index,
            notes=notes,
            start_time=filters["start_time"],
            end_time=filters["end_time"],
            pitch=filters["pitch"],
        )

    execute_command(
        ctx,
        command="arrangement clip notes replace",
        args={"track": track, "index": index, "start_time": start_time, "end_time": end_time},
        action=_run,
    )


@notes_app.command("import-browser")
def arrangement_clip_notes_import_browser(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    index: Annotated[int, typer.Argument(help="Arrangement clip index from list output")],
    target: Annotated[str, typer.Argument(help="Browser target (URI or path to .alc)")],
    mode: Annotated[
        str, typer.Option("--mode", help="Note import mode: replace|append")
    ] = "replace",
    import_length: Annotated[
        bool,
        typer.Option(
            "--import-length/--no-import-length",
            help="Copy source clip length into the destination arrangement clip",
        ),
    ] = False,
    import_groove: Annotated[
        bool,
        typer.Option(
            "--import-groove/--no-import-groove",
            help="Copy source clip groove settings into the destination arrangement clip",
        ),
    ] = False,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_index = require_non_negative(
            "index",
            index,
            hint="Use a valid arrangement clip index from 'ableton-cli arrangement clip list'.",
        )
        valid_mode = require_non_empty_string(
            "mode",
            mode,
            hint="Use --mode replace or append.",
        ).lower()
        if valid_mode not in {"replace", "append"}:
            raise invalid_argument(
                message=f"mode must be one of replace/append, got {mode}",
                hint="Use --mode replace or append.",
            )
        target_uri, target_path = resolve_uri_or_path_target(
            target=target,
            hint="Use a browser path or URI for a .alc MIDI clip item.",
        )
        return get_client(ctx).arrangement_clip_notes_import_browser(
            track=valid_track,
            index=valid_index,
            target_uri=target_uri,
            target_path=target_path,
            mode=valid_mode,
            import_length=import_length,
            import_groove=import_groove,
        )

    execute_command(
        ctx,
        command="arrangement clip notes import-browser",
        args={
            "track": track,
            "index": index,
            "target": target,
            "mode": mode,
            "import_length": import_length,
            "import_groove": import_groove,
        },
        action=_run,
    )


@clip_app.command("delete")
def arrangement_clip_delete(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    index: Annotated[
        int | None,
        typer.Argument(help="Arrangement clip index to delete", show_default=False),
    ] = None,
    start: Annotated[
        float | None,
        typer.Option("--start", help="Range start beat (inclusive)"),
    ] = None,
    end: Annotated[
        float | None,
        typer.Option("--end", help="Range end beat (exclusive)"),
    ] = None,
    all_: Annotated[
        bool,
        typer.Option("--all", help="Delete all arrangement clips on the track"),
    ] = False,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_index = (
            require_non_negative(
                "index",
                index,
                hint="Use a valid arrangement clip index from 'ableton-cli arrangement clip list'.",
            )
            if index is not None
            else None
        )
        has_range_value = start is not None or end is not None
        if has_range_value and (start is None or end is None):
            raise invalid_argument(
                message="--start and --end must be provided together for range delete mode",
                hint="Use both --start and --end, or use index/--all mode.",
            )
        mode_count = int(valid_index is not None) + int(has_range_value) + int(all_)
        if mode_count != 1:
            raise invalid_argument(
                message="Exactly one delete mode must be selected: index, range, or --all",
                hint="Use one of: <index> | --start/--end | --all.",
            )

        valid_start = None
        valid_end = None
        if has_range_value:
            assert start is not None
            assert end is not None
            valid_start = require_non_negative_float(
                "start",
                start,
                hint="Use a non-negative --start value in beats.",
            )
            valid_end = require_non_negative_float(
                "end",
                end,
                hint="Use a non-negative --end value in beats.",
            )
            if valid_end <= valid_start:
                raise invalid_argument(
                    message=(
                        f"end must be greater than start (start={valid_start}, end={valid_end})"
                    ),
                    hint="Use a valid [start, end) range with end > start.",
                )

        return get_client(ctx).arrangement_clip_delete(
            track=valid_track,
            index=valid_index,
            start=valid_start,
            end=valid_end,
            delete_all=all_,
        )

    execute_command(
        ctx,
        command="arrangement clip delete",
        args={"track": track, "index": index, "start": start, "end": end, "all": all_},
        action=_run,
    )


@arrangement_app.command("from-session")
def arrangement_from_session(
    ctx: typer.Context,
    scenes: Annotated[
        str,
        typer.Option(
            "--scenes",
            help="Scene duration map as CSV (scene_index:duration_beats,...)",
        ),
    ],
) -> None:
    def _run() -> dict[str, object]:
        parsed = parse_arrangement_scene_durations(scenes)
        return get_client(ctx).arrangement_from_session(parsed)

    execute_command(
        ctx,
        command="arrangement from-session",
        args={"scenes": require_non_empty_string("scenes", scenes, hint="Use --scenes 0:24,1:48.")},
        action=_run,
    )


arrangement_app.add_typer(record_app, name="record")
clip_app.add_typer(notes_app, name="notes")
arrangement_app.add_typer(clip_app, name="clip")


def register(app: typer.Typer) -> None:
    app.add_typer(arrangement_app, name="arrangement")
