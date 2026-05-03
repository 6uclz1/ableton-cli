from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..remix.arranger import apply_plan, export_plan, generate_plan
from ..remix.manifest import (
    init_manifest,
    inspect_manifest,
    load_manifest,
    resolve_manifest_path,
    set_target,
)
from ..remix.mix import (
    device_chain_apply,
    mix_macro,
    setup_mix,
    setup_returns,
    setup_sidechain,
    setup_sound,
)
from ..remix.qa import run_qa
from ..remix.vocal_chop import build_vocal_chop
from ..runtime import execute_command
from ..runtime import get_client as _runtime_get_client

remix_app = typer.Typer(help="Remix project workflow commands", no_args_is_help=True)
generate_app = typer.Typer(help="Pattern generation commands", no_args_is_help=True)
device_chain_app = typer.Typer(help="Remix device chain commands", no_args_is_help=True)


def get_client(ctx: typer.Context):  # noqa: ANN201
    return _runtime_get_client(ctx)


@remix_app.command("init")
def remix_init(
    ctx: typer.Context,
    source: Annotated[Path, typer.Option("--source", help="Absolute source audio path")],
    project: Annotated[Path, typer.Option("--project", help="Project directory or manifest path")],
    rights_status: Annotated[
        str,
        typer.Option("--rights-status", help="Rights status metadata"),
    ] = "unspecified",
) -> None:
    def _action() -> dict[str, object]:
        manifest_path = init_manifest(
            source_audio_path=source,
            project=project,
            rights_status=rights_status,
        )
        return {"project": str(manifest_path), **inspect_manifest(manifest_path)}

    execute_command(
        ctx,
        command="remix init",
        args={"source": str(source), "project": str(project), "rights_status": rights_status},
        action=_action,
    )


@remix_app.command("inspect")
def remix_inspect(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="remix inspect",
        args={"project": str(project)},
        action=lambda: inspect_manifest(project),
    )


@remix_app.command("set-target")
def remix_set_target(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    bpm: Annotated[float | None, typer.Option("--bpm", help="Target BPM")] = None,
    key: Annotated[str | None, typer.Option("--key", help="Target key")] = None,
) -> None:
    execute_command(
        ctx,
        command="remix set-target",
        args={"project": str(project), "bpm": bpm, "key": key},
        action=lambda: set_target(project, bpm=bpm, key=key),
    )


@remix_app.command("plan")
def remix_plan(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    style: Annotated[
        str, typer.Option("--style", help="Arrangement template style")
    ] = "anime-club",
    bars: Annotated[str | None, typer.Option("--bars", help="Explicit section bars")] = None,
    length: Annotated[str, typer.Option("--length", help="Arrangement length mode")] = "full",
) -> None:
    execute_command(
        ctx,
        command="remix plan",
        args={"project": str(project), "style": style, "bars": bars, "length": length},
        action=lambda: generate_plan(project, style=style, bars=bars, length=length),
    )


@remix_app.command("arrange")
def remix_arrange(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    form: Annotated[str, typer.Option("--form", help="Arrangement form")] = "anime-club",
    length: Annotated[str, typer.Option("--length", help="Arrangement length mode")] = "full",
    bars: Annotated[str | None, typer.Option("--bars", help="Explicit section bars")] = None,
) -> None:
    execute_command(
        ctx,
        command="remix arrange",
        args={"project": str(project), "form": form, "length": length, "bars": bars},
        action=lambda: generate_plan(project, style=form, bars=bars, length=length),
    )


@remix_app.command("apply")
def remix_apply(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Return planned batch steps only")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm applying plan")] = False,
) -> None:
    def _action() -> dict[str, object]:
        manifest = load_manifest(resolve_manifest_path(project))
        planned = apply_plan(manifest, dry_run=dry_run)
        if dry_run:
            return planned
        if not yes:
            return {**planned, "applied": False, "reason": "Pass --yes to execute the batch plan."}
        batch_result = get_client(ctx).execute_batch(planned["steps"])  # type: ignore[arg-type]
        return {**planned, "applied": True, "batch": batch_result}

    execute_command(
        ctx,
        command="remix apply",
        args={"project": str(project), "dry_run": dry_run, "yes": yes},
        action=_action,
    )


@remix_app.command("import-assets")
def remix_import_assets(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    to_arrangement: Annotated[
        bool,
        typer.Option("--to-arrangement", help="Build arrangement import steps"),
    ] = False,
) -> None:
    def _action() -> dict[str, object]:
        plan = generate_plan(project, style="anime-club") if to_arrangement else {"steps": []}
        return {
            "project": str(resolve_manifest_path(project)),
            "to_arrangement": to_arrangement,
            **plan,
        }

    execute_command(
        ctx,
        command="remix import-assets",
        args={"project": str(project), "to_arrangement": to_arrangement},
        action=_action,
    )


