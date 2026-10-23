"""Typer parameter types shared by several command modules."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

TrackArgument = Annotated[int, typer.Argument(help="Track index (0-based)")]
ClipArgument = Annotated[int, typer.Argument(help="Clip slot index (0-based)")]
ProjectOption = Annotated[Path, typer.Option("--project", help="Manifest path")]

StartTimeFilterOption = Annotated[
    float | None,
    typer.Option("--start-time", help="Inclusive start time filter in beats"),
]
EndTimeFilterOption = Annotated[
    float | None,
    typer.Option("--end-time", help="Exclusive end time filter in beats"),
]
PitchFilterOption = Annotated[int | None, typer.Option("--pitch", help="Exact MIDI pitch filter")]

NotesJsonOption = Annotated[
    str | None,
    typer.Option("--notes-json", help="JSON array of note objects"),
]
NotesFileOption = Annotated[
    str | None,
    typer.Option("--notes-file", help="Path to JSON file containing note array"),
]
