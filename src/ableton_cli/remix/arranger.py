from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..commands._validation import invalid_argument
from .templates import apply_section_profile, normalize_section_name, template_sections

BEATS_PER_BAR = 4
DRUM_POLICIES_ALLOWING_DRUMS = {
    "light",
    "filtered_break",
    "reduced",
    "full",
    "full_with_variation",
    "auto",
    "off_or_light",
}
BASS_POLICIES_ALLOWING_BASS = {"full", "variation", "reduced", "auto"}
CLEAN_DRUM_OFF_ROLES = {
    "vocal",
    "pad",
    "texture",
    "melody",
    "instrumental_no_drums",
    "drum_free_instrumental",
}
TRACK_DEFAULTS = {
    "full_mix": 1,
    "instrumental": 2,
    "vocal": 3,
    "drums": 4,
    "bass": 5,
    "fx": 6,
}


def _load_explicit_profiles(section_profile: Path | None) -> dict[str, dict[str, Any]] | None:
    if section_profile is None:
        return None
    try:
        payload = json.loads(section_profile.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise invalid_argument(
            message=f"section profile file does not exist: {section_profile}",
            hint="Pass a valid JSON file to --section-profile.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise invalid_argument(
            message=f"section profile file must be valid JSON: {exc.msg}",
            hint="Use an object such as {'sections': {'bridge': {'drum_policy': 'off'}}}.",
        ) from exc
    raw_sections = payload.get("sections") if isinstance(payload, dict) else None
    if not isinstance(raw_sections, dict):
        raise invalid_argument(
            message="section profile file must contain a sections object",
            hint="Use {'sections': {'bridge': {'drum_policy': 'off'}}}.",
        )
    return {
        normalize_section_name(str(name)): profile
        for name, profile in raw_sections.items()
        if isinstance(profile, dict)
    }


def _index_assets_by_role(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    raw_assets = manifest.get("assets", [])
    if not isinstance(raw_assets, list):
        return indexed
    for asset in raw_assets:
        if not isinstance(asset, dict):
            continue
        role = asset.get("role")
        if not isinstance(role, str):
            continue
        indexed.setdefault(role, []).append(asset)
    return indexed


def _first_asset(
    assets_by_role: dict[str, list[dict[str, Any]]],
    roles: tuple[str, ...],
) -> tuple[str, dict[str, Any]] | None:
    for role in roles:
        assets = assets_by_role.get(role, [])
        if assets:
            return role, assets[0]
    return None


def _track_for_role(manifest: dict[str, Any], role: str) -> int:
    track_refs = manifest.get("ableton_track_refs", {})
    if isinstance(track_refs, dict):
        value = track_refs.get(role)
        if isinstance(value, int):
            return value
    return TRACK_DEFAULTS.get(role, 1)


def _create_audio_step(
    *,
    manifest: dict[str, Any],
    section: dict[str, Any],
    role: str,
    asset: dict[str, Any],
    label_suffix: str | None = None,
) -> dict[str, Any]:
    start_bar = int(section["start_bar"])
    end_bar = int(section["end_bar"])
    label_role = role if label_suffix is None else f"{role}_{label_suffix}"
    return {
        "name": "arrangement_clip_create",
        "label": f"{section['name']}:{label_role}",
        "role": role,
        "section": section["name"],
        "args": {
            "track": _track_for_role(manifest, role),
            "start_time": (start_bar - 1) * BEATS_PER_BAR,
            "length": (end_bar - start_bar + 1) * BEATS_PER_BAR,
            "audio_path": asset.get("path"),
        },
    }


def _create_build_step(*, manifest: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
    start_bar = int(section["start_bar"])
    end_bar = int(section["end_bar"])
    return {
        "name": "arrangement_clip_create",
        "label": f"{section['name']}:build_fx",
        "role": "fx",
        "section": section["name"],
        "args": {
            "track": _track_for_role(manifest, "fx"),
            "start_time": max(0, (end_bar - 1) * BEATS_PER_BAR),
            "length": min(8, (end_bar - start_bar + 1) * BEATS_PER_BAR),
            "clip_type": "riser_or_snare_roll",
        },
    }


def _create_full_mix_reference_step(
    *,
    manifest: dict[str, Any],
    sections: list[dict[str, Any]],
    asset: dict[str, Any],
) -> dict[str, Any]:
    end_bar = max(int(section["end_bar"]) for section in sections)
    return {
        "name": "arrangement_clip_create",
        "label": "reference:full_mix",
        "role": "full_mix",
        "section": "reference",
        "args": {
            "track": _track_for_role(manifest, "full_mix"),
            "start_time": 0,
            "length": end_bar * BEATS_PER_BAR,
            "audio_path": asset.get("path"),
        },
    }


def _section_layer_policy(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "drums": profile.get("drum_policy", "auto"),
        "bass": profile.get("bass_policy", "auto"),
        "instrumental": profile.get("instrumental_policy", "auto"),
        "vocal": profile.get("vocal_policy", "auto"),
    }


def _should_place_drums(
    profile: dict[str, Any],
    assets_by_role: dict[str, list[dict[str, Any]]],
) -> bool:
    if not assets_by_role.get("drums"):
        return False
    drum_policy = str(profile.get("drum_policy", "auto"))
    return drum_policy in DRUM_POLICIES_ALLOWING_DRUMS


def _should_place_bass(
    profile: dict[str, Any],
    assets_by_role: dict[str, list[dict[str, Any]]],
) -> bool:
    if not assets_by_role.get("bass"):
        return False
    bass_policy = str(profile.get("bass_policy", "auto"))
    return bass_policy in BASS_POLICIES_ALLOWING_BASS


def _build_warnings(
    *,
    section_plans: list[dict[str, Any]],
    assets_by_role: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    has_drum_control_asset = bool(assets_by_role.get("drums")) or any(
        role in assets_by_role for role in CLEAN_DRUM_OFF_ROLES
    )
    has_baked_bed_asset = any(role in assets_by_role for role in ("full_mix", "instrumental"))
    if has_baked_bed_asset and not has_drum_control_asset:
        for section in section_plans:
            if section.get("drum_policy") == "off":
                warnings.append(
                    {
                        "code": "cannot_guarantee_drums_off",
                        "section": section["name"],
                        "message": (
                            "Only full-mix or drum-baked instrumental assets are available; "
                            "drums may be baked into the audio."
                        ),
                    }
                )
    return warnings


def generate_plan(
    manifest: dict[str, Any],
    *,
    style: str,
    bars: int | None = None,
    length: str = "full",
    dynamics: str = "section-profiles",
    drum_policy: str = "off-in-breaks",
    section_profile: Path | None = None,
) -> dict[str, Any]:
    del bars
    if dynamics not in {"none", "section-profiles", "explicit"}:
        raise invalid_argument(
            message=f"unsupported dynamics mode: {dynamics}",
            hint="Use one of: none, section-profiles, explicit.",
        )
    if drum_policy not in {"keep", "off-in-breaks", "strict"}:
        raise invalid_argument(
            message=f"unsupported drum policy: {drum_policy}",
            hint="Use one of: keep, off-in-breaks, strict.",
        )
    if dynamics == "explicit" and section_profile is None:
        raise invalid_argument(
            message="--section-profile is required when --dynamics explicit",
            hint="Pass a JSON section profile file.",
        )

    explicit_profiles = _load_explicit_profiles(section_profile)
    raw_sections = manifest.get("sections") or template_sections(style)
    assets_by_role = _index_assets_by_role(manifest)

    steps: list[dict[str, Any]] = []
    section_plans: list[dict[str, Any]] = []
    full_mix = _first_asset(assets_by_role, ("full_mix",))
    if full_mix is not None:
        _, asset = full_mix
        steps.append(
            _create_full_mix_reference_step(manifest=manifest, sections=raw_sections, asset=asset)
        )

    for raw_section in raw_sections:
        section = dict(raw_section)
        profile = apply_section_profile(
            section,
            style=style,
            dynamics=dynamics,
            explicit_profiles=explicit_profiles,
        )
        section.update(profile)
        section["layer_policy"] = _section_layer_policy(profile)

        section_steps: list[dict[str, Any]] = []
        instrumental = _first_asset(
            assets_by_role,
            ("instrumental_no_drums", "drum_free_instrumental", "instrumental"),
        )
        if instrumental is not None:
            asset_role, asset = instrumental
            step_role = "instrumental" if asset_role != "full_mix" else "full_mix"
            section_steps.append(
                _create_audio_step(manifest=manifest, section=section, role=step_role, asset=asset)
            )

        vocal = _first_asset(assets_by_role, ("vocal",))
        if vocal is not None:
            _, asset = vocal
            section_steps.append(
                _create_audio_step(manifest=manifest, section=section, role="vocal", asset=asset)
            )

        if drum_policy == "keep" or _should_place_drums(profile, assets_by_role):
            drums = _first_asset(assets_by_role, ("drums",))
            if drums is not None and profile.get("drum_policy") != "build_only":
                _, asset = drums
                section_steps.append(
                    _create_audio_step(
                        manifest=manifest,
                        section=section,
                        role="drums",
                        asset=asset,
                    )
                )
        if profile.get("drum_policy") == "build_only":
            section_steps.append(_create_build_step(manifest=manifest, section=section))

        if _should_place_bass(profile, assets_by_role):
            bass = _first_asset(assets_by_role, ("bass",))
            if bass is not None:
                _, asset = bass
                section_steps.append(
                    _create_audio_step(manifest=manifest, section=section, role="bass", asset=asset)
                )

        steps.extend(section_steps)
        section_plans.append({**section, "steps": section_steps})

    warnings = _build_warnings(section_plans=section_plans, assets_by_role=assets_by_role)
    return {
        "style": style,
        "length": length,
        "dynamics": dynamics,
        "drum_policy": drum_policy,
        "sections": section_plans,
        "steps": steps,
        "warnings": warnings,
    }
