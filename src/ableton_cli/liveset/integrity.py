from __future__ import annotations

from collections import Counter

from .document import LiveSetDocument
from .findings import Finding, listed_details
from .ids import global_id_elements, pointee_references


def _id_sort_key(value: str) -> tuple[int, int, str]:
    return (0, int(value), "") if value.isdigit() else (1, 0, value)


def _sorted_ids(values: set[str]) -> list[str]:
    return sorted(values, key=_id_sort_key)


def _next_pointee_findings(document: LiveSetDocument, numeric_ids: list[int]) -> list[Finding]:
    element = document.live_set.find("NextPointeeId")
    raw = None if element is None else element.get("Value", "")
    if raw is None or not raw.isdigit():
        return [
            Finding(
                severity="error",
                code="next_pointee_id_missing",
                message="LiveSet/NextPointeeId is missing or not an integer.",
                details={"value": raw},
            )
        ]
    next_id, max_id = int(raw), max(numeric_ids, default=-1)
    if max_id < next_id:
        return []
    return [
        Finding(
            severity="error",
            code="next_pointee_id_too_low",
            message="NextPointeeId is not above every global ID.",
            details={"next_pointee_id": next_id, "max_id": max_id},
        )
    ]


def check_integrity(document: LiveSetDocument) -> list[Finding]:
    counts = Counter(element.get("Id", "") for element in global_id_elements(document.root))
    checks = (
        (
            "pointee_id_invalid",
            "Global IDs must be non-negative integers.",
            {value for value in counts if not value.isdigit()},
        ),
        (
            "pointee_id_duplicate",
            "Global IDs must be unique across the set.",
            {value for value, seen in counts.items() if seen > 1},
        ),
        (
            "pointee_ref_dangling",
            "PointeeId values must refer to an existing global ID.",
            set(pointee_references(document.root)) - set(counts),
        ),
    )
    findings = [
        Finding(
            severity="error",
            code=code,
            message=message,
            details=listed_details("ids", _sorted_ids(offending)),
        )
        for code, message, offending in checks
        if offending
    ]
    numeric_ids = [int(value) for value in counts if value.isdigit()]
    return findings + _next_pointee_findings(document, numeric_ids)
