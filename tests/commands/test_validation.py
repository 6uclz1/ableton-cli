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
