from __future__ import annotations

from pathlib import Path
from typing import Any

from .manifest import load_manifest, resolve_manifest_path


def run_qa(project: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    source_path = Path(str(manifest.get("source_audio_path", "")))
    if not source_path.exists():
        errors.append({"code": "missing_source_audio", "message": str(source_path)})

    for asset in manifest.get("assets", []):
        asset_path = Path(str(asset.get("path", "")))
        if not asset_path.exists():
            errors.append({"code": "missing_asset", "message": str(asset_path)})

    if not manifest.get("sections"):
        warnings.append(
            {"code": "missing_sections", "message": "No section map has been imported."}
        )
    if manifest.get("arrangement_plan") is None:
        warnings.append(
            {"code": "missing_arrangement_plan", "message": "No remix plan has been generated."}
        )
    if manifest.get("rights_status") in {None, "", "unspecified"}:
        warnings.append(
            {
                "code": "rights_status_unspecified",
                "message": "Set rights_status for cleared, private, or original material.",
            }
        )

    return {
        "project": str(manifest_path),
        "ok": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
