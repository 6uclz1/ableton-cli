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
        signature: tuple[int, int] = (4, 4),
        file_path: str | None = "/tmp/capture/Track 1.wav",
        stop_beat: float = 0.0,
    ) -> None:
        self.calls: list[tuple[str, Any]] = []
        self._is_audio_track = is_audio_track
        self._current_routing_type = current_routing_type
        self._available_routing_types = available_routing_types or ["Resampling", "Ext. In"]
        self._available_routing_channels = available_routing_channels or ["1/2"]
        self._tempo = tempo
        self._signature = signature
        self._file_path = file_path
        self._stop_beat = stop_beat
        self._stopped = False

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
        numerator, denominator = self._signature
        return {
            "tempo": self._tempo,
            "is_playing": not self._stopped,
            "current_time": self._stop_beat if self._stopped else 0.0,
            "signature": {"numerator": numerator, "denominator": denominator},
        }

    def stop_clip(self, track, clip):  # noqa: ANN001, ANN201
        self.calls.append(("stop_clip", track, clip))
        return {"track": track, "clip": clip, "stopped": True}

    def transport_stop(self):  # noqa: ANN201
        self.calls.append(("transport_stop",))
        self._stopped = True
        return {"playing": False}

    def clip_file_path_get(self, track, clip):  # noqa: ANN001, ANN201
        self.calls.append(("clip_file_path_get", track, clip))
        return {"track": track, "clip": clip, "file_path": self._file_path}


def _recorded_from(start: float, *, stop_beat: float, tempo: float = 120.0):  # noqa: ANN202
    """A file-duration reader whose recording began at ``start`` and ended at ``stop_beat``."""
    return lambda _path: (stop_beat - start) * 60.0 / tempo


def _client_recording_from(start: float, **kwargs):  # noqa: ANN003, ANN202
    stop_beat = start + 64.0
    return _FakeCaptureClient(stop_beat=stop_beat, **kwargs), _recorded_from(
        start, stop_beat=stop_beat, tempo=kwargs.get("tempo", 120.0)
    )


def _waits(recorder: list[float]):  # noqa: ANN201
    def _wait(seconds: float) -> None:
        recorder.append(seconds)

    return _wait


def test_capture_session_call_sequence_and_wait_duration() -> None:
    client, recorded_seconds = _client_recording_from(32.0, tempo=120.0)
    waits: list[float] = []

    result = capture_session(
        client,
        track=0,
        slot=0,
        bars=8,
        start=32.0,
        wait_fn=_waits(waits),
        recorded_seconds_fn=recorded_seconds,
    )

    call_names = [call[0] for call in client.calls]
    assert call_names == [
        "get_track_info",
        "track_routing_input_get",
        "song_info",
        "track_arm_set",
        "transport_play",
        "transport_position_set",
        "fire_clip",
        "stop_clip",
        "transport_stop",
        "song_info",
        "clip_file_path_get",
    ]
    # One bar of pre-roll plus the 8 captured bars, at 2 s per bar.
    assert waits == [2.0 + 16.0 + 1.0]
    assert result["wait_seconds"] == 16.0
    assert result["file_path"] == "/tmp/capture/Track 1.wav"
    assert result["tempo"] == 120.0
    assert result["recorded_start_beat"] == 32.0


@pytest.mark.parametrize(("signature", "pre_roll_beat"), [((4, 4), 28.0), ((3, 4), 29.0)])
def test_capture_session_moves_the_playhead_one_bar_before_start_while_playing(
    signature: tuple[int, int], pre_roll_beat: float
) -> None:
    # Live ignores a playhead moved while stopped, and firing a clip from a stopped
    # transport restarts the song at 0, so the playhead moves after playback starts.
    # The clip fires one bar early so launch quantization starts recording at start.
    client, recorded_seconds = _client_recording_from(32.0, signature=signature)

    capture_session(
        client,
        track=0,
        slot=0,
        bars=1,
        start=32.0,
        wait_fn=lambda _seconds: None,
        recorded_seconds_fn=recorded_seconds,
    )

    names = [call[0] for call in client.calls]
    assert names.index("transport_play") < names.index("transport_position_set")
    assert names.index("transport_position_set") < names.index("fire_clip")
    assert ("transport_position_set", pre_roll_beat) in client.calls


