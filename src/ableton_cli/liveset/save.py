"""Write an edited Live Set to a new file.

Every write command goes through ``save_live_set``: the output must be a new
file next to an existing directory, the in-memory document must pass the
integrity check, and the file appears atomically (temporary file, then rename),
so the source set is never modified and a failure leaves no partial output.
"""

from __future__ import annotations

import gzip
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ..errors import AppError, ErrorCode, ExitCode
from .document import LiveSetDocument
from .integrity import check_integrity, integrity_failed

_XML_DECLARATION = b'<?xml version="1.0" encoding="UTF-8"?>\n'


def _invalid_output(out: Path, message: str, hint: str) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
        details={"out": str(out)},
    )


def require_new_output(source: Path, out: Path) -> None:
    if out.resolve() == source.resolve():
        raise _invalid_output(
            out, "--out must differ from --path", "Write the edited set to a new file."
        )
    if out.exists():
        raise _invalid_output(
            out, f"Output already exists: {out}", "Choose an --out path that does not exist yet."
        )
    if not out.parent.is_dir():
        raise _invalid_output(
            out,
            f"Output directory does not exist: {out.parent}",
            "Create the directory first, normally the set's project folder.",
        )


def _require_integrity(document: LiveSetDocument) -> None:
    findings = [finding for finding in check_integrity(document) if finding.severity == "error"]
    if findings:
        raise integrity_failed(
            str(document.path), len(findings), [finding.to_payload() for finding in findings]
        )


def save_live_set(document: LiveSetDocument, out: Path) -> None:
    require_new_output(document.path, out)
    _require_integrity(document)
    payload = _XML_DECLARATION + ET.tostring(document.root, encoding="unicode").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(dir=out.parent, prefix=f".{out.name}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb") as handle:
            handle.write(payload)
        os.replace(temporary, out)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
