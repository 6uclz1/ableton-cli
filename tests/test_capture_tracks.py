from __future__ import annotations

from typing import Any

import pytest

from ableton_cli.capture import capture_tracks
from ableton_cli.errors import AppError

MAIN = {"mode": "main"}


class _FakeLive:
    """Track solo, temporary track, and main-device state for capture_tracks."""

    def __init__(
        self,
        *,
        tracks: list[tuple[str, bool]],
        main_devices_active: list[bool] | None = None,
    ) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.tracks = [{"index": i, "name": n, "solo": s} for i, (n, s) in enumerate(tracks)]
        self.main_devices_active = list(main_devices_active or [])

    def tracks_list(self):  # noqa: ANN201
        return {"tracks": [dict(track) for track in self.tracks]}

    def track_solo_set(self, track_ref, value):  # noqa: ANN001, ANN201
        self.calls.append(("solo", track_ref["index"], value))
        self.tracks[track_ref["index"]]["solo"] = value
        return {"track": track_ref["index"], "solo": value}

    def create_audio_track(self, index=-1):  # noqa: ANN001, ANN201
        self.calls.append(("create_audio_track", index))
        self.tracks.append({"index": len(self.tracks), "name": "Audio", "solo": False})
        return {"index": len(self.tracks) - 1, "name": "Audio", "kind": "audio"}

    def track_volume_set(self, track_ref, value):  # noqa: ANN001, ANN201
        self.calls.append(("volume", track_ref["index"], value))
        return {"track": track_ref["index"], "volume": value}

    def tracks_delete(self, track):  # noqa: ANN001, ANN201
        self.calls.append(("tracks_delete", track))
        self.tracks.pop(track)
        return {"deleted": track}

    def master_devices_list(self):  # noqa: ANN201
        return {
            "devices": [
                {"index": i, "name": f"Device {i}"} for i in range(len(self.main_devices_active))
            ]
        }

    def device_active_get(self, track_ref, device_ref):  # noqa: ANN001, ANN201
        assert track_ref == MAIN
        return {
            "device": device_ref["index"],
            "active": self.main_devices_active[device_ref["index"]],
        }

    def device_active_set(self, track_ref, device_ref, value):  # noqa: ANN001, ANN201
        assert track_ref == MAIN
        self.calls.append(("main_device_active", device_ref["index"], value))
        self.main_devices_active[device_ref["index"]] = value
        return {"device": device_ref["index"], "active": value}


def _fake_capture(monkeypatch, live: _FakeLive, *, fail_on_track: int | None = None) -> None:
    def capture(client, *, track, slot, bars, start, set_routing, wait_fn):  # noqa: ANN001, ANN202
        soloed = [t["name"] for t in live.tracks if t["solo"]]
        live.calls.append(("capture", track, slot, bars, start, set_routing, tuple(soloed)))
        if fail_on_track is not None and soloed == [live.tracks[fail_on_track]["name"]]:
            raise AppError(error_code="INVALID_ARGUMENT", message="capture failed")
        return {"file_path": f"/rec/{soloed[0]}.wav"}

    monkeypatch.setattr("ableton_cli.capture.capture_session", capture)


def test_capture_tracks_solos_each_track_into_a_temporary_capture_track(monkeypatch) -> None:
    live = _FakeLive(tracks=[("Kick", False), ("Bass", False), ("Lead", False)])
    _fake_capture(monkeypatch, live)

    result = capture_tracks(live, tracks=[0, 2], bars=8.0, start=304.0)

    assert live.calls == [
        ("solo", 0, True),
        ("create_audio_track", -1),
        ("volume", 3, 0.0),
        ("capture", 3, 0, 8.0, 304.0, True, ("Kick",)),
        ("tracks_delete", 3),
        ("solo", 0, False),
        ("solo", 2, True),
        ("create_audio_track", -1),
        ("volume", 3, 0.0),
        ("capture", 3, 0, 8.0, 304.0, True, ("Lead",)),
        ("tracks_delete", 3),
        ("solo", 2, False),
    ]
    assert result == {
        "start": 304.0,
        "bars": 8.0,
        "bypassed_main_devices": [],
        "captures": [
            {"track_index": 0, "track_name": "Kick", "label": "Kick", "file_path": "/rec/Kick.wav"},
            {"track_index": 2, "track_name": "Lead", "label": "Lead", "file_path": "/rec/Lead.wav"},
        ],
    }
    assert [track["name"] for track in live.tracks] == ["Kick", "Bass", "Lead"]


