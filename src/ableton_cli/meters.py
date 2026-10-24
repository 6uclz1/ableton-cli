"""Sample Live's output meters over a short window.

One reading of ``output_meter_left/right/level`` is an instantaneous value
(Live's 0.0-1.0 meter scale, not dB) and is noisy, so the meter commands read
it ``samples`` times, ``interval_ms`` apart, and report each channel's peak
and mean. ``is_playing`` comes from the last reading: meters read 0.0 while
the transport is stopped, and a caller must be able to tell that from silence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .errors import AppError, ErrorCode, ExitCode

METER_CHANNELS = ("left", "right", "level")
MAX_SAMPLES = 1000
MAX_INTERVAL_MS = 10_000


def _invalid(message: str, hint: str) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def validate_sampling(samples: int, interval_ms: int) -> None:
    if not 1 <= samples <= MAX_SAMPLES:
        raise _invalid(
            f"samples must be in [1, {MAX_SAMPLES}], got {samples}",
            "Use --samples 1 for one reading, or more to measure a window.",
        )
    if not 0 <= interval_ms <= MAX_INTERVAL_MS:
        raise _invalid(
            f"interval_ms must be in [0, {MAX_INTERVAL_MS}], got {interval_ms}",
            "Use an --interval-ms such as 50.",
        )


def sample_meter(
    read: Callable[[], dict[str, Any]],
    *,
    samples: int,
    interval_ms: int,
    sleep: Callable[[float], Any] | None,
) -> dict[str, Any]:
    validate_sampling(samples, interval_ms)
    readings: list[dict[str, Any]] = []
    for index in range(samples):
        if index and sleep is not None:
            sleep(interval_ms / 1000)
        readings.append(read())
    last = readings[-1]
    identity = {
        key: value for key, value in last.items() if key not in {*METER_CHANNELS, "is_playing"}
    }
    channels = {
        channel: {
            "peak": max(float(reading[channel]) for reading in readings),
            "mean": sum(float(reading[channel]) for reading in readings) / samples,
        }
        for channel in METER_CHANNELS
    }
    return {
        **identity,
        "samples": samples,
        "interval_ms": interval_ms,
        "is_playing": bool(last["is_playing"]),
        **channels,
    }
