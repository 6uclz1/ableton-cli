from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def test_build_track_ref_requires_exactly_one_selector() -> None:
    from ableton_cli.refs import build_track_ref

    with pytest.raises(AppError) as exc:
        build_track_ref(
            track_index=None,
            track_name=None,
            selected_track=False,
            track_query=None,
            track_ref=None,
        )

    assert exc.value.message == "Exactly one track selector must be provided"


def test_build_track_ref_supports_selected_mode() -> None:
    from ableton_cli.refs import build_track_ref

    assert build_track_ref(
        track_index=None,
        track_name=None,
        selected_track=True,
        track_query=None,
        track_ref=None,
    ) == {"mode": "selected"}


def test_build_parameter_ref_supports_key_mode() -> None:
    from ableton_cli.refs import build_parameter_ref

    assert build_parameter_ref(
        parameter_index=None,
        parameter_name=None,
        parameter_query=None,
        parameter_key="filter_cutoff",
        parameter_ref=None,
    ) == {"mode": "key", "key": "filter_cutoff"}
