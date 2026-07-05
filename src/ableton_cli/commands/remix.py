from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..commands._validation import invalid_argument, require_absolute_path, require_non_empty_string
from ..remix.arranger import generate_plan
from ..remix.manifest import create_manifest, load_manifest, save_manifest, set_target
from ..remix.qa import run_qa
from ..runtime import execute_command

remix_app = typer.Typer(help="Manifest-first remix planning commands", no_args_is_help=True)


@remix_app.command("init")
def init(
    ctx: typer.Context,
    source: Annotated[Path, typer.Option("--source", help="Absolute local source audio path")],
    project: Annotated[Path, typer.Option("--project", help="Project directory")],
    rights_status: Annotated[
        str,
        typer.Option("--rights-status", help="Rights status such as private_test"),
    ] = "private_test",
) -> None:
    def _run() -> dict[str, object]:
        source_path = Path(
            require_absolute_path(
                "source",
                str(source),
                hint="Pass an absolute source audio path.",
            )
        )
        parsed_rights_status = require_non_empty_string(
            "rights_status",
            rights_status,
            hint="Pass a non-empty rights status.",
        )
        return create_manifest(
            source=source_path,
            project_dir=project,
            rights_status=parsed_rights_status,
        )

    execute_command(
        ctx,
        command="remix init",
        args={"source": str(source), "project": str(project), "rights_status": rights_status},
        action=_run,
    )


@remix_app.command("set-target")
def target_set(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Path to remix_project.json")],
    bpm: Annotated[float, typer.Option("--bpm", help="Target BPM")],
    key: Annotated[str, typer.Option("--key", help="Target musical key")],
) -> None:
    execute_command(
        ctx,
        command="remix set-target",
        args={"project": str(project), "bpm": bpm, "key": key},
        action=lambda: set_target(project=project, bpm=bpm, key=key),
    )


@remix_app.command("plan")
def plan(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Path to remix_project.json")],
    style: Annotated[str, typer.Option("--style", help="Remix style template")],
    bars: Annotated[int | None, typer.Option("--bars", help="Optional target bar count")] = None,
    length: Annotated[str, typer.Option("--length", help="Arrangement length label")] = "full",
    dynamics: Annotated[
        str,
        typer.Option(
            "--dynamics",
            help="Arrangement dynamics mode: none, section-profiles, explicit",
        ),
    ] = "section-profiles",
    drum_policy: Annotated[
        str,
        typer.Option("--drum-policy", help="Drum policy: keep, off-in-breaks, strict"),
    ] = "off-in-breaks",
    section_profile: Annotated[
        Path | None,
        typer.Option("--section-profile", help="Explicit section profile JSON"),
    ] = None,
) -> None:
    def _run() -> dict[str, object]:
        manifest = load_manifest(project)
        arrangement_plan = generate_plan(
            manifest,
            style=style,
            bars=bars,
            length=length,
            dynamics=dynamics,
            drum_policy=drum_policy,
            section_profile=section_profile,
        )
        manifest["arrangement_plan"] = arrangement_plan
        save_manifest(project, manifest)
        return arrangement_plan

    execute_command(
        ctx,
        command="remix plan",
        args={
            "project": str(project),
            "style": style,
            "bars": bars,
            "length": length,
            "dynamics": dynamics,
            "drum_policy": drum_policy,
            "section_profile": str(section_profile) if section_profile is not None else None,
        },
        action=_run,
    )


@remix_app.command("apply")
def apply(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Path to remix_project.json")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Return planned steps only")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm applying planned steps")] = False,
) -> None:
    def _run() -> dict[str, object]:
        manifest = load_manifest(project)
        plan_payload = manifest.get("arrangement_plan") or {}
        steps = plan_payload.get("steps", []) if isinstance(plan_payload, dict) else []
        if not dry_run and not yes:
            raise invalid_argument(
                message="remix apply requires --dry-run or --yes",
                hint="Inspect 'remix apply --dry-run' before applying with --yes.",
            )
        return {
            "project": str(project),
            "dry_run": dry_run,
            "applied": bool(yes and not dry_run),
            "steps": steps,
        }

    execute_command(
        ctx,
        command="remix apply",
        args={"project": str(project), "dry_run": dry_run, "yes": yes},
        action=_run,
    )


@remix_app.command("qa")
def qa(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Path to remix_project.json")],
    include_mastering: Annotated[
        bool,
        typer.Option("--include-mastering", help="Keep mastering readiness in the QA request"),
    ] = False,
    render: Annotated[Path | None, typer.Option("--render", help="Optional render path")] = None,
) -> None:
    def _run() -> dict[str, object]:
        manifest = load_manifest(project)
        result = run_qa(manifest)
        manifest["qa"] = {
            **result,
            "include_mastering": include_mastering,
            "render": str(render) if render is not None else None,
        }
        save_manifest(project, manifest)
        return manifest["qa"]

    execute_command(
        ctx,
        command="remix qa",
        args={
            "project": str(project),
            "include_mastering": include_mastering,
            "render": str(render) if render is not None else None,
        },
        action=_run,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(remix_app, name="remix")
