from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import create_tech_house


def test_generate_drum_notes_have_expected_density_and_schema() -> None:
    intro = create_tech_house.generate_drum_notes("Intro")
    build = create_tech_house.generate_drum_notes("Build")
    drop = create_tech_house.generate_drum_notes("Drop")
    outro = create_tech_house.generate_drum_notes("Outro")

    assert len(intro) < len(build) < len(drop)
    assert len(outro) < len(intro)

    valid_pitches = {36, 39, 42, 46}
    for note in drop:
        assert set(note.keys()) == {"pitch", "start_time", "duration", "velocity", "mute"}
        assert note["pitch"] in valid_pitches
        assert 0 <= note["pitch"] <= 127
        assert note["start_time"] >= 0
        assert note["duration"] > 0
        assert 1 <= note["velocity"] <= 127
        assert isinstance(note["mute"], bool)


def test_generate_bass_lead_chord_fx_notes_match_section_intent() -> None:
    intro_bass = create_tech_house.generate_bass_notes("Intro")
    build_bass = create_tech_house.generate_bass_notes("Build")
    drop_bass = create_tech_house.generate_bass_notes("Drop")
    outro_bass = create_tech_house.generate_bass_notes("Outro")

    assert len(intro_bass) < len(build_bass)
    assert len(build_bass) == len(drop_bass)
    assert len(outro_bass) < len(build_bass)

    intro_lead = create_tech_house.generate_lead_notes("Intro")
    build_lead = create_tech_house.generate_lead_notes("Build")
    drop_lead = create_tech_house.generate_lead_notes("Drop")
    outro_lead = create_tech_house.generate_lead_notes("Outro")

    assert intro_lead == []
    assert outro_lead == []
    assert len(build_lead) > 0
    assert len(drop_lead) > len(build_lead)

    intro_chord = create_tech_house.generate_chord_notes("Intro")
    drop_chord = create_tech_house.generate_chord_notes("Drop")
    assert len(drop_chord) > len(intro_chord)

    intro_fx = create_tech_house.generate_fx_notes("Intro")
    build_fx = create_tech_house.generate_fx_notes("Build")
    drop_fx = create_tech_house.generate_fx_notes("Drop")
    assert intro_fx == []
    assert len(build_fx) > 0
    assert len(drop_fx) >= len(build_fx)


def test_default_blueprint_has_fixed_practical_config() -> None:
    blueprint = create_tech_house.build_default_blueprint()

    assert blueprint.tempo == 126
    assert [section.name for section in blueprint.sections] == ["Intro", "Build", "Drop", "Outro"]
    assert [section.length_beats for section in blueprint.sections] == [64.0, 64.0, 128.0, 64.0]
    assert [track.name for track in blueprint.tracks] == ["DRUMS", "BASS", "CHORD", "LEAD", "FX"]


def test_runner_builds_command_and_writes_command_log(tmp_path: Path) -> None:
    log_path = tmp_path / "command-log.ndjson"
    calls: list[list[str]] = []

    def _executor(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"ok": True, "result": {"tempo": 128.0}, "error": None}),
            stderr="",
        )

    runner = create_tech_house.AbletonCliRunner(
        repo_root=tmp_path,
        log_path=log_path,
        timeout_ms=8000,
        executor=_executor,
    )

    payload = runner.run(["song", "info"])

    assert payload["result"]["tempo"] == 128.0
    assert calls == [
        [
            "uv",
            "run",
            "ableton-cli",
            "--output",
            "json",
            "--timeout-ms",
            "8000",
            "song",
            "info",
        ]
    ]

    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    assert entries[0]["command"] == "song"
    assert entries[0]["args"] == ["info"]
    assert entries[0]["ok"] is True
    assert entries[0]["error"] is None
    assert entries[0]["duration_ms"] >= 0.0


def test_run_preflight_is_fail_fast() -> None:
    calls: list[list[str]] = []

    class _Runner:
        def run(self, args: list[str]) -> dict[str, object]:
            calls.append(args)
            if args == ["ping"]:
                raise create_tech_house.CommandFailed("ping failed")
            return {"ok": True, "result": {}}

    with pytest.raises(create_tech_house.CommandFailed):
        create_tech_house.run_preflight(_Runner())

    assert calls == [["doctor"], ["ping"]]


