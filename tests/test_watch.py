from __future__ import annotations

import pytest

from ableton_cli.watch import build_watch_snapshot, run_watch_loop, strip_volatile


class _FakeSnapshotClient:
    def __init__(self, snapshots: list[dict]) -> None:
        self._snapshots = list(snapshots)
        self._index = 0

    def session_snapshot(self) -> dict:
        snapshot = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        return snapshot


def _full_snapshot(tempo: float = 120.0, current_time: float = 0.0) -> dict:
    return {
        "song_info": {
            "tempo": tempo,
            "is_playing": True,
            "current_time": current_time,
            "beat_position": current_time,
        },
        "session_info": {"track_count": 2},
        "tracks_list": {"tracks": [{"index": 0, "name": "Track 1"}]},
        "scenes_list": {"scenes": [{"index": 0, "name": "Intro"}]},
    }


# --- build_watch_snapshot / strip_volatile -----------------------------------


def test_build_watch_snapshot_scope_song_includes_only_song_info() -> None:
    client = _FakeSnapshotClient([_full_snapshot()])

    snapshot = build_watch_snapshot(client, "song")

    assert set(snapshot) == {"song_info"}


def test_build_watch_snapshot_scope_all_includes_everything() -> None:
    client = _FakeSnapshotClient([_full_snapshot()])

    snapshot = build_watch_snapshot(client, "all")

    assert set(snapshot) == {"song_info", "session_info", "tracks_list", "scenes_list"}


def test_build_watch_snapshot_rejects_unknown_scope() -> None:
    client = _FakeSnapshotClient([_full_snapshot()])

    with pytest.raises(ValueError):
        build_watch_snapshot(client, "bogus")


def test_strip_volatile_removes_position_fields_by_default() -> None:
    snapshot = build_watch_snapshot(_FakeSnapshotClient([_full_snapshot()]), "song")

    stripped = strip_volatile(snapshot, include_position=False)

    assert "current_time" not in stripped["song_info"]
    assert "beat_position" not in stripped["song_info"]
    assert stripped["song_info"]["tempo"] == 120.0


def test_strip_volatile_keeps_position_fields_when_included() -> None:
    snapshot = build_watch_snapshot(_FakeSnapshotClient([_full_snapshot()]), "song")

    kept = strip_volatile(snapshot, include_position=True)

    assert "current_time" in kept["song_info"]


# --- run_watch_loop ------------------------------------------------------------


def _bounded_sleep(max_calls: int) -> tuple[list[float], object]:
    calls: list[float] = []

    def _sleep(seconds: float) -> None:
        calls.append(seconds)
        if len(calls) >= max_calls:
            raise _StopPolling

    return calls, _sleep


class _StopPolling(Exception):
    pass


def test_no_output_when_consecutive_snapshots_are_equal() -> None:
    client = _FakeSnapshotClient([_full_snapshot(), _full_snapshot(), _full_snapshot()])
    emitted: list[dict] = []
    calls, bounded_sleep = _bounded_sleep(3)

    with pytest.raises(_StopPolling):
        run_watch_loop(
            client,
            scope="song",
            interval_seconds=0.5,
            count=5,
            include_position=False,
            emit=emitted.append,
            sleep_fn=bounded_sleep,
            time_fn=lambda: 1000.0,
        )

    assert len(calls) == 3
    assert emitted == []


def test_emits_one_line_when_tempo_changes() -> None:
    client = _FakeSnapshotClient([_full_snapshot(tempo=120.0), _full_snapshot(tempo=130.0)])
    emitted: list[dict] = []

    run_watch_loop(
        client,
        scope="song",
        interval_seconds=0.5,
        count=1,
        include_position=False,
        emit=emitted.append,
        sleep_fn=lambda _seconds: None,
        time_fn=lambda: 42.0,
    )

    assert len(emitted) == 1
    assert emitted[0]["ts"] == 42.0
    assert emitted[0]["diff"]["changed"]["song_info"]["tempo"] == {"from": 120.0, "to": 130.0}


def test_count_stops_after_n_diffs() -> None:
    snapshots = [
        _full_snapshot(tempo=120.0),
        _full_snapshot(tempo=121.0),
        _full_snapshot(tempo=122.0),
        _full_snapshot(tempo=123.0),
    ]
    client = _FakeSnapshotClient(snapshots)
    emitted: list[dict] = []

    run_watch_loop(
        client,
        scope="song",
        interval_seconds=0.5,
        count=2,
        include_position=False,
        emit=emitted.append,
        sleep_fn=lambda _seconds: None,
        time_fn=lambda: 1.0,
    )

    assert len(emitted) == 2


def test_position_excluded_by_default_does_not_trigger_diff() -> None:
    client = _FakeSnapshotClient(
        [_full_snapshot(current_time=0.0), _full_snapshot(current_time=4.0)]
    )
    emitted: list[dict] = []
    calls, bounded_sleep = _bounded_sleep(3)

    with pytest.raises(_StopPolling):
        run_watch_loop(
            client,
            scope="song",
            interval_seconds=0.5,
            count=1,
            include_position=False,
            emit=emitted.append,
            sleep_fn=bounded_sleep,
            time_fn=lambda: 1.0,
        )

    assert len(calls) == 3
    assert emitted == []


def test_position_included_triggers_diff_when_time_moves() -> None:
    client = _FakeSnapshotClient(
        [_full_snapshot(current_time=0.0), _full_snapshot(current_time=4.0)]
    )
    emitted: list[dict] = []

    run_watch_loop(
        client,
        scope="song",
        interval_seconds=0.5,
        count=1,
        include_position=True,
        emit=emitted.append,
        sleep_fn=lambda _seconds: None,
        time_fn=lambda: 1.0,
    )

    assert len(emitted) == 1
    assert "current_time" in emitted[0]["diff"]["changed"]["song_info"]


def test_scope_transport_only_diffs_song_info() -> None:
    client = _FakeSnapshotClient([_full_snapshot(tempo=120.0), _full_snapshot(tempo=125.0)])
    emitted: list[dict] = []

    run_watch_loop(
        client,
        scope="transport",
        interval_seconds=0.5,
        count=1,
        include_position=False,
        emit=emitted.append,
        sleep_fn=lambda _seconds: None,
        time_fn=lambda: 1.0,
    )

    assert set(emitted[0]["diff"]["changed"]) == {"song_info"}
