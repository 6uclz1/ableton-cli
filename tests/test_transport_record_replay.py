from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ableton_cli.client.transport import RecordingTransport, ReplayTransport
from ableton_cli.errors import AppError, ExitCode


def _write_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    lines = [json.dumps(entry, ensure_ascii=False) for entry in entries]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_replay_transport_returns_recorded_response_for_matching_name_args(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay.jsonl"
    _write_jsonl(
        replay_path,
        [
            {
                "request": {"name": "song_info", "args": {}},
                "response": {
                    "ok": True,
                    "request_id": "recorded-id",
                    "protocol_version": 2,
                    "result": {"tempo": 120.0},
                    "error": None,
                },
            }
        ],
    )

    transport = ReplayTransport(path=str(replay_path))
    payload = {
        "name": "song_info",
        "args": {},
        "request_id": "runtime-id",
        "protocol_version": 2,
    }

    response = transport.send(payload)

    assert response["ok"] is True
    assert response["request_id"] == "runtime-id"
    assert response["result"] == {"tempo": 120.0}


def test_replay_transport_rejects_unmatched_name_or_args(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay.jsonl"
    _write_jsonl(
        replay_path,
        [
            {
                "request": {"name": "song_info", "args": {}},
                "response": {
                    "ok": True,
                    "request_id": "recorded-id",
                    "protocol_version": 2,
                    "result": {"tempo": 120.0},
                    "error": None,
                },
            }
        ],
    )
    transport = ReplayTransport(path=str(replay_path))

    with pytest.raises(AppError) as exc_info:
        transport.send(
            {
                "name": "tracks_list",
                "args": {},
                "request_id": "runtime-id",
                "protocol_version": 2,
            }
        )

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"
    assert exc_info.value.exit_code == ExitCode.PROTOCOL_MISMATCH


def test_recording_transport_writes_request_and_response_entries(tmp_path: Path) -> None:
    record_path = tmp_path / "record.jsonl"

    class _InnerTransport:
        def send(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {"ok": True, "echo": payload}

    transport = RecordingTransport(inner=_InnerTransport(), path=str(record_path))
    request_payload = {"name": "ping", "args": {}, "request_id": "r-1", "protocol_version": 2}

    response = transport.send(request_payload)

    assert response["ok"] is True
    lines = record_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["request"] == request_payload
    assert entry["response"]["ok"] is True
    assert entry["error"] is None


def test_recording_transport_writes_error_entries(tmp_path: Path) -> None:
    record_path = tmp_path / "record.jsonl"

    class _InnerTransport:
        def send(self, payload: dict[str, Any]) -> dict[str, Any]:
            del payload
            raise AppError(
                error_code="TIMEOUT",
                message="timed out",
                hint="retry",
                exit_code=ExitCode.TIMEOUT,
            )

    transport = RecordingTransport(inner=_InnerTransport(), path=str(record_path))
    request_payload = {"name": "ping", "args": {}, "request_id": "r-1", "protocol_version": 2}

    with pytest.raises(AppError) as exc_info:
        transport.send(request_payload)
    assert exc_info.value.error_code == "TIMEOUT"

    lines = record_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["request"] == request_payload
    assert entry["response"] is None
    assert entry["error"]["error_code"] == "TIMEOUT"
