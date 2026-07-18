from __future__ import annotations

import json


def _ref_index(ref) -> int:  # noqa: ANN001
    if ref["mode"] != "index":
        raise AssertionError(f"unexpected ref mode: {ref}")
    return int(ref["index"])


class _FakeDeviceRacksClient:
    def device_chains_list(self, track_ref, device_ref):  # noqa: ANN001, ANN201
        return {
            "track": _ref_index(track_ref),
            "device": _ref_index(device_ref),
            "chains": [
                {
                    "index": 0,
                    "name": "Chain 1",
                    "devices": [
                        {
                            "index": 0,
                            "name": "Utility",
                            "class_name": "AudioEffect",
                            "stable_ref": "device:9",
                        }
                    ],
                }
            ],
        }

    def device_macro_list(self, track_ref, device_ref):  # noqa: ANN001, ANN201
        return {
            "track": _ref_index(track_ref),
            "device": _ref_index(device_ref),
            "macros": [
                {
                    "index": 0,
                    "name": "Macro 1",
                    "value": 0.0,
                    "min": 0.0,
                    "max": 127.0,
                    "stable_ref": "parameter:1",
                }
            ],
        }

    def device_macro_set(self, track_ref, device_ref, macro_index, value):  # noqa: ANN001, ANN201
        return {
            "track": _ref_index(track_ref),
            "device": _ref_index(device_ref),
            "macro_index": macro_index,
            "name": "Macro 1",
            "value": value,
        }


def test_device_chains_list_calls_client_and_returns_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import device

    monkeypatch.setattr(device, "get_client", lambda ctx: _FakeDeviceRacksClient())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "device",
            "chains",
            "list",
            "--track-index",
            "0",
            "--device-index",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["chains"][0]["devices"][0]["name"] == "Utility"


def test_device_macro_list_calls_client(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import device

    monkeypatch.setattr(device, "get_client", lambda ctx: _FakeDeviceRacksClient())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "device",
            "macro",
            "list",
            "--track-index",
            "0",
            "--device-index",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["result"]["macros"][0]["name"] == "Macro 1"


def test_device_macro_set_calls_client_with_index_and_value(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import device

    monkeypatch.setattr(device, "get_client", lambda ctx: _FakeDeviceRacksClient())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "device",
            "macro",
            "set",
            "0",
            "64.0",
            "--track-index",
            "0",
            "--device-index",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["result"]["value"] == 64.0
    assert payload["result"]["macro_index"] == 0


def test_device_chains_list_requires_exactly_one_device_selector(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import device

    monkeypatch.setattr(device, "get_client", lambda ctx: _FakeDeviceRacksClient())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "device", "chains", "list", "--track-index", "0"],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
