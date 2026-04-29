from __future__ import annotations

import json

import pytest


def test_song_info_contract_accepts_numeric_tempo(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import song

    class _ClientStub:
        def song_info(self):  # noqa: ANN201
            return {"tempo": 123.0}

    monkeypatch.setattr(song, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "song", "info"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["tempo"] == 123.0


def test_song_info_contract_rejects_invalid_result_shape(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import song

    class _ClientStub:
        def song_info(self):  # noqa: ANN201
            return {"tempo": "fast"}

    monkeypatch.setattr(song, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "song", "info"])

    assert result.exit_code == 13
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "PROTOCOL_INVALID_RESPONSE"
    assert payload["error"]["details"]["reason"] == "contract_validation_failed"
    assert isinstance(payload["error"]["details"]["validation_message"], str)


@pytest.mark.parametrize(
    "track_ref",
    [
        {"mode": "unknown"},
        {"mode": "selected", "index": 0},
        {"mode": "index", "index": -1},
        {"mode": "name", "name": ""},
    ],
)
def test_ref_contract_rejects_invalid_discriminated_track_ref(
    track_ref: dict[str, object],
) -> None:
    from ableton_cli.contracts.registry import validate_command_contract
    from ableton_cli.errors import AppError

    with pytest.raises(AppError) as exc_info:
        validate_command_contract(
            command="track volume get",
            args={"track_ref": track_ref},
            result={"track": 0, "volume": 0.5},
        )

    assert exc_info.value.error_code == "PROTOCOL_INVALID_RESPONSE"


def test_ref_contract_accepts_parameter_key_mode() -> None:
    from ableton_cli.contracts.registry import validate_command_contract

    validate_command_contract(
        command="device parameter set",
        args={
            "track_ref": {"mode": "index", "index": 0},
            "device_ref": {"mode": "selected"},
            "parameter_ref": {"mode": "key", "key": "filter_cutoff"},
            "value": 0.5,
        },
        result={
            "track": 0,
            "device": 0,
            "parameter": 0,
            "track_stable_ref": "track:0",
            "device_stable_ref": "device:0",
            "parameter_stable_ref": "parameter:0",
            "value": 0.5,
        },
    )


def test_tracks_list_contract_rejects_non_array_tracks(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import tracks

    class _ClientStub:
        def tracks_list(self):  # noqa: ANN201
            return {"tracks": "not-array"}

    monkeypatch.setattr(tracks, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "tracks", "list"])

    assert result.exit_code == 13
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "PROTOCOL_INVALID_RESPONSE"


def test_doctor_contract_rejects_invalid_summary_structure(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    monkeypatch.setattr(
        setup,
        "run_doctor",
        lambda _settings, *, platform_paths: {  # noqa: ANN001
            "summary": {"pass": "bad", "warn": 0, "fail": 0},
            "checks": [],
        },
    )

    result = runner.invoke(cli_app, ["--output", "json", "doctor"])

    assert result.exit_code == 13
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "PROTOCOL_INVALID_RESPONSE"
