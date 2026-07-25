from __future__ import annotations

import json
import socket
from collections.abc import Callable
from typing import Any

import pytest

from remote_script.AbletonCliRemote.command_backend import PROTOCOL_VERSION
from remote_script.AbletonCliRemote.server import (
    AbletonCommandServer,
    CommandExecutionError,
    _parse_command_request,
)


def test_parse_command_request_accepts_strict_protocol_shape() -> None:
    request = _parse_command_request(
        {
            "type": "command",
            "name": "song_info",
            "args": {},
            "meta": {"request_timeout_ms": 15000},
            "request_id": "request-1",
            "protocol_version": 2,
        }
    )

    assert request == ("request-1", "command", "song_info", {}, {"request_timeout_ms": 15000})


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {
            "type": "command",
            "name": "song_info",
            "args": {},
            "meta": {},
            "request_id": "request-1",
            "protocol_version": 2,
            "extra": "not allowed",
        },
        {
            "type": "command",
            "name": "",
            "args": {},
            "meta": {},
            "request_id": "request-1",
            "protocol_version": 2,
        },
        {
            "type": "command",
            "name": "song_info",
            "args": [],
            "meta": {},
            "request_id": "request-1",
            "protocol_version": 2,
        },
        {
            "type": "command",
            "name": "song_info",
            "args": {},
            "meta": {},
            "request_id": "request-1",
            "protocol_version": True,
        },
    ],
)
def test_parse_command_request_rejects_invalid_protocol_shape(payload: object) -> None:
    with pytest.raises(CommandExecutionError) as exc_info:
        _parse_command_request(payload)

    assert exc_info.value.code == "INVALID_ARGUMENT"


def _start_server(
    executor: Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> tuple[AbletonCommandServer, int]:
    server = AbletonCommandServer(host="127.0.0.1", port=0, command_executor=executor)
    server.start()
    port = server._server.server_address[1]  # noqa: SLF001
    return server, port


def test_handle_returns_invalid_argument_for_malformed_json() -> None:
    def _executor(name: str, args: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("command_executor must not run for malformed JSON")

    server, port = _start_server(_executor)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as sock:
            sock.sendall(b"not json\n")
            with sock.makefile("rb") as file_obj:
                raw = file_obj.readline()
    finally:
        server.stop()

    response = json.loads(raw.decode("utf-8"))

    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_ARGUMENT"


def _request_line(request_id: str, name: str = "ping") -> bytes:
    payload = {
        "type": "command",
        "name": name,
        "args": {},
        "meta": {},
        "request_id": request_id,
        "protocol_version": PROTOCOL_VERSION,
    }
    return (json.dumps(payload) + "\n").encode("utf-8")


def test_handle_processes_multiple_requests_on_one_connection() -> None:
    calls: list[str] = []

    def _executor(name: str, args: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        calls.append(name)
        return {"pong": name}

    server, port = _start_server(_executor)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as sock:
            with sock.makefile("rwb") as file_obj:
                file_obj.write(_request_line("request-1", "ping"))
                file_obj.flush()
                first = json.loads(file_obj.readline().decode("utf-8"))

                file_obj.write(_request_line("request-2", "ping"))
                file_obj.flush()
                second = json.loads(file_obj.readline().decode("utf-8"))
    finally:
        server.stop()

    assert calls == ["ping", "ping"]
    assert first["ok"] is True
    assert first["request_id"] == "request-1"
    assert second["ok"] is True
    assert second["request_id"] == "request-2"


def test_handle_closes_connection_after_malformed_json_line() -> None:
    def _executor(name: str, args: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("command_executor must not run for malformed JSON")

    server, port = _start_server(_executor)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as sock:
            with sock.makefile("rwb") as file_obj:
                file_obj.write(b"not json\n")
                file_obj.flush()
                first = json.loads(file_obj.readline().decode("utf-8"))

                # After the server closes the connection, reading yields a
                # clean EOF on POSIX but may raise ConnectionAbortedError or
                # ConnectionResetError on Windows once the follow-up write
                # has triggered an RST. Both signal the same server behavior.
                try:
                    file_obj.write(_request_line("request-2", "ping"))
                    file_obj.flush()
                    trailing = file_obj.readline()
                except ConnectionError:
                    trailing = b""
    finally:
        server.stop()

    assert first["error"]["code"] == "INVALID_ARGUMENT"
    assert trailing == b""
