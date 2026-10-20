"""Device commands address return-track devices with --return-track-index/--return-track-name."""

from __future__ import annotations

import json
from typing import Any

import pytest


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __getattr__(self, name: str):  # noqa: ANN204
        def _method(**kwargs: Any) -> dict[str, Any]:
            self.calls.append((name, kwargs))
            return _RESULTS.get(name, {"echo": kwargs})

        return _method


# ``device parameter set`` validates its result against a detailed contract.
_RESULTS: dict[str, dict[str, Any]] = {
    "set_device_parameter": {
        "track": {"kind": "return", "index": 1},
        "device": 0,
        "parameter": 1,
        "track_stable_ref": "track:9",
        "device_stable_ref": "device:9",
        "parameter_stable_ref": "parameter:9",
        "value": 0.5,
    }
}


@pytest.fixture
def client(monkeypatch) -> _RecordingClient:  # noqa: ANN001
    from ableton_cli.commands import device

    recording = _RecordingClient()
    monkeypatch.setattr(device, "get_client", lambda ctx: recording)
    return recording


_RETURN_INDEX = {"mode": "return_index", "index": 1}

# Every device command, with the arguments it needs besides the track/device selectors.
_DEVICE_COMMANDS: list[tuple[list[str], bool]] = [
    (["parameter", "set", "0.5", "--parameter-index", "1"], True),
    (["parameter", "set-display", "3000", "--parameter-name", "Frequency"], True),
    (["parameter", "select", "Hall", "--parameter-name", "Algo"], True),
    (["parameters", "list"], True),
    (["chains", "list"], True),
    (["macro", "list"], True),
    (["macro", "set", "0", "64"], True),
    (["active", "get"], True),
    (["active", "set", "false"], True),
    (["preset", "list"], True),
    (["preset", "set", "1"], True),
    (["sidechain", "get"], True),
    (["sidechain", "set", "--type", "1-Kick"], True),
    (["delete"], True),
    (["move", "--to-index", "0"], True),
    (["insert", "Hybrid Reverb"], False),
]


@pytest.mark.parametrize(("args", "needs_device"), _DEVICE_COMMANDS)
def test_every_device_command_accepts_a_return_track_index(
    runner, cli_app, client, args: list[str], needs_device: bool
) -> None:
    device_args = ["--device-index", "0"] if needs_device else []

    result = runner.invoke(
        cli_app,
        ["--output", "json", "device", *args, "--return-track-index", "1", *device_args],
    )

    assert result.exit_code == 0, result.output
    [(_, kwargs)] = client.calls
    assert kwargs["track_ref"] == _RETURN_INDEX


def test_return_track_name_selector(runner, cli_app, client) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "device",
            "parameters",
            "list",
            "--return-track-name",
            "A-Reverb",
            "--device-index",
            "0",
        ],
    )

    assert result.exit_code == 0, result.output
    assert client.calls[0][1]["track_ref"] == {"mode": "return_name", "name": "A-Reverb"}


def test_return_and_regular_selectors_are_exclusive(runner, cli_app, client) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "device",
            "parameters",
            "list",
            "--track-index",
            "0",
            "--return-track-index",
            "0",
            "--device-index",
            "0",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert "--return-track-index" in payload["error"]["hint"]
    assert client.calls == []


def test_negative_return_track_index_is_rejected(runner, cli_app, client) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "device",
            "parameters",
            "list",
            "--return-track-index",
            "-1",
            "--device-index",
            "0",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"
