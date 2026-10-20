from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import AppError, ErrorCode, ExitCode
from .schema import SetVersion, require_supported_version


@dataclass(frozen=True, slots=True)
class LiveSetDocument:
    path: Path
    root: ET.Element
    version: SetVersion

    @property
    def live_set(self) -> ET.Element:
        return self.root.find("LiveSet")  # type: ignore[return-value]


def set_file_invalid(path: Path, message: str, **details: Any) -> AppError:
    return AppError(
        error_code=ErrorCode.SET_FILE_INVALID,
        message=f"{path.name}: {message}",
        hint="Pass a Live Set (.als) saved by Ableton Live.",
        exit_code=ExitCode.INVALID_ARGUMENT,
        details={"path": str(path), **details},
    )


def _read_xml_bytes(path: Path) -> bytes:
    if not path.is_file():
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=f"Live Set file not found: {path}",
            hint="Pass the path of an existing .als file.",
            exit_code=ExitCode.INVALID_ARGUMENT,
            details={"path": str(path)},
        )
    try:
        with gzip.open(path, "rb") as handle:
            return handle.read()
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise set_file_invalid(path, "not a gzip-compressed Live Set", cause=str(exc)) from exc


def load_live_set(path: Path) -> LiveSetDocument:
    try:
        root = ET.fromstring(_read_xml_bytes(path))
    except ET.ParseError as exc:
        raise set_file_invalid(path, "malformed XML", cause=str(exc)) from exc
    if root.tag != "Ableton" or root.find("LiveSet") is None:
        raise set_file_invalid(path, "root element is not <Ableton> with a <LiveSet>")
    return LiveSetDocument(path=path, root=root, version=require_supported_version(path, root))
