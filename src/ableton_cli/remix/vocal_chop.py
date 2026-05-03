from __future__ import annotations

from pathlib import Path
from typing import Any

from .assets import find_asset
from .manifest import load_manifest, remix_error, resolve_manifest_path, save_manifest


def build_vocal_chop(
    project: str | Path,
    *,
    source: str,
    section: str,
    slice_grid: str,
    target_track: str | None,
    create_trigger: bool,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    asset = find_asset(manifest, source)
    section_payload = next(
        (item for item in manifest.get("sections", []) if item.get("name") == section),
        None,
    )
    if section_payload is None:
        raise remix_error(
            message=f"section not found: {section}",
            hint="Import it with 'audio sections import' first.",
        )
    track_refs = dict(manifest.get("ableton_track_refs", {}))
    source_track = track_refs.get(source)
    target_track_index = track_refs.get(target_track or "vocal_chop")
    step_args: dict[str, Any] = {
        "source_path": asset["path"],
        "grid": slice_grid,
        "start_pad": 0,
        "create_trigger_clip": create_trigger,
    }
    if isinstance(source_track, int):
        step_args["source_track"] = source_track
    if isinstance(target_track_index, int):
        step_args["target_track"] = target_track_index
    if create_trigger:
        step_args["trigger_clip_slot"] = 0
    result = {
        "project": str(manifest_path),
        "command": "clip_cut_to_drum_rack",
        "source": source,
        "section": section_payload,
        "slice": slice_grid,
        "target_track": target_track,
        "create_trigger": create_trigger,
        "args": step_args,
    }
    manifest.setdefault("generated_assets", []).append(
        {"kind": "vocal_chop_plan", "source_role": source, "section": section, "slice": slice_grid}
    )
    save_manifest(manifest_path, manifest)
    return result
