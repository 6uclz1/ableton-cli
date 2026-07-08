from __future__ import annotations

from typing import Any

import pytest

from ableton_cli.capture import capture_session
from ableton_cli.errors import AppError


class _FakeCaptureClient:
    def __init__(
        self,
        *,
        is_audio_track: bool = True,
        current_routing_type: str = "Resampling",
        available_routing_types: list[str] | None = None,
        available_routing_channels: list[str] | None = None,
        tempo: float = 120.0,
        file_path: str | None = "/tmp/capture/Track 1.wav",
    ) -> None:
        self.calls: list[tuple[str, Any]] = []
        self._is_audio_track = is_audio_track
        self._current_routing_type = current_routing_type
        self._available_routing_types = available_routing_types or ["Resampling", "Ext. In"]
        self._available_routing_channels = available_routing_channels or ["1/2"]
        self._tempo = tempo
        self._file_path = file_path

    def get_track_info(self, track_ref):  # noqa: ANN001, ANN201
        self.calls.append(("get_track_info", track_ref))
        return {"is_audio_track": self._is_audio_track, "is_midi_track": not self._is_audio_track}

    def track_routing_input_get(self, track_ref):  # noqa: ANN001, ANN201
        self.calls.append(("track_routing_input_get", track_ref))
        return {
            "current": {"type": self._current_routing_type, "channel": "1/2"},
            "available": {
                "types": self._available_routing_types,
                "channels": self._available_routing_channels,
            },
        }

    def track_routing_input_set(self, track_ref, routing_type, routing_channel):  # noqa: ANN001, ANN201
        self.calls.append(("track_routing_input_set", track_ref, routing_type, routing_channel))
        self._current_routing_type = routing_type
        return {"track": track_ref, "type": routing_type, "channel": routing_channel}

    def track_arm_set(self, track_ref, value):  # noqa: ANN001, ANN201
        self.calls.append(("track_arm_set", track_ref, value))
        return {"track": track_ref, "arm": value}

    def transport_position_set(self, beats):  # noqa: ANN001, ANN201
        self.calls.append(("transport_position_set", beats))
        return {"beats": beats}

    def fire_clip(self, track, clip):  # noqa: ANN001, ANN201
        self.calls.append(("fire_clip", track, clip))
        return {"track": track, "clip": clip, "fired": True}

    def transport_play(self):  # noqa: ANN201
        self.calls.append(("transport_play",))
        return {"playing": True}

    def song_info(self):  # noqa: ANN201
        self.calls.append(("song_info",))
        return {"tempo": self._tempo, "is_playing": True}

    def stop_clip(self, track, clip):  # noqa: ANN001, ANN201
        self.calls.append(("stop_clip", track, clip))
        return {"track": track, "clip": clip, "stopped": True}

    def transport_stop(self):  # noqa: ANN201
        self.calls.append(("transport_stop",))
        return {"playing": False}

    def clip_file_path_get(self, track, clip):  # noqa: ANN001, ANN201
        self.calls.append(("clip_file_path_get", track, clip))
        return {"track": track, "clip": clip, "file_path": self._file_path}


def _waits(recorder: list[float]):  # noqa: ANN201
    def _wait(seconds: float) -> None:
        recorder.append(seconds)

    return _wait


def test_capture_session_call_sequence_and_wait_duration() -> None:
    client = _FakeCaptureClient(tempo=120.0)
    waits: list[float] = []

    result = capture_session(
        client,
        track=0,
        slot=0,
        bars=8,
        wait_fn=_waits(waits),
    )

    call_names = [call[0] for call in client.calls]
    assert call_names == [
        "get_track_info",
        "track_routing_input_get",
        "track_arm_set",
        "transport_position_set",
        "fire_clip",
        "transport_play",
        "song_info",
        "stop_clip",
        "transport_stop",
        "clip_file_path_get",
    ]
    assert waits == [16.0 + 1.0]
    assert result["wait_seconds"] == 16.0
    assert result["file_path"] == "/tmp/capture/Track 1.wav"
    assert result["tempo"] == 120.0


def test_capture_session_sets_routing_when_flag_passed() -> None:
    client = _FakeCaptureClient(current_routing_type="Ext. In")

    capture_session(
        client,
        track=0,
        slot=0,
        bars=1,
        set_routing=True,
        wait_fn=lambda _seconds: None,
    )

    set_calls = [call for call in client.calls if call[0] == "track_routing_input_set"]
    assert len(set_calls) == 1
    assert set_calls[0][2] == "Resampling"


def test_capture_session_rejects_non_audio_track() -> None:
    client = _FakeCaptureClient(is_audio_track=False)

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=1, wait_fn=lambda _seconds: None)

    assert excinfo.value.details["step"] == "validate_track_is_audio"


def test_capture_session_rejects_wrong_routing_without_set_routing_flag() -> None:
    client = _FakeCaptureClient(current_routing_type="Ext. In")

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=1, wait_fn=lambda _seconds: None)

    assert excinfo.value.details["step"] == "check_routing"


def test_capture_session_rejects_resampling_unavailable() -> None:
    client = _FakeCaptureClient(
        current_routing_type="Ext. In",
        available_routing_types=["Ext. In"],
    )

    with pytest.raises(AppError) as excinfo:
        capture_session(
            client, track=0, slot=0, bars=1, set_routing=True, wait_fn=lambda _seconds: None
        )

    assert excinfo.value.details["step"] == "set_routing"


def test_capture_session_rejects_no_recorded_file_path() -> None:
    client = _FakeCaptureClient(file_path=None)

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=1, wait_fn=lambda _seconds: None)

    assert excinfo.value.details["step"] == "read_file_path"


def test_capture_session_rejects_non_positive_bars() -> None:
    client = _FakeCaptureClient()

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=0, wait_fn=lambda _seconds: None)

    assert excinfo.value.details["step"] == "validate_bars"


def test_capture_session_analyze_invokes_analyzer_entry_points(monkeypatch) -> None:
    import ableton_cli.capture as capture_module

    loudness_calls: list[str] = []
    spectrum_calls: list[str] = []
    monkeypatch.setattr(
        capture_module,
        "analyze_loudness",
        lambda path: loudness_calls.append(path) or {"integrated_lufs": -14.0},
    )
    monkeypatch.setattr(
        capture_module,
        "analyze_spectrum",
        lambda path: spectrum_calls.append(path) or {"bands": {}},
    )
    client = _FakeCaptureClient(file_path="/tmp/capture/Track 1.wav")

    result = capture_session(
        client, track=0, slot=0, bars=1, analyze=True, wait_fn=lambda _seconds: None
    )

    assert loudness_calls == ["/tmp/capture/Track 1.wav"]
    assert spectrum_calls == ["/tmp/capture/Track 1.wav"]
    assert result["loudness"] == {"integrated_lufs": -14.0}
    assert result["spectrum"] == {"bands": {}}


def test_capture_session_qa_project_invokes_mastering_qa(monkeypatch) -> None:
    import ableton_cli.capture as capture_module

    qa_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        capture_module,
        "run_mastering_qa",
        lambda project, *, render: qa_calls.append((project, render)) or {"ok": True},
    )
    client = _FakeCaptureClient(file_path="/tmp/capture/Track 1.wav")

    result = capture_session(
        client,
        track=0,
        slot=0,
        bars=1,
        qa_project="./proj/x.json",
        wait_fn=lambda _seconds: None,
    )

    assert qa_calls == [("./proj/x.json", "/tmp/capture/Track 1.wav")]
    assert result["qa"] == {"ok": True}
