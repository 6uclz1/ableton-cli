"""The Python environment ableton-cli runs in, as seen by ``uv`` and ``importlib.metadata``.

Plugins are installed into the interpreter running ableton-cli itself, with
every package already there pinned through a constraints file: installing a
plugin can add packages but never move ableton-cli's own dependencies or
another plugin's.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
import tempfile
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Any

from ..errors import AppError, ErrorCode, ExitCode
from .github import CommandRunner, GitHubSource, run_subprocess, run_tool
from .model import ENTRY_POINT_GROUP

PROBE_MODULE = "ableton_cli.plugins.probe"


@dataclass(frozen=True, slots=True)
class InstalledDistribution:
    name: str
    version: str
    #: From PEP 610 ``direct_url.json``; ``None`` for index or local installs.
    url: str | None
    commit: str | None
    plugin_names: tuple[str, ...]


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


class PluginEnvironment:
    def __init__(
        self,
        *,
        python: str = sys.executable,
        run: CommandRunner = run_subprocess,
        list_distributions: Callable[[], Iterable[Distribution]] = distributions,
    ) -> None:
        self.python = python
        self._run = run
        self._list_distributions = list_distributions

    def installed(self) -> list[InstalledDistribution]:
        importlib.invalidate_caches()
        found: dict[str, InstalledDistribution] = {}
        for dist in self._list_distributions():
            name = dist.metadata["Name"]
            if not name or canonical_name(name) in found:
                continue  # first on sys.path wins, as it does for imports
            url, commit = _direct_url(dist)
            found[canonical_name(name)] = InstalledDistribution(
                name=name,
                version=dist.version,
                url=url,
                commit=commit,
                plugin_names=tuple(
                    sorted(ep.name for ep in dist.entry_points.select(group=ENTRY_POINT_GROUP))
                ),
            )
        return sorted(found.values(), key=lambda item: canonical_name(item.name))

    def find_by_source(self, source: GitHubSource) -> InstalledDistribution | None:
        for dist in self.installed():
            if dist.url is not None and source.matches_url(dist.url):
                return dist
        return None

    def install(self, requirement: str, *, unpinned: Collection[str] = ()) -> None:
        """``uv pip install`` with every installed package pinned except ``unpinned``."""
        skip = {canonical_name(name) for name in unpinned}
        constraints = [
            f"{dist.name}=={dist.version}"
            for dist in self.installed()
            if canonical_name(dist.name) not in skip
        ]
        with tempfile.TemporaryDirectory(prefix="ableton-cli-plugins-") as directory:
            constraints_path = Path(directory) / "constraints.txt"
            constraints_path.write_text("\n".join(constraints) + "\n", encoding="utf-8")
            run_tool(
                self._run,
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    self.python,
                    "--constraint",
                    str(constraints_path),
                    requirement,
                ],
                what="uv pip install",
            )

    def uninstall(self, distribution: str) -> None:
        run_tool(
            self._run,
            ["uv", "pip", "uninstall", "--python", self.python, distribution],
            what="uv pip uninstall",
        )

    def probe(self) -> list[dict[str, Any]]:
        """Load every installed plugin in a fresh interpreter and report the result.

        A fresh process is the only way to see newly installed code: this one
        already imported the old version of any plugin being updated.
        """
        completed = run_tool(self._run, [self.python, "-m", PROBE_MODULE], what="plugin load check")
        try:
            payload = json.loads(completed.stdout)
            return list(payload["plugins"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AppError(
                error_code=ErrorCode.PLUGIN_INSTALL_FAILED,
                message="The plugin load check printed an unreadable report",
                hint="Run 'python -m ableton_cli.plugins.probe' to see its output.",
                exit_code=ExitCode.EXECUTION_FAILED,
                details={"stdout": completed.stdout.strip()[-2000:]},
            ) from exc


def _direct_url(dist: Distribution) -> tuple[str | None, str | None]:
    raw = dist.read_text("direct_url.json")
    if raw is None:
        return None, None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, None
    url = data.get("url") if isinstance(data, dict) else None
    vcs_info = data.get("vcs_info") if isinstance(data, dict) else None
    commit = vcs_info.get("commit_id") if isinstance(vcs_info, dict) else None
    return (url if isinstance(url, str) else None), (commit if isinstance(commit, str) else None)
