from __future__ import annotations

import pytest

from ableton_cli.pattern_notation import (
    Chord,
    NoteEvent,
    PatternSyntaxError,
    Repeat,
    Rest,
    Sequence,
    compile_pattern,
    parse,
)

# --- parser: grammar rules ----------------------------------------------------


def test_parse_single_note_name() -> None:
    result = parse("c3")
    assert result == Sequence((NoteEvent(pitch=60),))


def test_parse_midi_number() -> None:
    result = parse("60")
    assert result == Sequence((NoteEvent(pitch=60),))


def test_parse_sharp_and_flat() -> None:
    result = parse("c#3 db3")
    assert result.steps[0] == NoteEvent(pitch=61)
    assert result.steps[1] == NoteEvent(pitch=61)


def test_parse_rest() -> None:
    result = parse("~")
    assert result == Sequence((Rest(),))


def test_parse_subdivision_group() -> None:
    result = parse("[c3 e3]")
    assert result == Sequence((Sequence((NoteEvent(60), NoteEvent(64))),))


def test_parse_nested_subdivision() -> None:
    result = parse("[c3 [e3 g3]]")
    group = result.steps[0]
    assert isinstance(group, Sequence)
    assert group.steps[0] == NoteEvent(60)
    assert group.steps[1] == Sequence((NoteEvent(64), NoteEvent(67)))


def test_parse_repeat() -> None:
    result = parse("c3*3")
    assert result == Sequence((Repeat(NoteEvent(60), 3),))


def test_parse_chord() -> None:
    result = parse("c3,e3,g3")
    assert result == Sequence((Chord((NoteEvent(60), NoteEvent(64), NoteEvent(67))),))


def test_parse_velocity_suffix() -> None:
    result = parse("c3@90")
    assert result == Sequence((NoteEvent(pitch=60, velocity=90),))


def test_parse_chord_with_per_note_velocity() -> None:
    result = parse("c3@90,e3@50")
    assert result == Sequence((Chord((NoteEvent(60, 90), NoteEvent(64, 50))),))


def test_parse_multiple_steps() -> None:
    result = parse("c3 ~ e3")
    assert result == Sequence((NoteEvent(60), Rest(), NoteEvent(64)))


def test_parse_negative_octave() -> None:
    result = parse("c-1")
    assert result == Sequence((NoteEvent(pitch=(-1 + 2) * 12),))


# --- parser: error cases with column info -------------------------------------


def test_unclosed_bracket_reports_column() -> None:
    with pytest.raises(PatternSyntaxError) as excinfo:
        parse("[c3 e3")
    assert excinfo.value.column == 1


def test_bad_pitch_name_reports_column() -> None:
    with pytest.raises(PatternSyntaxError) as excinfo:
        parse("h3")
    assert excinfo.value.column == 1


def test_bad_pitch_name_mid_pattern_reports_column() -> None:
    with pytest.raises(PatternSyntaxError) as excinfo:
        parse("c3 h3")
    assert excinfo.value.column == 4


def test_empty_group_rejected() -> None:
    with pytest.raises(PatternSyntaxError) as excinfo:
        parse("[]")
    assert excinfo.value.column == 1


def test_empty_pattern_rejected() -> None:
    with pytest.raises(PatternSyntaxError):
        parse("")


def test_midi_pitch_out_of_range_rejected() -> None:
    with pytest.raises(PatternSyntaxError):
        parse("200")


def test_note_name_out_of_midi_range_rejected() -> None:
    with pytest.raises(PatternSyntaxError):
        parse("c9")


def test_missing_octave_rejected() -> None:
    with pytest.raises(PatternSyntaxError):
        parse("c")


def test_repeat_count_below_one_rejected() -> None:
    with pytest.raises(PatternSyntaxError):
        parse("c3*0")


def test_velocity_out_of_range_rejected() -> None:
    with pytest.raises(PatternSyntaxError):
        parse("c3@200")


# --- compiler: golden test -----------------------------------------------------


def test_golden_pattern_compiles_to_exact_notes_json() -> None:
    node = parse("c3 ~ [e3 g3] c4*2")

    events = compile_pattern(node, pattern_length=4.0, default_velocity=100, gate=1.0)

    assert events == [
        {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100, "mute": False},
        {"pitch": 64, "start_time": 2.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": 67, "start_time": 2.5, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": 72, "start_time": 3.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": 72, "start_time": 3.5, "duration": 0.5, "velocity": 100, "mute": False},
    ]


def test_compile_is_deterministic_across_runs() -> None:
    node = parse("c3 ~ [e3 g3] c4*2")

    first = compile_pattern(node, pattern_length=4.0)
    second = compile_pattern(node, pattern_length=4.0)

    assert first == second


def test_compile_orders_by_start_time_then_pitch() -> None:
    node = parse("e3,c3")

    events = compile_pattern(node, pattern_length=1.0)

    assert [event["pitch"] for event in events] == [60, 64]


def test_compile_chord_shares_start_and_duration() -> None:
    node = parse("c3,e3,g3")

    events = compile_pattern(node, pattern_length=2.0)

    assert all(event["start_time"] == 0.0 for event in events)
    assert all(event["duration"] == 2.0 for event in events)


def test_compile_gate_scales_duration_not_spacing() -> None:
    node = parse("c3 e3")

    events = compile_pattern(node, pattern_length=2.0, gate=0.5)

    assert events[0]["start_time"] == 0.0
    assert events[0]["duration"] == 0.5
    assert events[1]["start_time"] == 1.0
    assert events[1]["duration"] == 0.5


def test_compile_per_note_velocity_overrides_default() -> None:
    node = parse("c3@42")

    events = compile_pattern(node, pattern_length=1.0, default_velocity=100)

    assert events[0]["velocity"] == 42


def test_compile_rejects_non_positive_pattern_length() -> None:
    node = parse("c3")
    with pytest.raises(ValueError):
        compile_pattern(node, pattern_length=0.0)


def test_compile_rejects_out_of_range_gate() -> None:
    node = parse("c3")
    with pytest.raises(ValueError):
        compile_pattern(node, pattern_length=1.0, gate=1.5)
