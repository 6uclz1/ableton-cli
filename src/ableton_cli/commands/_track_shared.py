from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypeVar

import typer

from ..refs import RefPayload

TValue = TypeVar("TValue")

ReturnTrackArgument = Annotated[int, typer.Argument(help="Return track index (0-based)")]
VolumeValueArgument = Annotated[float, typer.Argument(help="Volume value in [0.0, 1.0]")]
PanningValueArgument = Annotated[float, typer.Argument(help="Panning value in [-1.0, 1.0]")]

ValueValidator = Callable[[TValue], TValue]
TrackAction = Callable[[object, RefPayload], dict[str, object]]
TrackValueAction = Callable[[object, RefPayload, TValue], dict[str, object]]
