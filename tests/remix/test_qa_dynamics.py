from __future__ import annotations


def test_qa_errors_when_drum_step_exists_in_drum_off_section() -> None:
    from ableton_cli.remix.qa import run_qa

    manifest = {
        "source": "/tmp/source.wav",
        "rights_status": "private_test",
        "assets": [{"role": "drums", "path": "/tmp/drums.wav"}],
        "sections": [{"name": "bridge", "start_bar": 1, "end_bar": 16}],
        "arrangement_plan": {
            "sections": [{"name": "bridge", "drum_policy": "off", "energy": 1}],
            "steps": [
                {
                    "name": "arrangement_clip_create",
                    "section": "bridge",
                    "role": "drums",
                    "args": {"track": 4, "start_time": 0, "length": 64},
                }
            ],
        },
    }

    result = run_qa(manifest)

    assert result["summary"]["fail"] == 1
    assert result["errors"][0]["code"] == "drums_present_in_drum_off_section"
    assert result["errors"][0]["section"] == "bridge"


def test_qa_warns_when_drums_off_cannot_be_guaranteed() -> None:
    from ableton_cli.remix.qa import run_qa

    manifest = {
        "source": "/tmp/source.wav",
        "rights_status": "private_test",
        "assets": [{"role": "full_mix", "path": "/tmp/source.wav"}],
        "sections": [{"name": "bridge", "start_bar": 1, "end_bar": 16}],
        "arrangement_plan": {
            "sections": [{"name": "bridge", "drum_policy": "off", "energy": 1}],
            "steps": [
                {
                    "name": "arrangement_clip_create",
                    "section": "bridge",
                    "role": "full_mix",
                    "args": {"track": 1, "start_time": 0, "length": 64},
                }
            ],
        },
    }

    result = run_qa(manifest)

    assert result["summary"]["warn"] == 1
    assert result["warnings"][0]["code"] == "drums_off_not_guaranteed"


def test_qa_warns_when_final_drop_lacks_contrast() -> None:
    from ableton_cli.remix.qa import run_qa

    manifest = {
        "source": "/tmp/source.wav",
        "rights_status": "private_test",
        "assets": [
            {"role": "drums", "path": "/tmp/drums.wav"},
            {"role": "bass", "path": "/tmp/bass.wav"},
        ],
        "sections": [{"name": "final_drop", "start_bar": 1, "end_bar": 16}],
        "arrangement_plan": {
            "sections": [
                {"name": "build", "drum_policy": "build_only", "energy": 3},
                {"name": "final_drop", "drum_policy": "full", "energy": 5},
            ],
            "steps": [
                {"name": "arrangement_clip_create", "section": "final_drop", "role": "drums"},
                {"name": "arrangement_clip_create", "section": "final_drop", "role": "bass"},
            ],
        },
    }

    result = run_qa(manifest)

    warning_codes = {warning["code"] for warning in result["warnings"]}
    assert "missing_contrast_before_final_drop" in warning_codes
