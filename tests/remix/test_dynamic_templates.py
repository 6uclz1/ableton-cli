from __future__ import annotations


def test_template_sections_include_dynamic_profiles() -> None:
    from ableton_cli.remix.templates import template_sections

    sections = template_sections("anime-dnb")

    bridge = next(section for section in sections if section["name"] == "bridge")
    drop = next(section for section in sections if section["name"] == "drop")
    second_drop = next(section for section in sections if section["name"] == "second_drop")

    assert bridge["energy"] == 1
    assert bridge["drum_policy"] == "off"
    assert drop["drum_policy"] == "full"
    assert second_drop["energy"] == 5
    assert second_drop["drum_policy"] == "full_with_variation"


def test_infer_section_profile_marks_breaks_and_drops() -> None:
    from ableton_cli.remix.templates import infer_section_profile

    assert infer_section_profile("interlude")["drum_policy"] == "off"
    assert infer_section_profile("breakdown")["energy"] == 1
    assert infer_section_profile("intro-pad")["drum_policy"] == "off"
    assert infer_section_profile("build")["drum_policy"] == "build_only"
    assert infer_section_profile("final_chorus")["drum_policy"] == "full"
    assert infer_section_profile("outro")["drum_policy"] == "reduced"
