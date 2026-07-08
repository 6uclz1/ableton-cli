from __future__ import annotations

import json

import ableton_cli.watch as watch_module


class _FakeSnapshotClient:
    def __init__(self, snapshots: list[dict]) -> None:
        self._snapshots = snapshots
        self._index = 0

    def session_snapshot(self) -> dict:
        snapshot = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        return snapshot


def _snapshot(tempo: float) -> dict:
    return {
        "song_info": {
            "tempo": tempo,
            "is_playing": True,
            "current_time": 0.0,
            "beat_position": 0.0,
        },
        "session_info": {},
        "tracks_list": {},
        "scenes_list": {},
    }


def test_session_watch_emits_jsonl_lines_for_each_change(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    client = _FakeSnapshotClient([_snapshot(120.0), _snapshot(121.0), _snapshot(122.0)])
    monkeypatch.setattr(session, "get_client", lambda ctx: client)
    monkeypatch.setattr(watch_module.time, "sleep", lambda _seconds: None)

    result = runner.invoke(cli_app, ["session", "watch", "--count", "2"])

    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 2
    for line in lines:
        payload = json.loads(line)
        assert "ts" in payload
        assert "diff" in payload


def test_session_watch_rejects_interval_below_minimum(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    client = _FakeSnapshotClient([_snapshot(120.0)])
    monkeypatch.setattr(session, "get_client", lambda ctx: client)

    result = runner.invoke(cli_app, ["--output", "json", "session", "watch", "--interval-ms", "10"])

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_session_watch_rejects_unknown_scope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    client = _FakeSnapshotClient([_snapshot(120.0)])
    monkeypatch.setattr(session, "get_client", lambda ctx: client)

    result = runner.invoke(cli_app, ["--output", "json", "session", "watch", "--scope", "bogus"])

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
