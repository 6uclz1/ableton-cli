from __future__ import annotations

from typing import Any

from .document import LiveSetDocument
from .integrity import check_integrity, integrity_failed
from .media import scan_media


def lint_live_set(document: LiveSetDocument) -> dict[str, Any]:
    media = scan_media(document)
    findings = [*check_integrity(document), *media.findings]
    return {
        "path": str(document.path),
        "version": document.version.to_payload(),
        "error_count": sum(finding.severity == "error" for finding in findings),
        "warning_count": sum(finding.severity == "warning" for finding in findings),
        "findings": [finding.to_payload() for finding in findings],
        "media": media.summary,
    }


def require_no_errors(report: dict[str, Any]) -> dict[str, Any]:
    if report["error_count"] == 0:
        return report
    raise integrity_failed(report["path"], report["error_count"], report["findings"])
