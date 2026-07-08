from __future__ import annotations

import random

import pytest

from ableton_cli.music_theory import (
    MusicTheoryError,
    arpeggiate,
    bjorklund,
    euclidean_notes,
    ratchet_notes,
    retrograde_notes,
    rotate_pattern,
    scale_pitches,
    transpose_in_scale,
)


def _note(pitch: int, start: float, duration: float = 0.25, velocity: int = 100) -> dict:
    return {
        "pitch": pitch,
        "start_time": start,
        "duration": duration,
        "velocity": velocity,
        "mute": False,
    }


# --- transpose_in_scale -----------------------------------------------------


def test_c_major_transpose_plus_one_degree_e4_to_f4() -> None:
    notes = [_note(64, 0.0)]  # E

    result = transpose_in_scale(notes, root="C", scale="major", degrees=1)

    assert result[0]["pitch"] == 65  # F


def test_transpose_in_scale_snaps_out_of_scale_note_first() -> None:
    # C harmonic minor near C4: 60 62 63 65 67 68 71 (augmented 2nd gap 68->71).
    # 69 sits 1 semitone from 68 and 2 semitones from 71, so it snaps to 68.
    notes = [_note(69, 0.0)]

    result = transpose_in_scale(notes, root="C", scale="harmonic_minor", degrees=0)

    assert result[0]["pitch"] == 68


def test_transpose_in_scale_negative_degrees() -> None:
    notes = [_note(65, 0.0)]  # F

    result = transpose_in_scale(notes, root="C", scale="major", degrees=-1)

    assert result[0]["pitch"] == 64  # E


def test_transpose_in_scale_raises_with_offending_indices_when_out_of_range() -> None:
    notes = [_note(0, 0.0), _note(64, 0.0)]

    with pytest.raises(MusicTheoryError) as excinfo:
        transpose_in_scale(notes, root="C", scale="major", degrees=-1)

    assert excinfo.value.offending_indices == [0]


def test_transpose_in_scale_rejects_unknown_scale() -> None:
    with pytest.raises(ValueError):
        transpose_in_scale([_note(64, 0.0)], root="C", scale="not-a-scale", degrees=1)


def test_transpose_in_scale_rejects_unknown_root() -> None:
    with pytest.raises(ValueError):
        transpose_in_scale([_note(64, 0.0)], root="H", scale="major", degrees=1)


def test_scale_pitches_are_sorted_and_within_bounds() -> None:
    pitches = scale_pitches("C", "major", low=60, high=72)

    assert pitches == [60, 62, 64, 65, 67, 69, 71, 72]


# --- arpeggiate --------------------------------------------------------------


def test_arpeggiate_three_note_chord_at_1_16_spaces_by_quarter_beat() -> None:
    chord = [
        _note(60, 0.0, duration=1.0),
        _note(64, 0.0, duration=1.0),
        _note(67, 0.0, duration=1.0),
    ]

    result = arpeggiate(chord, mode="up", rate="1/16", gate=1.0)

    assert len(result) == 3
    start_times = [note["start_time"] for note in result]
    assert start_times == pytest.approx([0.0, 0.25, 0.5])


def test_arpeggiate_up_orders_ascending_by_pitch() -> None:
    chord = [_note(67, 0.0), _note(60, 0.0), _note(64, 0.0)]

    result = arpeggiate(chord, mode="up", rate="1/16")

    assert [note["pitch"] for note in result] == [60, 64, 67]


def test_arpeggiate_down_orders_descending_by_pitch() -> None:
    chord = [_note(60, 0.0), _note(64, 0.0), _note(67, 0.0)]

    result = arpeggiate(chord, mode="down", rate="1/16")

    assert [note["pitch"] for note in result] == [67, 64, 60]


def test_arpeggiate_gate_scales_duration() -> None:
    chord = [_note(60, 0.0), _note(64, 0.0)]

    result = arpeggiate(chord, mode="up", rate="1/16", gate=0.5)

    assert all(note["duration"] == pytest.approx(0.125) for note in result)


def test_arpeggiate_random_is_deterministic_with_seeded_rng() -> None:
    chord = [_note(60, 0.0), _note(64, 0.0), _note(67, 0.0), _note(72, 0.0)]

    result_a = arpeggiate(chord, mode="random", rate="1/16", rng=random.Random(42))
    result_b = arpeggiate(chord, mode="random", rate="1/16", rng=random.Random(42))

    assert [n["pitch"] for n in result_a] == [n["pitch"] for n in result_b]


