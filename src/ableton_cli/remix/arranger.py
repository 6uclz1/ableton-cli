from __future__ import annotations

from pathlib import Path
from typing import Any

from .assets import find_asset
from .manifest import load_manifest, remix_error, resolve_manifest_path, save_manifest
from .templates import template_sections

BEATS_PER_BAR = 4.0


def _section_length_beats(section: dict[str, Any]) -> float:
    return (int(section["end_bar"]) - int(section["start_bar"]) + 1) * BEATS_PER_BAR


def _section_start_beat(section: dict[str, Any]) -> float:
    return (int(section["start_bar"]) - 1) * BEATS_PER_BAR


def generate_plan(
    project: str | Path,
    *,
    style: str,
    bars: str | None = None,
    length: str = "full",
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    source_sections = list(manifest.get("sections", []))
    planned_sections = (
        source_sections if source_sections and bars is None else template_sections(style, bars)
    )
    asset_role = "instrumental"
    try:
        primary_asset = find_asset(manifest, asset_role)
    except Exception:
        asset_role = "vocal"
        primary_asset = find_asset(manifest, asset_role)
    track_refs = dict(manifest.get("ableton_track_refs", {}))
    track = int(track_refs.get(asset_role, track_refs.get("default_audio_track", 2)))
    steps = [
        {
            "name": "arrangement_clip_create",
            "args": {
                "track": track,
                "start_time": _section_start_beat(section),
                "length": _section_length_beats(section),
                "audio_path": primary_asset["path"],
            },
            "label": section["name"],
        }
        for section in planned_sections
    ]
    plan = {
        "style": style,
        "length": length,
        "sections": planned_sections,
        "asset_role": asset_role,
        "steps": steps,
        "step_count": len(steps),
    }
    manifest["arrangement_plan"] = plan
    save_manifest(manifest_path, manifest)
    return plan


def apply_plan(
    manifest: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    plan = manifest.get("arrangement_plan")
    if not isinstance(plan, dict):
        raise remix_error(
            message="arrangement_plan is missing",
            hint="Run 'ableton-cli remix plan' before apply.",
        )
    steps = list(plan.get("steps", []))
    return {
        "dry_run": dry_run,
        "style": plan.get("style"),
        "step_count": len(steps),
        "steps": steps,
    }


def export_plan(project: str | Path, *, target: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    target_path = Path(target).expanduser()
    if not target_path.is_absolute():
        raise remix_error(
            message=f"target must be absolute, got {str(target_path)!r}",
            hint="Pass an absolute path to --target.",
        )
    return {
        "project": str(manifest_path),
        "target": str(target_path.resolve()),
        "can_export_via_live_api": False,
        "manual_steps": [
            "Open Ableton Live Export Audio/Video.",
            "Set the render range to the planned arrangement.",
            "Render to the target path.",
        ],
        "arrangement_step_count": len((manifest.get("arrangement_plan") or {}).get("steps", [])),
    }
