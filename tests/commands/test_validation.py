from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def _assert_invalid_argument(exc: pytest.ExceptionInfo[AppError]) -> None:
    assert exc.value.error_code == "INVALID_ARGUMENT"


def test_require_track_index_accepts_zero_or_positive_values() -> None:
    from ableton_cli.commands._validation import require_track_index

    assert require_track_index(0) == 0
    assert require_track_index(3) == 3


def test_require_track_index_rejects_negative_values() -> None:
    from ableton_cli.commands._validation import require_track_index

    with pytest.raises(AppError) as exc:
        require_track_index(-1)

    _assert_invalid_argument(exc)
    assert exc.value.message == "track must be >= 0, got -1"
    assert exc.value.hint == "Use a valid track index from 'ableton-cli tracks list'."


def test_require_device_index_accepts_zero_or_positive_values() -> None:
    from ableton_cli.commands._validation import require_device_index

    assert require_device_index(0) == 0
    assert require_device_index(5) == 5


def test_require_device_index_rejects_negative_values() -> None:
    from ableton_cli.commands._validation import require_device_index

    with pytest.raises(AppError) as exc:
        require_device_index(-1)

    _assert_invalid_argument(exc)
    assert exc.value.message == "device must be >= 0, got -1"
    assert exc.value.hint == "Use a valid device index from 'ableton-cli track info'."


def test_require_parameter_index_rejects_negative_values_with_custom_hint() -> None:
    from ableton_cli.commands._validation import require_parameter_index

    with pytest.raises(AppError) as exc:
        require_parameter_index(
            -1, hint="Use a valid parameter index from 'ableton-cli synth parameters list'."
        )

    _assert_invalid_argument(exc)
    assert exc.value.message == "parameter must be >= 0, got -1"
    assert exc.value.hint == "Use a valid parameter index from 'ableton-cli synth parameters list'."


def test_require_float_in_range_accepts_boundary_values() -> None:
    from ableton_cli.commands._validation import require_float_in_range

    assert (
        require_float_in_range(
            "value",
            0.0,
            minimum=0.0,
            maximum=1.0,
            hint="Use a normalized value such as 0.75.",
        )
        == 0.0
    )
    assert (
        require_float_in_range(
            "value",
            1.0,
            minimum=0.0,
            maximum=1.0,
            hint="Use a normalized value such as 0.75.",
        )
        == 1.0
    )


def test_require_float_in_range_rejects_out_of_range_values() -> None:
    from ableton_cli.commands._validation import require_float_in_range

    with pytest.raises(AppError) as exc:
        require_float_in_range(
            "value",
            1.2,
            minimum=0.0,
            maximum=1.0,
            hint="Use a normalized value such as 0.75.",
        )

    _assert_invalid_argument(exc)
    assert exc.value.message == "value must be between 0.0 and 1.0, got 1.2"
    assert exc.value.hint == "Use a normalized value such as 0.75."


def test_require_track_and_volume_accepts_valid_track_and_value() -> None:
    from ableton_cli.commands._validation import require_track_and_volume

    assert require_track_and_volume(2, 0.75) == (2, 0.75)


def test_require_track_and_volume_rejects_out_of_range_value() -> None:
    from ableton_cli.commands._validation import require_track_and_volume

    with pytest.raises(AppError) as exc:
        require_track_and_volume(1, 1.1)

    _assert_invalid_argument(exc)
    assert exc.value.message == "value must be between 0.0 and 1.0, got 1.1"
    assert exc.value.hint == "Use a normalized volume value such as 0.75."


def test_require_track_and_pan_accepts_valid_track_and_value() -> None:
    from ableton_cli.commands._validation import require_track_and_pan

    assert require_track_and_pan(1, -0.25) == (1, -0.25)


def test_require_track_and_pan_rejects_out_of_range_value() -> None:
    from ableton_cli.commands._validation import require_track_and_pan

    with pytest.raises(AppError) as exc:
        require_track_and_pan(0, -1.2)

    _assert_invalid_argument(exc)
    assert exc.value.message == "value must be between -1.0 and 1.0, got -1.2"
    assert exc.value.hint == "Use a normalized panning value such as -0.25."


def test_require_scene_and_name_accepts_valid_values() -> None:
    from ableton_cli.commands._validation import require_scene_and_name

    assert require_scene_and_name(3, "  Build  ") == (3, "Build")


def test_require_scene_and_name_rejects_negative_scene() -> None:
    from ableton_cli.commands._validation import require_scene_and_name

    with pytest.raises(AppError) as exc:
        require_scene_and_name(-1, "Build")

    _assert_invalid_argument(exc)
    assert exc.value.message == "scene must be >= 0, got -1"
    assert exc.value.hint == "Use a valid scene index from 'scenes list'."


def test_require_scene_move_accepts_non_negative_values() -> None:
    from ableton_cli.commands._validation import require_scene_move

    assert require_scene_move(2, 5) == (2, 5)


def test_require_scene_move_rejects_negative_source_index() -> None:
    from ableton_cli.commands._validation import require_scene_move

    with pytest.raises(AppError) as exc:
        require_scene_move(-1, 1)

    _assert_invalid_argument(exc)
    assert exc.value.message == "from must be >= 0, got -1"
    assert exc.value.hint == "Use a valid source scene index from 'scenes list'."


def test_require_scene_insert_index_rejects_values_below_minus_one() -> None:
    from ableton_cli.commands._validation import require_scene_insert_index

    with pytest.raises(AppError) as exc:
        require_scene_insert_index(-2)

    _assert_invalid_argument(exc)
    assert exc.value.message == "index must be >= -1, got -2"
    assert exc.value.hint == "Use -1 for append or a non-negative insertion index."


def test_require_optional_track_index_accepts_none() -> None:
    from ableton_cli.commands._validation import require_optional_track_index

    assert require_optional_track_index(None) is None


def test_require_optional_track_index_rejects_negative_track() -> None:
    from ableton_cli.commands._validation import require_optional_track_index

    with pytest.raises(AppError) as exc:
        require_optional_track_index(-1)

    _assert_invalid_argument(exc)
    assert exc.value.message == "track must be >= 0, got -1"
    assert exc.value.hint == "Use a valid track index from 'ableton-cli tracks list'."


def test_require_track_and_device_accepts_non_negative_indices() -> None:
    from ableton_cli.commands._validation import require_track_and_device

    assert require_track_and_device(1, 2) == (1, 2)


def test_require_track_and_device_rejects_negative_device_index() -> None:
    from ableton_cli.commands._validation import require_track_and_device

    with pytest.raises(AppError) as exc:
        require_track_and_device(1, -1)

    _assert_invalid_argument(exc)
    assert exc.value.message == "device must be >= 0, got -1"
    assert exc.value.hint == "Use a valid device index from 'ableton-cli track info'."
