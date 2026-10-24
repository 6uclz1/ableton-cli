from __future__ import annotations

import random

import pytest

from ableton_cli.pattern_library import (
    BASS_PATTERNS,
    DRUM_STYLES,
    DRUM_VOICE_PITCHES,
    STEPS_PER_BAR,
    PatternLibraryError,
    bass_pattern_notes,
    drum_pattern_notes,
)


def test_every_style_step_string_is_one_bar_of_sixteenths() -> None:
    for style, voices in DRUM_STYLES.items():
        for voice in voices:
            assert len(voice.steps) == STEPS_PER_BAR, f"{style}/{voice.voice}"
            assert set(voice.steps) <= {"x", "o", "."}, f"{style}/{voice.voice}"
            assert voice.voice in DRUM_VOICE_PITCHES
    for pattern, steps in BASS_PATTERNS.items():
        assert len(steps) == STEPS_PER_BAR, pattern


def test_drum_pattern_is_not_empty_and_uses_drum_pitches() -> None:
    notes = drum_pattern_notes("house", bars=1)
    assert notes
    assert {note["pitch"] for note in notes} <= set(DRUM_VOICE_PITCHES.values())
    assert all(0.0 <= note["start_time"] < 4.0 for note in notes)
    assert all(note["mute"] is False for note in notes)


def test_drum_pattern_repeats_per_bar() -> None:
    one_bar = drum_pattern_notes("dnb", bars=1)
    two_bars = drum_pattern_notes("dnb", bars=2)
    assert len(two_bars) == 2 * len(one_bar)
    assert max(note["start_time"] for note in two_bars) < 8.0


def test_drum_pattern_is_deterministic_without_rng() -> None:
    assert drum_pattern_notes("trap") == drum_pattern_notes("trap")


def test_humanize_is_reproducible_for_the_same_seed() -> None:
    first = drum_pattern_notes("trap", humanize=0.8, rng=random.Random(7))
    second = drum_pattern_notes("trap", humanize=0.8, rng=random.Random(7))
    third = drum_pattern_notes("trap", humanize=0.8, rng=random.Random(8))
    assert first == second
    assert first != third


def test_humanize_without_rng_changes_nothing() -> None:
    assert drum_pattern_notes("trap", humanize=1.0) == drum_pattern_notes("trap")


def test_unknown_style_raises() -> None:
    with pytest.raises(PatternLibraryError):
        drum_pattern_notes("gabber")


def test_invalid_common_arguments_raise() -> None:
    with pytest.raises(PatternLibraryError):
        drum_pattern_notes("house", bars=0)
    with pytest.raises(PatternLibraryError):
        drum_pattern_notes("house", gate=0.0)
    with pytest.raises(PatternLibraryError):
        drum_pattern_notes("house", humanize=1.5)


def test_bass_pattern_follows_one_root_per_bar() -> None:
    notes = bass_pattern_notes("offbeat", root_pitches=[41, 37], bars=4)
    by_bar: dict[int, set[int]] = {}
    for note in notes:
        by_bar.setdefault(int(note["start_time"] // 4.0), set()).add(note["pitch"])
    assert by_bar == {0: {41}, 1: {37}, 2: {41}, 3: {37}}


def test_bass_pattern_bars_default_to_root_count() -> None:
    notes = bass_pattern_notes("root-half", root_pitches=[36, 38, 40])
    assert max(note["start_time"] for note in notes) < 12.0


def test_bass_pattern_rejects_unknown_names_and_empty_roots() -> None:
    with pytest.raises(PatternLibraryError):
        bass_pattern_notes("wobble", root_pitches=[36])
    with pytest.raises(PatternLibraryError):
        bass_pattern_notes("offbeat", root_pitches=[])


def test_bass_note_durations_reach_the_next_hit() -> None:
    notes = bass_pattern_notes("root-half", root_pitches=[36], bars=1, gate=1.0)
    assert [note["start_time"] for note in notes] == [0.0, 2.0]
    assert [note["duration"] for note in notes] == [2.0, 2.0]


def test_out_of_range_pitch_raises() -> None:
    with pytest.raises(PatternLibraryError):
        bass_pattern_notes("offbeat", root_pitches=[200], bars=1)
