from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..audio_analysis.transient import analyze_transients
from ..runtime import execute_command


def register(app: typer.Typer) -> None:
    app.command("analyze")(audio_transient_analyze)


def audio_transient_analyze(
    ctx: typer.Context,
    path: Annotated[Path, typer.Option("--path", help="PCM WAV file to analyze")],
    bpm: Annotated[float, typer.Option("--bpm", help="Source tempo in BPM")],
    max_slices: Annotated[
        int,
        typer.Option("--max-slices", help="Maximum number of output slices"),
    ] = 32,
) -> None:
    execute_command(
        ctx,
        command="audio transient analyze",
        args={"path": str(path), "bpm": bpm, "max_slices": max_slices},
        action=lambda: analyze_transients(path, bpm=bpm, max_slices=max_slices),
    )
