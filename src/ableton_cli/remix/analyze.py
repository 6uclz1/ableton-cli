from __future__ import annotations

from pathlib import Path
from typing import Any

from .manifest import load_manifest, remix_error, resolve_manifest_path, save_manifest


def _parse_section(raw: str) -> dict[str, Any]:
    name_part, _, range_part = raw.partition(":")
    name = name_part.strip()
    if not name or "-" not in range_part:
        raise remix_error(
            message=f"invalid section spec: {raw!r}",
            hint="Use section specs like intro:1-8,verse:9-24.",
        )
    start_raw, end_raw = range_part.split("-", 1)
    try:
        start_bar = int(start_raw.strip())
        end_bar = int(end_raw.strip())
    except ValueError as exc:
        raise remix_error(
            message=f"section bars must be integers: {raw!r}",
            hint="Use section specs like chorus:33-48.",
        ) from exc
    if start_bar < 1 or end_bar < start_bar:
        raise remix_error(
            message=f"section range must be 1-based and increasing: {raw!r}",
            hint="Use start_bar >= 1 and end_bar >= start_bar.",
        )
    return {"name": name, "start_bar": start_bar, "end_bar": end_bar}


def parse_sections(sections: str) -> list[dict[str, Any]]:
    parsed = [_parse_section(item) for item in sections.split(",") if item.strip()]
    if not parsed:
        raise remix_error(
            message="sections must not be empty",
            hint="Use section specs like intro:1-8,chorus:33-48.",
        )
    return parsed


def import_sections(project: str | Path, sections: str) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    parsed = parse_sections(sections)
    manifest["sections"] = parsed
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "sections": parsed, "section_count": len(parsed)}


def import_beatgrid(project: str | Path, downbeats: str) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    try:
        parsed = [float(item.strip()) for item in downbeats.split(",") if item.strip()]
    except ValueError as exc:
        raise remix_error(
            message="downbeats must be comma-separated numbers",
            hint="Use --downbeats '0.0,1.395,2.790'.",
        ) from exc
    manifest["downbeats"] = parsed
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "downbeats": parsed, "downbeat_count": len(parsed)}


def analyze_audio(
    project: str | Path,
    *,
    detect: str,
    manual_bpm: float | None,
    manual_key: str | None,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    requested = [item.strip() for item in detect.split(",") if item.strip()]
    confidence: dict[str, float] = {}
    if manual_bpm is not None:
        manifest["detected_bpm"] = float(manual_bpm)
        confidence["bpm"] = 1.0
    if manual_key is not None:
        manifest["detected_key"] = manual_key.strip()
        confidence["key"] = 1.0
    for item in requested:
        confidence.setdefault(item, 0.0)
    manifest["analysis_confidence"] = confidence
    save_manifest(manifest_path, manifest)
    return {
        "project": str(manifest_path),
        "detect": requested,
        "bpm": manifest.get("detected_bpm"),
        "key": manifest.get("detected_key"),
        "sections": manifest.get("sections", []),
        "confidence": confidence,
        "provider": "manual",
    }
