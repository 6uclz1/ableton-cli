from __future__ import annotations

import pytest

from ableton_cli.groove_apply import apply_groove


def _note(pitch: int, start: float, velocity: int = 100, duration: float = 0.25) -> dict:
    return {
        "pitch": pitch,
        "start_time": start,
        "duration": duration,
        "velocity": velocity,
        "mute": False,
    }


def _swing_profile(delta: float = 0.03) -> dict:
    slots = []
    for index in range(16):
        offset = delta if index % 2 == 1 else 0.0
        slots.append({"position": index * 0.25, "timing_offset": offset, "velocity_scale": 1.0})
    return {"grid": "1/16", "slots": slots}


def test_swing_profile_shifts_odd_sixteenth_notes() -> None:
    notes = [_note(60, 0.0), _note(64, 0.25), _note(67, 0.5), _note(72, 0.75)]

    result = apply_groove(notes, _swing_profile(0.03), timing_amount=1.0)

    starts = [note["start_time"] for note in result]
    assert starts == pytest.approx([0.0, 0.28, 0.5, 0.78])


def test_timing_amount_scales_shift() -> None:
    notes = [_note(64, 0.25)]

    result = apply_groove(notes, _swing_profile(0.04), timing_amount=0.5)

    assert result[0]["start_time"] == pytest.approx(0.27)


def test_velocity_amount_zero_leaves_velocities_untouched() -> None:
    profile = {
        "grid": "1/16",
        "slots": [{"position": 0.0, "timing_offset": 0.0, "velocity_scale": 0.3}],
    }
    notes = [_note(60, 0.0, velocity=100)]

    result = apply_groove(notes, profile, timing_amount=0.0, velocity_amount=0.0)

    assert result[0]["velocity"] == 100


def test_velocity_amount_one_applies_full_scale() -> None:
    profile = {
        "grid": "1/16",
        "slots": [{"position": 0.0, "timing_offset": 0.0, "velocity_scale": 0.5}],
    }
    notes = [_note(60, 0.0, velocity=100)]

    result = apply_groove(notes, profile, timing_amount=0.0, velocity_amount=1.0)

    assert result[0]["velocity"] == 50


def test_velocity_clamps_at_upper_bound_127() -> None:
    profile = {
        "grid": "1/16",
        "slots": [{"position": 0.0, "timing_offset": 0.0, "velocity_scale": 2.0}],
    }
    notes = [_note(60, 0.0, velocity=120)]

    result = apply_groove(notes, profile, timing_amount=0.0, velocity_amount=1.0)

    assert result[0]["velocity"] == 127


def test_velocity_clamps_at_lower_bound_1() -> None:
    profile = {
        "grid": "1/16",
        "slots": [{"position": 0.0, "timing_offset": 0.0, "velocity_scale": 0.0}],
    }
    notes = [_note(60, 0.0, velocity=10)]

    result = apply_groove(notes, profile, timing_amount=0.0, velocity_amount=1.0)

    assert result[0]["velocity"] == 1


def test_notes_beyond_first_bar_wrap_to_correct_slot() -> None:
    notes = [_note(64, 4.25)]  # second bar, slot index 1 (odd)

    result = apply_groove(notes, _swing_profile(0.03), timing_amount=1.0)

    assert result[0]["start_time"] == pytest.approx(4.28)


def test_rejects_out_of_range_timing_amount() -> None:
    with pytest.raises(ValueError):
        apply_groove([_note(60, 0.0)], _swing_profile(), timing_amount=1.5)


def test_rejects_out_of_range_velocity_amount() -> None:
    with pytest.raises(ValueError):
        apply_groove([_note(60, 0.0)], _swing_profile(), velocity_amount=-0.1)
