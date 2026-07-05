from __future__ import annotations

from typing import Any

from .arranger import CLEAN_DRUM_OFF_ROLES

DROP_SECTION_NAMES = {"drop", "chorus_drop", "final_drop", "second_drop", "final_chorus"}
PEAK_DROP_SECTION_NAMES = {"final_drop", "second_drop", "final_chorus"}
CONTRAST_NAMES = {"bridge", "interlude", "breakdown", "intro_pad"}


def _group_steps_by_section(steps: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for step in steps:
        section = step.get("section")
        if isinstance(section, str):
            grouped.setdefault(section, []).append(step)
    return grouped


def _roles_in_manifest(manifest: dict[str, Any]) -> set[str]:
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return set()
    return {asset["role"] for asset in assets if isinstance(asset, dict) and "role" in asset}


def _has_baked_only_assets(manifest: dict[str, Any]) -> bool:
    roles = _roles_in_manifest(manifest)
    return bool(roles.intersection({"full_mix", "instrumental"})) and not bool(
        roles.intersection(CLEAN_DRUM_OFF_ROLES)
    )


def _add_presence_checks(manifest: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    for field in ("source", "assets", "sections", "arrangement_plan", "rights_status"):
        if not manifest.get(field):
            errors.append({"code": f"missing_{field}", "message": f"Manifest is missing {field}."})


def _qa_arrangement_dynamics(
    manifest: dict[str, Any],
    *,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    plan = manifest.get("arrangement_plan") or {}
    if not isinstance(plan, dict):
        return
    raw_sections = plan.get("sections", [])
    raw_steps = plan.get("steps", [])
    sections = [section for section in raw_sections if isinstance(section, dict)]
    steps = [step for step in raw_steps if isinstance(step, dict)]
    steps_by_section = _group_steps_by_section(steps)

    for section in sections:
        section_name = section.get("name")
        if not isinstance(section_name, str):
            continue
        if "energy" not in section:
            warnings.append(
                {
                    "code": "missing_section_energy",
                    "section": section_name,
                    "message": "Section has no energy value.",
                }
            )
        if section.get("drum_policy") == "off":
            drum_steps = [
                step
                for step in steps_by_section.get(section_name, [])
                if step.get("role") == "drums"
            ]
            if drum_steps:
                errors.append(
                    {
                        "code": "drums_present_in_drum_off_section",
                        "section": section_name,
                        "message": "Drum steps are present in a drum-off section.",
                    }
                )
            if _has_baked_only_assets(manifest):
                warnings.append(
                    {
                        "code": "drums_off_not_guaranteed",
                        "section": section_name,
                        "message": (
                            "Only full-mix or drum-baked instrumental assets are available; "
                            "drums may be baked into the audio."
                        ),
                    }
                )

    for section in sections:
        section_name = section.get("name")
        if section_name not in DROP_SECTION_NAMES:
            continue
        roles = {step.get("role") for step in steps_by_section.get(str(section_name), [])}
        if "drums" not in roles and "bass" not in roles:
            warnings.append(
                {
                    "code": "drop_lacks_rhythmic_density",
                    "section": section_name,
                    "message": "Drop section has neither drums nor bass steps.",
                }
            )

    energies = [
        section.get("energy") for section in sections if isinstance(section.get("energy"), int)
    ]
    if energies and all(energy >= 3 for energy in energies):
        warnings.append(
            {
                "code": "no_low_energy_contrast",
                "message": "All sections are energy 3 or higher.",
            }
        )

    final_index = next(
        (
            index
            for index, section in enumerate(sections)
            if section.get("name") in PEAK_DROP_SECTION_NAMES
        ),
        None,
    )
    if final_index is not None:
        prior_sections = sections[:final_index]
        has_contrast = any(
            section.get("name") in CONTRAST_NAMES
            or section.get("drum_policy") == "off"
            or section.get("energy") == 1
            for section in prior_sections
        )
        if not has_contrast:
            warnings.append(
                {
                    "code": "missing_contrast_before_final_drop",
                    "message": "No contrast section appears before the first drop/final drop.",
                }
            )


def run_qa(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    _add_presence_checks(manifest, errors)
    _qa_arrangement_dynamics(manifest, errors=errors, warnings=warnings)

    return {
        "summary": {
            "pass": 1 if not errors else 0,
            "warn": len(warnings),
            "fail": len(errors),
        },
        "errors": errors,
        "warnings": warnings,
    }