@remix_app.command("vocal-chop")
def remix_vocal_chop(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    source: Annotated[str, typer.Option("--source", help="Source asset role")] = "vocal",
    section: Annotated[str, typer.Option("--section", help="Source section name")] = "chorus",
    slice_grid: Annotated[str, typer.Option("--slice", help="Slice grid")] = "1/8",
    target_track: Annotated[
        str | None, typer.Option("--target-track", help="Target track ref key")
    ] = None,
    create_trigger: Annotated[
        bool,
        typer.Option("--create-trigger", help="Create trigger MIDI clip"),
    ] = False,
) -> None:
    execute_command(
        ctx,
        command="remix vocal-chop",
        args={
            "project": str(project),
            "source": source,
            "section": section,
            "slice": slice_grid,
            "target_track": target_track,
            "create_trigger": create_trigger,
        },
        action=lambda: build_vocal_chop(
            project,
            source=source,
            section=section,
            slice_grid=slice_grid,
            target_track=target_track,
            create_trigger=create_trigger,
        ),
    )


@remix_app.command("qa")
def remix_qa(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="remix qa",
        args={"project": str(project)},
        action=lambda: run_qa(project),
    )


@remix_app.command("export-plan")
def remix_export_plan(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    target: Annotated[Path, typer.Option("--target", help="Absolute export target path")],
) -> None:
    execute_command(
        ctx,
        command="remix export-plan",
        args={"project": str(project), "target": str(target)},
        action=lambda: export_plan(project, target=target),
    )


@remix_app.command("setup-sound")
def remix_setup_sound(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    kit: Annotated[str | None, typer.Option("--kit", help="Drum kit search query")] = None,
    bass: Annotated[str | None, typer.Option("--bass", help="Bass search query")] = None,
    lead: Annotated[str | None, typer.Option("--lead", help="Lead search query")] = None,
) -> None:
    execute_command(
        ctx,
        command="remix setup-sound",
        args={"project": str(project), "kit": kit, "bass": bass, "lead": lead},
        action=lambda: setup_sound(project, kit=kit, bass=bass, lead=lead),
    )


@remix_app.command("mix-macro")
def remix_mix_macro(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    preset: Annotated[str, typer.Option("--preset", help="Mix macro preset")] = "anime-club-basic",
) -> None:
    execute_command(
        ctx,
        command="remix mix-macro",
        args={"project": str(project), "preset": preset},
        action=lambda: mix_macro(project, preset=preset),
    )


@remix_app.command("setup-mix")
def remix_setup_mix(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="remix setup-mix",
        args={"project": str(project)},
        action=lambda: setup_mix(project),
    )


@remix_app.command("setup-returns")
def remix_setup_returns(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="remix setup-returns",
        args={"project": str(project)},
        action=lambda: setup_returns(project),
    )


@remix_app.command("setup-sidechain")
def remix_setup_sidechain(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="remix setup-sidechain",
        args={"project": str(project)},
        action=lambda: setup_sidechain(project),
    )


@generate_app.command("drums")
def remix_generate_drums(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project")],
    style: Annotated[str, typer.Option("--style")] = "dnb",
    section: Annotated[str | None, typer.Option("--section")] = None,
    apply: Annotated[bool, typer.Option("--apply")] = False,
) -> None:
    execute_command(
        ctx,
        command="remix generate drums",
        args={"project": str(project), "style": style, "section": section, "apply": apply},
        action=lambda: {
            "project": str(resolve_manifest_path(project)),
            "kind": "drums",
            "style": style,
            "section": section,
            "apply": apply,
            "pattern": {"notes": []},
        },
    )


@generate_app.command("bass")
def remix_generate_bass(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project")],
    pattern: Annotated[str, typer.Option("--pattern")] = "offbeat",
    key: Annotated[str | None, typer.Option("--key")] = None,
    apply: Annotated[bool, typer.Option("--apply")] = False,
) -> None:
    execute_command(
        ctx,
        command="remix generate bass",
        args={"project": str(project), "pattern": pattern, "key": key, "apply": apply},
        action=lambda: {
            "project": str(resolve_manifest_path(project)),
            "kind": "bass",
            "pattern_name": pattern,
            "key": key,
            "apply": apply,
            "pattern": {"notes": []},
        },
    )


@generate_app.command("chords")
def remix_generate_chords(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project")],
    progression: Annotated[str, typer.Option("--progression")],
    apply: Annotated[bool, typer.Option("--apply")] = False,
) -> None:
    execute_command(
        ctx,
        command="remix generate chords",
        args={"project": str(project), "progression": progression, "apply": apply},
        action=lambda: {
            "project": str(resolve_manifest_path(project)),
            "kind": "chords",
            "progression": progression,
            "apply": apply,
            "pattern": {"notes": []},
        },
    )


@device_chain_app.command("apply")
def remix_device_chain_apply(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project")],
    chain: Annotated[str, typer.Option("--chain")],
) -> None:
    execute_command(
        ctx,
        command="remix device-chain apply",
        args={"project": str(project), "chain": chain},
        action=lambda: device_chain_apply(project, chain=chain),
    )


remix_app.add_typer(generate_app, name="generate")
remix_app.add_typer(device_chain_app, name="device-chain")


def register(app: typer.Typer) -> None:
    app.add_typer(remix_app, name="remix")
