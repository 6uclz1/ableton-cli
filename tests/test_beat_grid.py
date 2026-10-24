from __future__ import annotations

import pytest

from ableton_cli.beat_grid import parse_grid_to_beats


@pytest.mark.parametrize(
    ("grid", "expected_beats"),
    [
        ("1/4", 1.0),
        ("1/8", 0.5),
        ("1/16", 0.25),
        ("1/8T", 0.5 * 2 / 3),
        ("1/16T", 0.25 * 2 / 3),
        ("1/16t", 0.25 * 2 / 3),
    ],
)
def test_parse_grid_to_beats(grid: str, expected_beats: float) -> None:
    assert parse_grid_to_beats(grid) == pytest.approx(expected_beats)


@pytest.mark.parametrize("bad_grid", ["", "1", "1/0", "0/4", "-1/4", "a/b", "1/4/8"])
def test_parse_grid_to_beats_rejects_invalid_input(bad_grid: str) -> None:
    with pytest.raises(ValueError):
        parse_grid_to_beats(bad_grid)
