from __future__ import annotations

import pytest

from ableton_cli.harmony import (
    HarmonyError,
    parse_chord_symbol,
    parse_key,
    parse_progression,
    progression_notes,
    voice_chord,
    voice_lead,
)


def pitch_classes(symbol: str) -> list[int]:
    return list(parse_chord_symbol(symbol).pitch_classes)


def test_parse_triads() -> None:
    assert pitch_classes("C") == [0, 4, 7]
    assert pitch_classes("Cm") == [0, 3, 7]
    assert pitch_classes("Cdim") == [0, 3, 6]
    assert pitch_classes("Caug") == [0, 4, 8]
    assert pitch_classes("Csus4") == [0, 5, 7]
    assert pitch_classes("Csus2") == [0, 2, 7]


def test_parse_sevenths_and_extensions() -> None:
    assert pitch_classes("Cmaj7") == [0, 4, 7, 11]
    assert pitch_classes("C7") == [0, 4, 7, 10]
    assert pitch_classes("Cm7") == [0, 3, 7, 10]
    assert pitch_classes("Cm9") == [0, 3, 7, 10, 2]


def test_parse_half_diminished_with_accidental_root() -> None:
    chord = parse_chord_symbol("F#m7b5")
    assert chord.root == 6
    assert list(chord.pitch_classes) == [6, 9, 0, 4]


def test_parse_altered_thirteenth() -> None:
    chord = parse_chord_symbol("Bb13#11")
    # Bb D F Ab C E G
    assert list(chord.pitch_classes) == [10, 2, 5, 8, 0, 4, 7]


def test_parse_slash_chord_keeps_bass() -> None:
    chord = parse_chord_symbol("Dm7/G")
    assert list(chord.pitch_classes) == [2, 5, 9, 0]
    assert chord.bass == 7


def test_add_and_omit_modifiers() -> None:
    assert pitch_classes("Cadd9") == [0, 4, 7, 2]
    assert pitch_classes("Cmaj7no5") == [0, 4, 11]


def test_unknown_symbol_raises() -> None:
    with pytest.raises(HarmonyError):
        parse_chord_symbol("Hmaj7")
    with pytest.raises(HarmonyError):
        parse_chord_symbol("")


def test_parse_key_modes() -> None:
    assert parse_key("F minor").scale == "natural_minor"
    assert parse_key("C").scale == "major"
    assert parse_key("Bb dorian").scale == "dorian"
    with pytest.raises(HarmonyError):
        parse_key("F klingon")


def test_roman_progression_in_f_minor() -> None:
    chords = parse_progression("i-VI-III-VII", key="F minor")
    assert [chord.root for chord in chords] == [5, 1, 8, 3]
    assert [list(chord.intervals) for chord in chords] == [
        [0, 3, 7],
        [0, 4, 7],
        [0, 4, 7],
        [0, 4, 7],
    ]


def test_roman_numeral_with_figures() -> None:
    chords = parse_progression("ii7 V7 Imaj7", key="C major")
    assert [chord.root for chord in chords] == [2, 7, 0]
    assert list(chords[0].pitch_classes) == [2, 5, 9, 0]
    assert list(chords[1].pitch_classes) == [7, 11, 2, 5]
    assert list(chords[2].pitch_classes) == [0, 4, 7, 11]


def test_roman_numeral_accidental_degree() -> None:
    (chord,) = parse_progression("bVII", key="C major")
    assert chord.root == 10


def test_roman_numeral_requires_key() -> None:
    with pytest.raises(HarmonyError):
        parse_progression("i-VI", key=None)


def test_absolute_symbols_do_not_need_key() -> None:
    chords = parse_progression("Cmaj7, A7 | Dm7 G7")
    assert [chord.symbol for chord in chords] == ["Cmaj7", "A7", "Dm7", "G7"]


def test_voicings() -> None:
    chord = parse_chord_symbol("Cmaj7")
    assert voice_chord(chord, base_pitch=60, voicing="close") == [60, 64, 67, 71]
    assert voice_chord(chord, base_pitch=60, voicing="drop2") == [55, 60, 64, 71]
    assert voice_chord(chord, base_pitch=60, voicing="drop3") == [52, 60, 67, 71]
    assert voice_chord(chord, base_pitch=60, voicing="rootless") == [64, 67, 71]
    assert voice_chord(chord, base_pitch=60, voicing="shell") == [60, 64, 71]


def test_quartal_voicing_stacks_fourths_or_wider() -> None:
    pitches = voice_chord(parse_chord_symbol("Cm11"), base_pitch=60, voicing="quartal")
    gaps = [second - first for first, second in zip(pitches, pitches[1:], strict=False)]
    assert all(gap >= 5 for gap in gaps)


def test_slash_chord_puts_bass_below() -> None:
    pitches = voice_chord(parse_chord_symbol("Dm7/G"), base_pitch=60)
    assert min(pitches) % 12 == 7
    assert min(pitches) < sorted(pitches)[1]


def test_unknown_voicing_raises() -> None:
    with pytest.raises(HarmonyError):
        voice_chord(parse_chord_symbol("C"), voicing="cluster")


def test_voice_lead_prefers_the_nearest_inversion() -> None:
    previous = [60, 64, 67]
    candidate = [65, 69, 72]  # F major in root position
    assert voice_lead(previous, candidate) == [60, 65, 69]  # second inversion, C stays put


def test_voice_lead_is_identity_without_previous() -> None:
    assert voice_lead([], [60, 64, 67]) == [60, 64, 67]


def test_progression_notes_layout() -> None:
    chords = parse_progression("i-VI", key="F minor")
    notes = progression_notes(chords, beats_per_chord=4.0, base_pitch=60, voice_leading=False)
    assert len(notes) == 6
    assert {note["start_time"] for note in notes} == {0.0, 4.0}
    assert all(note["duration"] == pytest.approx(3.92) for note in notes)
    assert all(note["velocity"] == 90 for note in notes)
    assert all(note["mute"] is False for note in notes)


def test_progression_notes_voice_leading_reduces_movement() -> None:
    chords = parse_progression("I-IV-V-I", key="C major")
    led = progression_notes(chords, voice_leading=True)
    plain = progression_notes(chords, voice_leading=False)
    led_span = max(note["pitch"] for note in led) - min(note["pitch"] for note in led)
    plain_span = max(note["pitch"] for note in plain) - min(note["pitch"] for note in plain)
    assert led_span <= plain_span


def test_progression_notes_validates_arguments() -> None:
    chords = parse_progression("C")
    with pytest.raises(HarmonyError):
        progression_notes(chords, beats_per_chord=0.0)
    with pytest.raises(HarmonyError):
        progression_notes(chords, gate=0.0)
    with pytest.raises(HarmonyError):
        progression_notes(chords, velocity=0)


def test_voicing_out_of_range_raises() -> None:
    with pytest.raises(HarmonyError):
        voice_chord(parse_chord_symbol("C13"), base_pitch=120)
