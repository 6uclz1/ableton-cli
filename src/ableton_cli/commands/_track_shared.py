from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypeVar

import typer

TValue = TypeVar("TValue")

TrackArgument = Annotated[int, typer.Argument(help="Track index (0-based)")]
ReturnTrackArgument = Annotated[int, typer.Argument(help="Return track index (0-based)")]
SendArgument = Annotated[int, typer.Argument(help="Send index (0-based)")]
VolumeValueArgument = Annotated[float, typer.Argument(help="Volume value in [0.0, 1.0]")]
PanningValueArgument = Annotated[float, typer.Argument(help="Panning value in [-1.0, 1.0]")]

TrackValidator = Callable[[int], int]
TrackValueValidator = Callable[[int, TValue], tuple[int, TValue]]
TrackAction = Callable[[object, int], dict[str, object]]
TrackValueAction = Callable[[object, int, TValue], dict[str, object]]
