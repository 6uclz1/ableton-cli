from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class _FakeClient:
    def __init__(self, notes: list[dict[str, Any]]) -> None:
        self._notes = notes
        self.replace_calls: list[dict[str, Any]] = []
        self.add_calls: list[dict[str, Any]] = []

    def get_clip_notes(self, *, track, clip, start_time, end_time, pitch):  # noqa: ANN001, ANN201
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "notes": self._notes,
            "note_count": len(self._notes),
        }

    def replace_clip_notes(self, *, track, clip, notes, start_time, end_time, pitch):  # noqa: ANN001, ANN201
        self.replace_calls.append(
            {
                "track": track,
                "clip": clip,
                "notes": notes,
                "start_time": start_time,
                "end_time": end_time,
                "pitch": pitch,
            }
        )
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": len(self._notes),
            "added_count": len(notes),
        }

    def add_notes_to_clip(self, track, clip, notes):  # noqa: ANN001, ANN201
        self.add_calls.append({"track": track, "clip": clip, "notes": notes})
        return {"track": track, "clip": clip, "note_count": len(notes)}


def _note(pitch: int, start: float, duration: float = 1.0, velocity: int = 100) -> dict:
    return {
        "note_id": pitch,
        "pitch": pitch,
        "start_time": start,
        "duration": duration,
        "velocity": velocity,
        "mute": False,
    }


def test_transpose_in_scale_sends_replace_payload(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(64, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "transpose-in-scale",
            "0",
            "0",
            "--root",
            "C",
            "--scale",
            "major",
            "--degrees",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert fake.replace_calls[0]["notes"][0]["pitch"] == 65


def test_transpose_in_scale_rejects_unknown_scale(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(64, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "transpose-in-scale",
            "0",
            "0",
            "--root",
            "C",
            "--scale",
            "not-a-scale",
            "--degrees",
            "1",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_transpose_in_scale_out_of_range_reports_offending_indices(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(0, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "transpose-in-scale",
            "0",
            "0",
            "--root",
            "C",
            "--scale",
            "major",
            "--degrees",
            "-1",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["details"]["offending_indices"] == [0]


def test_arpeggiate_sends_replace_payload_with_spaced_start_times(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0), _note(64, 0.0), _note(67, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "arpeggiate",
            "0",
            "0",
            "--mode",
            "up",
            "--rate",
            "1/16",
            "--gate",
            "1.0",
        ],
    )

    assert result.exit_code == 0, result.output
    sent_notes = fake.replace_calls[0]["notes"]
    assert [n["start_time"] for n in sent_notes] == [0.0, 0.25, 0.5]


def test_euclidean_replace_mode_sends_pattern(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "euclidean",
            "0",
            "0",
            "--pitch",
            "36",
            "--steps",
            "16",
            "--pulses",
            "5",
            "--length",
            "4",
        ],
    )

    assert result.exit_code == 0, result.output
    sent_notes = fake.replace_calls[0]["notes"]
    assert len(sent_notes) == 5
    assert all(n["pitch"] == 36 for n in sent_notes)


def test_euclidean_merge_mode_calls_add_notes(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "euclidean",
            "0",
            "0",
            "--pitch",
            "36",
            "--steps",
            "16",
            "--pulses",
            "5",
            "--length",
            "4",
            "--mode",
            "merge",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(fake.add_calls) == 1
    assert len(fake.replace_calls) == 0


def test_ratchet_splits_notes_into_repeats(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0, duration=1.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "ratchet",
            "0",
            "0",
            "--division",
            "4",
            "--probability",
            "1.0",
        ],
    )

    assert result.exit_code == 0, result.output
    sent_notes = fake.replace_calls[0]["notes"]
    assert len(sent_notes) == 4


def test_retrograde_reverses_note_order(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0, duration=1.0), _note(64, 1.0, duration=1.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "retrograde",
            "0",
            "0",
            "--loop-length",
            "4",
        ],
    )

    assert result.exit_code == 0, result.output
    sent_notes = fake.replace_calls[0]["notes"]
    starts = sorted(n["start_time"] for n in sent_notes)
    assert starts == [2.0, 3.0]


def test_retrograde_rejects_non_positive_loop_length(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "retrograde",
            "0",
            "0",
            "--loop-length",
            "0",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def _write_groove_profile(path: Path, *, delta: float = 0.03) -> None:
    slots = [
        {
            "position": index * 0.25,
            "timing_offset": delta if index % 2 == 1 else 0.0,
            "velocity_scale": 1.0,
        }
        for index in range(16)
    ]
    path.write_text(json.dumps({"grid": "1/16", "slots": slots}), encoding="utf-8")


def test_apply_groove_shifts_notes_per_profile(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0, duration=0.25), _note(64, 0.25, duration=0.25)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)
    groove_path = tmp_path / "groove.json"
    _write_groove_profile(groove_path, delta=0.03)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "apply-groove",
            "0",
            "0",
            "--groove-file",
            str(groove_path),
            "--timing-amount",
            "1.0",
        ],
    )

    assert result.exit_code == 0, result.output
    sent_notes = fake.replace_calls[0]["notes"]
    starts = sorted(n["start_time"] for n in sent_notes)
    assert starts == [0.0, 0.28]


def test_apply_groove_rejects_malformed_groove_file(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)
    groove_path = tmp_path / "groove.json"
    groove_path.write_text("not json", encoding="utf-8")

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "apply-groove",
            "0",
            "0",
            "--groove-file",
            str(groove_path),
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_apply_groove_rejects_out_of_range_velocity_amount(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)
    groove_path = tmp_path / "groove.json"
    _write_groove_profile(groove_path)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "apply-groove",
            "0",
            "0",
            "--groove-file",
            str(groove_path),
            "--velocity-amount",
            "1.5",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_round_trip_transforms_strip_note_id_from_replace_payload(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import clip

    groove_path = tmp_path / "groove.json"
    _write_groove_profile(groove_path, delta=0.03)
    commands = [
        ["transpose-in-scale", "0", "0", "--root", "C", "--scale", "major", "--degrees", "1"],
        ["arpeggiate", "0", "0", "--rate", "1/16"],
        ["ratchet", "0", "0", "--division", "2"],
        ["retrograde", "0", "0", "--loop-length", "4"],
        ["apply-groove", "0", "0", "--groove-file", str(groove_path)],
    ]
    for args in commands:
        fake = _FakeClient([_note(60, 0.0, duration=0.25), _note(64, 0.25, duration=0.25)])
        monkeypatch.setattr(clip, "get_client", lambda ctx, fake=fake: fake)

        result = runner.invoke(cli_app, ["--output", "json", "clip", "notes", *args])

        assert result.exit_code == 0, (args, result.output)
        sent_notes = fake.replace_calls[0]["notes"]
        assert sent_notes, args
        assert all("note_id" not in note for note in sent_notes), args


def _arpeggiate_with_seed(runner, cli_app, monkeypatch, seed: str) -> list[int]:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0), _note(64, 0.0), _note(67, 0.0), _note(71, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "arpeggiate",
            "0",
            "0",
            "--mode",
            "random",
            "--seed",
            seed,
        ],
    )
    assert result.exit_code == 0, result.output
    return [note["pitch"] for note in fake.replace_calls[0]["notes"]]


