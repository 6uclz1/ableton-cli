from __future__ import annotations

import json


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
