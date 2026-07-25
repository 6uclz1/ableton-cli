from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

from .manifest import load_manifest, remix_error, resolve_manifest_path
from .unsupported import fail_unsupported


def list_stems(project: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    stems = list(manifest.get("stems", []))
    return {"project": str(manifest_path), "stem_count": len(stems), "stems": stems}


def split_stems(project: str | Path, *, provider: str, out: str | Path) -> NoReturn:
    """Validate the request, then fail: nothing here separates stems."""
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
    fail_unsupported(
        "audio stems split",
        project=str(resolve_manifest_path(project)),
        provider=provider,
        out=str(out_path.resolve()),
    )
