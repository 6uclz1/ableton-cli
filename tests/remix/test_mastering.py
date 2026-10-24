from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

import pytest


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


def _write_report(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _loudness_report(audio: Path, **overrides: object) -> dict[str, object]:
    """The fields of an ``analysis loudness analyze`` report that mastering QA reads."""
    return {
        "path": str(audio),
        "integrated_lufs": -9.0,
        "true_peak_dbtp": -1.5,
        "crest_db": 6.0,
        "clipping_sample_count": 0,
        **overrides,
    }


def _spectrum_report(audio: Path) -> dict[str, object]:
    return {
        "path": str(audio),
        "bands": {},
        "stereo": {"mono_low_end_risk": False},
        "warnings": [],
    }


def _project(tmp_path: Path) -> tuple[Path, Path]:
    from ableton_cli.remix.manifest import init_manifest

    source = tmp_path / "source.wav"
    render = tmp_path / "render.wav"
    for path in (source, render):
        _write_sine(path)
    return init_manifest(source_audio_path=source, project=tmp_path / "proj"), render


def test_remix_mastering_target_reference_plan_and_qa(tmp_path: Path) -> None:
    from ableton_cli.remix.manifest import load_manifest
    from ableton_cli.remix.mastering import (
        add_reference,
        add_report,
        apply_chain_plan,
        plan_chain,
        run_mastering_qa,
        set_targets,
    )

    manifest_path, render = _project(tmp_path)
    reference = tmp_path / "reference.wav"
    _write_sine(reference)
    reports = tmp_path / "proj" / "reports"

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
    )
    loudness = add_report(
        manifest_path,
        kind="loudness",
        report=_write_report(reports / "render_loudness.json", _loudness_report(render)),
    )
    add_report(
        manifest_path,
        kind="spectrum",
        report=_write_report(reports / "render_spectrum.json", _spectrum_report(render)),
    )
    plan = plan_chain(manifest_path, target_profile="anime-club-demo", chain="utility,eq8,limiter")
    dry_run = apply_chain_plan(load_manifest(manifest_path), dry_run=True)
    qa = run_mastering_qa(manifest_path, render=render, strict=False)

    assert target["mastering_targets"]["profile"] == "anime-club-demo"
    assert ref["reference"]["id"] == "ref-main"
    assert loudness["report"]["kind"] == "loudness"
    assert loudness["report"]["path"] == str(reports / "render_loudness.json")
    assert loudness["report"]["source_audio_path"] == str(render)
    assert len(load_manifest(manifest_path)["analysis_reports"]) == 2
    assert plan["master_chain_plan"]["status"] == "planned"
    assert [step["name"] for step in dry_run["steps"]][0] == "device_insert"
    assert dry_run["steps"][0]["args"]["track_ref"] == {"mode": "main"}
    assert qa["ok"] is True


def test_mastering_qa_reads_a_registered_loudness_report(tmp_path: Path) -> None:
    from ableton_cli.remix.mastering import add_report, plan_chain, run_mastering_qa, set_targets

    manifest_path, render = _project(tmp_path)
    set_targets(manifest_path, profile="anime-club-demo", true_peak_dbtp_max=-1.0)
    plan_chain(manifest_path, target_profile="anime-club-demo", chain="limiter")
    report = _loudness_report(render, true_peak_dbtp=-0.2, clipping_sample_count=3)
    add_report(manifest_path, kind="loudness", report=_write_report(tmp_path / "l.json", report))

    qa = run_mastering_qa(manifest_path, render=render)

    assert {error["code"] for error in qa["errors"]} == {"clipping", "true_peak_over_target"}


def test_add_report_takes_the_source_of_a_reference_comparison_from_its_candidate(
    tmp_path: Path,
) -> None:
    from ableton_cli.remix.mastering import add_report

    manifest_path, render = _project(tmp_path)
    comparison = {"candidate": str(render), "reference": "/refs/ref.wav", "delta": {}}

    result = add_report(
        manifest_path,
        kind="reference_compare",
        report=_write_report(tmp_path / "compare.json", comparison),
    )

    assert result["report"]["source_audio_path"] == str(render)


@pytest.mark.parametrize(
    ("kind", "content", "message"),
    [
        ("tempo", {}, "unsupported report kind: tempo"),
        ("loudness", None, "report not found"),
        ("loudness", "not json", "report is not valid JSON"),
        ("loudness", [], "report must be a JSON object"),
        ("spectrum", {"path": "/x.wav", "bands": {}}, "missing stereo, warnings"),
        ("loudness", {"integrated_lufs": -9.0}, "missing path"),
    ],
)
def test_add_report_rejects_reports_mastering_qa_cannot_read(
    tmp_path: Path, kind: str, content: object, message: str
) -> None:
    from ableton_cli.errors import AppError
    from ableton_cli.remix.manifest import load_manifest
    from ableton_cli.remix.mastering import add_report

    manifest_path, _render = _project(tmp_path)
    report = tmp_path / "report.json"
    if isinstance(content, str):
        report.write_text(content, encoding="utf-8")
    elif content is not None:
        _write_report(report, content)  # type: ignore[arg-type]

    with pytest.raises(AppError) as exc_info:
        add_report(manifest_path, kind=kind, report=report)

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert message in exc_info.value.message
    assert load_manifest(manifest_path)["analysis_reports"] == []
