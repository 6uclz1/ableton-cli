from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._validation import (
    invalid_argument,
    require_non_empty_string,
    require_non_negative,
    resolve_uri_or_path_target,
)

browser_app = typer.Typer(help="Ableton browser commands", no_args_is_help=True)


BrowserCommandSpec = CommandSpec


BROWSER_TREE_SPEC = BrowserCommandSpec(
    command_name="browser tree",
    client_method="get_browser_tree",
)
BROWSER_ITEMS_AT_PATH_SPEC = BrowserCommandSpec(
    command_name="browser items-at-path",
    client_method="get_browser_items_at_path",
)
BROWSER_ITEM_SPEC = BrowserCommandSpec(
    command_name="browser item",
    client_method="get_browser_item",
)
BROWSER_CATEGORIES_SPEC = BrowserCommandSpec(
    command_name="browser categories",
    client_method="get_browser_categories",
)
BROWSER_ITEMS_SPEC = BrowserCommandSpec(
    command_name="browser items",
    client_method="get_browser_items",
)
BROWSER_SEARCH_SPEC = BrowserCommandSpec(
    command_name="browser search",
    client_method="search_browser_items",
)
BROWSER_LOAD_SPEC = BrowserCommandSpec(
    command_name="browser load",
    client_method="load_instrument_or_effect",
)
BROWSER_LOAD_DRUM_KIT_SPEC = BrowserCommandSpec(
    command_name="browser load-drum-kit",
    client_method="load_drum_kit",
)


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: BrowserCommandSpec,
    args: dict[str, object],
    method_kwargs: dict[str, object] | Callable[[], dict[str, object]] | None = None,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
        method_kwargs=method_kwargs,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


def _validate_item_type(item_type: str) -> str:
    if item_type not in {"all", "folder", "device", "loadable"}:
        raise invalid_argument(
            message=f"item_type must be one of all/folder/device/loadable, got {item_type}",
            hint="Use one of: all, folder, device, loadable.",
        )
    return item_type


def _validate_paging(*, limit: int, offset: int) -> tuple[int, int]:
    if limit <= 0:
        raise invalid_argument(
            message=f"limit must be > 0, got {limit}",
            hint="Use a positive limit value.",
        )
    if offset < 0:
        raise invalid_argument(
            message=f"offset must be >= 0, got {offset}",
            hint="Use a non-negative offset value.",
        )
    return limit, offset


@browser_app.command("tree")
def browser_tree(
    ctx: typer.Context,
    category_type: Annotated[
        str,
        typer.Argument(help="Category type, e.g. all/instruments/sounds/drums/audio_effects."),
    ] = "all",
) -> None:
    run_client_command_spec(
        ctx,
        spec=BROWSER_TREE_SPEC,
        args={"category_type": category_type},
        method_kwargs={"category_type": category_type},
    )


