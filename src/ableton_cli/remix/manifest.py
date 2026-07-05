from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..commands._validation import invalid_argument, require_absolute_path, require_non_empty_string
from .templates import infer_section_profile


def load_manifest(project: Path) -> dict[str, Any]:
    try:
        return json.loads(project.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise invalid_argument(
            message=f"project manifest does not exist: {project}",
            hint="Run 'uv run ableton-cli remix init' first.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise invalid_argument(
            message=f"project manifest must be valid JSON: {exc.msg}",
            hint="Fix remix_project.json before retrying.",
        ) from exc


def save_manifest(project: Path, manifest: dict[str, Any]) -> None:
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_manifest(*, source: Path, project_dir: Path, rights_status: str) -> dict[str, Any]:
    manifest_path = project_dir / "remix_project.json"
    manifest = {
        "source": str(source),
        "project_dir": str(project_dir),
        "rights_status": rights_status,
        "assets": [],
        "sections": [],
        "target": {},
        "analysis": {},
        "arrangement_plan": None,
        "qa": None,
    }
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "manifest": manifest}


def add_asset(*, project: Path, role: str, path: Path) -> dict[str, Any]:
    manifest = load_manifest(project)
    asset = {
        "role": require_non_empty_string("role", role, hint="Pass a non-empty stem role."),
        "path": require_absolute_path("path", str(path), hint="Pass an absolute local audio path."),
    }
    assets = manifest.setdefault("assets", [])
    if not isinstance(assets, list):
        raise invalid_argument(
            message="manifest.assets must be an array",
            hint="Fix remix_project.json before adding assets.",
        )
    assets.append(asset)
    save_manifest(project, manifest)
    return {"project": str(project), "asset": asset, "asset_count": len(assets)}


def parse_sections(raw_sections: str) -> list[dict[str, Any]]:
    sections_text = require_non_empty_string(
        "sections",
        raw_sections,
        hint="Use section ranges such as intro:1-8,bridge:49-64.",
    )
    sections: list[dict[str, Any]] = []
    for index, raw_part in enumerate(sections_text.split(",")):
        part = raw_part.strip()
        if not part:
            continue
        name, separator, range_text = part.partition(":")
        if separator != ":":
            raise invalid_argument(
                message=f"sections[{index}] must use name:start-end format",
                hint="Use section ranges such as intro:1-8,bridge:49-64.",
            )
        start_text, range_separator, end_text = range_text.partition("-")
        if range_separator != "-":
            raise invalid_argument(
                message=f"sections[{index}] bar range must use start-end format",
                hint="Use a range such as 17-32.",
            )
        try:
            start_bar = int(start_text)
            end_bar = int(end_text)
        except ValueError as exc:
            raise invalid_argument(
                message=f"sections[{index}] bar range must contain integers",
                hint="Use a range such as 17-32.",
            ) from exc
        if start_bar < 1 or end_bar < start_bar:
            raise invalid_argument(
                message=f"sections[{index}] has invalid bar range: {range_text}",
                hint="Use 1-based inclusive bar ranges where end is >= start.",
            )
        section_name = require_non_empty_string(
            "section name",
            name,
            hint="Use a non-empty section name.",
        )
        profile = infer_section_profile(section_name)
        sections.append(
            {
                "name": section_name,
                "start_bar": start_bar,
                "end_bar": end_bar,
                **profile,
            }
        )
    if not sections:
        raise invalid_argument(
            message="sections must include at least one section",
            hint="Use section ranges such as intro:1-8,bridge:49-64.",
        )
    return sections


def import_sections(*, project: Path, sections: str) -> dict[str, Any]:
    manifest = load_manifest(project)
    parsed_sections = parse_sections(sections)
    manifest["sections"] = parsed_sections
    save_manifest(project, manifest)
    return {"project": str(project), "sections": parsed_sections}


def set_target(*, project: Path, bpm: float, key: str) -> dict[str, Any]:
    manifest = load_manifest(project)
    target = {
        "bpm": bpm,
        "key": require_non_empty_string("key", key, hint="Pass a non-empty musical key."),
    }
    manifest["target"] = target
    save_manifest(project, manifest)
    return {"project": str(project), "target": target}
