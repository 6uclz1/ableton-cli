from __future__ import annotations

from typing import Any

import pytest

from ableton_cli.capabilities import compute_command_set_hash, required_remote_commands
from ableton_cli.client.ableton_client import AbletonClient
from ableton_cli.config import Settings
from ableton_cli.errors import AppError, ExitCode


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


def _ok_response(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "request_id": request["request_id"],
        "protocol_version": request["protocol_version"],
        "result": result,
        "error": None,
    }


def test_client_rejects_remote_without_required_command(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests: list[dict[str, Any]] = []
    supported_commands = ["ping", "transport_play"]

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        if request["name"] == "ping":
            return _ok_response(
                request,
                {
                    "protocol_version": 2,
                    "remote_script_version": "0.2.0",
                    "supported_commands": supported_commands,
                    "command_set_hash": compute_command_set_hash(supported_commands),
                },
            )
        return _ok_response(request, {"tempo": 120.0})

    monkeypatch.setattr(client.transport, "send", _send)

    with pytest.raises(AppError) as exc_info:
        client.song_info()

    assert exc_info.value.error_code == "REMOTE_SCRIPT_INCOMPATIBLE"
    assert exc_info.value.exit_code == ExitCode.PROTOCOL_MISMATCH
    assert [request["name"] for request in requests] == ["ping"]


def test_client_does_not_retry_read_command_on_timeout(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests: list[dict[str, Any]] = []
    state = {"song_info_calls": 0}
    supported_commands = sorted(required_remote_commands())

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        if request["name"] == "ping":
            return _ok_response(
                request,
                {
                    "protocol_version": 2,
                    "remote_script_version": "0.2.0",
                    "supported_commands": supported_commands,
                    "command_set_hash": compute_command_set_hash(supported_commands),
                },
            )
        if request["name"] == "song_info":
            state["song_info_calls"] += 1
            raise AppError(
                error_code="TIMEOUT",
                message="Timed out while communicating with 127.0.0.1:8765",
                hint="Increase --timeout-ms or verify Ableton Remote Script responsiveness.",
                exit_code=ExitCode.TIMEOUT,
            )
        return _ok_response(request, {})

    monkeypatch.setattr(client.transport, "send", _send)

    with pytest.raises(AppError) as exc_info:
        client.song_info()

    assert exc_info.value.error_code == "TIMEOUT"
    assert [request["name"] for request in requests] == ["ping", "song_info"]


def test_client_does_not_retry_write_command_on_timeout(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests: list[dict[str, Any]] = []
    supported_commands = sorted(required_remote_commands())

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        if request["name"] == "ping":
            return _ok_response(
                request,
                {
                    "protocol_version": 2,
                    "remote_script_version": "0.2.0",
                    "supported_commands": supported_commands,
                    "command_set_hash": compute_command_set_hash(supported_commands),
                },
            )
        if request["name"] == "track_volume_set":
            raise AppError(
                error_code="TIMEOUT",
                message="Timed out while communicating with 127.0.0.1:8765",
                hint="Increase --timeout-ms or verify Ableton Remote Script responsiveness.",
                exit_code=ExitCode.TIMEOUT,
            )
        return _ok_response(request, {})

    monkeypatch.setattr(client.transport, "send", _send)

    with pytest.raises(AppError) as exc_info:
        client.track_volume_set(0, 0.7)

    assert exc_info.value.error_code == "TIMEOUT"
    assert [request["name"] for request in requests] == ["ping", "track_volume_set"]


def test_client_sends_request_timeout_meta(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests: list[dict[str, Any]] = []
    supported_commands = sorted(required_remote_commands())

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        if request["name"] == "ping":
            return _ok_response(
                request,
                {
                    "protocol_version": 2,
                    "remote_script_version": "0.2.0",
                    "supported_commands": supported_commands,
                    "command_set_hash": compute_command_set_hash(supported_commands),
                },
            )
        return _ok_response(request, {"tempo": 128.0})

    monkeypatch.setattr(client.transport, "send", _send)

    client.song_info()

    assert requests[0]["meta"]["request_timeout_ms"] == 15000
    assert requests[1]["meta"]["request_timeout_ms"] == 15000
