from __future__ import annotations

from collections.abc import Callable
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


def _capture_requests(
    monkeypatch: pytest.MonkeyPatch,
    client: AbletonClient,
) -> list[dict[str, Any]]:
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
        return _ok_response(request, {"ok": True})

    monkeypatch.setattr(client.transport, "send", _send)
    return requests


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


@pytest.mark.parametrize(
    ("runner", "expected_command", "expected_args"),
    [
        (
            lambda client: client.get_clip_notes(
                track=1,
                clip=2,
                start_time=None,
                end_time=4.0,
                pitch=None,
            ),
            "get_clip_notes",
            {"track": 1, "clip": 2, "end_time": 4.0},
        ),
        (
            lambda client: client.replace_clip_notes(
                track=3,
                clip=4,
                notes=[
                    {
                        "pitch": 60,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
                start_time=0.0,
                end_time=None,
                pitch=60,
            ),
            "replace_clip_notes",
            {
                "track": 3,
                "clip": 4,
                "notes": [
                    {
                        "pitch": 60,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
                "start_time": 0.0,
                "pitch": 60,
            },
        ),
        (
            lambda client: client.search_browser_items(
                query="drift",
                path=None,
                item_type="loadable",
                limit=10,
                offset=2,
                exact=True,
                case_sensitive=False,
            ),
            "search_browser_items",
            {
                "query": "drift",
                "item_type": "loadable",
                "limit": 10,
                "offset": 2,
                "exact": True,
                "case_sensitive": False,
            },
        ),
        (
            lambda client: client.search_browser_items(
                query="kit",
                path="drums/Kits",
                item_type="folder",
                limit=20,
                offset=0,
                exact=False,
                case_sensitive=True,
            ),
            "search_browser_items",
            {
                "query": "kit",
                "path": "drums/Kits",
                "item_type": "folder",
                "limit": 20,
                "offset": 0,
                "exact": False,
                "case_sensitive": True,
            },
        ),
    ],
)
def test_client_builds_optional_arguments_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    runner: Callable[[AbletonClient], dict[str, Any]],
    expected_command: str,
    expected_args: dict[str, Any],
) -> None:
    client = AbletonClient(_settings())
    requests = _capture_requests(monkeypatch, client)
    runner(client)

    assert [request["name"] for request in requests] == ["ping", expected_command]
    assert requests[1]["args"] == expected_args


@pytest.mark.parametrize(
    ("runner", "expected_command", "expected_value"),
    [
        (
            lambda client: client.set_device_parameter(track=0, device=1, parameter=2, value=0.3),
            "set_device_parameter",
            0.3,
        ),
        (
            lambda client: client.set_synth_parameter_safe(
                track=0,
                device=1,
                parameter=2,
                value=0.4,
            ),
            "set_synth_parameter_safe",
            0.4,
        ),
        (
            lambda client: client.set_effect_parameter_safe(
                track=0,
                device=1,
                parameter=2,
                value=0.5,
            ),
            "set_effect_parameter_safe",
            0.5,
        ),
    ],
)
def test_client_parameter_commands_share_payload_shape(
    monkeypatch: pytest.MonkeyPatch,
    runner: Callable[[AbletonClient], dict[str, Any]],
    expected_command: str,
    expected_value: float,
) -> None:
    client = AbletonClient(_settings())
    requests = _capture_requests(monkeypatch, client)
    runner(client)

    assert requests[1]["name"] == expected_command
    assert requests[1]["args"] == {
        "track": 0,
        "device": 1,
        "parameter": 2,
        "value": expected_value,
    }
