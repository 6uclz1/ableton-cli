"""``plugins install / update / uninstall / sync``.

Every install is pinned to a commit and validated by loading it in a fresh
interpreter. A plugin that installs but does not load is rolled back (the
previous commit is reinstalled, or the new package is removed), so a failed
command leaves the environment and the manifest as they were.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any

from ..errors import AppError, ErrorCode, ExitCode
from .environment import InstalledDistribution, PluginEnvironment
from .github import CommandRunner, PinnedSource, parse_github_url, pin_source
from .manifest import ManifestEntry, read_manifest, write_manifest
from .model import ENTRY_POINT_GROUP


def install_plugin(
    pinned: PinnedSource, *, manifest_path: Path, environment: PluginEnvironment
) -> dict[str, Any]:
    manifest = read_manifest(manifest_path)
    for existing in manifest.values():
        if pinned.source.matches_url(existing.source):
            raise AppError(
                error_code=ErrorCode.INVALID_ARGUMENT,
                message=f"{existing.source} is already installed as plugin '{existing.name}'",
                hint=f"Run 'ableton-cli plugins update {existing.name}' to change its ref.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )
    entry = _install_validated(
        environment,
        pinned,
        previous=environment.find_by_source(pinned.source),
        expected_name=None,
        taken_names=set(manifest),
    )
    manifest[entry.name] = entry
    write_manifest(manifest_path, manifest)
    return {"action": "installed", "plugin": entry.to_dict()}


def pin_managed_plugin(
    name: str, ref: str | None, *, manifest_path: Path, run: CommandRunner
) -> PinnedSource:
    """The commit ``plugins update`` would install; ``ref=None`` keeps the recorded ref."""
    entry = _managed_entry(read_manifest(manifest_path), name)
    return pin_source(entry.source, entry.requested_ref if ref is None else ref, run=run)


def update_plugin(
    name: str, pinned: PinnedSource, *, manifest_path: Path, environment: PluginEnvironment
) -> dict[str, Any]:
    manifest = read_manifest(manifest_path)
    entry = _managed_entry(manifest, name)
    previous = environment.find_by_source(pinned.source)
    if (
        previous is not None
        and previous.commit == pinned.rev
        and entry.rev == pinned.rev
        and entry.requested_ref == pinned.requested_ref
    ):
        return {"action": "unchanged", "plugin": entry.to_dict(), "previous_rev": entry.rev}
    updated = _install_validated(
        environment,
        pinned,
        previous=previous,
        expected_name=name,
        taken_names=set(manifest) - {name},
    )
    manifest[name] = updated
    write_manifest(manifest_path, manifest)
    return {"action": "updated", "plugin": updated.to_dict(), "previous_rev": entry.rev}


def uninstall_plugin(
    name: str, *, manifest_path: Path, environment: PluginEnvironment
) -> dict[str, Any]:
    manifest = read_manifest(manifest_path)
    entry = _managed_entry(manifest, name)
    source, _ = parse_github_url(entry.source)
    installed = environment.find_by_source(source)
    if installed is not None:
        environment.uninstall(installed.name)
    del manifest[name]
    write_manifest(manifest_path, manifest)
    return {
        "action": "uninstalled" if installed is not None else "removed_from_manifest",
        "plugin": entry.to_dict(),
    }


def sync_plugins(*, manifest_path: Path, environment: PluginEnvironment) -> dict[str, Any]:
    """Install every manifest entry whose recorded commit is not the installed one."""
    manifest = read_manifest(manifest_path)
    results: list[dict[str, Any]] = []
    for name in sorted(manifest):
        entry = manifest[name]
        source, _ = parse_github_url(entry.source)
        current = environment.find_by_source(source)
        if current is not None and current.commit == entry.rev:
            results.append({"name": name, "action": "unchanged", "rev": entry.rev})
            continue
        try:
            manifest[name] = _install_validated(
                environment,
                PinnedSource(source=source, requested_ref=entry.requested_ref, rev=entry.rev),
                previous=current,
                expected_name=name,
                taken_names=set(manifest) - {name},
            )
        except AppError as exc:
            exc.details["completed"] = results
            raise
        write_manifest(manifest_path, manifest)
        results.append({"name": name, "action": "installed", "rev": entry.rev})
    return {"plugins": results}


def _install_validated(
    environment: PluginEnvironment,
    pinned: PinnedSource,
    *,
    previous: InstalledDistribution | None,
    expected_name: str | None,
    taken_names: Collection[str],
) -> ManifestEntry:
    environment.install(
        pinned.source.requirement(pinned.rev),
        unpinned=() if previous is None else (previous.name,),
    )
    try:
        installed = environment.find_by_source(pinned.source)
        if installed is None:
            raise AppError(
                error_code=ErrorCode.PLUGIN_INSTALL_FAILED,
                message=f"uv finished but no installed distribution comes from {pinned.source.url}",
                hint="Check that the repository is an installable Python project.",
                exit_code=ExitCode.EXECUTION_FAILED,
            )
        name = _validated_plugin_name(environment, installed, expected_name, taken_names)
    except AppError as exc:
        _roll_back(environment, pinned, previous, exc)
        raise
    return ManifestEntry(
        name=name,
        source=pinned.source.url,
        requested_ref=pinned.requested_ref,
        rev=pinned.rev,
        distribution=installed.name,
        version=installed.version,
    )


def _validated_plugin_name(
    environment: PluginEnvironment,
    installed: InstalledDistribution,
    expected_name: str | None,
    taken_names: Collection[str],
) -> str:
    if len(installed.plugin_names) != 1:
        raise _plugin_invalid(
            f"{installed.name} must expose exactly one '{ENTRY_POINT_GROUP}' entry point, "
            f"found {list(installed.plugin_names)}",
            distribution=installed.name,
        )
    name = installed.plugin_names[0]
    if expected_name is not None and name != expected_name:
        raise _plugin_invalid(
            f"{installed.name} now provides plugin '{name}' instead of '{expected_name}'",
            plugin=name,
        )
    if name in taken_names:
        raise _plugin_invalid(f"Another installed plugin is already named '{name}'", plugin=name)
    report = {item["name"]: item for item in environment.probe()}
    entry = report.get(name)
    if entry is None or entry.get("state") != "loaded":
        raise _plugin_invalid(
            f"Plugin '{name}' from {installed.name} does not load",
            plugin=name,
            load_error=None if entry is None else entry.get("error"),
        )
    return name


def _roll_back(
    environment: PluginEnvironment,
    pinned: PinnedSource,
    previous: InstalledDistribution | None,
    failure: AppError,
) -> None:
    try:
        if previous is not None and previous.commit is not None:
            environment.install(
                pinned.source.requirement(previous.commit), unpinned=(previous.name,)
            )
            return
        current = environment.find_by_source(pinned.source)
        if current is not None:
            environment.uninstall(current.name)
    except AppError as rollback_error:
        failure.details["rollback_error"] = rollback_error.to_payload()


def _managed_entry(manifest: dict[str, ManifestEntry], name: str) -> ManifestEntry:
    entry = manifest.get(name)
    if entry is None:
        raise AppError(
            error_code=ErrorCode.INVALID_ARGUMENT,
            message=f"Plugin '{name}' was not installed with 'ableton-cli plugins install'",
            hint=(
                "Run 'ableton-cli plugins list'. Plugins installed another way are "
                "updated and removed with the tool that installed them."
            ),
            exit_code=ExitCode.INVALID_ARGUMENT,
        )
    return entry


def _plugin_invalid(message: str, **details: Any) -> AppError:
    return AppError(
        error_code=ErrorCode.PLUGIN_INVALID,
        message=message,
        hint="The install was rolled back. Fix the plugin repository or choose another ref.",
        exit_code=ExitCode.EXECUTION_FAILED,
        details=details,
    )
