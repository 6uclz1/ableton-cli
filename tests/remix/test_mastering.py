from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path


def _write_sine(path: Path, *, amp: float = 0.35, seconds: float = 0.5) -> None:
    sample_rate = 48000
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(int(sample_rate * seconds)):
            sample = int(amp * 32767 * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(struct.pack("<hh", sample, sample))
        wav.writeframes(bytes(frames))


def _allow_ffmpeg_engine(monkeypatch) -> None:
    monkeypatch.setattr(
        "ableton_cli.audio_analysis.loudness.require_ffmpeg_engine",
        lambda engine: engine.strip().lower(),
    )


def test_manifest_schema_v1_migrates_to_mastering_v2(tmp_path: Path) -> None:
    from ableton_cli.remix.manifest import init_manifest, load_manifest

    source = tmp_path / "source.wav"
    source.write_bytes(b"audio")
    manifest_path = init_manifest(source_audio_path=source, project=tmp_path / "proj")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 1
    payload.pop("mastering_targets", None)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    migrated = load_manifest(manifest_path)

    assert migrated["schema_version"] == 2
    assert migrated["mastering_targets"]["profile"] == "anime-club-demo"
    assert migrated["reference_tracks"] == []
    assert migrated["analysis_reports"] == []
    assert migrated["master_chain_plan"] is None


def test_remix_mastering_target_reference_plan_and_qa(tmp_path: Path, monkeypatch) -> None:
    _allow_ffmpeg_engine(monkeypatch)
    from ableton_cli.remix.manifest import init_manifest, load_manifest
    from ableton_cli.remix.mastering import (
        add_reference,
        analyze_render,
        apply_chain_plan,
        plan_chain,
        run_mastering_qa,
        set_targets,
    )

    source = tmp_path / "source.wav"
    render = tmp_path / "render.wav"
    reference = tmp_path / "reference.wav"
    for path in (source, render, reference):
        _write_sine(path)
    manifest_path = init_manifest(source_audio_path=source, project=tmp_path / "proj")

    target = set_targets(
        manifest_path,
        profile="anime-club-demo",
        true_peak_dbtp_max=-1.0,
        crest_db_min=3.0,
    )
    ref = add_reference(
        manifest_path,
        path=reference,
        role="commercial-reference",
        reference_id="ref-main",
        analyze=False,
    )
    analysis = analyze_render(
        manifest_path,
        render=render,
        reference_id="ref-main",
        report_dir=tmp_path / "proj" / "reports",
    )
    plan = plan_chain(manifest_path, target_profile="anime-club-demo", chain="utility,eq8,limiter")
    dry_run = apply_chain_plan(load_manifest(manifest_path), dry_run=True)
    qa = run_mastering_qa(manifest_path, render=render, strict=False)

    assert target["mastering_targets"]["profile"] == "anime-club-demo"
    assert ref["reference"]["id"] == "ref-main"
    assert len(analysis["reports"]) == 3
    assert plan["master_chain_plan"]["status"] == "planned"
    assert [step["name"] for step in dry_run["steps"]][0] == "master_device_load"
    assert qa["ok"] is True
