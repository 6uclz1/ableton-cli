from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..audio_analysis import analyze_spectrum, spectrum_shares
from ..runtime import execute_command
from ._validation import invalid_argument


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

    _register_shares(spectrum_app)


def _register_shares(spectrum_app: typer.Typer) -> None:
    @spectrum_app.command("shares")
    def audio_spectrum_shares(
        ctx: typer.Context,
        stems: Annotated[
            list[str] | None,
            typer.Option(
                "--stem",
                help="Stem as LABEL=PATH (repeatable), e.g. a solo capture of one track",
            ),
        ] = None,
        resolution: Annotated[
            str,
            typer.Option("--resolution", help="Band set: bands or third-octave"),
        ] = "bands",
        focus: Annotated[
            str | None,
            typer.Option(
                "--focus", help="Stem label to compare against the loudest other stem per band"
            ),
        ] = None,
        report_out: Annotated[
            Path | None,
            typer.Option("--report-out", help="Write JSON report to this path"),
        ] = None,
    ) -> None:
        values = stems or []
        execute_command(
            ctx,
            command="audio spectrum shares",
            args={
                "stems": [_describe_stem(value) for value in values],
                "resolution": resolution,
                "focus": focus,
                "report_out": _path_or_none(report_out),
            },
            action=lambda: spectrum_shares(
                [_parse_stem(value) for value in values],
                resolution=resolution,
                focus=focus,
                report_out=report_out,
            ),
        )


def _describe_stem(value: str) -> dict[str, str | None]:
    label, separator, path = value.partition("=")
    if not separator:
        return {"label": None, "path": value}
    return {"label": label, "path": path}


def _parse_stem(value: str) -> tuple[str, str]:
    label, separator, path = value.partition("=")
    if not separator or not label or not path:
        raise invalid_argument(
            message=f"--stem must be LABEL=PATH, got {value!r}",
            hint="Pass each stem as --stem LABEL=PATH, e.g. --stem Kick=./kick.wav.",
        )
    return label, path


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)
