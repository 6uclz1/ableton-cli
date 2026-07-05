from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..remix.manifest import add_asset, import_sections, load_manifest, save_manifest
from ..runtime import execute_command

audio_app = typer.Typer(help="Audio asset and analysis commands", no_args_is_help=True)
asset_app = typer.Typer(help="Audio asset commands", no_args_is_help=True)
sections_app = typer.Typer(help="Audio section-map commands", no_args_is_help=True)


@asset_app.command("add")
def asset_add(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Path to remix_project.json")],
    role: Annotated[str, typer.Option("--role", help="Asset role such as full_mix or drums")],
    path: Annotated[Path, typer.Option("--path", help="Absolute local audio path")],
) -> None:
    execute_command(
        ctx,
        command="audio asset add",
        args={"project": str(project), "role": role, "path": str(path)},
        action=lambda: add_asset(project=project, role=role, path=path),
    )


@sections_app.command("import")
def sections_import(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Path to remix_project.json")],
    sections: Annotated[str, typer.Option("--sections", help="Comma-separated section ranges")],
) -> None:
    execute_command(
        ctx,
        command="audio sections import",
        args={"project": str(project), "sections": sections},
        action=lambda: import_sections(project=project, sections=sections),
    )


@audio_app.command("analyze")
def analyze(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Path to remix_project.json")],
) -> None:
    def _run() -> dict[str, object]:
        manifest = load_manifest(project)
        analysis = {
            "status": "manual_or_external_required",
            "message": (
                "Record BPM, key, chord, and section notes before arranging harmonic layers."
            ),
        }
        manifest["analysis"] = analysis
        save_manifest(project, manifest)
        return {"project": str(project), "analysis": analysis}

    execute_command(ctx, command="audio analyze", args={"project": str(project)}, action=_run)


audio_app.add_typer(asset_app, name="asset")
audio_app.add_typer(sections_app, name="sections")


def register(app: typer.Typer) -> None:
    app.add_typer(audio_app, name="audio")
