from __future__ import annotations

from pathlib import Path
from typing import Any

from .manifest import load_manifest, resolve_manifest_path, save_manifest


def setup_sound(
    project: str | Path,
    *,
    kit: str | None,
    bass: str | None,
    lead: str | None,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    plan = {
        "kind": "setup_sound",
        "kit": kit,
        "bass": bass,
        "lead": lead,
        "requires_browser_search": True,
        "steps": [
            {"action": "browser search", "query": value}
            for value in (kit, bass, lead)
            if value is not None
        ],
    }
    manifest.setdefault("generated_assets", []).append(plan)
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), **plan}


def mix_macro(project: str | Path, *, preset: str) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    plan = {
        "kind": "mix_macro",
        "preset": preset,
        "steps": [
            {"action": "create_bus", "name": "Vocal Bus"},
            {"action": "create_bus", "name": "Drum Bus"},
            {"action": "create_bus", "name": "Music Bus"},
            {"action": "return_track", "name": "Reverb"},
            {"action": "return_track", "name": "Delay"},
        ],
        "automation": "manual_or_device_snapshot",
    }
    manifest.setdefault("generated_assets", []).append(plan)
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), **plan}


def setup_mix(project: str | Path) -> dict[str, Any]:
    return mix_macro(project, preset="anime-club-basic")


def setup_returns(project: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    return {
        "project": str(manifest_path),
        "kind": "setup_returns",
        "steps": [
            {"action": "return_track", "name": "Reverb"},
            {"action": "return_track", "name": "Delay"},
        ],
    }


def setup_sidechain(project: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    return {
        "project": str(manifest_path),
        "kind": "setup_sidechain",
        "steps": [{"action": "manual_routing", "source": "Kick", "target": "Bass"}],
        "automation": "manual_or_device_snapshot",
    }


def device_chain_apply(project: str | Path, *, chain: str) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    plan = {
        "kind": "device_chain",
        "chain": chain,
        "requires_browser_search": True,
        "steps": [{"action": "browser search", "query": chain}],
    }
    manifest.setdefault("generated_assets", []).append(plan)
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), **plan}
