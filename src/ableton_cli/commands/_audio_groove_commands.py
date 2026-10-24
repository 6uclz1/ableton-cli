from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ..audio_analysis.groove import BEATS_PER_BAR, extract_groove
from ..audio_analysis.transient import analyze_transients
from ..runtime import execute_command


def register(app: typer.Typer) -> None:
    app.command("extract")(audio_groove_extract)


def audio_groove_extract(
    ctx: typer.Context,
    path: Annotated[Path, typer.Option("--path", help="PCM WAV file to analyze")],
    bpm: Annotated[float, typer.Option("--bpm", help="Source tempo in BPM")],
    grid: Annotated[
        str,
        typer.Option("--grid", help="Groove grid: 1/8, 1/16, 1/8T, or 1/16T"),
    ] = "1/16",
    bars: Annotated[
        int | None,
        typer.Option("--bars", help="Limit analysis to the first N bars"),
    ] = None,
    max_slices: Annotated[
        int,
        typer.Option("--max-slices", help="Maximum number of transients to detect"),
    ] = 256,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Write the groove profile JSON to this path"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        analysis = analyze_transients(path, bpm=bpm, max_slices=max_slices)
        transients = list(
            zip(analysis["onset_points_beats"], analysis["onset_strengths"], strict=True)
        )
        if bars is not None:
            max_beat = bars * BEATS_PER_BAR
            transients = [item for item in transients if item[0] < max_beat]
        profile = extract_groove(transients, grid=grid)
        if out is not None:
            out.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        return profile

    execute_command(
        ctx,
        command="audio groove extract",
        args={
            "path": str(path),
            "bpm": bpm,
            "grid": grid,
            "bars": bars,
            "max_slices": max_slices,
            "out": str(out) if out is not None else None,
        },
        action=_run,
    )
