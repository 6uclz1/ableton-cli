from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _as_bool,
    _invalid_argument,
    _non_empty_string,
    _non_negative_int,
    _parse_exclusive_string_args,
    _positive_int,
    _track_index,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]
_ALLOWED_ITEM_TYPES = frozenset({"all", "folder", "device", "loadable"})
_ALLOWED_TARGET_TRACK_MODES = frozenset({"auto", "existing", "new"})
_ALLOWED_NOTES_MODES = frozenset({"replace", "append"})


def _parse_target_track_mode(args: dict[str, Any]) -> str:
    parsed = _non_empty_string("target_track_mode", args.get("target_track_mode", "auto")).lower()
    if parsed not in _ALLOWED_TARGET_TRACK_MODES:
        raise _invalid_argument(
            message=f"target_track_mode must be one of auto/existing/new, got {parsed}",
            hint="Use a supported target_track_mode.",
        )
    return parsed


def _parse_optional_clip_slot(args: dict[str, Any]) -> int | None:
    raw = args.get("clip_slot")
    if raw is None:
        return None
    return _non_negative_int("clip_slot", raw)


def _parse_optional_notes_mode(args: dict[str, Any]) -> str | None:
    raw = args.get("notes_mode")
    if raw is None:
        return None
    parsed = _non_empty_string("notes_mode", raw).lower()
    if parsed not in _ALLOWED_NOTES_MODES:
        raise _invalid_argument(
            message=f"notes_mode must be one of replace/append, got {parsed}",
            hint="Use notes_mode replace or append.",
        )
    return parsed


def _handle_load_instrument_or_effect(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    uri, path = _parse_exclusive_string_args(
        args,
        first_key="uri",
        second_key="path",
        required_hint="Provide --uri or --path.",
    )
    target_track_mode = _parse_target_track_mode(args)
    clip_slot = _parse_optional_clip_slot(args)
    notes_mode = _parse_optional_notes_mode(args)
    preserve_track_name = _as_bool("preserve_track_name", args.get("preserve_track_name", False))
    return backend.load_instrument_or_effect(
        track,
        uri,
        path,
        target_track_mode,
        clip_slot,
        preserve_track_name,
        notes_mode,
    )


def _handle_get_browser_tree(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    category_type = _non_empty_string("category_type", args.get("category_type", "all"))
    return backend.get_browser_tree(category_type)


def _handle_get_browser_items_at_path(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    return backend.get_browser_items_at_path(path)


def _handle_get_browser_item(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    uri, path = _parse_exclusive_string_args(
        args,
        first_key="uri",
        second_key="path",
        required_hint="Provide --uri or --path.",
    )
    return backend.get_browser_item(uri=uri, path=path)


def _handle_get_browser_categories(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    category_type = _non_empty_string("category_type", args.get("category_type", "all"))
    return backend.get_browser_categories(category_type)


def _validate_item_type(item_type: str) -> str:
    if item_type not in _ALLOWED_ITEM_TYPES:
        raise ValueError(item_type)
    return item_type


def _parse_item_type(args: dict[str, Any], *, default: str) -> str:
    parsed = _non_empty_string("item_type", args.get("item_type", default))
    try:
        return _validate_item_type(parsed)
    except ValueError as exc:
        raise _invalid_item_type(parsed) from exc


def _invalid_item_type(item_type: str) -> Exception:
    return _invalid_argument(
        message=f"item_type must be one of all/folder/device/loadable, got {item_type}",
        hint="Use a supported item type.",
    )


def _handle_get_browser_items(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    item_type = _parse_item_type(args, default="all")
    limit = _positive_int("limit", args.get("limit", 100))
    offset = _non_negative_int("offset", args.get("offset", 0))
    return backend.get_browser_items(path, item_type, limit, offset)


def _handle_search_browser_items(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    query = _non_empty_string("query", args.get("query"))
    path_raw = args.get("path")
    path = _non_empty_string("path", path_raw) if path_raw is not None else None
    item_type = _parse_item_type(args, default="loadable")
    limit = _positive_int("limit", args.get("limit", 50))
    offset = _non_negative_int("offset", args.get("offset", 0))
    exact = _as_bool("exact", args.get("exact", False))
    case_sensitive = _as_bool("case_sensitive", args.get("case_sensitive", False))
    return backend.search_browser_items(
        query=query,
        path=path,
        item_type=item_type,
        limit=limit,
        offset=offset,
        exact=exact,
        case_sensitive=case_sensitive,
    )


def _handle_load_drum_kit(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    rack_uri = _non_empty_string("rack_uri", args.get("rack_uri"))
    kit_uri, kit_path = _parse_exclusive_string_args(
        args,
        first_key="kit_uri",
        second_key="kit_path",
        required_hint="Provide kit_uri or kit_path.",
    )
    return backend.load_drum_kit(track, rack_uri, kit_uri, kit_path)


BROWSER_HANDLERS: dict[str, Handler] = {
    "load_instrument_or_effect": _handle_load_instrument_or_effect,
    "get_browser_tree": _handle_get_browser_tree,
    "get_browser_items_at_path": _handle_get_browser_items_at_path,
    "get_browser_item": _handle_get_browser_item,
    "get_browser_categories": _handle_get_browser_categories,
    "get_browser_items": _handle_get_browser_items,
    "search_browser_items": _handle_search_browser_items,
    "load_drum_kit": _handle_load_drum_kit,
}
