"""Pure curve generators for clip automation envelopes.

Ableton's Live Object Model only supports writing an automation envelope as
a list of ``(time, value)`` breakpoints (see ``clip.create_automation_envelope``
and ``envelope.insert_step`` in the Remote Script). All curve mathematics
live here, in the CLI (core) layer, so they are testable without Live.
"""

from __future__ import annotations

import math
from typing import Literal

EnvelopeShape = Literal["ramp", "exp", "scurve", "lfo-sine", "lfo-square"]

_PERIODIC_SHAPES = frozenset({"lfo-sine", "lfo-square"})
_SHAPES = frozenset({"ramp", "exp", "scurve", "lfo-sine", "lfo-square"})


def _normalized_positions(shape: str, resolution: int) -> list[float]:
    if resolution == 1:
        return [0.0]
    if shape in _PERIODIC_SHAPES:
        return [index / resolution for index in range(resolution)]
    return [index / (resolution - 1) for index in range(resolution)]


def _eased_fraction(shape: str, t_norm: float, *, rate: float) -> float:
    if shape == "ramp":
        return t_norm
    if shape == "exp":
        return (math.exp(t_norm) - 1.0) / (math.e - 1.0)
    if shape == "scurve":
        return t_norm * t_norm * (3.0 - 2.0 * t_norm)
    raise ValueError(f"Shape {shape!r} does not use an eased fraction")


def generate_shape_points(
    shape: str,
    *,
    from_value: float,
    to_value: float,
    start: float,
    length: float,
    resolution: int,
    rate: float = 1.0,
) -> list[dict[str, float]]:
    """Generate breakpoints for an automation envelope curve.

    ``ramp``/``exp``/``scurve`` span ``[start, start + length]`` inclusive of
    both endpoints, hitting ``from_value``/``to_value`` exactly.
    ``lfo-sine``/``lfo-square`` oscillate between ``from_value`` and
    ``to_value`` at ``rate`` cycles per beat of ``length``, sampled at
    ``resolution`` evenly spaced positions (endpoint exclusive, since they
    are periodic).
    """
    if shape not in _SHAPES:
        raise ValueError(f"Unknown envelope shape: {shape!r}")
    if resolution < 1:
        raise ValueError("resolution must be >= 1")
    if length <= 0:
        raise ValueError("length must be > 0")

    positions = _normalized_positions(shape, resolution)
    points: list[dict[str, float]] = []
    for t_norm in positions:
        time = start + length * t_norm
        if shape in _PERIODIC_SHAPES:
            phase = (t_norm * rate) % 1.0
            if shape == "lfo-sine":
                mid = (from_value + to_value) / 2.0
                amplitude = (to_value - from_value) / 2.0
                value = mid + amplitude * math.sin(2.0 * math.pi * phase)
            else:  # lfo-square
                value = from_value if phase < 0.5 else to_value
        else:
            fraction = _eased_fraction(shape, t_norm, rate=rate)
            value = from_value + (to_value - from_value) * fraction
        points.append({"time": time, "value": value})
    return points
