"""Strict element access over a loaded Live Set.

A missing element the reader depends on means the set does not have the
structure this version of the tool understands, so it fails with
``SET_SCHEMA_UNSUPPORTED`` instead of returning a default.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ..errors import AppError, ErrorCode, ExitCode
from .document import LiveSetDocument


def schema_unsupported(document: LiveSetDocument, element: str, message: str) -> AppError:
    return AppError(
        error_code=ErrorCode.SET_SCHEMA_UNSUPPORTED,
        message=f"{document.path.name}: {message}",
        hint="Re-save the set in a supported Live version, or report the set structure.",
        exit_code=ExitCode.INVALID_ARGUMENT,
        details={"path": str(document.path), "element": element},
    )


def require(document: LiveSetDocument, parent: ET.Element, path: str, *, where: str) -> ET.Element:
    element = parent.find(path)
    if element is None:
        location = f"{where}/{path}" if where else path
        raise schema_unsupported(document, location, f"missing element {location}")
    return element


def require_value(document: LiveSetDocument, parent: ET.Element, path: str, *, where: str) -> str:
    element = require(document, parent, path, where=where)
    value = element.get("Value")
    if value is None:
        location = f"{where}/{path}" if where else path
        raise schema_unsupported(document, location, f"element {location} has no Value")
    return value


def track_name(document: LiveSetDocument, track: ET.Element) -> str:
    """The name Live displays: ``UserName`` when set, else the generated ``EffectiveName``."""
    return require_value(document, track, "Name/UserName", where=track.tag) or require_value(
        document, track, "Name/EffectiveName", where=track.tag
    )


def parse_number(document: LiveSetDocument, raw: str, *, element: str, kind: type) -> Any:
    try:
        return kind(raw)
    except ValueError as exc:
        raise schema_unsupported(document, element, f"{element} is not a number: {raw!r}") from exc


def envelope_events_by_target(root: ET.Element) -> dict[str, list[ET.Element]]:
    """Map each automated ``AutomationTarget`` ID to its arrangement envelope events."""
    envelopes: dict[str, list[ET.Element]] = {}
    for envelope in root.iter("AutomationEnvelope"):
        target = envelope.find("EnvelopeTarget/PointeeId")
        events = envelope.find("Automation/Events")
        if target is not None and events is not None:
            envelopes[target.get("Value", "")] = list(events)
    return envelopes
