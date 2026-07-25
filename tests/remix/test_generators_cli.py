from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ableton_cli.commands import _remix_generate_commands as generate_commands


class _BatchClientStub:
    def __init__(self) -> None:
        self.batches: list[list[dict[str, Any]]] = []

    def execute_batch(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        self.batches.append(steps)
        return {"executed": len(steps)}


@pytest.fixture
def project(runner, cli_app, tmp_path: Path) -> Path:
    source = tmp_path / "source.wav"
    source.write_bytes(b"audio")
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
            str(tmp_path / "proj"),
        ],
    )
    assert result.exit_code == 0, result.stdout
    return tmp_path / "proj" / "remix_project.json"


def _invoke(runner, cli_app, *args: str):  # noqa: ANN201
    return runner.invoke(cli_app, ["--output", "json", "remix", "generate", *args])


def _result(stdout: str) -> dict[str, Any]:
    payload = json.loads(stdout)
    assert payload["ok"] is True, payload
    return payload["result"]


def test_generate_drums_returns_real_notes(runner, cli_app, project: Path) -> None:
    result = _invoke(runner, cli_app, "drums", "--project", str(project), "--style", "house")
    payload = _result(result.stdout)
    notes = payload["pattern"]["notes"]
    assert notes, "drum generation must not return an empty pattern"
    assert payload["note_count"] == len(notes)
    assert payload["bars"] == 4
    assert payload["length_beats"] == 16.0
    assert payload["applied"] is False


def test_generate_drums_rejects_unknown_style(runner, cli_app, project: Path) -> None:
    result = _invoke(runner, cli_app, "drums", "--project", str(project), "--style", "gabber")
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_generate_drums_seed_is_reproducible(runner, cli_app, project: Path) -> None:
    args = ["drums", "--project", str(project), "--humanize", "0.9", "--seed", "42"]
    first = _result(_invoke(runner, cli_app, *args).stdout)["pattern"]["notes"]
    second = _result(_invoke(runner, cli_app, *args).stdout)["pattern"]["notes"]
    other = _result(
        _invoke(
            runner,
            cli_app,
            "drums",
            "--project",
            str(project),
            "--humanize",
            "0.9",
            "--seed",
            "43",
        ).stdout
    )["pattern"]["notes"]
    assert first == second
    assert first != other


def test_generate_chords_expands_roman_numerals(runner, cli_app, project: Path) -> None:
    result = _invoke(
        runner,
        cli_app,
        "chords",
        "--project",
        str(project),
        "--progression",
        "i-VI-III-VII",
        "--key",
        "F minor",
    )
    payload = _result(result.stdout)
    assert [chord["root"] for chord in payload["chords"]] == [5, 1, 8, 3]
    assert payload["note_count"] == 12
    assert {note["start_time"] for note in payload["pattern"]["notes"]} == {0.0, 4.0, 8.0, 12.0}


def test_generate_chords_without_a_key_fails_explicitly(runner, cli_app, project: Path) -> None:
    result = _invoke(
        runner, cli_app, "chords", "--project", str(project), "--progression", "i-VI"
    )
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_generate_bass_follows_generated_chord_roots(runner, cli_app, project: Path) -> None:
    _invoke(
        runner,
        cli_app,
        "chords",
        "--project",
        str(project),
        "--progression",
        "i-VI-III-VII",
        "--key",
        "F minor",
    )
    payload = _result(
        _invoke(runner, cli_app, "bass", "--project", str(project), "--pattern", "offbeat").stdout
    )
    assert payload["root_source"] == "chords"
    pitches = [note["pitch"] for note in payload["pattern"]["notes"]]
    assert sorted(set(pitches)) == [37, 39, 41, 44]


def test_generate_bass_without_chords_or_key_fails_explicitly(
    runner, cli_app, project: Path
) -> None:
    result = _invoke(
        runner, cli_app, "bass", "--project", str(project), "--no-follow-chords"
    )
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_generated_assets_are_recorded_in_the_manifest(runner, cli_app, project: Path) -> None:
    _invoke(runner, cli_app, "drums", "--project", str(project), "--style", "dnb")
    manifest = json.loads(project.read_text(encoding="utf-8"))
    kinds = [asset["kind"] for asset in manifest["generated_assets"]]
    assert kinds == ["drums"]

    _invoke(runner, cli_app, "drums", "--project", str(project), "--style", "trap")
    manifest = json.loads(project.read_text(encoding="utf-8"))
    assert [asset["style"] for asset in manifest["generated_assets"]] == ["trap"]


def test_apply_executes_a_batch(runner, cli_app, project: Path, monkeypatch) -> None:
    client = _BatchClientStub()
    monkeypatch.setattr(generate_commands, "get_client", lambda ctx: client)
    payload = _result(
        _invoke(
            runner,
            cli_app,
            "drums",
            "--project",
            str(project),
            "--bars",
            "1",
            "--apply",
            "--track",
            "3",
            "--clip",
            "0",
        ).stdout
    )
    assert payload["applied"] is True
    assert payload["batch"] == {"executed": 2}
    (steps,) = client.batches
    assert [step["name"] for step in steps] == ["create_clip", "replace_clip_notes"]
    assert steps[0]["args"] == {"track": 3, "clip": 0, "length": 4.0}
    assert steps[1]["args"]["notes"] == payload["pattern"]["notes"]


def test_apply_without_a_target_fails_explicitly(runner, cli_app, project: Path) -> None:
    result = _invoke(runner, cli_app, "drums", "--project", str(project), "--apply")
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "--track" in payload["error"]["message"]


def test_section_sets_the_bar_count(runner, cli_app, project: Path) -> None:
    manifest = json.loads(project.read_text(encoding="utf-8"))
    manifest["sections"] = [{"name": "drop", "start_bar": 9, "end_bar": 16}]
    project.write_text(json.dumps(manifest), encoding="utf-8")
    payload = _result(
        _invoke(
            runner, cli_app, "drums", "--project", str(project), "--section", "drop"
        ).stdout
    )
    assert payload["bars"] == 8
    assert payload["length_beats"] == 32.0


def test_unknown_section_fails_explicitly(runner, cli_app, project: Path) -> None:
    result = _invoke(runner, cli_app, "drums", "--project", str(project), "--section", "nope")
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"
