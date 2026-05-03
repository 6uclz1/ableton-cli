from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..audio_analysis import analyze_spectrum
from ..runtime import execute_command


def register(spectrum_app: typer.Typer) -> None:
    @spectrum_app.command("analyze")
    def audio_spectrum_analyze(
        ctx: typer.Context,
        path: Annotated[Path, typer.Option("--path", help="Rendered audio file path")],
        profile: Annotated[str, typer.Option("--profile", help="Spectrum profile")] = "anime-club",
        report_out: Annotated[
            Path | None,
            typer.Option("--report-out", help="Write JSON report to this path"),
        ] = None,
    ) -> None:
        execute_command(
            ctx,
            command="audio spectrum analyze",
            args={"path": str(path), "profile": profile, "report_out": _path_or_none(report_out)},
            action=lambda: analyze_spectrum(path, profile=profile, report_out=report_out),
        )


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)
