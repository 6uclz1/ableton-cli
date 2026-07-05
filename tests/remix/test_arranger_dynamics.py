from __future__ import annotations

from pathlib import Path


def _asset(role: str, path: str) -> dict[str, object]:
    return {"role": role, "path": path}


def test_generate_plan_omits_drums_in_bridge() -> None:
    from ableton_cli.remix.arranger import generate_plan

    manifest = {
        "assets": [
            _asset("instrumental", "/tmp/instrumental.wav"),
            _asset("drums", "/tmp/drums.wav"),
            _asset("bass", "/tmp/bass.wav"),
        ],
        "sections": [
            {"name": "drop", "start_bar": 1, "end_bar": 16},
            {"name": "bridge", "start_bar": 17, "end_bar": 32},
            {"name": "second_drop", "start_bar": 33, "end_bar": 48},
        ],
    }

    plan = generate_plan(manifest, style="anime-dnb", dynamics="section-profiles")

    bridge = next(section for section in plan["sections"] if section["name"] == "bridge")
    bridge_steps = [step for step in plan["steps"] if step["section"] == "bridge"]

    assert bridge["energy"] == 1
    assert bridge["drum_policy"] == "off"
    assert all(step["role"] != "drums" for step in bridge_steps)
    assert any(step["role"] == "instrumental" for step in bridge_steps)


def test_generate_plan_keeps_full_drums_in_drop() -> None:
    from ableton_cli.remix.arranger import generate_plan

    manifest = {
        "assets": [
            _asset("instrumental", "/tmp/instrumental.wav"),
            _asset("drums", "/tmp/drums.wav"),
            _asset("bass", "/tmp/bass.wav"),
        ],
        "sections": [
            {"name": "drop", "start_bar": 1, "end_bar": 16},
            {"name": "bridge", "start_bar": 17, "end_bar": 32},
        ],
    }

    plan = generate_plan(manifest, style="anime-dnb", dynamics="section-profiles")

    drop = next(section for section in plan["sections"] if section["name"] == "drop")
    drop_steps = [step for step in plan["steps"] if step["section"] == "drop"]

    assert drop["drum_policy"] == "full"
    assert any(step["role"] == "drums" for step in drop_steps)
    assert any(step["role"] == "bass" for step in drop_steps)


def test_generate_plan_loads_explicit_section_profile(tmp_path: Path) -> None:
    from ableton_cli.remix.arranger import generate_plan

    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        """
        {
          "sections": {
            "custom_reset": {
              "energy": 1,
              "drum_policy": "off",
              "bass_policy": "off",
              "instrumental_policy": "pad_or_filtered"
            }
          }
        }
        """,
        encoding="utf-8",
    )
    manifest = {
        "assets": [
            _asset("instrumental", "/tmp/instrumental.wav"),
            _asset("drums", "/tmp/drums.wav"),
        ],
        "sections": [{"name": "custom_reset", "start_bar": 1, "end_bar": 8}],
    }

    plan = generate_plan(
        manifest,
        style="anime-club",
        dynamics="explicit",
        section_profile=profile_path,
    )

    assert plan["sections"][0]["drum_policy"] == "off"
    assert all(step["role"] != "drums" for step in plan["steps"])


def test_generate_plan_preserves_full_mix_once() -> None:
    from ableton_cli.remix.arranger import generate_plan

    manifest = {
        "assets": [_asset("full_mix", "/tmp/source.wav")],
        "sections": [
            {"name": "intro", "start_bar": 1, "end_bar": 8},
            {"name": "bridge", "start_bar": 9, "end_bar": 16},
            {"name": "final_drop", "start_bar": 17, "end_bar": 32},
        ],
    }

    plan = generate_plan(manifest, style="anime-club", dynamics="section-profiles")
    full_mix_steps = [step for step in plan["steps"] if step["role"] == "full_mix"]

    assert len(full_mix_steps) == 1
    assert full_mix_steps[0]["section"] == "reference"
    assert full_mix_steps[0]["args"]["length"] == 128