def test_arpeggiate_handles_multiple_chords_independently() -> None:
    notes = [_note(60, 0.0), _note(64, 0.0), _note(67, 1.0)]

    result = arpeggiate(notes, mode="up", rate="1/16")

    assert len(result) == 3
    starts = sorted(note["start_time"] for note in result)
    assert starts[-1] == pytest.approx(1.0)


def test_arpeggiate_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        arpeggiate([_note(60, 0.0)], mode="sideways", rate="1/16")


# --- euclidean / bjorklund ----------------------------------------------------


def test_bjorklund_e_5_16_matches_canonical_pattern() -> None:
    pattern = bjorklund(16, 5)

    assert "".join("1" if hit else "0" for hit in pattern) == "1001001001001000"
    assert sum(pattern) == 5
    assert len(pattern) == 16


def test_bjorklund_all_pulses_true() -> None:
    assert bjorklund(4, 4) == [True, True, True, True]


def test_bjorklund_zero_pulses_all_false() -> None:
    assert bjorklund(4, 0) == [False, False, False, False]


def test_bjorklund_rejects_pulses_greater_than_steps() -> None:
    with pytest.raises(ValueError):
        bjorklund(4, 5)


def test_rotate_pattern_shifts_left() -> None:
    pattern = [True, False, False, True]

    assert rotate_pattern(pattern, 1) == [False, False, True, True]


def test_euclidean_notes_places_hits_on_grid() -> None:
    notes = euclidean_notes(pitch=36, steps=16, pulses=5, rotate=0, length=4.0, velocity=100)

    assert len(notes) == 5
    assert notes[0]["start_time"] == pytest.approx(0.0)
    assert all(note["pitch"] == 36 for note in notes)
    assert all(note["velocity"] == 100 for note in notes)


def test_euclidean_notes_rejects_out_of_range_pitch() -> None:
    with pytest.raises(MusicTheoryError):
        euclidean_notes(pitch=200, steps=16, pulses=5, length=4.0)


def test_euclidean_notes_rejects_out_of_range_velocity() -> None:
    with pytest.raises(MusicTheoryError):
        euclidean_notes(pitch=36, steps=16, pulses=5, length=4.0, velocity=0)


# --- ratchet -------------------------------------------------------------------


def test_ratchet_splits_note_into_equal_repeats_at_probability_one() -> None:
    notes = [_note(60, 0.0, duration=1.0)]

    result = ratchet_notes(notes, division=4, probability=1.0)

    assert len(result) == 4
    assert [n["start_time"] for n in result] == pytest.approx([0.0, 0.25, 0.5, 0.75])
    assert all(n["duration"] == pytest.approx(0.25) for n in result)


def test_ratchet_first_repeat_always_included() -> None:
    notes = [_note(60, 0.0, duration=1.0)]

    result = ratchet_notes(notes, division=4, probability=0.0, rng=random.Random(1))

    assert len(result) == 1
    assert result[0]["start_time"] == pytest.approx(0.0)


def test_ratchet_rejects_division_below_one() -> None:
    with pytest.raises(ValueError):
        ratchet_notes([_note(60, 0.0)], division=0)


# --- retrograde ------------------------------------------------------------------


def test_retrograde_reverses_note_order_in_time() -> None:
    notes = [_note(60, 0.0, duration=1.0), _note(64, 1.0, duration=1.0)]

    result = retrograde_notes(notes, loop_length=4.0)

    starts = sorted(note["start_time"] for note in result)
    assert starts == pytest.approx([2.0, 3.0])


def test_retrograde_preserves_pitch_pairing_with_new_start() -> None:
    notes = [_note(60, 0.0, duration=1.0), _note(64, 2.0, duration=1.0)]

    result = retrograde_notes(notes, loop_length=4.0)

    by_pitch = {note["pitch"]: note["start_time"] for note in result}
    assert by_pitch[60] == pytest.approx(3.0)
    assert by_pitch[64] == pytest.approx(1.0)


def test_retrograde_rejects_note_extending_past_loop_length() -> None:
    notes = [_note(60, 3.5, duration=1.0)]

    with pytest.raises(ValueError):
        retrograde_notes(notes, loop_length=4.0)