class _WorkflowRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self._next_track_index = 0

    def run(self, args: list[str]) -> dict[str, Any]:
        self.calls.append(args)

        if args == ["doctor"]:
            return {
                "ok": True,
                "result": {"summary": {"pass": 8, "warn": 0, "fail": 0}, "checks": []},
            }
        if args == ["ping"]:
            return {
                "ok": True,
                "result": {
                    "protocol_version": 2,
                    "remote_script_version": "0.4.0",
                    "supported_commands": ["ping", "tracks_list", "session_snapshot"],
                },
            }
        if args == ["session", "snapshot"]:
            return {
                "ok": True,
                "result": {
                    "tracks_list": {"tracks": []},
                    "scenes_list": {"scenes": []},
                },
            }
        if args == ["tracks", "list"]:
            return {"ok": True, "result": {"tracks": []}}
        if args[:3] == ["tracks", "create", "midi"]:
            index = self._next_track_index
            self._next_track_index += 1
            return {"ok": True, "result": {"index": index, "name": f"MIDI {index}", "kind": "midi"}}
        if args[:3] == ["track", "name", "set"]:
            return {"ok": True, "result": {"track": int(args[3]), "name": args[4]}}
        if args == ["scenes", "list"]:
            return {"ok": True, "result": {"scenes": []}}
        if args[:2] == ["scenes", "create"]:
            scene_index = int(args[-1])
            return {"ok": True, "result": {"index": scene_index, "name": ""}}
        if args[:3] == ["scenes", "name", "set"]:
            return {"ok": True, "result": {"scene": int(args[3]), "name": args[4]}}
        if args[:2] == ["transport", "tempo"] and args[2] == "set":
            return {"ok": True, "result": {"tempo": float(args[3])}}
        if args[:2] == ["track", "volume"] and args[2] == "set":
            return {"ok": True, "result": {"track": int(args[3]), "volume": float(args[4])}}
        if args[:2] == ["track", "panning"] and args[2] == "set":
            return {"ok": True, "result": {"track": int(args[3]), "panning": float(args[4])}}
        if args[:2] == ["browser", "load"]:
            return {"ok": True, "result": {"loaded": True}}
        if args[:2] == ["browser", "load-drum-kit"]:
            return {"ok": True, "result": {"loaded": True}}
        if args[:2] == ["effect", "find"]:
            return {"ok": True, "result": {"count": 1, "devices": [{"track": 0, "device": 1}]}}
        if args[:2] == ["clip", "create"]:
            return {"ok": True, "result": {"track": int(args[2]), "clip": int(args[3])}}
        if args[:3] == ["clip", "notes", "replace"]:
            return {
                "ok": True,
                "result": {"track": int(args[3]), "clip": int(args[4]), "added": True},
            }
        if args[:3] == ["clip", "name", "set"]:
            return {
                "ok": True,
                "result": {"track": int(args[3]), "clip": int(args[4]), "name": args[5]},
            }
        if args[:2] == ["effect", "eq8"] and args[2] == "set":
            return {"ok": True, "result": {"applied": True}}
        if args[:2] == ["effect", "compressor"] and args[2] == "set":
            return {"ok": True, "result": {"applied": True}}
        if args[:2] == ["effect", "reverb"] and args[2] == "set":
            return {"ok": True, "result": {"applied": True}}
        if args[:2] == ["effect", "utility"] and args[2] == "set":
            return {"ok": True, "result": {"applied": True}}

        return {"ok": True, "result": {}}


def test_run_practical_song_workflow_includes_expected_sequence() -> None:
    runner = _WorkflowRunner()
    blueprint = create_tech_house.build_default_blueprint()

    build = create_tech_house.run_practical_song_workflow(runner, blueprint=blueprint)

    assert runner.calls[0] == ["doctor"]
    assert runner.calls[1] == ["ping"]
    assert runner.calls[2] == ["session", "snapshot"]
    assert ["transport", "tempo", "set", "126"] in runner.calls
    assert any(call[:2] == ["tracks", "create"] for call in runner.calls)
    assert any(call[:2] == ["scenes", "name"] for call in runner.calls)
    assert any(call[:2] == ["clip", "create"] for call in runner.calls)

    assert build.tempo == 126
    assert build.track_count == len(blueprint.tracks)
    assert build.scene_count == len(blueprint.sections)
    assert build.clip_count == len(blueprint.tracks) * len(blueprint.sections)
    assert build.note_count > 0


def test_ensure_clean_set_fails_when_clip_exists() -> None:
    class _DirtyRunner:
        def run(self, args: list[str]) -> dict[str, Any]:
            if args == ["track", "info", "0"]:
                return {
                    "ok": True,
                    "result": {
                        "index": 0,
                        "name": "Dirty Track",
                        "clip_slots": [
                            {"index": 0, "has_clip": False, "clip": None},
                            {
                                "index": 1,
                                "has_clip": True,
                                "clip": {"name": "Existing", "length": 4.0},
                            },
                        ],
                    },
                }
            return {"ok": True, "result": {}}

    with pytest.raises(create_tech_house.CommandFailed, match="clean"):
        create_tech_house.ensure_clean_set(
            _DirtyRunner(),
            snapshot={"tracks_list": {"tracks": [{"index": 0, "name": "Dirty Track"}]}},
        )


