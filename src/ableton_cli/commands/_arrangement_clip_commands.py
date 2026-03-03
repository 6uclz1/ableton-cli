from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._arrangement_shared import require_arrangement_clip_index, require_track_index
from ._arrangement_specs import ArrangementCommandSpec
from ._validation import (
    invalid_argument,
    parse_notes_input,
    require_absolute_path,
    require_non_negative_float,
    require_positive_float,
)

CLIP_CREATE_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip create",
    client_method="arrangement_clip_create",
)

CLIP_LIST_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip list",
    client_method="arrangement_clip_list",
)

CLIP_DELETE_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip delete",
    client_method="arrangement_clip_delete",
)


def register_commands(
    clip_app: typer.Typer,
    *,
    run_client_command_spec: Callable[..., None],
) -> None:
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
            typer.Option(
                "--notes-file",
                help="Path to JSON file containing note array for MIDI clips",
            ),
        ] = None,
    ) -> None:
        def _method_kwargs() -> dict[str, object]:
            valid_track = require_track_index(track)
            valid_start = require_non_negative_float(
                "start",
                start,
                hint="Use a non-negative --start value in beats.",
            )
            valid_length = require_positive_float(
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
            return {
                "track": valid_track,
                "start_time": valid_start,
                "length": valid_length,
                "audio_path": normalized_audio_path,
                "notes": notes,
            }

        run_client_command_spec(
            ctx,
            spec=CLIP_CREATE_SPEC,
            args={
                "track": track,
                "start_time": start,
                "length": length,
                "audio_path": audio_path,
                "notes": notes_json is not None or notes_file is not None,
            },
            method_kwargs=_method_kwargs,
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
        def _method_kwargs() -> dict[str, object]:
            valid_track = require_track_index(track) if track is not None else None
            return {"track": valid_track}

        run_client_command_spec(
            ctx,
            spec=CLIP_LIST_SPEC,
            args={"track": track},
            method_kwargs=_method_kwargs,
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
        def _method_kwargs() -> dict[str, object]:
            valid_track = require_track_index(track)
            valid_index = require_arrangement_clip_index(index) if index is not None else None
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

            return {
                "track": valid_track,
                "index": valid_index,
                "start": valid_start,
                "end": valid_end,
                "delete_all": all_,
            }

        run_client_command_spec(
            ctx,
            spec=CLIP_DELETE_SPEC,
            args={"track": track, "index": index, "start": start, "end": end, "all": all_},
            method_kwargs=_method_kwargs,
        )
