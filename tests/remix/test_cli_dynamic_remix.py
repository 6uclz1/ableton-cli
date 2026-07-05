from __future__ import annotations

import json
from pathlib import Path


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def _init_project(runner, cli_app, tmp_path: Path) -> Path:
    source = tmp_path / "source.wav"
    source.write_bytes(b"private test audio")
    project_dir = tmp_path / "proj"

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "init",
            "--source",
            str(source),
            "--project",
            str(project_dir),
            "--rights-status",
            "private_test",
        ],
    )

    assert result.exit_code == 0, result.stdout
    return project_dir / "remix_project.json"


def test_remix_plan_outputs_section_profiles_and_role_steps(runner, cli_app, tmp_path) -> None:
    project = _init_project(runner, cli_app, tmp_path)

    for role in ("instrumental", "drums", "bass"):
        asset_path = tmp_path / f"{role}.wav"
        asset_path.write_bytes(b"audio")
        added = runner.invoke(
            cli_app,
            [
                "--output",
                "json",
                "audio",
                "asset",
                "add",
                "--project",
                str(project),
                "--role",
                role,
                "--path",
                str(asset_path),
            ],
        )
        assert added.exit_code == 0, added.stdout

    imported = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "sections",
            "import",
            "--project",
            str(project),
            "--sections",
            "drop:1-16,bridge:17-32,second_drop:33-48",
        ],
    )
    assert imported.exit_code == 0, imported.stdout

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "plan",
            "--project",
            str(project),
            "--style",
            "anime-dnb",
            "--dynamics",
            "section-profiles",
        ],
    )

    assert result.exit_code == 0, result.stdout
    plan = _payload(result.stdout)["result"]
    bridge = next(section for section in plan["sections"] if section["name"] == "bridge")
    bridge_steps = [step for step in plan["steps"] if step["section"] == "bridge"]
    drop_steps = [step for step in plan["steps"] if step["section"] == "drop"]

    assert bridge["drum_policy"] == "off"
    assert all(step["role"] != "drums" for step in bridge_steps)
    assert any(step["role"] == "drums" for step in drop_steps)


def test_remix_qa_reports_drum_off_violation(runner, cli_app, tmp_path) -> None:
    project = _init_project(runner, cli_app, tmp_path)
    manifest = json.loads(project.read_text(encoding="utf-8"))
    manifest["assets"] = [{"role": "drums", "path": str(tmp_path / "drums.wav")}]
    manifest["sections"] = [{"name": "bridge", "start_bar": 1, "end_bar": 16}]
    manifest["arrangement_plan"] = {
        "sections": [{"name": "bridge", "energy": 1, "drum_policy": "off"}],
        "steps": [
            {
                "name": "arrangement_clip_create",
                "section": "bridge",
                "role": "drums",
                "args": {"track": 4, "start_time": 0, "length": 64},
            }
        ],
    }
    project.write_text(json.dumps(manifest), encoding="utf-8")

    result = runner.invoke(
        cli_app,
        ["--output", "json", "remix", "qa", "--project", str(project)],
    )

    assert result.exit_code == 0, result.stdout
    qa = _payload(result.stdout)["result"]
    assert qa["summary"]["fail"] == 1
    assert qa["errors"][0]["code"] == "drums_present_in_drum_off_section"
