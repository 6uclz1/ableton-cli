from __future__ import annotations

from pathlib import Path
from typing import Any

from .manifest import load_manifest, remix_error, resolve_manifest_path, save_manifest

STEM_ROLES = frozenset({"vocal", "instrumental", "drums", "bass", "other"})


def _asset_id(role: str, path: Path) -> str:
    safe_role = role.strip().lower().replace(" ", "_")
    return f"{safe_role}:{path.name}"


def _normalized_asset(role: str, path: str | Path) -> dict[str, Any]:
    parsed_role = role.strip().lower()
    if not parsed_role:
        raise remix_error(message="role must not be empty", hint="Pass a role such as vocal.")
    parsed_path = Path(path).expanduser()
    if not parsed_path.is_absolute():
        raise remix_error(
            message=f"asset path must be absolute, got {str(parsed_path)!r}",
            hint="Pass an absolute path to --path.",
        )
    resolved = parsed_path.resolve()
    return {
        "id": _asset_id(parsed_role, resolved),
        "role": parsed_role,
        "path": str(resolved),
    }


def add_asset(project: str | Path, *, role: str, path: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    asset = _normalized_asset(role, path)
    assets = [item for item in manifest.get("assets", []) if item.get("id") != asset["id"]]
    assets.append(asset)
    manifest["assets"] = assets
    if asset["role"] in STEM_ROLES:
        stems = [item for item in manifest.get("stems", []) if item.get("id") != asset["id"]]
        stems.append({**asset, "source": "asset_registry", "quality": None})
        manifest["stems"] = stems
    save_manifest(manifest_path, manifest)
    return asset


def remove_asset(project: str | Path, *, role: str, path: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    asset = _normalized_asset(role, path)
    before = len(manifest.get("assets", []))
    manifest["assets"] = [
        item for item in manifest.get("assets", []) if item.get("id") != asset["id"]
    ]
    manifest["stems"] = [
        item for item in manifest.get("stems", []) if item.get("id") != asset["id"]
    ]
    save_manifest(manifest_path, manifest)
    return {
        "project": str(manifest_path),
        "removed": before - len(manifest["assets"]),
        "asset": asset,
    }


def list_assets(manifest_or_project: dict[str, Any] | str | Path) -> list[dict[str, Any]]:
    manifest = (
        manifest_or_project
        if isinstance(manifest_or_project, dict)
        else load_manifest(resolve_manifest_path(manifest_or_project))
    )
    return list(manifest.get("assets", []))


def find_asset(manifest: dict[str, Any], role: str) -> dict[str, Any]:
    parsed_role = role.strip().lower()
    for asset in manifest.get("assets", []):
        if asset.get("role") == parsed_role:
            return dict(asset)
    raise remix_error(
        message=f"asset role not found: {parsed_role}",
        hint="Register it with 'audio asset add' first.",
    )