def test_capture_session_needs_one_bar_of_pre_roll_before_start() -> None:
    client = _FakeCaptureClient()

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=1, start=2.0, wait_fn=lambda _s: None)

    assert excinfo.value.details["step"] == "validate_start"
    assert "transport_play" not in [call[0] for call in client.calls]


def test_capture_session_fails_when_recording_did_not_begin_at_start() -> None:
    # Recording began a bar late (e.g. launch quantization set to 2 bars).
    client = _FakeCaptureClient(stop_beat=100.0)

    with pytest.raises(AppError) as excinfo:
        capture_session(
            client,
            track=0,
            slot=0,
            bars=1,
            start=32.0,
            wait_fn=lambda _s: None,
            recorded_seconds_fn=_recorded_from(36.0, stop_beat=100.0),
        )

    assert excinfo.value.details["step"] == "verify_recorded_start"
    assert excinfo.value.details["recorded_start_beat"] == 36.0
    assert excinfo.value.details["requested_start_beat"] == 32.0


def test_capture_session_sets_routing_when_flag_passed() -> None:
    client, recorded_seconds = _client_recording_from(4.0, current_routing_type="Ext. In")

    capture_session(
        client,
        track=0,
        slot=0,
        bars=1,
        start=4.0,
        set_routing=True,
        wait_fn=lambda _seconds: None,
        recorded_seconds_fn=recorded_seconds,
    )

    set_calls = [call for call in client.calls if call[0] == "track_routing_input_set"]
    assert len(set_calls) == 1
    assert set_calls[0][2] == "Resampling"
    # Channel must be omitted: valid channels change with the routing type,
    # so Live's auto-selected default is the only correct choice.
    assert set_calls[0][3] is None


def test_capture_session_rejects_non_audio_track() -> None:
    client = _FakeCaptureClient(is_audio_track=False)

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=1, start=4.0, wait_fn=lambda _seconds: None)

    assert excinfo.value.details["step"] == "validate_track_is_audio"


def test_capture_session_rejects_wrong_routing_without_set_routing_flag() -> None:
    client = _FakeCaptureClient(current_routing_type="Ext. In")

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=1, start=4.0, wait_fn=lambda _seconds: None)

    assert excinfo.value.details["step"] == "check_routing"


def test_capture_session_rejects_resampling_unavailable() -> None:
    client = _FakeCaptureClient(
        current_routing_type="Ext. In",
        available_routing_types=["Ext. In"],
    )

    with pytest.raises(AppError) as excinfo:
        capture_session(
            client,
            track=0,
            slot=0,
            bars=1,
            start=4.0,
            set_routing=True,
            wait_fn=lambda _seconds: None,
        )

    assert excinfo.value.details["step"] == "set_routing"


def test_capture_session_rejects_no_recorded_file_path() -> None:
    client = _FakeCaptureClient(file_path=None)

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=1, start=4.0, wait_fn=lambda _seconds: None)

    assert excinfo.value.details["step"] == "read_file_path"


def test_capture_session_rejects_non_positive_bars() -> None:
    client = _FakeCaptureClient()

    with pytest.raises(AppError) as excinfo:
        capture_session(client, track=0, slot=0, bars=0, start=4.0, wait_fn=lambda _seconds: None)

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
    client, recorded_seconds = _client_recording_from(4.0)

    result = capture_session(
        client,
        track=0,
        slot=0,
        bars=1,
        start=4.0,
        analyze=True,
        wait_fn=lambda _seconds: None,
        recorded_seconds_fn=recorded_seconds,
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
    client, recorded_seconds = _client_recording_from(4.0)

    result = capture_session(
        client,
        track=0,
        slot=0,
        bars=1,
        start=4.0,
        qa_project="./proj/x.json",
        wait_fn=lambda _seconds: None,
        recorded_seconds_fn=recorded_seconds,
    )

    assert qa_calls == [("./proj/x.json", "/tmp/capture/Track 1.wav")]
    assert result["qa"] == {"ok": True}
