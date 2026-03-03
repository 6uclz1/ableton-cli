from __future__ import annotations

from typing import Any


def _diff_node(before: Any, after: Any) -> tuple[Any | None, Any | None, Any | None, bool]:
    if isinstance(before, dict) and isinstance(after, dict):
        added: dict[str, Any] = {}
        removed: dict[str, Any] = {}
        changed: dict[str, Any] = {}

        for key in sorted(set(before) | set(after)):
            if key not in before:
                added[key] = after[key]
                continue
            if key not in after:
                removed[key] = before[key]
                continue

            child_added, child_removed, child_changed, child_has_diff = _diff_node(
                before[key],
                after[key],
            )
            if not child_has_diff:
                continue
            if child_added is not None:
                added[key] = child_added
            if child_removed is not None:
                removed[key] = child_removed
            if child_changed is not None:
                changed[key] = child_changed

        has_diff = bool(added or removed or changed)
        return (
            added if added else None,
            removed if removed else None,
            changed if changed else None,
            has_diff,
        )

    if before != after:
        return None, None, {"from": before, "to": after}, True

    return None, None, None, False


def compute_session_diff(
    from_snapshot: dict[str, Any],
    to_snapshot: dict[str, Any],
) -> dict[str, Any]:
    added, removed, changed, _has_diff = _diff_node(from_snapshot, to_snapshot)
    return {
        "added": {} if added is None else added,
        "removed": {} if removed is None else removed,
        "changed": {} if changed is None else changed,
    }
