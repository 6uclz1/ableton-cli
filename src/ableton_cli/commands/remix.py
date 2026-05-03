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
from ..remix.mastering import (
    add_reference,
    analyze_render,
    apply_chain_plan,
    list_references,
    mark_chain_applied,
    plan_chain,
    profiles_list,
    remove_reference,
    run_mastering_qa,
    set_targets,
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
mastering_app = typer.Typer(help="Remix mastering workflow commands", no_args_is_help=True)
mastering_profile_app = typer.Typer(help="Mastering profile commands", no_args_is_help=True)
mastering_target_app = typer.Typer(help="Mastering target commands", no_args_is_help=True)
mastering_reference_app = typer.Typer(help="Mastering reference commands", no_args_is_help=True)


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
    include_mastering: Annotated[
        bool,
        typer.Option("--include-mastering", help="Include mastering QA checks"),
    ] = False,
    render: Annotated[
        Path | None,
        typer.Option("--render", help="Rendered audio path for mastering QA"),
    ] = None,
) -> None:
    def _action() -> dict[str, object]:
        qa = run_qa(project)
        if not include_mastering:
            return qa
        mastering_qa = run_mastering_qa(project, render=render, strict=False)
        return {
            **qa,
            "ok": bool(qa["ok"] and mastering_qa["ok"]),
            "mastering": mastering_qa,
        }

    execute_command(
        ctx,
        command="remix qa",
        args={
            "project": str(project),
            "include_mastering": include_mastering,
            "render": None if render is None else str(render),
        },
        action=_action,
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


@mastering_profile_app.command("list")
def remix_mastering_profile_list(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="remix mastering profile list",
        args={},
        action=profiles_list,
    )


@mastering_target_app.command("set")
def remix_mastering_target_set(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    profile: Annotated[str, typer.Option("--profile", help="Mastering target profile")],
    integrated_lufs: Annotated[
        float | None,
        typer.Option("--integrated-lufs", help="Integrated LUFS target"),
    ] = None,
    true_peak_dbtp_max: Annotated[
        float | None,
        typer.Option("--true-peak-dbtp-max", help="Maximum true peak in dBTP"),
    ] = None,
    lra_lu_min: Annotated[float | None, typer.Option("--lra-lu-min")] = None,
    lra_lu_max: Annotated[float | None, typer.Option("--lra-lu-max")] = None,
    crest_db_min: Annotated[
        float | None,
        typer.Option("--crest-db-min", help="Minimum crest factor"),
    ] = None,
    spectrum_profile: Annotated[
        str | None,
        typer.Option("--spectrum-profile", help="Spectrum diagnostic profile"),
    ] = None,
    notes: Annotated[str | None, typer.Option("--notes", help="Target notes")] = None,
) -> None:
    execute_command(
        ctx,
        command="remix mastering target set",
        args={
            "project": str(project),
            "profile": profile,
            "integrated_lufs": integrated_lufs,
            "true_peak_dbtp_max": true_peak_dbtp_max,
            "lra_lu_min": lra_lu_min,
            "lra_lu_max": lra_lu_max,
            "crest_db_min": crest_db_min,
            "spectrum_profile": spectrum_profile,
            "notes": notes,
        },
        action=lambda: set_targets(
            project,
            profile=profile,
            integrated_lufs=integrated_lufs,
            true_peak_dbtp_max=true_peak_dbtp_max,
            lra_lu_min=lra_lu_min,
            lra_lu_max=lra_lu_max,
            crest_db_min=crest_db_min,
            spectrum_profile=spectrum_profile,
            notes=notes,
        ),
    )


@mastering_reference_app.command("add")
def remix_mastering_reference_add(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    path: Annotated[Path, typer.Option("--path", help="Reference audio path")],
    role: Annotated[str, typer.Option("--role", help="Reference role")],
    reference_id: Annotated[str, typer.Option("--id", help="Reference id")],
    notes: Annotated[str, typer.Option("--notes", help="Reference notes")] = "",
    analyze: Annotated[bool, typer.Option("--analyze", help="Analyze reference on add")] = False,
    report_dir: Annotated[
        Path | None,
        typer.Option("--report-dir", help="Analysis report directory"),
    ] = None,
) -> None:
    execute_command(
        ctx,
        command="remix mastering reference add",
        args={
            "project": str(project),
            "path": str(path),
            "role": role,
            "id": reference_id,
            "notes": notes,
            "analyze": analyze,
            "report_dir": None if report_dir is None else str(report_dir),
        },
        action=lambda: add_reference(
            project,
            path=path,
            role=role,
            reference_id=reference_id,
            notes=notes,
            analyze=analyze,
            report_dir=report_dir,
        ),
    )


@mastering_reference_app.command("list")
def remix_mastering_reference_list(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
) -> None:
    execute_command(
        ctx,
        command="remix mastering reference list",
        args={"project": str(project)},
        action=lambda: list_references(project),
    )


@mastering_reference_app.command("remove")
def remix_mastering_reference_remove(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    reference_id: Annotated[str, typer.Option("--id", help="Reference id")],
) -> None:
    execute_command(
        ctx,
        command="remix mastering reference remove",
        args={"project": str(project), "id": reference_id},
        action=lambda: remove_reference(project, reference_id=reference_id),
    )


@mastering_app.command("analyze")
def remix_mastering_analyze(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    render: Annotated[Path, typer.Option("--render", help="Rendered audio path")],
    reference: Annotated[
        str | None,
        typer.Option("--reference", help="Registered reference id"),
    ] = None,
    report_dir: Annotated[
        Path | None,
        typer.Option("--report-dir", help="Analysis report directory"),
    ] = None,
) -> None:
    execute_command(
        ctx,
        command="remix mastering analyze",
        args={
            "project": str(project),
            "render": str(render),
            "reference": reference,
            "report_dir": None if report_dir is None else str(report_dir),
        },
        action=lambda: analyze_render(
            project,
            render=render,
            reference_id=reference,
            report_dir=report_dir,
        ),
    )


@mastering_app.command("plan")
def remix_mastering_plan(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    target: Annotated[
        str | None,
        typer.Option("--target", help="Mastering target profile"),
    ] = None,
    chain: Annotated[
        str,
        typer.Option("--chain", help="Comma-separated master chain"),
    ] = "utility,eq8,compressor,limiter",
) -> None:
    execute_command(
        ctx,
        command="remix mastering plan",
        args={"project": str(project), "target": target, "chain": chain},
        action=lambda: plan_chain(project, target_profile=target, chain=chain),
    )


@mastering_app.command("apply")
def remix_mastering_apply(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Return planned batch steps only")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm applying plan")] = False,
) -> None:
    def _action() -> dict[str, object]:
        manifest = load_manifest(resolve_manifest_path(project))
        planned = apply_chain_plan(manifest, dry_run=dry_run)
        if dry_run:
            return planned
        if not yes:
            return {**planned, "applied": False, "reason": "Pass --yes to execute the batch plan."}
        batch_result = get_client(ctx).execute_batch(planned["steps"])  # type: ignore[arg-type]
        applied_plan = mark_chain_applied(project, batch_result)
        return {
            **planned,
            "applied": True,
            "batch": batch_result,
            "master_chain_plan": applied_plan,
        }

    execute_command(
        ctx,
        command="remix mastering apply",
        args={"project": str(project), "dry_run": dry_run, "yes": yes},
        action=_action,
    )


@mastering_app.command("qa")
def remix_mastering_qa(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Manifest path")],
    render: Annotated[
        Path | None,
        typer.Option("--render", help="Rendered audio path"),
    ] = None,
    strict: Annotated[bool, typer.Option("--strict", help="Treat unapplied plan as error")] = False,
) -> None:
    execute_command(
        ctx,
        command="remix mastering qa",
        args={
            "project": str(project),
            "render": None if render is None else str(render),
            "strict": strict,
        },
        action=lambda: run_mastering_qa(project, render=render, strict=strict),
    )


remix_app.add_typer(generate_app, name="generate")
remix_app.add_typer(device_chain_app, name="device-chain")
mastering_app.add_typer(mastering_profile_app, name="profile")
mastering_app.add_typer(mastering_target_app, name="target")
mastering_app.add_typer(mastering_reference_app, name="reference")
remix_app.add_typer(mastering_app, name="mastering")


def register(app: typer.Typer) -> None:
    app.add_typer(remix_app, name="remix")
