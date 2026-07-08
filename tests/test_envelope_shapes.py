from __future__ import annotations

import pytest

from ableton_cli.envelope_shapes import generate_shape_points


def test_ramp_endpoints_are_exact() -> None:
    points = generate_shape_points(
        "ramp", from_value=0.1, to_value=0.9, start=0.0, length=4.0, resolution=8
    )

    assert points[0]["value"] == pytest.approx(0.1)
    assert points[-1]["value"] == pytest.approx(0.9)
    assert points[0]["time"] == pytest.approx(0.0)
    assert points[-1]["time"] == pytest.approx(4.0)


def test_ramp_resolution_controls_point_count() -> None:
    points = generate_shape_points(
        "ramp", from_value=0.0, to_value=1.0, start=0.0, length=4.0, resolution=8
    )

    assert len(points) == 8


def test_ramp_times_are_strictly_increasing() -> None:
    points = generate_shape_points(
        "ramp", from_value=0.0, to_value=1.0, start=2.0, length=4.0, resolution=16
    )

    times = [point["time"] for point in points]
    assert times == sorted(times)
    assert len(set(times)) == len(times)


def test_ramp_is_linear() -> None:
    points = generate_shape_points(
        "ramp", from_value=0.0, to_value=1.0, start=0.0, length=1.0, resolution=5
    )

    assert [point["value"] for point in points] == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])


def test_exp_and_scurve_endpoints_are_exact() -> None:
    for shape in ("exp", "scurve"):
        points = generate_shape_points(
            shape, from_value=0.2, to_value=0.8, start=0.0, length=4.0, resolution=10
        )
        assert points[0]["value"] == pytest.approx(0.2)
        assert points[-1]["value"] == pytest.approx(0.8)


def test_scurve_midpoint_matches_smoothstep() -> None:
    points = generate_shape_points(
        "scurve", from_value=0.0, to_value=1.0, start=0.0, length=1.0, resolution=3
    )

    assert points[1]["value"] == pytest.approx(0.5)


def test_lfo_sine_completes_one_period_over_length_at_rate_one() -> None:
    points = generate_shape_points(
        "lfo-sine", from_value=0.0, to_value=1.0, start=0.0, length=4.0, resolution=4, rate=1.0
    )

    values = [point["value"] for point in points]
    mid = 0.5
    assert values[0] == pytest.approx(mid)
    assert values[1] == pytest.approx(mid + 0.5, abs=1e-9)
    assert values[2] == pytest.approx(mid, abs=1e-9)
    assert values[3] == pytest.approx(mid - 0.5, abs=1e-9)


def test_lfo_sine_rate_scales_number_of_cycles() -> None:
    points_one_cycle = generate_shape_points(
        "lfo-sine", from_value=0.0, to_value=1.0, start=0.0, length=8.0, resolution=8, rate=1.0
    )
    points_two_cycles = generate_shape_points(
        "lfo-sine", from_value=0.0, to_value=1.0, start=0.0, length=8.0, resolution=8, rate=2.0
    )

    assert points_one_cycle[4]["value"] == pytest.approx(0.5, abs=1e-9)
    assert points_two_cycles[2]["value"] == pytest.approx(0.5, abs=1e-9)


def test_lfo_square_alternates_between_endpoints() -> None:
    points = generate_shape_points(
        "lfo-square", from_value=0.2, to_value=0.9, start=0.0, length=4.0, resolution=4, rate=1.0
    )

    values = [point["value"] for point in points]
    assert values[0] == pytest.approx(0.2)
    assert values[2] == pytest.approx(0.9)


def test_periodic_shapes_do_not_repeat_the_start_position() -> None:
    points = generate_shape_points(
        "lfo-sine", from_value=0.0, to_value=1.0, start=0.0, length=4.0, resolution=4, rate=1.0
    )

    assert points[-1]["time"] < 4.0


def test_resolution_one_yields_single_point_at_start() -> None:
    points = generate_shape_points(
        "ramp", from_value=0.3, to_value=0.7, start=1.0, length=4.0, resolution=1
    )

    assert len(points) == 1
    assert points[0]["time"] == pytest.approx(1.0)
    assert points[0]["value"] == pytest.approx(0.3)


@pytest.mark.parametrize("bad_resolution", [0, -1])
def test_rejects_non_positive_resolution(bad_resolution: int) -> None:
    with pytest.raises(ValueError):
        generate_shape_points(
            "ramp", from_value=0.0, to_value=1.0, start=0.0, length=4.0, resolution=bad_resolution
        )


@pytest.mark.parametrize("bad_length", [0.0, -1.0])
def test_rejects_non_positive_length(bad_length: float) -> None:
    with pytest.raises(ValueError):
        generate_shape_points(
            "ramp", from_value=0.0, to_value=1.0, start=0.0, length=bad_length, resolution=4
        )


def test_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError):
        generate_shape_points(
            "triangle", from_value=0.0, to_value=1.0, start=0.0, length=4.0, resolution=4
        )
