"""Shared runner for the ``track|return-track|master meter get`` commands."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Annotated, Any

import typer

from ..meters import sample_meter
from ..runtime import execute_command

MeterSamplesOption = Annotated[
    int, typer.Option("--samples", help="Number of meter readings to take (1-1000)")
]
MeterIntervalOption = Annotated[
    int, typer.Option("--interval-ms", help="Delay between readings in milliseconds")
]


def run_meter_command(
    ctx: typer.Context,
    *,
    command_name: str,
    target_args: dict[str, Any],
    read: Callable[[], dict[str, Any]],
    samples: int,
    interval_ms: int,
    resolved_target_args: Callable[[], dict[str, Any]] | None = None,
) -> None:
    sampling = {"samples": samples, "interval_ms": interval_ms}
    execute_command(
        ctx,
        command=command_name,
        args={**target_args, **sampling},
        resolved_args=(
            None if resolved_target_args is None else lambda: {**resolved_target_args(), **sampling}
        ),
        action=lambda: sample_meter(
            read, samples=samples, interval_ms=interval_ms, sleep=time.sleep
        ),
    )
