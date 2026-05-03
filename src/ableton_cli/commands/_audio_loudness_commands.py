from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..audio_analysis import analyze_loudness
from ..runtime import execute_command


def register(loudness_app: typer.Typer) -> None:
    @loudness_app.command("analyze")
    def audio_loudness_analyze(
        ctx: typer.Context,
        path: Annotated[Path, typer.Option("--path", help="Rendered audio file path")],
        engine: Annotated[str, typer.Option("--engine", help="Analysis engine")] = "ffmpeg",
        report_out: Annotated[
            Path | None,
            typer.Option("--report-out", help="Write JSON report to this path"),
        ] = None,
    ) -> None:
        execute_command(
            ctx,
            command="audio loudness analyze",
            args={"path": str(path), "engine": engine, "report_out": _path_or_none(report_out)},
            action=lambda: analyze_loudness(path, engine=engine, report_out=report_out),
        )


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)
