from __future__ import annotations

import json
import socket
from collections.abc import Callable
from typing import Any

import pytest

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

    assert request == ("request-1", "song_info", {}, {"request_timeout_ms": 15000})


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
