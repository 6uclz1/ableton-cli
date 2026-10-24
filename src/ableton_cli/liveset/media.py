"""Sample-reference checks for lint.

Only ``SampleRef/FileRef`` elements are media; other ``FileRef`` elements record
where a preset or device came from and do not affect playback.

``RelativePathType`` 3 marks a project-relative sample. Live resolves it against
the project folder (the nearest ancestor holding ``Ableton Project Info``) and
does not use the stored absolute ``Path``, so neither does this check. Every
other type resolves against a location this tool must not assume (Core Library,
User Library, built-in content, ...), and a stored ``Path`` is often from another
machine. Those references are counted as unchecked rather than guessed at.
Findings carry relative paths and file names only, never absolute paths.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

from .document import LiveSetDocument
from .findings import Finding, listed_details

PROJECT_INFO_DIR = "Ableton Project Info"
PROJECT_RELATIVE = "3"

_MESSAGES = {
    "project_root_not_found": f"No '{PROJECT_INFO_DIR}' folder above the set; "
    "project-relative samples cannot be resolved.",
    "media_missing": "Project samples were not found in the project folder.",
}


@dataclass(frozen=True, slots=True)
class MediaScan:
    findings: list[Finding]
    summary: dict[str, Any]


def find_project_root(set_path: Path) -> Path | None:
    start = set_path.parent.resolve()
    for directory in (start, *start.parents):
        if (directory / PROJECT_INFO_DIR).is_dir():
            return directory
    return None


def _value(file_ref: ET.Element, tag: str) -> str:
    element = file_ref.find(tag)
    return "" if element is None else element.get("Value", "")


def _sample_refs(document: LiveSetDocument) -> set[tuple[str, str, str]]:
    """Unique ``(relative_path_type, relative_path, path)`` sample references."""
    refs = set()
    for file_ref in document.root.iterfind(".//SampleRef/FileRef"):
        ref = tuple(_value(file_ref, tag) for tag in ("RelativePathType", "RelativePath", "Path"))
        if ref[1] or ref[2]:
            refs.add(ref)
    return refs  # type: ignore[return-value]


def _project_problem(relative_path: str, project_root: Path | None) -> str | None:
    if project_root is None:
        return "project_root_not_found"
    if not (project_root / relative_path).is_file():
        return "media_missing"
    return None


def _findings(problems: list[tuple[str | None, str]]) -> list[Finding]:
    by_code: dict[str, list[dict[str, str]]] = {}
    for code, relative_path in problems:
        if code is not None:
            entry = {"relative_path": relative_path, "file_name": PurePath(relative_path).name}
            by_code.setdefault(code, []).append(entry)
    return [
        Finding(
            severity="warning",
            code=code,
            message=message,
            details=listed_details("files", by_code[code]),
        )
        for code, message in _MESSAGES.items()
        if code in by_code
    ]


def scan_media(document: LiveSetDocument) -> MediaScan:
    project_root = find_project_root(document.path)
    refs = _sample_refs(document)
    project = sorted({rel for kind, rel, _ in refs if kind == PROJECT_RELATIVE and rel})
    unchecked = Counter(kind for kind, rel, _ in refs if not (kind == PROJECT_RELATIVE and rel))
    findings = _findings([(_project_problem(rel, project_root), rel) for rel in project])
    summary = {
        "checked_count": len(project),
        "unchecked_count": sum(unchecked.values()),
        "unchecked_by_relative_path_type": dict(sorted(unchecked.items())),
    }
    return MediaScan(findings=findings, summary=summary)