def test_arpeggiate_random_mode_is_reproducible_with_a_seed(runner, cli_app, monkeypatch) -> None:
    first = _arpeggiate_with_seed(runner, cli_app, monkeypatch, "1234")
    second = _arpeggiate_with_seed(runner, cli_app, monkeypatch, "1234")
    other = _arpeggiate_with_seed(runner, cli_app, monkeypatch, "9999")
    assert first == second
    assert sorted(first) == [60, 64, 67, 71]
    assert first != other


def _ratchet_with_seed(runner, cli_app, monkeypatch, seed: str) -> list[float]:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0, duration=4.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "ratchet",
            "0",
            "0",
            "--division",
            "8",
            "--probability",
            "0.5",
            "--seed",
            seed,
        ],
    )
    assert result.exit_code == 0, result.output
    return [note["start_time"] for note in fake.replace_calls[0]["notes"]]


def test_ratchet_probability_is_reproducible_with_a_seed(runner, cli_app, monkeypatch) -> None:
    first = _ratchet_with_seed(runner, cli_app, monkeypatch, "7")
    second = _ratchet_with_seed(runner, cli_app, monkeypatch, "7")
    assert first == second


def test_seed_is_echoed_in_the_command_args(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeClient([_note(60, 0.0)])
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "arpeggiate", "0", "0", "--seed", "5"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["args"]["seed"] == 5
