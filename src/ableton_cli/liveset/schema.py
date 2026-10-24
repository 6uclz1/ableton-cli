"""Supported Live Set versions.

The ``.als`` format is undocumented, so only versions verified against Live are
accepted. Widening this gate requires opening real sets of the new version in
Live and checking the result (see ``docs/offline-set-editing-design.md``).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from ..errors import AppError, ErrorCode, ExitCode

SUPPORTED_MAJOR_VERSION = "5"
SUPPORTED_MINOR_VERSION_PREFIXES: tuple[str, ...] = ("12.",)


@dataclass(frozen=True, slots=True)
class SetVersion:
    major: str
    minor: str
    creator: str

    def to_payload(self) -> dict[str, str]:
        return {"major": self.major, "minor": self.minor, "creator": self.creator}


def require_supported_version(path: Path, root: ET.Element) -> SetVersion:
    version = SetVersion(
        major=root.get("MajorVersion", ""),
        minor=root.get("MinorVersion", ""),
        creator=root.get("Creator", ""),
    )
    if version.major == SUPPORTED_MAJOR_VERSION and version.minor.startswith(
        SUPPORTED_MINOR_VERSION_PREFIXES
    ):
        return version
    raise AppError(
        error_code=ErrorCode.SET_SCHEMA_UNSUPPORTED,
        message=f"{path.name}: unsupported Live Set version {version.minor or '<missing>'}",
        hint="Only Live 12 sets are supported. Re-save the set in Live 12.",
        exit_code=ExitCode.INVALID_ARGUMENT,
        details={
            "path": str(path),
            "major_version": version.major,
            "minor_version": version.minor,
            "creator": version.creator,
            "supported_minor_prefixes": list(SUPPORTED_MINOR_VERSION_PREFIXES),
        },
    )
