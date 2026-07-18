from __future__ import annotations

import json
from typing import Any


class _FakeEnvelopeClient:
    def __init__(self) -> None:
        self.set_calls: list[dict[str, Any]] = []
        self.clear_calls: list[dict[str, Any]] = []

    def clip_envelope_set(self, track, clip, device_ref, parameter_ref, points, mode):  # noqa: ANN001, ANN201
        self.set_calls.append(
            {
                "track": track,
                "clip": clip,
                "device_ref": device_ref,
                "parameter_ref": parameter_ref,
                "points": points,
                "mode": mode,
            }
        )
        return {
            "track": track,
            "clip": clip,
            "mode": mode,
            "point_count": len(points),
        }

    def clip_envelope_clear(
        self, track, clip, device_ref=None, parameter_ref=None, clear_all=False
    ):  # noqa: ANN001, ANN201
        self.clear_calls.append(
            {
                "track": track,
                "clip": clip,
                "device_ref": device_ref,
                "parameter_ref": parameter_ref,
                "clear_all": clear_all,
            }
        )
        return {"track": track, "clip": clip, "cleared_all": clear_all}


def test_envelope_set_parses_points_json_and_calls_client(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeEnvelopeClient()
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)
    points_json = json.dumps([{"time": 0.0, "value": 0.1}, {"time": 1.0, "value": 0.9}])

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "envelope",
            "set",
            "0",
            "0",
            "--points-json",
            points_json,
            "--device-index",
            "1",
            "--parameter-index",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert fake.set_calls[0]["points"] == [
        {"time": 0.0, "value": 0.1},
        {"time": 1.0, "value": 0.9},
    ]
    assert fake.set_calls[0]["device_ref"] == {"mode": "index", "index": 1}
    assert fake.set_calls[0]["parameter_ref"] == {"mode": "index", "index": 2}
    assert fake.set_calls[0]["mode"] == "replace"


def test_envelope_set_rejects_malformed_points_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeEnvelopeClient()
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "envelope",
            "set",
            "0",
            "0",
            "--points-json",
            "not json",
            "--device-index",
            "0",
            "--parameter-index",
            "0",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_envelope_shape_generates_points_and_calls_client(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeEnvelopeClient()
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "envelope",
            "shape",
            "0",
            "0",
            "--device-index",
            "0",
            "--parameter-key",
            "filter_cutoff",
            "--shape",
            "ramp",
            "--from",
            "0.1",
            "--to",
            "0.9",
            "--start",
            "0",
            "--length",
            "4",
            "--resolution",
            "8",
        ],
    )

    assert result.exit_code == 0, result.output
    sent_points = fake.set_calls[0]["points"]
    assert len(sent_points) == 8
    assert sent_points[0]["value"] == 0.1
    assert sent_points[-1]["value"] == 0.9
    assert fake.set_calls[0]["parameter_ref"] == {"mode": "key", "key": "filter_cutoff"}


def test_envelope_shape_rejects_unknown_shape(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeEnvelopeClient()
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "envelope",
            "shape",
            "0",
            "0",
            "--parameter-key",
            "filter_cutoff",
            "--shape",
            "triangle",
            "--from",
            "0.1",
            "--to",
            "0.9",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_envelope_clear_single_parameter(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeEnvelopeClient()
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "envelope",
            "clear",
            "0",
            "0",
            "--device-index",
            "1",
            "--parameter-index",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert fake.clear_calls[0]["clear_all"] is False
    assert fake.clear_calls[0]["device_ref"] == {"mode": "index", "index": 1}


def test_envelope_clear_all(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    fake = _FakeEnvelopeClient()
    monkeypatch.setattr(clip, "get_client", lambda ctx: fake)

    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "envelope", "clear", "0", "0", "--all"],
    )

    assert result.exit_code == 0, result.output
    assert fake.clear_calls[0]["clear_all"] is True
    assert fake.clear_calls[0]["device_ref"] is None
