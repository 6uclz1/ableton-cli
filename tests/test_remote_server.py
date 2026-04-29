from __future__ import annotations

import pytest

from remote_script.AbletonCliRemote.server import CommandExecutionError, _parse_command_request


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
