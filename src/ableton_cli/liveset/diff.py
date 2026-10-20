from __future__ import annotations

from typing import Any

from ..session_diff import compute_session_diff
from .document import LiveSetDocument
from .inspect import inspect_live_set


def _by_key(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item[key]): item for item in items}


def _diffable(document: LiveSetDocument) -> dict[str, Any]:
    """Key lists by stable identity so a reorder is a field change, not remove+add."""
    summary = inspect_live_set(document)
    return {
        "version": summary["version"],
        "song": summary["song"],
        "tracks": _by_key(summary["tracks"], "id"),
        "return_tracks": _by_key(summary["return_tracks"], "id"),
        "scenes": _by_key(summary["scenes"], "index"),
        "locators": _by_key(summary["locators"], "id"),
        "plugins": {f"{item['format']}:{item['name']}": item for item in summary["plugins"]},
    }


def diff_live_sets(before: LiveSetDocument, after: LiveSetDocument) -> dict[str, Any]:
    return {
        "from_path": str(before.path),
        "to_path": str(after.path),
        **compute_session_diff(_diffable(before), _diffable(after)),
    }
