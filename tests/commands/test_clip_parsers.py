from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def _assert_invalid_argument(exc: pytest.ExceptionInfo[AppError]) -> None:
    assert exc.value.error_code == "INVALID_ARGUMENT"


def test_parse_duplicate_destinations_rejects_mutually_exclusive_inputs() -> None:
    from ableton_cli.commands.clip._parsers import parse_duplicate_destinations

    with pytest.raises(AppError) as exc:
        parse_duplicate_destinations(src_clip=1, dst_clip=2, to="3")

    _assert_invalid_argument(exc)


def test_parse_duplicate_destinations_rejects_empty_to() -> None:
    from ableton_cli.commands.clip._parsers import parse_duplicate_destinations

    with pytest.raises(AppError) as exc:
        parse_duplicate_destinations(src_clip=1, dst_clip=None, to="")

    _assert_invalid_argument(exc)


def test_parse_duplicate_destinations_rejects_self_reference() -> None:
    from ableton_cli.commands.clip._parsers import parse_duplicate_destinations

    with pytest.raises(AppError) as exc:
        parse_duplicate_destinations(src_clip=1, dst_clip=1, to=None)

    _assert_invalid_argument(exc)


def test_parse_duplicate_destinations_rejects_duplicate_values() -> None:
    from ableton_cli.commands.clip._parsers import parse_duplicate_destinations

    with pytest.raises(AppError) as exc:
        parse_duplicate_destinations(src_clip=1, dst_clip=None, to="2,2")

    _assert_invalid_argument(exc)


def test_parse_place_pattern_destinations_rejects_descending_range() -> None:
    from ableton_cli.commands.clip._parsers import parse_place_pattern_destinations

    with pytest.raises(AppError) as exc:
        parse_place_pattern_destinations(
            src_clip=1,
            scenes="5-2",
            load_scenes=lambda: {"scenes": []},
        )

    _assert_invalid_argument(exc)


def test_parse_place_pattern_destinations_resolves_scene_names() -> None:
    from ableton_cli.commands.clip._parsers import parse_place_pattern_destinations

    parsed = parse_place_pattern_destinations(
        src_clip=1,
        scenes="Intro,Peak",
        load_scenes=lambda: {
            "scenes": [
                {"index": 0, "name": "Intro"},
                {"index": 1, "name": "Drop"},
                {"index": 2, "name": "Peak"},
            ]
        },
    )

    assert parsed == [0, 2]


def test_parse_place_pattern_destinations_rejects_duplicates() -> None:
    from ableton_cli.commands.clip._parsers import parse_place_pattern_destinations

    with pytest.raises(AppError) as exc:
        parse_place_pattern_destinations(
            src_clip=1,
            scenes="2,2",
            load_scenes=lambda: {"scenes": [{"index": 2, "name": "Verse"}]},
        )

    _assert_invalid_argument(exc)


def test_parse_clip_name_assignments_rejects_invalid_pair() -> None:
    from ableton_cli.commands.clip._parsers import parse_clip_name_assignments

    with pytest.raises(AppError) as exc:
        parse_clip_name_assignments("1Main,2:Var")

    _assert_invalid_argument(exc)


def test_parse_clip_name_assignments_rejects_duplicate_clip_index() -> None:
    from ableton_cli.commands.clip._parsers import parse_clip_name_assignments

    with pytest.raises(AppError) as exc:
        parse_clip_name_assignments("1:Main,1:Var")

    _assert_invalid_argument(exc)


def test_parse_clip_name_assignments_rejects_empty_name() -> None:
    from ableton_cli.commands.clip._parsers import parse_clip_name_assignments

    with pytest.raises(AppError) as exc:
        parse_clip_name_assignments("1:Main,2:   ")

    _assert_invalid_argument(exc)
