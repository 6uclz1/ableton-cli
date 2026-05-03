from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..remix.analyze import analyze_audio, import_beatgrid, import_sections
from ..remix.assets import add_asset, list_assets, remove_asset
from ..remix.manifest import resolve_manifest_path
from ..remix.stems import list_stems, split_stems
from ..runtime import execute_command
from . import _audio_loudness_commands, _audio_reference_commands, _audio_spectrum_commands

audio_app = typer.Typer(help="Audio asset and analysis commands", no_args_is_help=True)
asset_app = typer.Typer(help="Audio asset registry commands", no_args_is_help=True)
sections_app = typer.Typer(help="Audio section map commands", no_args_is_help=True)
beatgrid_app = typer.Typer(help="Audio beatgrid commands", no_args_is_help=True)
stems_app = typer.Typer(help="Audio stem commands", no_args_is_help=True)
loudness_app = typer.Typer(help="Offline loudness analysis commands", no_args_is_help=True)
spectrum_app = typer.Typer(help="Offline spectrum analysis commands", no_args_is_help=True)
reference_app = typer.Typer(help="Reference comparison commands", no_args_is_help=True)


@asset_app.command("add")
def audio_asset_add(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    role: Annotated[str, typer.Option("--role", help="Asset role")],
    path: Annotated[Path, typer.Option("--path", help="Absolute audio path")],
) -> None:
    execute_command(
        ctx,
        command="audio asset add",
        args={"project": str(project), "role": role, "path": str(path)},
        action=lambda: {
            "project": str(resolve_manifest_path(project)),
            "asset": add_asset(project, role=role, path=path),
            **add_asset_result(project),
        },
    )


def add_asset_result(project: Path) -> dict[str, object]:
    assets = list_assets(project)
    return {"asset_count": len(assets)}


@asset_app.command("list")
def audio_asset_list(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="audio asset list",
        args={"project": str(project)},
        action=lambda: {
            "project": str(resolve_manifest_path(project)),
            "asset_count": len(list_assets(project)),
            "assets": list_assets(project),
        },
    )


@asset_app.command("remove")
def audio_asset_remove(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    role: Annotated[str, typer.Option("--role", help="Asset role")],
    path: Annotated[Path, typer.Option("--path", help="Absolute audio path")],
) -> None:
    execute_command(
        ctx,
        command="audio asset remove",
        args={"project": str(project), "role": role, "path": str(path)},
        action=lambda: remove_asset(project, role=role, path=path),
    )


@sections_app.command("import")
def audio_sections_import(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    sections: Annotated[str, typer.Option("--sections", help="Section specs")],
) -> None:
    execute_command(
        ctx,
        command="audio sections import",
        args={"project": str(project), "sections": sections},
        action=lambda: import_sections(project, sections),
    )


@beatgrid_app.command("import")
def audio_beatgrid_import(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    downbeats: Annotated[str, typer.Option("--downbeats", help="Comma-separated downbeat times")],
) -> None:
    execute_command(
        ctx,
        command="audio beatgrid import",
        args={"project": str(project), "downbeats": downbeats},
        action=lambda: import_beatgrid(project, downbeats),
    )


@audio_app.command("analyze")
def audio_analyze(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    detect: Annotated[
        str, typer.Option("--detect", help="Comma-separated detectors")
    ] = "bpm,key,downbeats,sections",
    manual_bpm: Annotated[float | None, typer.Option("--manual-bpm")] = None,
    manual_key: Annotated[str | None, typer.Option("--manual-key")] = None,
) -> None:
    execute_command(
        ctx,
        command="audio analyze",
        args={
            "project": str(project),
            "detect": detect,
            "manual_bpm": manual_bpm,
            "manual_key": manual_key,
        },
        action=lambda: analyze_audio(
            project,
            detect=detect,
            manual_bpm=manual_bpm,
            manual_key=manual_key,
        ),
    )


@stems_app.command("split")
def audio_stems_split(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    provider: Annotated[str, typer.Option("--provider", help="Stem provider")] = "manual",
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Absolute stem output directory"),
    ] = None,
) -> None:
    out_path = Path.cwd() if out is None else out
    execute_command(
        ctx,
        command="audio stems split",
        args={"project": str(project), "provider": provider, "out": str(out_path)},
        action=lambda: split_stems(project, provider=provider, out=out_path),
    )


@stems_app.command("list")
def audio_stems_list(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="audio stems list",
        args={"project": str(project)},
        action=lambda: list_stems(project),
    )


audio_app.add_typer(asset_app, name="asset")
audio_app.add_typer(sections_app, name="sections")
audio_app.add_typer(beatgrid_app, name="beatgrid")
audio_app.add_typer(stems_app, name="stems")
_audio_loudness_commands.register(loudness_app)
_audio_spectrum_commands.register(spectrum_app)
_audio_reference_commands.register(reference_app)
audio_app.add_typer(loudness_app, name="loudness")
audio_app.add_typer(spectrum_app, name="spectrum")
audio_app.add_typer(reference_app, name="reference")


def register(app: typer.Typer) -> None:
    app.add_typer(audio_app, name="audio")
