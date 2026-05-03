from __future__ import annotations

from pathlib import Path
from typing import Any

from .manifest import load_manifest, remix_error, resolve_manifest_path


def list_stems(project: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    stems = list(manifest.get("stems", []))
    return {"project": str(manifest_path), "stem_count": len(stems), "stems": stems}


def split_stems(project: str | Path, *, provider: str, out: str | Path) -> dict[str, Any]:
    if provider not in {"manual", "external"}:
        raise remix_error(
            message=f"unknown stem provider: {provider}",
            hint="Use provider manual or external.",
        )
    out_path = Path(out).expanduser()
    if not out_path.is_absolute():
        raise remix_error(
            message=f"out must be absolute, got {str(out_path)!r}",
            hint="Pass an absolute output directory.",
        )
    listed = list_stems(project)
    return {
        **listed,
        "provider": provider,
        "out": str(out_path.resolve()),
        "executed": False,
        "reason": "Stem provider interface is registered; separation execution is external.",
    }
