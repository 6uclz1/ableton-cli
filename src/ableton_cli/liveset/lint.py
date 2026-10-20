from __future__ import annotations

from typing import Any

from ..errors import AppError, ErrorCode, ExitCode
from .document import LiveSetDocument
from .integrity import check_integrity
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
    raise AppError(
        error_code=ErrorCode.SET_INTEGRITY_FAILED,
        message=f"Live Set has {report['error_count']} integrity error(s)",
        hint="Open and re-save the set in Live, or restore it from a backup.",
        exit_code=ExitCode.EXECUTION_FAILED,
        details={"path": report["path"], "findings": report["findings"]},
    )