def test_report_contains_runtime_observations_and_summary(tmp_path: Path) -> None:
    log_path = tmp_path / "command-log.ndjson"
    entries = [
        {"command": "doctor", "args": [], "duration_ms": 12.0, "ok": True, "error": None},
        {
            "command": "browser",
            "args": ["search", "drift"],
            "duration_ms": 2100.0,
            "ok": False,
            "error": {"code": "TIMEOUT", "message": "Timed out"},
        },
    ]
    log_path.write_text("\n".join(json.dumps(item) for item in entries) + "\n", encoding="utf-8")

    report_path = tmp_path / "practical-song-report.md"
    build = create_tech_house.PracticalSongBuild(
        tempo=126,
        track_count=5,
        scene_count=4,
        clip_count=20,
        note_count=320,
        supported_commands={"ping"},
    )
    create_tech_house.write_practical_song_report(
        output_path=report_path,
        command_log_path=log_path,
        build=build,
        friction_notes=["Track deletion is not available via CLI."],
    )

    text = report_path.read_text(encoding="utf-8")
    assert "## Execution Summary" in text
    assert "success_count" in text
    assert "failure_count" in text
    assert "average_duration_ms" in text
    assert "## Runtime Observations" in text
    assert "Track deletion is not available via CLI." in text


def test_issue_draft_contains_required_sections_and_new_gap_titles(tmp_path: Path) -> None:
    log_path = tmp_path / "command-log.ndjson"
    log_path.write_text(
        json.dumps(
            {
                "command": "browser",
                "args": ["load", "0", "query:Synths#Drift"],
                "duration_ms": 2100.0,
                "ok": False,
                "error": {"code": "TIMEOUT", "message": "Timed out", "hint": "Increase timeout"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "improvement-issue-drafts.md"

    create_tech_house.write_issue_drafts(
        output_path=output_path,
        command_log_path=log_path,
        friction_notes=["Preview quality cannot be judged automatically from CLI."],
        supported_commands={"ping", "song_info"},
    )

    text = output_path.read_text(encoding="utf-8")
    assert "新規Set作成API不足" in text
    assert "Set保存API不足" in text
    assert "オーディオ書き出しAPI不足" in text
    assert "Arrangement録音API不足" in text
    assert "クリップ複製API不足" in text
    assert "Scene移動API不足" in text
    assert "トラック削除API不足" in text

    assert "song new" in text
    assert "song save --path <als>" in text
    assert "song export audio --path <wav>" in text
    assert "arrangement record start|stop" in text
    assert "clip duplicate <track> <src_clip> <dst_clip>" in text
    assert "scenes move <from> <to>" in text
    assert "tracks delete <track>" in text

    assert "browser search のタイムアウト耐性不足" not in text
    assert "clip notes が add のみで編集系不足" not in text

    assert "## Runtime Observations" in text
    assert "### Background" in text
    assert "### Repro Steps" in text
    assert "### Expected" in text
    assert "### Actual" in text
    assert "### Proposed API" in text
    assert "### Acceptance Criteria" in text
    assert "## ToDo Progress" in text
    assert "`song_new`" in text
    assert "`missing`" in text


def test_issue_draft_todo_progress_supports_done_missing_blocked(tmp_path: Path) -> None:
    log_path = tmp_path / "command-log.ndjson"
    entries = [
        {
            "command": "song",
            "args": ["new"],
            "duration_ms": 10.0,
            "ok": False,
            "error": {
                "code": "INVALID_ARGUMENT",
                "message": "not supported",
                "details": {"reason": "not_supported_by_live_api"},
            },
        },
        {
            "command": "arrangement",
            "args": ["record", "start"],
            "duration_ms": 10.0,
            "ok": False,
            "error": {
                "code": "INVALID_ARGUMENT",
                "message": "not supported",
                "details": {"reason": "not_supported_by_live_api"},
            },
        },
    ]
    log_path.write_text("\n".join(json.dumps(item) for item in entries) + "\n", encoding="utf-8")
    output_path = tmp_path / "improvement-issue-drafts.md"

    create_tech_house.write_issue_drafts(
        output_path=output_path,
        command_log_path=log_path,
        friction_notes=[],
        supported_commands={
            "song_new",
            "song_save",
            "song_export_audio",
            "arrangement_record_start",
            "arrangement_record_stop",
            "clip_duplicate",
        },
    )

    text = output_path.read_text(encoding="utf-8")
    assert "## ToDo Progress" in text
    assert "| `song_new` | `blocked` |" in text
    assert "| `song_save` | `done` |" in text
    assert "| `song_export_audio` | `done` |" in text
    assert "| `arrangement_record` | `blocked` |" in text
    assert "| `clip_duplicate` | `done` |" in text
    assert "| `scenes_move` | `missing` |" in text
    assert "| `tracks_delete` | `missing` |" in text

    assert "新規Set作成API不足" in text
    assert "Arrangement録音API不足" in text
    assert "Scene移動API不足" in text
    assert "トラック削除API不足" in text
    assert "Set保存API不足" not in text
    assert "オーディオ書き出しAPI不足" not in text
    assert "クリップ複製API不足" not in text
