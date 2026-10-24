"""What ``plugins list``, ``plugins info`` and ``doctor`` report about plugins."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import AppError
from .environment import PluginEnvironment
from .github import parse_github_url
from .manifest import ManifestEntry, read_manifest
from .model import PluginLoadReport


@dataclass(frozen=True, slots=True)
class PluginHealth:
    enabled: bool
    loaded: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
    out_of_sync: tuple[str, ...] = ()
    manifest_error: str | None = None


def plugin_listing(
    report: PluginLoadReport,
    manifest: dict[str, ManifestEntry],
    environment: PluginEnvironment,
) -> list[dict[str, Any]]:
    """Loaded and failed plugins plus every manifest entry, merged by name."""
    entries = {
        item["name"]: {
            **item,
            "managed": False,
            "source": None,
            "installed_rev": None,
            "in_sync": None,
        }
        for item in report.entries()
    }
    for name, managed in manifest.items():
        source, _ = parse_github_url(managed.source)
        installed = environment.find_by_source(source)
        installed_rev = None if installed is None else installed.commit
        base = entries.get(name) or {
            "name": name,
            "state": "not_installed" if report.enabled else "disabled",
            "description": None,
            "distribution": None,
            "commands": [],
            "skills": [],
            "error": None,
        }
        entries[name] = {
            **base,
            "managed": True,
            "source": {
                "url": managed.source,
                "requested_ref": managed.requested_ref,
                "rev": managed.rev,
            },
            "installed_rev": installed_rev,
            "in_sync": installed_rev == managed.rev,
        }
    return [entries[name] for name in sorted(entries)]


def plugin_health(
    report: PluginLoadReport, *, manifest_path: Path, environment: PluginEnvironment
) -> PluginHealth:
    loaded = tuple(item.name for item in report.loaded)
    failed = tuple(item.name for item in report.failed)
    try:
        manifest = read_manifest(manifest_path)
    except AppError as exc:
        return PluginHealth(
            enabled=report.enabled, loaded=loaded, failed=failed, manifest_error=exc.message
        )
    listing = plugin_listing(report, manifest, environment)
    return PluginHealth(
        enabled=report.enabled,
        loaded=loaded,
        failed=failed,
        out_of_sync=tuple(
            item["name"] for item in listing if item["managed"] and not item["in_sync"]
        ),
    )
