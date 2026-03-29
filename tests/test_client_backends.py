from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ableton_cli.client.ableton_client import AbletonClient
from ableton_cli.client.backends import LiveBackendClient, RecordingClient, ReplayClient
from ableton_cli.config import Settings
from ableton_cli.errors import AppError, ErrorCode


def _settings() -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8765,
        timeout_ms=15000,
        log_level="INFO",
        log_file=None,
        protocol_version=2,
        config_path="/tmp/ableton-cli-test.toml",
    )


def test_client_uses_live_backend_by_default() -> None:
    client = AbletonClient(_settings())
    assert isinstance(client._backend, LiveBackendClient)


def test_client_uses_recording_backend_with_record_path(tmp_path: Path) -> None:
    client = AbletonClient(_settings(), record_path=str(tmp_path / "record.jsonl"))
    assert isinstance(client._backend, RecordingClient)


def test_client_uses_replay_backend_with_replay_path(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay.jsonl"
    replay_path.write_text("", encoding="utf-8")

    client = AbletonClient(_settings(), replay_path=str(replay_path))
    assert isinstance(client._backend, ReplayClient)


def test_client_dispatch_uses_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AbletonClient(_settings())
    captured: dict[str, Any] = {}

    def _dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
        captured["name"] = name
        captured["args"] = args
        return {"tempo": 123.0}

    monkeypatch.setattr(client._backend, "dispatch", _dispatch)

    result = client.song_info()

    assert result == {"tempo": 123.0}
    assert captured == {"name": "song_info", "args": {}}


def test_client_read_only_stops_dispatch_before_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AbletonClient(_settings(), read_only=True)

    def _dispatch(_name: str, _args: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("backend dispatch must not run for blocked write commands")

    monkeypatch.setattr(client._backend, "dispatch", _dispatch)

    with pytest.raises(AppError) as exc_info:
        client.track_volume_set(0, 0.5)

    assert exc_info.value.error_code == ErrorCode.READ_ONLY_VIOLATION


def test_client_read_only_blocks_song_undo(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AbletonClient(_settings(), read_only=True)

    def _dispatch(_name: str, _args: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("backend dispatch must not run for blocked write commands")

    monkeypatch.setattr(client._backend, "dispatch", _dispatch)

    with pytest.raises(AppError) as exc_info:
        client.song_undo()

    assert exc_info.value.error_code == ErrorCode.READ_ONLY_VIOLATION
