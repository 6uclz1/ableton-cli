from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._arrangement_shared import (
    filters_payload,
    require_arrangement_clip_index,
    require_track_index,
)
from ._arrangement_specs import ArrangementCommandSpec
from ._validation import (
    invalid_argument,
    parse_notes_input,
    require_non_empty_string,
    resolve_uri_or_path_target,
    validate_clip_note_filters,
)

NOTES_ADD_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip notes add",
    client_method="arrangement_clip_notes_add",
)

NOTES_GET_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip notes get",
    client_method="arrangement_clip_notes_get",
)

NOTES_CLEAR_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip notes clear",
    client_method="arrangement_clip_notes_clear",
)

NOTES_REPLACE_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip notes replace",
    client_method="arrangement_clip_notes_replace",
)

NOTES_IMPORT_BROWSER_SPEC = ArrangementCommandSpec(
    command_name="arrangement clip notes import-browser",
    client_method="arrangement_clip_notes_import_browser",
)


RunClientCommandSpec = Callable[..., None]


def _note_filter_method_kwargs(
    *,
    track: int,
    index: int,
    start_time: float | None,
    end_time: float | None,
    pitch: int | None,
) -> dict[str, object]:
    valid_track = require_track_index(track)
    valid_index = require_arrangement_clip_index(index)
    filters = validate_clip_note_filters(
        start_time=start_time,
        end_time=end_time,
        pitch=pitch,
    )
    return {
        "track": valid_track,
        "index": valid_index,
        "start_time": filters["start_time"],
        "end_time": filters["end_time"],
        "pitch": filters["pitch"],
    }


def _validate_import_mode(mode: str) -> str:
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
    return valid_mode


def _register_add_command(
    notes_app: typer.Typer,
    *,
    run_client_command_spec: RunClientCommandSpec,
) -> None:
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
        def _method_kwargs() -> dict[str, object]:
            return {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "notes": parse_notes_input(notes_json=notes_json, notes_file=notes_file),
            }

        run_client_command_spec(
            ctx,
            spec=NOTES_ADD_SPEC,
            args={"track": track, "index": index},
            method_kwargs=_method_kwargs,
        )


def _register_get_command(
    notes_app: typer.Typer,
    *,
    run_client_command_spec: RunClientCommandSpec,
) -> None:
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
        pitch: Annotated[
            int | None,
            typer.Option("--pitch", help="Exact MIDI pitch filter"),
        ] = None,
    ) -> None:
        def _method_kwargs() -> dict[str, object]:
            return _note_filter_method_kwargs(
                track=track,
                index=index,
                start_time=start_time,
                end_time=end_time,
                pitch=pitch,
            )

        run_client_command_spec(
            ctx,
            spec=NOTES_GET_SPEC,
            args=filters_payload(
                track=track,
                index=index,
                start_time=start_time,
                end_time=end_time,
                pitch=pitch,
            ),
            method_kwargs=_method_kwargs,
        )


def _register_clear_command(
    notes_app: typer.Typer,
    *,
    run_client_command_spec: RunClientCommandSpec,
) -> None:
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
        pitch: Annotated[
            int | None,
            typer.Option("--pitch", help="Exact MIDI pitch filter"),
        ] = None,
    ) -> None:
        def _method_kwargs() -> dict[str, object]:
            return _note_filter_method_kwargs(
                track=track,
                index=index,
                start_time=start_time,
                end_time=end_time,
                pitch=pitch,
            )

        run_client_command_spec(
            ctx,
            spec=NOTES_CLEAR_SPEC,
            args=filters_payload(
                track=track,
                index=index,
                start_time=start_time,
                end_time=end_time,
                pitch=pitch,
            ),
            method_kwargs=_method_kwargs,
        )


def _register_replace_command(
    notes_app: typer.Typer,
    *,
    run_client_command_spec: RunClientCommandSpec,
) -> None:
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
        pitch: Annotated[
            int | None,
            typer.Option("--pitch", help="Exact MIDI pitch filter"),
        ] = None,
    ) -> None:
        def _method_kwargs() -> dict[str, object]:
            payload = _note_filter_method_kwargs(
                track=track,
                index=index,
                start_time=start_time,
                end_time=end_time,
                pitch=pitch,
            )
            payload["notes"] = parse_notes_input(notes_json=notes_json, notes_file=notes_file)
            return payload

        run_client_command_spec(
            ctx,
            spec=NOTES_REPLACE_SPEC,
            args=filters_payload(
                track=track,
                index=index,
                start_time=start_time,
                end_time=end_time,
                pitch=pitch,
            ),
            method_kwargs=_method_kwargs,
        )


def _register_import_browser_command(
    notes_app: typer.Typer,
    *,
    run_client_command_spec: RunClientCommandSpec,
) -> None:
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
        def _method_kwargs() -> dict[str, object]:
            target_uri, target_path = resolve_uri_or_path_target(
                target=target,
                hint="Use a browser path or URI for a .alc MIDI clip item.",
            )
            return {
                "track": require_track_index(track),
                "index": require_arrangement_clip_index(index),
                "target_uri": target_uri,
                "target_path": target_path,
                "mode": _validate_import_mode(mode),
                "import_length": import_length,
                "import_groove": import_groove,
            }

        run_client_command_spec(
            ctx,
            spec=NOTES_IMPORT_BROWSER_SPEC,
            args={
                "track": track,
                "index": index,
                "target": target,
                "mode": mode,
                "import_length": import_length,
                "import_groove": import_groove,
            },
            method_kwargs=_method_kwargs,
        )


def register_commands(
    notes_app: typer.Typer,
    *,
    run_client_command_spec: RunClientCommandSpec,
) -> None:
    _register_add_command(notes_app, run_client_command_spec=run_client_command_spec)
    _register_get_command(notes_app, run_client_command_spec=run_client_command_spec)
    _register_clear_command(notes_app, run_client_command_spec=run_client_command_spec)
    _register_replace_command(notes_app, run_client_command_spec=run_client_command_spec)
    _register_import_browser_command(notes_app, run_client_command_spec=run_client_command_spec)