def test_capture_tracks_bypasses_only_active_main_devices_and_restores_them(monkeypatch) -> None:
    live = _FakeLive(tracks=[("Kick", False)], main_devices_active=[True, False, True])
    _fake_capture(monkeypatch, live)

    result = capture_tracks(live, tracks=[0], bars=4.0, start=0.0, bypass_main_devices=True)

    device_calls = [call for call in live.calls if call[0] == "main_device_active"]
    assert device_calls == [
        ("main_device_active", 0, False),
        ("main_device_active", 2, False),
        ("main_device_active", 0, True),
        ("main_device_active", 2, True),
    ]
    assert live.calls.index(("main_device_active", 2, False)) < live.calls.index(("solo", 0, True))
    assert result["bypassed_main_devices"] == [0, 2]
    assert live.main_devices_active == [True, False, True]


def test_capture_tracks_restores_solo_devices_and_track_when_capture_fails(monkeypatch) -> None:
    live = _FakeLive(tracks=[("Kick", False), ("Lead", False)], main_devices_active=[True])
    _fake_capture(monkeypatch, live, fail_on_track=1)

    with pytest.raises(AppError) as exc_info:
        capture_tracks(live, tracks=[0, 1], bars=4.0, start=0.0, bypass_main_devices=True)

    assert exc_info.value.message == "capture failed"

    assert [track["name"] for track in live.tracks] == ["Kick", "Lead"]
    assert [track["solo"] for track in live.tracks] == [False, False]
    assert live.main_devices_active == [True]


def test_capture_tracks_labels_duplicate_track_names_by_index(monkeypatch) -> None:
    live = _FakeLive(tracks=[("Synth", False), ("Synth", False)])
    _fake_capture(monkeypatch, live)

    result = capture_tracks(live, tracks=[0, 1], bars=4.0, start=0.0)

    assert [capture["label"] for capture in result["captures"]] == ["0:Synth", "1:Synth"]


@pytest.mark.parametrize(
    ("tracks", "message"),
    [
        ([], "at least one --track-index"),
        ([0, 0], "duplicate track index: 0"),
        ([5], "track index 5 does not exist"),
    ],
)
def test_capture_tracks_rejects_invalid_track_lists(
    monkeypatch, tracks: list[int], message: str
) -> None:
    live = _FakeLive(tracks=[("Kick", False)])
    _fake_capture(monkeypatch, live)

    with pytest.raises(AppError) as exc_info:
        capture_tracks(live, tracks=tracks, bars=4.0, start=0.0)

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert message in exc_info.value.message
    assert live.calls == []


def test_capture_tracks_refuses_when_a_track_is_already_soloed(monkeypatch) -> None:
    live = _FakeLive(tracks=[("Kick", False), ("Pad", True)])
    _fake_capture(monkeypatch, live)

    with pytest.raises(AppError) as exc_info:
        capture_tracks(live, tracks=[0], bars=4.0, start=0.0)

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert exc_info.value.details["soloed_tracks"] == ["Pad"]
    assert live.calls == []


def test_session_capture_tracks_is_blocked_in_read_only_mode(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "--read-only",
            "session",
            "capture-tracks",
            "--track-index",
            "0",
            "--bars",
            "4",
            "--start",
            "8",
        ],
    )

    assert result.exit_code == 20, result.stdout
    assert '"code": "READ_ONLY_VIOLATION"' in result.stdout
