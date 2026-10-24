from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning"]

#: Findings that list items carry at most this many, plus the full ``count``,
#: so a badly damaged set cannot produce an unbounded payload.
MAX_LISTED_ITEMS = 20


@dataclass(frozen=True, slots=True)
class Finding:
    severity: Severity
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def listed_details(key: str, items: Iterable[Any]) -> dict[str, Any]:
    listed = list(items)
    return {"count": len(listed), key: listed[:MAX_LISTED_ITEMS]}
