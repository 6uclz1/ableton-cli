from __future__ import annotations

import json


class _FakeCaptureClient:
    def get_track_info(self, track_ref):  # noqa: ANN001, ANN201
        return {"is_audio_track": True, "is_midi_track": False}

    def track_routing_input_get(self, track_ref):  # noqa: ANN001, ANN201
        return {
            "current": {"type": "Resampling", "channel": "1/2"},
            "available": {"types": ["Resampling"], "channels": ["1/2"]},
        }

    def track_routing_input_set(self, track_ref, routing_type, routing_channel):  # noqa: ANN001, ANN201
        return {}

    def track_arm_set(self, track_ref, value):  # noqa: ANN001, ANN201
        return {}

    def transport_position_set(self, beats):  # noqa: ANN001, ANN201
        return {}

    def fire_clip(self, track, clip):  # noqa: ANN001, ANN201
        return {"fired": True}

    def transport_play(self):  # noqa: ANN201
        return {}

    def song_info(self):  # noqa: ANN201
        return {"tempo": 120.0}

    def stop_clip(self, track, clip):  # noqa: ANN001, ANN201
        return {}

    def transport_stop(self):  # noqa: ANN201
        return {}

    def clip_file_path_get(self, track, clip):  # noqa: ANN001, ANN201
        return {"track": track, "clip": clip, "file_path": "/tmp/capture/Track 1.wav"}


def test_session_capture_calls_through_and_returns_file_path(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _FakeCaptureClient())
    monkeypatch.setattr("ableton_cli.capture.time.sleep", lambda _seconds: None)

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "session",
            "capture",
            "--track-index",
            "0",
            "--slot",
            "0",
            "--bars",
            "4",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["file_path"] == "/tmp/capture/Track 1.wav"
    assert payload["result"]["wait_seconds"] == 8.0


def test_session_capture_rejects_non_positive_bars(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _FakeCaptureClient())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "session",
            "capture",
            "--track-index",
            "0",
            "--slot",
            "0",
            "--bars",
            "0",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
