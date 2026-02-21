from __future__ import annotations

from ableton_cli.output import error_payload, format_human_result, success_payload


def test_success_payload_shape() -> None:
    payload = success_payload("ping", {}, {"tempo": 120})
    assert payload["ok"] is True
    assert payload["command"] == "ping"
    assert payload["args"] == {}
    assert payload["result"] == {"tempo": 120}
    assert payload["error"] is None


def test_error_payload_shape() -> None:
    payload = error_payload("ping", {}, "ABLETON_NOT_REACHABLE", "no route", "start live")
    assert payload["ok"] is False
    assert payload["command"] == "ping"
    assert payload["args"] == {}
    assert payload["result"] is None
    assert payload["error"]["code"] == "ABLETON_NOT_REACHABLE"
    assert payload["error"]["message"] == "no route"
    assert payload["error"]["hint"] == "start live"


def test_human_result_format_for_mapping() -> None:
    text = format_human_result("song info", {"tempo": 120.0})
    assert "OK: song info" in text
    assert '"tempo": 120.0' in text
