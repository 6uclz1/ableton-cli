from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from test_live_backend import _SurfaceStub

from remote_script.AbletonCliRemote.command_backend import CommandError
from remote_script.AbletonCliRemote.live_backend import LiveBackend


class _RangeEnforcingClip:
    """Clip fake that rejects start >= end on every single write, as Live does.

    The optional flags reproduce writes Live accepts without raising but does not apply.
    """

    def __init__(
        self,
        start: float,
        end: float,
        *,
        ignore_start_marker_past_loop_end: bool = False,
        max_loop_end: float | None = None,
    ) -> None:
        self._ignore_start_marker_past_loop_end = ignore_start_marker_past_loop_end
        self._max_loop_end = max_loop_end
        self.name = "Range"
        self.is_audio_clip = True
        self.is_midi_clip = False
        self.start_time = 0.0
        self.looping = True
        self.warping = True
        self.warp_mode = 0
        self._start_marker = float(start)
        self._end_marker = float(end)
        self._loop_start = float(start)
        self._loop_end = float(end)

    @property
    def length(self) -> float:
        return self._loop_end - self._loop_start

    @property
    def start_marker(self) -> float:
        return self._start_marker

    @start_marker.setter
    def start_marker(self, value: float) -> None:
        if value >= self._end_marker:
            raise RuntimeError("StartMarker out of range")
        if self._ignore_start_marker_past_loop_end and value > self._loop_end:
            return
        self._start_marker = value

    @property
    def end_marker(self) -> float:
        return self._end_marker

    @end_marker.setter
    def end_marker(self, value: float) -> None:
        if value <= self._start_marker:
            raise RuntimeError("EndMarker out of range")
        self._end_marker = value

    @property
    def loop_start(self) -> float:
        return self._loop_start

    @loop_start.setter
    def loop_start(self, value: float) -> None:
        if value >= self._loop_end:
            raise RuntimeError("LoopStart out of range")
        self._loop_start = value

    @property
    def loop_end(self) -> float:
        return self._loop_end

    @loop_end.setter
    def loop_end(self, value: float) -> None:
        if value <= self._loop_start:
            raise RuntimeError("LoopEnd out of range")
        if self._max_loop_end is not None:
            value = min(value, self._max_loop_end)
        self._loop_end = value


def _session_backend(clip: _RangeEnforcingClip) -> LiveBackend:
    backend = LiveBackend(_SurfaceStub())
    backend.context._clip_slot_at(0, 0).clip = clip
    return backend


def _arrangement_backend(clip: _RangeEnforcingClip) -> LiveBackend:
    backend = LiveBackend(_SurfaceStub())
    backend.context._track_at(0).arrangement_clips = [clip]
    return backend


_RangeSetter = Callable[[LiveBackend, float, float], Any]

_CASES: dict[str, tuple[Callable[[_RangeEnforcingClip], LiveBackend], _RangeSetter, str, str]] = {
    "session-marker": (
        _session_backend,
        lambda backend, start, end: backend.clip_marker_set(0, 0, start, end),
        "start_marker",
        "end_marker",
    ),
    "session-loop": (
        _session_backend,
        lambda backend, start, end: backend.clip_loop_set(0, 0, start, end, True),
        "loop_start",
        "loop_end",
    ),
    "arrangement-marker": (
        _arrangement_backend,
        lambda backend, start, end: backend.arrangement_clip_marker_set(0, 0, start, end),
        "start_marker",
        "end_marker",
    ),
    "arrangement-loop": (
        _arrangement_backend,
        lambda backend, start, end: backend.arrangement_clip_loop_set(0, 0, start, end, True),
        "loop_start",
        "loop_end",
    ),
}


@pytest.mark.parametrize("case", sorted(_CASES))
@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(1.0, 1.5, id="forward-past-current-end"),
        pytest.param(0.5, 1.0, id="start-equals-current-end"),
        pytest.param(0.0, 0.25, id="backward-shrink"),
        pytest.param(0.25, 2.0, id="overlapping-widen"),
    ],
)
def test_clip_range_set_moves_range_without_violating_start_before_end(
    case: str, start: float, end: float
) -> None:
    make_backend, set_range, start_attr, end_attr = _CASES[case]
    clip = _RangeEnforcingClip(start=0.0, end=0.5)
    backend = make_backend(clip)

    set_range(backend, start, end)

    assert getattr(clip, start_attr) == start
    assert getattr(clip, end_attr) == end


_MARKER_CASES = sorted(case for case in _CASES if case.endswith("-marker"))
_LOOP_CASES = sorted(case for case in _CASES if case.endswith("-loop"))


@pytest.mark.parametrize("case", _MARKER_CASES)
def test_clip_marker_set_fails_when_live_ignores_start_marker_past_loop_end(case: str) -> None:
    make_backend, set_range, _start_attr, _end_attr = _CASES[case]
    clip = _RangeEnforcingClip(start=0.0, end=0.5, ignore_start_marker_past_loop_end=True)
    backend = make_backend(clip)

    with pytest.raises(CommandError) as exc_info:
        set_range(backend, 1.0, 1.5)

    error = exc_info.value
    assert error.code == "INVALID_ARGUMENT"
    assert "start_marker" in error.message
    assert error.hint is not None and "loop" in error.hint
    assert error.details == {
        "mismatches": [{"attribute": "start_marker", "requested": 1.0, "actual": 0.0}]
    }


@pytest.mark.parametrize("case", _MARKER_CASES)
def test_clip_marker_set_succeeds_after_loop_is_moved_first(case: str) -> None:
    make_backend, set_range, _start_attr, _end_attr = _CASES[case]
    clip = _RangeEnforcingClip(start=0.0, end=0.5, ignore_start_marker_past_loop_end=True)
    backend = make_backend(clip)
    clip.loop_end = 1.5
    clip.loop_start = 1.0

    set_range(backend, 1.0, 1.5)

    assert (clip.start_marker, clip.end_marker) == (1.0, 1.5)


@pytest.mark.parametrize("case", _LOOP_CASES)
def test_clip_loop_set_fails_when_live_clamps_loop_end(case: str) -> None:
    make_backend, set_range, _start_attr, _end_attr = _CASES[case]
    clip = _RangeEnforcingClip(start=0.0, end=0.5, max_loop_end=1.25)
    backend = make_backend(clip)

    with pytest.raises(CommandError) as exc_info:
        set_range(backend, 1.0, 1.5)

    error = exc_info.value
    assert error.code == "INVALID_ARGUMENT"
    assert "loop_end" in error.message
    assert error.details == {
        "mismatches": [{"attribute": "loop_end", "requested": 1.5, "actual": 1.25}]
    }
