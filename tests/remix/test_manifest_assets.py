from __future__ import annotations

from pathlib import Path


def test_remix_manifest_init_and_asset_registry_normalize_paths(tmp_path: Path) -> None:
    from ableton_cli.remix.assets import add_asset, list_assets
    from ableton_cli.remix.manifest import init_manifest, load_manifest

    source = tmp_path / "song.wav"
    vocal = tmp_path / "vocal.wav"
    source.write_bytes(b"source")
    vocal.write_bytes(b"vocal")

    manifest_path = init_manifest(
        source_audio_path=source,
        project=tmp_path / "proj",
        rights_status="private_test",
    )
    manifest = load_manifest(manifest_path)

    assert manifest["schema_version"] == 1
    assert manifest["source_audio_path"] == str(source.resolve())
    assert manifest["rights_status"] == "private_test"
    assert manifest["sections"] == []
    assert manifest["stems"] == []

    added = add_asset(manifest_path, role="vocal", path=vocal)
    assert added["path"] == str(vocal.resolve())
    assert added["role"] == "vocal"

    reloaded = load_manifest(manifest_path)
    assert list_assets(reloaded) == [added]


def test_section_import_and_plan_generate_stable_batch_steps(tmp_path: Path) -> None:
    from ableton_cli.remix.analyze import import_sections
    from ableton_cli.remix.arranger import apply_plan, generate_plan
    from ableton_cli.remix.assets import add_asset
    from ableton_cli.remix.manifest import init_manifest, load_manifest

    source = tmp_path / "song.wav"
    vocal = tmp_path / "vocal.wav"
    inst = tmp_path / "instrumental.wav"
    for path in (source, vocal, inst):
        path.write_bytes(b"audio")

    manifest_path = init_manifest(source_audio_path=source, project=tmp_path / "proj")
    add_asset(manifest_path, role="vocal", path=vocal)
    add_asset(manifest_path, role="instrumental", path=inst)
    import_sections(manifest_path, "intro:1-8,verse:9-24,pre:25-32,chorus:33-48")

    plan = generate_plan(manifest_path, style="anime-club")

    assert plan["style"] == "anime-club"
    assert plan["sections"][0]["name"] == "intro"
    assert plan["steps"][0]["name"] == "arrangement_clip_create"
    assert plan["steps"][0]["args"]["track"] == 2
    assert plan["steps"][0]["args"]["audio_path"] == str(inst.resolve())

    dry_run = apply_plan(load_manifest(manifest_path), dry_run=True)
    assert dry_run["dry_run"] is True
    assert dry_run["step_count"] == len(plan["steps"])
