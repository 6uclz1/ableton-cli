from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .manifest import load_manifest, remix_error, resolve_manifest_path, save_manifest
from .mastering_profiles import list_profiles, profile_targets

# The fields mastering QA reads from each report kind, as written by the analysis
# plugin's ``--report-out``; the audio a report measures is in its source field.
_REPORT_FIELDS: dict[str, tuple[str, ...]] = {
    "loudness": ("path", "integrated_lufs", "true_peak_dbtp", "crest_db", "clipping_sample_count"),
    "spectrum": ("path", "bands", "stereo", "warnings"),
    "reference_compare": ("candidate", "reference", "delta"),
}
_REPORT_SOURCE_FIELD = {"loudness": "path", "spectrum": "path", "reference_compare": "candidate"}


def profiles_list() -> dict[str, Any]:
    return list_profiles()


def set_targets(
    project: str | Path,
    *,
    profile: str,
    integrated_lufs: float | None = None,
    true_peak_dbtp_max: float | None = None,
    lra_lu_min: float | None = None,
    lra_lu_max: float | None = None,
    crest_db_min: float | None = None,
    spectrum_profile: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    targets = profile_targets(profile)
    overrides = {
        "integrated_lufs": integrated_lufs,
        "true_peak_dbtp_max": true_peak_dbtp_max,
        "lra_lu_min": lra_lu_min,
        "lra_lu_max": lra_lu_max,
        "crest_db_min": crest_db_min,
        "spectrum_profile": spectrum_profile,
        "notes": notes,
    }
    for key, value in overrides.items():
        if value is not None:
            targets[key] = value
    manifest["mastering_targets"] = targets
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "mastering_targets": targets}


def add_reference(
    project: str | Path,
    *,
    path: str | Path,
    role: str,
    reference_id: str,
    notes: str = "",
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    audio_path = Path(path).expanduser()
    if not audio_path.exists():
        raise remix_error(
            message=f"reference track not found: {audio_path}",
            hint="Pass an existing --path for the reference track.",
        )
    if any(item.get("id") == reference_id for item in manifest.get("reference_tracks", [])):
        raise remix_error(
            message=f"reference id already exists: {reference_id}",
            hint="Use a unique --id or remove the existing reference.",
        )
    reference = {
        "id": reference_id,
        "path": str(audio_path.resolve()),
        "role": role,
        "notes": notes,
    }
    manifest.setdefault("reference_tracks", []).append(reference)
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "reference": reference}


def list_references(project: str | Path) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    references = manifest.get("reference_tracks", [])
    return {
        "project": str(manifest_path),
        "reference_count": len(references),
        "references": references,
    }


def remove_reference(project: str | Path, *, reference_id: str) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    references = manifest.get("reference_tracks", [])
    kept = [item for item in references if item.get("id") != reference_id]
    if len(kept) == len(references):
        raise remix_error(
            message=f"reference id not found: {reference_id}",
            hint="Use 'remix mastering reference list' to inspect references.",
        )
    manifest["reference_tracks"] = kept
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "removed": reference_id, "reference_count": len(kept)}


def add_report(project: str | Path, *, kind: str, report: str | Path) -> dict[str, Any]:
    """Register an analysis report so mastering QA reads it for the audio it measures."""
    if kind not in _REPORT_FIELDS:
        raise remix_error(
            message=f"unsupported report kind: {kind}",
            hint=f"Use one of: {', '.join(_REPORT_FIELDS)}.",
        )
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    report_path = Path(report).expanduser().resolve()
    payload = _read_report(report_path)
    missing = [field for field in _REPORT_FIELDS[kind] if field not in payload]
    if missing:
        raise remix_error(
            message=f"{kind} report {report_path} is missing {', '.join(missing)}",
            hint=f"Pass a report written by 'ableton-cli analysis ... --report-out' for {kind}.",
        )
    record = _report_record(
        kind=kind,
        path=report_path,
        source_audio_path=Path(str(payload[_REPORT_SOURCE_FIELD[kind]])).expanduser(),
        payload=payload,
    )
    manifest.setdefault("analysis_reports", []).append(record)
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "report": record}


def _read_report(report_path: Path) -> dict[str, Any]:
    if not report_path.is_file():
        raise remix_error(
            message=f"report not found: {report_path}",
            hint="Pass the --report-out path of an analysis command.",
        )
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise remix_error(
            message=f"report is not valid JSON: {report_path} ({exc.msg})",
            hint="Pass the --report-out path of an analysis command.",
        ) from exc
    if not isinstance(payload, dict):
        raise remix_error(
            message=f"report must be a JSON object: {report_path}",
            hint="Pass the --report-out path of an analysis command.",
        )
    return payload


