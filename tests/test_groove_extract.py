from __future__ import annotations

import pytest

from ableton_cli.audio_analysis.groove import extract_groove
from ableton_cli.beat_grid import parse_grid_to_beats


def test_straight_sixteenths_have_near_zero_timing_offset() -> None:
    grid_beats = parse_grid_to_beats("1/16")
    transients = [(index * grid_beats, 1.0) for index in range(16)]  # 2 bars, straight

    profile = extract_groove(transients, grid="1/16")

    assert profile["grid"] == "1/16"
    assert len(profile["slots"]) == 16
    for slot in profile["slots"]:
        assert slot["timing_offset"] == pytest.approx(0.0, abs=1e-9)
        assert slot["velocity_scale"] == pytest.approx(1.0)


def test_constant_swing_pushes_odd_sixteenths_late() -> None:
    grid_beats = parse_grid_to_beats("1/16")
    delta = 0.03
    transients = []
    for bar_index in range(4):
        for slot_index in range(16):
            position = bar_index * 4.0 + slot_index * grid_beats
            if slot_index % 2 == 1:
                position += delta
            transients.append((position, 1.0))

    profile = extract_groove(transients, grid="1/16")

    for slot in profile["slots"]:
        slot_index = round(slot["position"] / grid_beats)
        if slot_index % 2 == 1:
            assert slot["timing_offset"] == pytest.approx(delta, abs=1e-6)
        else:
            assert slot["timing_offset"] == pytest.approx(0.0, abs=1e-9)


def test_triplet_grid_produces_twelve_slots_per_bar() -> None:
    grid_beats = parse_grid_to_beats("1/8T")
    transients = [(index * grid_beats, 1.0) for index in range(12)]

    profile = extract_groove(transients, grid="1/8T")

    assert len(profile["slots"]) == 12
    for slot in profile["slots"]:
        assert slot["timing_offset"] == pytest.approx(0.0, abs=1e-6)


def test_velocity_scale_is_median_strength_per_slot() -> None:
    grid_beats = parse_grid_to_beats("1/16")
    transients = [
        (0.0, 0.2),
        (4.0, 0.4),
        (8.0, 0.9),
        (grid_beats, 1.0),
    ]

    profile = extract_groove(transients, grid="1/16")

    slot0 = next(slot for slot in profile["slots"] if slot["position"] == pytest.approx(0.0))
    assert slot0["velocity_scale"] == pytest.approx(0.4)


def test_slots_without_transients_default_to_neutral() -> None:
    profile = extract_groove([(0.0, 1.0)], grid="1/16")

    empty_slots = [slot for slot in profile["slots"] if slot["position"] != 0.0]
    assert empty_slots
    for slot in empty_slots:
        assert slot["timing_offset"] == 0.0
        assert slot["velocity_scale"] == 1.0


def test_rejects_negative_transient_position() -> None:
    with pytest.raises(ValueError):
        extract_groove([(-0.1, 1.0)], grid="1/16")


def test_rejects_grid_that_does_not_divide_bar() -> None:
    with pytest.raises(ValueError):
        extract_groove([(0.0, 1.0)], grid="1/16", beats_per_bar=0.0)
