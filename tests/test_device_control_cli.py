from __future__ import annotations

import json
from typing import Any

import pytest


class _RecordingClient:
    """Records the kwargs every client method receives and echoes them back."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __getattr__(self, name: str):  # noqa: ANN204
        def _method(**kwargs: Any) -> dict[str, Any]:
            self.calls.append((name, kwargs))
            return {"echo": kwargs}

        return _method


@pytest.fixture
def client(monkeypatch) -> _RecordingClient:  # noqa: ANN001
    from ableton_cli.commands import device, return_tracks, song

    recording = _RecordingClient()
    for module in (device, return_tracks, song):
        monkeypatch.setattr(module, "get_client", lambda ctx: recording)
    return recording


def _invoke(runner, cli_app, *args: str):  # noqa: ANN001, ANN202
    return runner.invoke(cli_app, ["--output", "json", *args])


_INDEX_TRACK = {"mode": "index", "index": 0}
_INDEX_DEVICE = {"mode": "index", "index": 1}


def test_device_sidechain_set_sends_type_and_channel(runner, cli_app, client) -> None:
    result = _invoke(
        runner,
        cli_app,
        "device",
        "sidechain",
        "set",
        "--type",
        "1-Kick",
        "--channel",
        "Post FX",
        "--track-index",
        "0",
        "--device-index",
        "1",
    )

    assert result.exit_code == 0, result.output
    assert client.calls == [
        (
            "device_sidechain_set",
            {
                "track_ref": _INDEX_TRACK,
                "device_ref": _INDEX_DEVICE,
                "routing_type": "1-Kick",
                "routing_channel": "Post FX",
            },
        )
    ]


def test_device_sidechain_set_omits_channel_by_default(runner, cli_app, client) -> None:
    result = _invoke(
        runner,
        cli_app,
        "device",
        "sidechain",
        "set",
        "--type",
        "1-Kick",
        "--track-index",
        "0",
        "--device-index",
        "1",
    )

    assert result.exit_code == 0, result.output
    assert client.calls[0][1]["routing_channel"] is None


def test_device_parameter_select_passes_item_and_parameter_ref(runner, cli_app, client) -> None:
    result = _invoke(
        runner,
        cli_app,
        "device",
        "parameter",
        "select",
        "RMS",
        "--track-index",
        "0",
        "--device-index",
        "1",
        "--parameter-name",
        "Model",
    )

    assert result.exit_code == 0, result.output
    name, kwargs = client.calls[0]
    assert name == "device_parameter_select"
    assert kwargs["item"] == "RMS"
    assert kwargs["parameter_ref"] == {"mode": "name", "name": "Model"}


def test_device_parameter_set_display_accepts_negative_values(runner, cli_app, client) -> None:
    result = _invoke(
        runner,
        cli_app,
        "device",
        "parameter",
        "set-display",
        "--track-index",
        "0",
        "--device-index",
        "1",
        "--parameter-index",
        "2",
        "--",
        "-18",
    )

    assert result.exit_code == 0, result.output
    name, kwargs = client.calls[0]
    assert name == "device_parameter_display_set"
    assert kwargs["value"] == -18.0


def test_device_insert_defaults_to_append(runner, cli_app, client) -> None:
    result = _invoke(runner, cli_app, "device", "insert", "Compressor", "--track-name", "Bass")

    assert result.exit_code == 0, result.output
    assert client.calls == [
        (
            "device_insert",
            {
                "track_ref": {"mode": "name", "name": "Bass"},
                "device_name": "Compressor",
                "index": -1,
            },
        )
    ]


def test_device_active_set_parses_boolean(runner, cli_app, client) -> None:
    result = _invoke(
        runner,
        cli_app,
        "device",
        "active",
        "set",
        "false",
        "--track-index",
        "0",
        "--device-index",
        "1",
    )

    assert result.exit_code == 0, result.output
    assert client.calls[0] == (
        "device_active_set",
        {"track_ref": _INDEX_TRACK, "device_ref": _INDEX_DEVICE, "value": False},
    )


def test_device_preset_set_passes_index(runner, cli_app, client) -> None:
    result = _invoke(
        runner,
        cli_app,
        "device",
        "preset",
        "set",
        "2",
        "--track-index",
        "0",
        "--device-index",
        "1",
    )

    assert result.exit_code == 0, result.output
    assert client.calls[0][1]["preset_index"] == 2


def test_device_move_requires_to_index(runner, cli_app, client) -> None:
    result = _invoke(runner, cli_app, "device", "move", "--track-index", "0", "--device-index", "1")

    assert result.exit_code != 0
    assert client.calls == []


def test_return_tracks_create_and_delete(runner, cli_app, client) -> None:
    created = _invoke(runner, cli_app, "return-tracks", "create")
    deleted = _invoke(runner, cli_app, "return-tracks", "delete", "1")

    assert created.exit_code == 0, created.output
    assert deleted.exit_code == 0, deleted.output
    assert client.calls == [
        ("return_track_create", {}),
        ("return_track_delete", {"return_track": 1}),
    ]


@pytest.mark.parametrize(("root", "expected"), [("A", 9), ("F#", 6), ("bb", 10), ("3", 3)])
def test_song_scale_set_parses_root_note(runner, cli_app, client, root, expected) -> None:
    result = _invoke(runner, cli_app, "song", "scale", "set", "--root", root)

    assert result.exit_code == 0, result.output
    assert client.calls == [
        ("song_scale_set", {"root_note": expected, "scale_name": None, "scale_mode": None})
    ]


def test_song_scale_set_passes_name_and_mode(runner, cli_app, client) -> None:
    result = _invoke(runner, cli_app, "song", "scale", "set", "--name", "Dorian", "--no-mode")

    assert result.exit_code == 0, result.output
    assert client.calls == [
        ("song_scale_set", {"root_note": None, "scale_name": "Dorian", "scale_mode": False})
    ]


@pytest.mark.parametrize("root", ["H", "12", "-1"])
def test_song_scale_set_rejects_invalid_root(runner, cli_app, client, root) -> None:
    result = _invoke(runner, cli_app, "song", "scale", "set", "--root", root)

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert client.calls == []


def test_song_scale_set_requires_a_field(runner, cli_app, client) -> None:
    result = _invoke(runner, cli_app, "song", "scale", "set")

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert client.calls == []