def plan_chain(
    project: str | Path,
    *,
    target_profile: str | None = None,
    chain: str = "utility,eq8,compressor,limiter",
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    targets = manifest.get("mastering_targets") or profile_targets(
        target_profile or "anime-club-demo"
    )
    if target_profile is not None and targets.get("profile") != target_profile:
        targets = profile_targets(target_profile)
        manifest["mastering_targets"] = targets
    devices = [_planned_device(name.strip(), targets) for name in chain.split(",") if name.strip()]
    plan = {
        "status": "planned",
        "target_profile": targets.get("profile", target_profile or "anime-club-demo"),
        "created_at": _now(),
        "devices": devices,
        "warnings": _planning_warnings(manifest, targets),
    }
    manifest["master_chain_plan"] = plan
    save_manifest(manifest_path, manifest)
    return {"project": str(manifest_path), "master_chain_plan": plan, "steps": _plan_steps(plan)}


def apply_chain_plan(manifest: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    plan = manifest.get("master_chain_plan")
    if not isinstance(plan, dict):
        raise remix_error(
            message="master_chain_plan is missing",
            hint="Run 'ableton-cli remix mastering plan' before apply.",
        )
    steps = _plan_steps(plan)
    return {"dry_run": dry_run, "step_count": len(steps), "steps": steps}


def mark_chain_applied(project: str | Path, batch_result: dict[str, Any]) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    plan = manifest.get("master_chain_plan")
    if not isinstance(plan, dict):
        raise remix_error(
            message="master_chain_plan is missing",
            hint="Run 'ableton-cli remix mastering plan' before apply.",
        )
    plan["status"] = "applied"
    plan["applied_at"] = _now()
    plan["batch_result"] = batch_result
    save_manifest(manifest_path, manifest)
    return plan


def run_mastering_qa(
    project: str | Path,
    *,
    render: str | Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    targets = manifest.get("mastering_targets") or {}

    render_path = Path(render).expanduser() if render is not None else None
    if render_path is not None and not render_path.exists():
        errors.append(
            {"code": "missing_render", "message": f"Render file not found: {render_path}"}
        )

    latest_loudness = _latest_report(manifest, "loudness", render_path)
    latest_spectrum = _latest_report(manifest, "spectrum", render_path)
    if render_path is not None and latest_loudness is None:
        errors.append(
            {"code": "missing_loudness_report", "message": "No loudness report for render"}
        )
    if render_path is not None and latest_spectrum is None:
        warnings.append(
            {"code": "missing_spectrum_report", "message": "No spectrum report for render"}
        )

    loudness_payload = _load_report_payload(latest_loudness)
    if loudness_payload is not None:
        _qa_loudness(loudness_payload, targets, errors, warnings)
    spectrum_payload = _load_report_payload(latest_spectrum)
    if spectrum_payload is not None:
        _qa_spectrum(spectrum_payload, warnings)

    plan = manifest.get("master_chain_plan")
    if not isinstance(plan, dict):
        errors.append({"code": "missing_master_chain_plan", "message": "No master chain plan"})
    else:
        device_types = [str(device.get("type", "")) for device in plan.get("devices", [])]
        if "limiter" not in device_types:
            errors.append({"code": "missing_limiter", "message": "Master chain has no limiter"})
        if strict and plan.get("status") not in {"applied", "intentional_skip"}:
            errors.append(
                {
                    "code": "master_chain_not_applied",
                    "message": "Master chain plan has not been applied or intentionally skipped",
                }
            )

    return {
        "project": str(manifest_path),
        "strict": strict,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def _report_record(
    *,
    kind: str,
    path: Path,
    source_audio_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"{source_audio_path.stem}-{kind}-{len(json.dumps(payload, sort_keys=True))}",
        "kind": kind,
        "path": str(path),
        "source_audio_path": str(source_audio_path),
        "created_at": _now(),
    }


def _planned_device(name: str, targets: dict[str, Any]) -> dict[str, Any]:
    normalized = name.lower()
    if normalized == "utility":
        return {
            "type": "utility",
            "purpose": "input_gain_and_width",
            "parameters": {"gain": 0.0, "width": 1.0},
        }
    if normalized == "eq8":
        return {"type": "eq8", "purpose": "broad_tonal_balance", "parameters": []}
    if normalized == "compressor":
        return {"type": "compressor", "purpose": "gentle_bus_control", "parameters": {}}
    if normalized == "limiter":
        ceiling = _limiter_ceiling_native_value(targets.get("true_peak_dbtp_max", -1.0))
        return {
            "type": "limiter",
            "purpose": "ceiling",
            "parameters": {"ceiling": ceiling},
        }
    raise remix_error(
        message=f"unsupported mastering chain device: {name}",
        hint="Use utility, eq8, compressor, and/or limiter.",
    )


def _plan_steps(plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for device in plan.get("devices", []):
        device_type = device["type"]
        steps.append(
            {
                "name": "device_insert",
                "args": {
                    "track_ref": {"mode": "main"},
                    "device_name": _device_display_name(device_type),
                    "index": -1,
                },
            }
        )
        for key, value in _parameter_items(device):
            steps.append(
                {
                    "name": f"master_effect_{device_type}_set",
                    "args": {
                        "device_ref": {"mode": "query", "query": _device_display_name(device_type)},
                        "parameter_key": key,
                        "value": value,
                    },
                }
            )
    return steps


def _parameter_items(device: dict[str, Any]) -> list[tuple[str, float]]:
    parameters = device.get("parameters")
    if not isinstance(parameters, dict):
        return []
    items: list[tuple[str, float]] = []
    for key, value in parameters.items():
        if isinstance(value, int | float):
            items.append((key, float(value)))
    return items


def _limiter_ceiling_native_value(value: Any) -> float:
    if not isinstance(value, int | float):
        return 0.9701444506645203
    # Ableton Limiter exposes Ceiling as a native 0..1 parameter. The approximate
    # display range is -35 dB to 0 dB, so -1 dB maps near Live's default 0.97 value.
    return round(max(0.0, min(1.0, (float(value) + 35.0) / 35.0)), 6)


def _device_display_name(device_type: str) -> str:
    return {
        "utility": "Utility",
        "eq8": "EQ Eight",
        "compressor": "Compressor",
        "limiter": "Limiter",
    }[device_type]


def _planning_warnings(manifest: dict[str, Any], targets: dict[str, Any]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    latest_loudness = _latest_report(manifest, "loudness", None)
    payload = _load_report_payload(latest_loudness)
    if payload is None:
        return warnings
    true_peak = payload.get("true_peak_dbtp")
    ceiling = targets.get("true_peak_dbtp_max")
    if isinstance(true_peak, int | float) and isinstance(ceiling, int | float):
        if true_peak >= ceiling - 0.5:
            warnings.append(
                {
                    "scope": "master",
                    "code": "limited_true_peak_headroom",
                    "message": "True peak is close to ceiling; do not add global gain",
                }
            )
    crest = payload.get("crest_db")
    crest_min = targets.get("crest_db_min")
    if isinstance(crest, int | float) and isinstance(crest_min, int | float) and crest < crest_min:
        warnings.append(
            {
                "scope": "mix",
                "code": "crest_low",
                "message": "Crest factor is low; avoid stronger bus compression or limiting",
            }
        )
    return warnings


def _qa_loudness(
    payload: dict[str, Any],
    targets: dict[str, Any],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    if payload.get("clipping_sample_count", 0) != 0:
        errors.append({"code": "clipping", "message": "Render contains clipped samples"})
    true_peak = payload.get("true_peak_dbtp")
    ceiling = targets.get("true_peak_dbtp_max")
    if (
        isinstance(true_peak, int | float)
        and isinstance(ceiling, int | float)
        and true_peak > ceiling
    ):
        errors.append(
            {
                "code": "true_peak_over_target",
                "message": f"true_peak_dbtp {true_peak} exceeds target {ceiling}",
            }
        )
    integrated = payload.get("integrated_lufs")
    target_lufs = targets.get("integrated_lufs")
    if isinstance(integrated, int | float) and isinstance(target_lufs, int | float):
        if abs(integrated - target_lufs) > 2.0:
            warnings.append(
                {
                    "code": "integrated_lufs_outside_profile",
                    "message": "Integrated LUFS is outside target profile tolerance",
                }
            )
    crest = payload.get("crest_db")
    crest_min = targets.get("crest_db_min")
    if isinstance(crest, int | float) and isinstance(crest_min, int | float) and crest < crest_min:
        warnings.append({"code": "crest_low", "message": "Crest factor is below target minimum"})


def _qa_spectrum(payload: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    for warning in payload.get("warnings", []):
        if isinstance(warning, dict):
            warnings.append(
                {
                    "code": str(warning.get("code", "spectrum_warning")),
                    "message": str(warning.get("message", "Spectrum profile warning")),
                }
            )
    stereo = payload.get("stereo", {})
    if isinstance(stereo, dict) and stereo.get("mono_low_end_risk") is True:
        warnings.append(
            {"code": "mono_low_end_risk", "message": "Stereo correlation indicates mono risk"}
        )


def _latest_report(
    manifest: dict[str, Any],
    kind: str,
    source_audio_path: Path | None,
) -> dict[str, Any] | None:
    reports = [
        item
        for item in manifest.get("analysis_reports", [])
        if item.get("kind") == kind
        and (
            source_audio_path is None
            or Path(str(item.get("source_audio_path", ""))).expanduser() == source_audio_path
        )
    ]
    if not reports:
        return None
    return sorted(reports, key=lambda item: str(item.get("created_at", "")))[-1]


def _load_report_payload(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if report is None:
        return None
    path = Path(str(report.get("path", ""))).expanduser()
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
