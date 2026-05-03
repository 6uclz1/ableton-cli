from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def _write_sine(path: Path, *, amp: float = 0.35) -> None:
    sample_rate = 48000
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_rate // 2):
            sample = int(amp * 32767 * math.sin(2 * math.pi * 220 * index / sample_rate))
            frames.extend(struct.pack("<hh", sample, sample))
        wav.writeframes(bytes(frames))


def test_remix_mastering_cli_flow_outputs_json(runner, cli_app, tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    render = tmp_path / "render.wav"
    reference = tmp_path / "reference.wav"
    for path in (source, render, reference):
        _write_sine(path)
    project_dir = tmp_path / "proj"
    init = runner.invoke(
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
    assert init.exit_code == 0, init.stdout
    manifest_path = project_dir / "remix_project.json"

    profile = runner.invoke(cli_app, ["--output", "json", "remix", "mastering", "profile", "list"])
    target = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "mastering",
            "target",
            "set",
            "--project",
            str(manifest_path),
            "--profile",
            "anime-club-demo",
            "--crest-db-min",
            "3.0",
        ],
    )
    ref = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "mastering",
            "reference",
            "add",
            "--project",
            str(manifest_path),
            "--path",
            str(reference),
            "--role",
            "commercial-reference",
            "--id",
            "ref-main",
        ],
    )
    analyze = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "mastering",
            "analyze",
            "--project",
            str(manifest_path),
            "--render",
            str(render),
            "--reference",
            "ref-main",
        ],
    )
    plan = runner.invoke(
        cli_app,
        ["--output", "json", "remix", "mastering", "plan", "--project", str(manifest_path)],
    )
    apply = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "mastering",
            "apply",
            "--project",
            str(manifest_path),
            "--dry-run",
        ],
    )
    qa = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "mastering",
            "qa",
            "--project",
            str(manifest_path),
            "--render",
            str(render),
        ],
    )
    remix_qa = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "remix",
            "qa",
            "--project",
            str(manifest_path),
            "--include-mastering",
            "--render",
            str(render),
        ],
    )

    assert profile.exit_code == 0, profile.stdout
    assert target.exit_code == 0, target.stdout
    assert ref.exit_code == 0, ref.stdout
    assert analyze.exit_code == 0, analyze.stdout
    assert plan.exit_code == 0, plan.stdout
    assert apply.exit_code == 0, apply.stdout
    assert qa.exit_code == 0, qa.stdout
    assert remix_qa.exit_code == 0, remix_qa.stdout
    assert _payload(analyze.stdout)["result"]["reports"][0]["kind"] == "loudness"  # type: ignore[index]
    assert _payload(apply.stdout)["result"]["steps"][0]["name"] == "master_device_load"  # type: ignore[index]
    assert _payload(qa.stdout)["result"]["ok"] is True  # type: ignore[index]
    assert "mastering" in _payload(remix_qa.stdout)["result"]  # type: ignore[operator]
