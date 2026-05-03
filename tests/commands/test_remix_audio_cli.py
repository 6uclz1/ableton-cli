from __future__ import annotations

import json
from pathlib import Path


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def test_remix_cli_mvp_flow_outputs_json(runner, cli_app, tmp_path: Path) -> None:
    source = tmp_path / "anime_song.wav"
    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    for path in (source, vocal, instrumental):
        path.write_bytes(b"audio")

    project_dir = tmp_path / "proj"
    init_result = runner.invoke(
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
        ],
    )
    assert init_result.exit_code == 0, init_result.stdout
    manifest_path = project_dir / "remix_project.json"
    assert manifest_path.exists()

    for role, path in (("vocal", vocal), ("instrumental", instrumental)):
        add_result = runner.invoke(
            cli_app,
            [
                "--output",
                "json",
                "audio",
                "asset",
                "add",
                "--project",
                str(manifest_path),
                "--role",
                role,
                "--path",
                str(path),
            ],
        )
        assert add_result.exit_code == 0, add_result.stdout

    sections = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "audio",
            "sections",
            "import",
            "--project",
            str(manifest_path),
            "--sections",
            "intro:1-8,verse:9-24,pre:25-32,chorus:33-48",
        ],
    )
    assert sections.exit_code == 0, sections.stdout

    plan = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "plan",
            "--project",
            str(manifest_path),
            "--style",
            "anime-club",
        ],
    )
    assert plan.exit_code == 0, plan.stdout
    plan_payload = _payload(plan.stdout)
    assert plan_payload["result"]["style"] == "anime-club"  # type: ignore[index]

    apply = runner.invoke(
        cli_app,
        ["--output", "json", "remix", "apply", "--project", str(manifest_path), "--dry-run"],
    )
    assert apply.exit_code == 0, apply.stdout
    assert _payload(apply.stdout)["result"]["dry_run"] is True  # type: ignore[index]

    qa = runner.invoke(
        cli_app, ["--output", "json", "remix", "qa", "--project", str(manifest_path)]
    )
    assert qa.exit_code == 0, qa.stdout
    assert _payload(qa.stdout)["result"]["ok"] is True  # type: ignore[index]


def test_remix_vocal_chop_and_stem_commands_are_manifest_backed(
    runner,
    cli_app,
    tmp_path: Path,
) -> None:
    source = tmp_path / "song.wav"
    vocal = tmp_path / "vocal.wav"
    source.write_bytes(b"source")
    vocal.write_bytes(b"vocal")
    project_dir = tmp_path / "proj"

    runner.invoke(
        cli_app,
        ["remix", "init", "--source", str(source), "--project", str(project_dir)],
    )
    manifest_path = project_dir / "remix_project.json"
    runner.invoke(
        cli_app,
        [
            "audio",
            "asset",
            "add",
            "--project",
            str(manifest_path),
            "--role",
            "vocal",
            "--path",
            str(vocal),
        ],
    )
    runner.invoke(
        cli_app,
        [
            "audio",
            "sections",
            "import",
            "--project",
            str(manifest_path),
            "--sections",
            "chorus:33-48",
        ],
    )

    chop = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "vocal-chop",
            "--project",
            str(manifest_path),
            "--source",
            "vocal",
            "--section",
            "chorus",
            "--slice",
            "1/8",
            "--create-trigger",
        ],
    )
    assert chop.exit_code == 0, chop.stdout
    assert _payload(chop.stdout)["result"]["command"] == "clip_cut_to_drum_rack"  # type: ignore[index]

    stems = runner.invoke(
        cli_app,
        ["--output", "json", "audio", "stems", "list", "--project", str(manifest_path)],
    )
    assert stems.exit_code == 0, stems.stdout
    assert _payload(stems.stdout)["result"]["stem_count"] == 1  # type: ignore[index]


def test_remix_mix_and_device_chain_commands_return_plans(runner, cli_app, tmp_path: Path) -> None:
    source = tmp_path / "song.wav"
    source.write_bytes(b"source")
    project_dir = tmp_path / "proj"
    runner.invoke(
        cli_app, ["remix", "init", "--source", str(source), "--project", str(project_dir)]
    )
    manifest_path = project_dir / "remix_project.json"

    setup_sound = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "setup-sound",
            "--project",
            str(manifest_path),
            "--kit",
            "club-drums",
            "--bass",
            "reese",
            "--lead",
            "supersaw",
        ],
    )
    mix_macro = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "mix-macro",
            "--project",
            str(manifest_path),
            "--preset",
            "anime-club-basic",
        ],
    )
    device_chain = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "device-chain",
            "apply",
            "--project",
            str(manifest_path),
            "--chain",
            "drop-filter",
        ],
    )

    assert setup_sound.exit_code == 0, setup_sound.stdout
    assert mix_macro.exit_code == 0, mix_macro.stdout
    assert device_chain.exit_code == 0, device_chain.stdout
    assert _payload(setup_sound.stdout)["result"]["requires_browser_search"] is True  # type: ignore[index]
    assert _payload(mix_macro.stdout)["result"]["preset"] == "anime-club-basic"  # type: ignore[index]
    assert _payload(device_chain.stdout)["result"]["chain"] == "drop-filter"  # type: ignore[index]