@browser_app.command("items-at-path")
def browser_items_at_path(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Browser path, e.g. drums/Kits")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_path = require_non_empty_string("path", path, hint="Pass a non-empty browser path.")
        return {"path": valid_path}

    run_client_command_spec(
        ctx,
        spec=BROWSER_ITEMS_AT_PATH_SPEC,
        args={"path": path},
        method_kwargs=_method_kwargs,
    )


@browser_app.command("item")
def browser_item(
    ctx: typer.Context,
    target: Annotated[str, typer.Argument(help="Browser target (URI or path)")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_uri, valid_path = resolve_uri_or_path_target(target=target)
        return {"uri": valid_uri, "path": valid_path}

    run_client_command_spec(
        ctx,
        spec=BROWSER_ITEM_SPEC,
        args={"target": target},
        method_kwargs=_method_kwargs,
    )


@browser_app.command("categories")
def browser_categories(
    ctx: typer.Context,
    category_type: Annotated[str, typer.Argument(help="Category filter")] = "all",
) -> None:
    run_client_command_spec(
        ctx,
        spec=BROWSER_CATEGORIES_SPEC,
        args={"category_type": category_type},
        method_kwargs={"category_type": category_type},
    )


@browser_app.command("items")
def browser_items(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Browser path")],
    item_type: Annotated[
        str,
        typer.Option("--item-type", help="Filter: all|folder|device|loadable"),
    ] = "all",
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of items")] = 100,
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_path = require_non_empty_string("path", path, hint="Pass a non-empty browser path.")
        valid_item_type = _validate_item_type(item_type)
        valid_limit, valid_offset = _validate_paging(limit=limit, offset=offset)
        return {
            "path": valid_path,
            "item_type": valid_item_type,
            "limit": valid_limit,
            "offset": valid_offset,
        }

    run_client_command_spec(
        ctx,
        spec=BROWSER_ITEMS_SPEC,
        args={"path": path, "item_type": item_type, "limit": limit, "offset": offset},
        method_kwargs=_method_kwargs,
    )


@browser_app.command("search")
def browser_search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query")],
    path: Annotated[
        str | None,
        typer.Option("--path", help="Optional browser subtree path"),
    ] = None,
    item_type: Annotated[
        str,
        typer.Option("--item-type", help="Filter: all|folder|device|loadable"),
    ] = "loadable",
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of results")] = 50,
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
    exact: Annotated[bool, typer.Option("--exact", help="Use exact matching")] = False,
    case_sensitive: Annotated[
        bool,
        typer.Option("--case-sensitive", help="Use case-sensitive matching"),
    ] = False,
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_query = require_non_empty_string("query", query, hint="Pass a non-empty query.")
        valid_path = (
            require_non_empty_string("path", path, hint="Pass a non-empty browser path.")
            if path is not None
            else None
        )
        valid_item_type = _validate_item_type(item_type)
        valid_limit, valid_offset = _validate_paging(limit=limit, offset=offset)
        return {
            "query": valid_query,
            "path": valid_path,
            "item_type": valid_item_type,
            "limit": valid_limit,
            "offset": valid_offset,
            "exact": exact,
            "case_sensitive": case_sensitive,
        }

    run_client_command_spec(
        ctx,
        spec=BROWSER_SEARCH_SPEC,
        args={
            "query": query,
            "path": path,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "exact": exact,
            "case_sensitive": case_sensitive,
        },
        method_kwargs=_method_kwargs,
    )


@browser_app.command("load")
def browser_load(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    target: Annotated[str, typer.Argument(help="Browser target (URI or path)")],
    target_track_mode: Annotated[
        str,
        typer.Option(
            "--target-track-mode",
            help="Track target mode: auto|existing|new",
        ),
    ] = "auto",
    clip_slot: Annotated[
        int | None,
        typer.Option("--clip-slot", help="Clip slot (scene index, 0-based)"),
    ] = None,
    notes_mode: Annotated[
        str | None,
        typer.Option(
            "--notes-mode",
            help="Import .alc notes into the target clip using replace|append",
        ),
    ] = None,
    preserve_track_name: Annotated[
        bool,
        typer.Option("--preserve-track-name", help="Restore original track name after loading"),
    ] = False,
    import_length: Annotated[
        bool,
        typer.Option(
            "--import-length/--no-import-length",
            help="When using --notes-mode, copy source clip length into the destination clip",
        ),
    ] = False,
    import_groove: Annotated[
        bool,
        typer.Option(
            "--import-groove/--no-import-groove",
            help="When using --notes-mode, copy source clip groove settings",
        ),
    ] = False,
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_mode = require_non_empty_string(
            "target_track_mode",
            target_track_mode,
            hint="Use one of: auto, existing, new.",
        ).lower()
        if valid_mode not in {"auto", "existing", "new"}:
            raise invalid_argument(
                message=(
                    f"target_track_mode must be one of auto/existing/new, got {target_track_mode}"
                ),
                hint="Use --target-track-mode auto, existing, or new.",
            )
        valid_clip_slot = (
            require_non_negative(
                "clip_slot",
                clip_slot,
                hint="Use a non-negative clip slot index.",
            )
            if clip_slot is not None
            else None
        )
        valid_notes_mode = (
            require_non_empty_string(
                "notes_mode",
                notes_mode,
                hint="Use --notes-mode replace or append.",
            ).lower()
            if notes_mode is not None
            else None
        )
        if valid_notes_mode is not None and valid_notes_mode not in {"replace", "append"}:
            raise invalid_argument(
                message=f"notes_mode must be one of replace/append, got {notes_mode}",
                hint="Use --notes-mode replace or append.",
            )
        if valid_notes_mode is None and (import_length or import_groove):
            raise invalid_argument(
                message="--import-length/--import-groove require --notes-mode",
                hint="Use --notes-mode replace or append when importing clip length/groove.",
            )
        valid_uri, valid_path = resolve_uri_or_path_target(target=target)
        return {
            "track": valid_track,
            "uri": valid_uri,
            "path": valid_path,
            "target_track_mode": valid_mode,
            "clip_slot": valid_clip_slot,
            "notes_mode": valid_notes_mode,
            "preserve_track_name": preserve_track_name,
            "import_length": import_length,
            "import_groove": import_groove,
        }

    run_client_command_spec(
        ctx,
        spec=BROWSER_LOAD_SPEC,
        args={
            "track": track,
            "target": target,
            "target_track_mode": target_track_mode,
            "clip_slot": clip_slot,
            "notes_mode": notes_mode,
            "preserve_track_name": preserve_track_name,
            "import_length": import_length,
            "import_groove": import_groove,
        },
        method_kwargs=_method_kwargs,
    )


@browser_app.command("load-drum-kit")
def browser_load_drum_kit(
    ctx: typer.Context,
    track: Annotated[int, typer.Argument(help="Track index (0-based)")],
    rack_uri: Annotated[str, typer.Argument(help="URI for drum rack item")],
    kit_uri: Annotated[str | None, typer.Option("--kit-uri", help="URI for drum kit item")] = None,
    kit_path: Annotated[
        str | None,
        typer.Option("--kit-path", help="Browser path for drum kit item"),
    ] = None,
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_track = require_non_negative(
            "track",
            track,
            hint="Use a valid track index from 'ableton-cli tracks list'.",
        )
        valid_rack_uri = require_non_empty_string(
            "rack_uri",
            rack_uri,
            hint="Pass a non-empty rack URI.",
        )
        if kit_uri is None and kit_path is None:
            raise invalid_argument(
                message="Exactly one of --kit-uri or --kit-path must be provided",
                hint="Provide --kit-uri or --kit-path.",
            )
        if kit_uri is not None and kit_path is not None:
            raise invalid_argument(
                message="--kit-uri and --kit-path are mutually exclusive",
                hint="Provide only one of --kit-uri or --kit-path.",
            )
        valid_kit_uri = (
            require_non_empty_string("kit_uri", kit_uri, hint="Pass a non-empty kit URI.")
            if kit_uri is not None
            else None
        )
        valid_kit_path = (
            require_non_empty_string("kit_path", kit_path, hint="Pass a non-empty drum kit path.")
            if kit_path is not None
            else None
        )
        return {
            "track": valid_track,
            "rack_uri": valid_rack_uri,
            "kit_uri": valid_kit_uri,
            "kit_path": valid_kit_path,
        }

    run_client_command_spec(
        ctx,
        spec=BROWSER_LOAD_DRUM_KIT_SPEC,
        args={"track": track, "rack_uri": rack_uri, "kit_uri": kit_uri, "kit_path": kit_path},
        method_kwargs=_method_kwargs,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(browser_app, name="browser")
