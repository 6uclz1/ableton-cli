from __future__ import annotations

from copy import deepcopy
from typing import Any

SECTION_PROFILE_KEYS = {
    "energy",
    "drum_policy",
    "bass_policy",
    "vocal_policy",
    "instrumental_policy",
    "lead_policy",
    "transition_out",
}

TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "anime-club": [
        {
            "name": "intro",
            "bars": 8,
            "energy": 2,
            "drum_policy": "light",
            "bass_policy": "off",
            "instrumental_policy": "filtered",
        },
        {
            "name": "verse_chop",
            "bars": 16,
            "energy": 2,
            "drum_policy": "off_or_light",
            "vocal_policy": "chop_source",
        },
        {
            "name": "build",
            "bars": 16,
            "energy": 3,
            "drum_policy": "build_only",
            "transition_out": "riser_last_2_bars",
        },
        {
            "name": "chorus_drop",
            "bars": 32,
            "energy": 4,
            "drum_policy": "full",
            "bass_policy": "full",
            "vocal_policy": "chop_response",
        },
        {
            "name": "breakdown",
            "bars": 16,
            "energy": 1,
            "drum_policy": "off",
            "bass_policy": "off",
            "instrumental_policy": "pad_or_melody",
            "transition_out": "riser_last_2_bars",
        },
        {
            "name": "final_drop",
            "bars": 32,
            "energy": 5,
            "drum_policy": "full_with_variation",
            "bass_policy": "variation",
            "vocal_policy": "chop_variation",
        },
        {
            "name": "outro",
            "bars": 8,
            "energy": 2,
            "drum_policy": "reduced",
            "bass_policy": "reduced",
        },
    ],
    "anime-dnb": [
        {
            "name": "intro",
            "bars": 16,
            "energy": 2,
            "drum_policy": "filtered_break",
            "bass_policy": "off",
            "lead_policy": "teaser",
        },
        {
            "name": "pre_drop_vocal",
            "bars": 8,
            "energy": 2,
            "drum_policy": "off",
            "bass_policy": "off",
            "vocal_policy": "featured",
            "transition_out": "pickup_or_riser",
        },
        {
            "name": "drop",
            "bars": 32,
            "energy": 4,
            "drum_policy": "full",
            "bass_policy": "full",
            "vocal_policy": "chop_response",
        },
        {
            "name": "bridge",
            "bars": 16,
            "energy": 1,
            "drum_policy": "off",
            "bass_policy": "off",
            "instrumental_policy": "pad_or_melody",
            "transition_out": "riser_last_2_bars",
        },
        {
            "name": "second_drop",
            "bars": 32,
            "energy": 5,
            "drum_policy": "full_with_variation",
            "bass_policy": "variation",
            "vocal_policy": "chop_variation",
        },
        {
            "name": "outro",
            "bars": 8,
            "energy": 2,
            "drum_policy": "reduced",
            "bass_policy": "reduced",
        },
    ],
    "anime-future-bass": [
        {
            "name": "intro_pad",
            "bars": 8,
            "energy": 1,
            "drum_policy": "off",
            "bass_policy": "off",
            "instrumental_policy": "pad_or_melody",
        },
        {
            "name": "verse",
            "bars": 16,
            "energy": 2,
            "drum_policy": "off_or_light",
            "bass_policy": "off",
            "vocal_policy": "featured",
        },
        {
            "name": "build",
            "bars": 16,
            "energy": 3,
            "drum_policy": "build_only",
            "transition_out": "snare_roll_or_riser",
        },
        {
            "name": "chorus_drop",
            "bars": 32,
            "energy": 4,
            "drum_policy": "full",
            "bass_policy": "full",
            "instrumental_policy": "wide_chords",
        },
        {
            "name": "breakdown",
            "bars": 16,
            "energy": 1,
            "drum_policy": "off",
            "bass_policy": "off",
            "instrumental_policy": "pad_or_vocal_tail",
            "transition_out": "impact_tail",
        },
        {
            "name": "final_chorus",
            "bars": 32,
            "energy": 5,
            "drum_policy": "full_with_variation",
            "bass_policy": "variation",
            "instrumental_policy": "wide_chords_variation",
        },
        {
            "name": "outro",
            "bars": 8,
            "energy": 2,
            "drum_policy": "reduced",
            "bass_policy": "reduced",
        },
    ],
}


def normalize_section_name(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def infer_section_profile(name: str) -> dict[str, Any]:
    normalized = normalize_section_name(name)
    if normalized in {"bridge", "interlude", "breakdown", "intro_pad"}:
        return {"energy": 1, "drum_policy": "off", "bass_policy": "off"}
    if normalized in {"build", "pre", "pre_drop", "pre_drop_vocal"}:
        return {"energy": 3, "drum_policy": "build_only"}
    if normalized in {
        "chorus",
        "chorus_drop",
        "drop",
        "final_chorus",
        "final_drop",
        "second_drop",
    }:
        return {"energy": 4, "drum_policy": "full", "bass_policy": "full"}
    if normalized == "outro":
        return {"energy": 2, "drum_policy": "reduced", "bass_policy": "reduced"}
    if normalized in {"intro", "verse", "vocal_verse", "verse_chop"}:
        return {"energy": 2, "drum_policy": "off_or_light"}
    return {"energy": 2, "drum_policy": "auto"}


def default_profile_for_section(style: str, name: str) -> dict[str, Any]:
    normalized = normalize_section_name(name)
    for section in TEMPLATES.get(style, []):
        if normalize_section_name(str(section["name"])) == normalized:
            return {
                key: deepcopy(value)
                for key, value in section.items()
                if key in SECTION_PROFILE_KEYS
            }
    return infer_section_profile(name)


def apply_section_profile(
    section: dict[str, Any],
    *,
    style: str,
    dynamics: str = "section-profiles",
    explicit_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if dynamics == "none":
        return {
            "energy": section.get("energy", 2),
            "drum_policy": section.get("drum_policy", "auto"),
        }

    normalized = normalize_section_name(str(section.get("name", "")))
    profile: dict[str, Any] = {}
    if explicit_profiles is not None:
        profile.update(deepcopy(explicit_profiles.get(normalized, {})))
    if dynamics == "section-profiles" and not profile:
        profile.update(default_profile_for_section(style, normalized))
    if not profile:
        profile.update(infer_section_profile(normalized))

    for key in SECTION_PROFILE_KEYS:
        if key in section:
            profile[key] = section[key]
    profile.setdefault("energy", 2)
    profile.setdefault("drum_policy", "auto")
    return profile


def template_sections(style: str) -> list[dict[str, Any]]:
    if style not in TEMPLATES:
        raise KeyError(f"Unknown remix style: {style}")

    sections: list[dict[str, Any]] = []
    start_bar = 1
    for raw_section in TEMPLATES[style]:
        bars = int(raw_section["bars"])
        section = {
            "name": raw_section["name"],
            "start_bar": start_bar,
            "end_bar": start_bar + bars - 1,
            "default_bars": bars,
        }
        for key in SECTION_PROFILE_KEYS:
            if key in raw_section:
                section[key] = deepcopy(raw_section[key])
        sections.append(section)
        start_bar += bars
    return sections
