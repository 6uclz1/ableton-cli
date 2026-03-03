from __future__ import annotations

from typing import Any

_LARGE_ARRAY_THRESHOLD = 20


def _item_type(values: list[Any]) -> str:
    if not values:
        return "empty"
    type_names = {type(value).__name__ for value in values}
    if len(type_names) == 1:
        return next(iter(type_names))
    return "mixed"


def compact_payload(
    payload: dict[str, Any],
    *,
    threshold: int = _LARGE_ARRAY_THRESHOLD,
) -> dict[str, Any]:
    if payload.get("ok") is not True:
        return payload

    refs: dict[str, dict[str, Any]] = {}
    counter = 0

    def compact_value(value: Any, *, path: str) -> Any:
        nonlocal counter

        if isinstance(value, list):
            if len(value) > threshold:
                counter += 1
                ref = f"ref_{counter}"
                summary = {
                    "count": len(value),
                    "item_type": _item_type(value),
                }
                refs[ref] = {
                    "path": path,
                    **summary,
                }
                return {
                    "_compact_ref": ref,
                    "_compact_summary": summary,
                }
            return [compact_value(item, path=f"{path}.{index}") for index, item in enumerate(value)]

        if isinstance(value, dict):
            return {key: compact_value(item, path=f"{path}.{key}") for key, item in value.items()}

        return value

    compacted = dict(payload)
    compacted["result"] = compact_value(payload.get("result"), path="result")
    if refs:
        compacted["compact_refs"] = refs
    return compacted
