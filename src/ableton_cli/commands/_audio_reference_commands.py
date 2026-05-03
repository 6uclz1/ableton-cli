from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..audio_analysis import compare_reference
from ..runtime import execute_command


def register(reference_app: typer.Typer) -> None:
    @reference_app.command("compare")
    def audio_reference_compare(
        ctx: typer.Context,
        candidate: Annotated[Path, typer.Option("--candidate", help="Candidate render path")],
        reference: Annotated[Path, typer.Option("--reference", help="Reference track path")],
        metrics: Annotated[
            str,
            typer.Option("--metrics", help="Comma-separated metrics"),
        ] = "loudness,spectrum,stereo",
        report_out: Annotated[
            Path | None,
            typer.Option("--report-out", help="Write JSON report to this path"),
        ] = None,
    ) -> None:
        execute_command(
            ctx,
            command="audio reference compare",
            args={
                "candidate": str(candidate),
                "reference": str(reference),
                "metrics": metrics,
                "report_out": _path_or_none(report_out),
            },
            action=lambda: compare_reference(
                candidate=candidate,
                reference=reference,
                metrics=metrics,
                report_out=report_out,
            ),
        )


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)
