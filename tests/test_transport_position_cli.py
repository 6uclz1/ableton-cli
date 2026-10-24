from __future__ import annotations

import json

import pytest


class _PositionClientStub:
    """Mimics Live applying the position write only after the request returns."""

    def __init__(self, *, applied_time: float, is_playing: bool = False) -> None:
        self._applied_time = applied_time
        self._is_playing = is_playing
        self.calls: list[str] = []

    def transport_position_set(self, beats: float):  # noqa: ANN201
        self.calls.append("transport_position_set")
        return {"current_time": 0.0, "beat_position": 0.0}

    def transport_rewind(self):  # noqa: ANN201
        self.calls.append("transport_rewind")
        return {"current_time": 12.0, "beat_position": 12.0}

    def song_info(self):  # noqa: ANN201
        self.calls.append("song_info")
        return {
            "tempo": 120.0,
            "is_playing": self._is_playing,
            "current_time": self._applied_time,
            "beat_position": self._applied_time,
            "signature": {"numerator": 4, "denominator": 4},
        }


def _invoke(runner, cli_app, monkeypatch, client, *args: str):  # noqa: ANN202
    from ableton_cli.commands import transport

    monkeypatch.setattr(transport, "get_client", lambda ctx: client)
    result = runner.invoke(cli_app, ["--output", "json", "transport", *args])
    return result, json.loads(result.stdout)


def test_position_set_reports_position_read_back_in_a_later_request(
    runner, cli_app, monkeypatch
) -> None:
    client = _PositionClientStub(applied_time=64.0)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, "position", "set", "64")

    assert result.exit_code == 0
    assert payload["result"] == {"current_time": 64.0, "beat_position": 64.0}
    assert client.calls == ["transport_position_set", "song_info"]


def test_position_set_fails_when_stopped_playhead_did_not_move(
    runner, cli_app, monkeypatch
) -> None:
    client = _PositionClientStub(applied_time=9.0)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, "position", "set", "64")

    assert result.exit_code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert payload["error"]["details"]["mismatches"] == [
        {"attribute": "current_song_time", "requested": 64.0, "actual": 9.0}
    ]


@pytest.mark.parametrize("applied_time", [64.0, 65.5])
def test_position_set_accepts_playhead_advancing_while_playing(
    runner, cli_app, monkeypatch, applied_time: float
) -> None:
    client = _PositionClientStub(applied_time=applied_time, is_playing=True)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, "position", "set", "64")

    assert result.exit_code == 0
    assert payload["result"]["current_time"] == applied_time


def test_position_set_fails_when_playing_playhead_is_before_target(
    runner, cli_app, monkeypatch
) -> None:
    client = _PositionClientStub(applied_time=10.0, is_playing=True)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, "position", "set", "64")

    assert result.exit_code == 2
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_rewind_verifies_read_back(runner, cli_app, monkeypatch) -> None:
    client = _PositionClientStub(applied_time=12.0)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, "rewind")

    assert result.exit_code == 2
    assert payload["error"]["details"]["mismatches"] == [
        {"attribute": "current_song_time", "requested": 0.0, "actual": 12.0}
    ]


class _PlaybackClientStub:
    """Live resumes from the last stop point and only honours a playhead write while playing."""

    def __init__(self, *, playhead: float, last_stop: float, is_playing: bool = False) -> None:
        self.playhead = playhead
        self.last_stop = last_stop
        self.is_playing = is_playing
        self.calls: list[str] = []

    def _start(self) -> dict[str, object]:
        if not self.is_playing:
            self.playhead = self.last_stop
        self.is_playing = True
        return {"is_playing": False}  # Live reports the state before the tick applies it.

    def transport_play(self):  # noqa: ANN201
        self.calls.append("transport_play")
        return self._start()

    def transport_toggle(self):  # noqa: ANN201
        self.calls.append("transport_toggle")
        if self.is_playing:
            self.is_playing = False
            self.last_stop = self.playhead
            return {"is_playing": True}
        return self._start()

    def transport_position_set(self, beats: float):  # noqa: ANN201
        self.calls.append("transport_position_set")
        if self.is_playing:
            self.playhead = beats
        return {"current_time": 0.0, "beat_position": 0.0}

    def song_info(self):  # noqa: ANN201
        self.calls.append("song_info")
        return {
            "tempo": 120.0,
            "is_playing": self.is_playing,
            "current_time": self.playhead,
            "beat_position": self.playhead,
            "signature": {"numerator": 4, "denominator": 4},
        }


@pytest.mark.parametrize("command", ["play", "toggle"])
def test_starting_playback_moves_to_playhead_set_while_stopped(
    runner, cli_app, monkeypatch, command: str
) -> None:
    client = _PlaybackClientStub(playhead=64.0, last_stop=9.0)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, command)

    assert result.exit_code == 0
    assert payload["result"] == {"is_playing": True}
    assert client.playhead == 64.0
    assert client.calls == [
        "song_info",
        f"transport_{command}",
        "transport_position_set",
        "song_info",
    ]


def test_play_while_playing_does_not_move_playhead(runner, cli_app, monkeypatch) -> None:
    client = _PlaybackClientStub(playhead=12.0, last_stop=0.0, is_playing=True)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, "play")

    assert result.exit_code == 0
    assert payload["result"] == {"is_playing": True}
    assert client.playhead == 12.0
    assert "transport_position_set" not in client.calls


def test_toggle_that_stops_playback_reports_stopped(runner, cli_app, monkeypatch) -> None:
    client = _PlaybackClientStub(playhead=12.0, last_stop=0.0, is_playing=True)

    result, payload = _invoke(runner, cli_app, monkeypatch, client, "toggle")

    assert result.exit_code == 0
    assert payload["result"] == {"is_playing": False}
    assert "transport_position_set" not in client.calls
