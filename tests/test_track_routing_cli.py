from __future__ import annotations

import json

import pytest


class _RoutingClientStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, str, str | None]] = []

    def _set(self, name: str, track_ref, routing_type: str, routing_channel: str | None):  # noqa: ANN001, ANN201
        self.calls.append((name, track_ref, routing_type, routing_channel))
        return {
            "track": 0,
            "current": {"type": routing_type, "channel": routing_channel or ""},
            "available": {"types": [routing_type], "channels": [""]},
        }

    def track_routing_input_set(self, track_ref, routing_type, routing_channel):  # noqa: ANN001, ANN201
        return self._set("input", track_ref, routing_type, routing_channel)

    def track_routing_output_set(self, track_ref, routing_type, routing_channel):  # noqa: ANN001, ANN201
        return self._set("output", track_ref, routing_type, routing_channel)


def _invoke(runner, cli_app, monkeypatch, *args: str):  # noqa: ANN202
    from ableton_cli.commands import track

    client = _RoutingClientStub()
    monkeypatch.setattr(track, "get_client", lambda ctx: client)
    result = runner.invoke(cli_app, ["--output", "json", "track", "routing", *args])
    return result, json.loads(result.stdout), client


@pytest.mark.parametrize("direction", ["input", "output"])
def test_routing_set_without_channel_keeps_live_default(
    runner, cli_app, monkeypatch, direction: str
) -> None:
    result, payload, client = _invoke(
        runner, cli_app, monkeypatch, direction, "set", "--type", "Resampling", "--track-index", "2"
    )

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["args"]["routing_channel"] is None
    assert client.calls == [(direction, {"mode": "index", "index": 2}, "Resampling", None)]


@pytest.mark.parametrize(
    ("option", "value"),
    [("--type", " "), ("--channel", " ")],
)
def test_routing_set_reports_blank_values_as_json_errors(
    runner, cli_app, monkeypatch, option: str, value: str
) -> None:
    args = {"--type": "Master", option: value}
    flat = [item for pair in args.items() for item in pair]

    result, payload, client = _invoke(
        runner, cli_app, monkeypatch, "input", "set", *flat, "--track-index", "0"
    )

    assert result.exit_code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert client.calls == []
