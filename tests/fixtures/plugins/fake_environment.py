"""A simulated plugin environment: uv installs and fresh-interpreter probes, in memory."""

from __future__ import annotations

from dataclasses import dataclass

from ableton_cli.errors import AppError, ErrorCode, ExitCode
from ableton_cli.plugins.environment import InstalledDistribution, PluginEnvironment
from ableton_cli.plugins.github import GitHubSource

SOURCE = GitHubSource(owner="someone", repo="ableton-cli-demo")
GOOD, NEWER, BROKEN, TWO_ENTRY_POINTS, RENAMED = ("1" * 40, "2" * 40, "3" * 40, "4" * 40, "5" * 40)


@dataclass(frozen=True)
class _Commit:
    version: str
    plugin_names: tuple[str, ...] = ("demo",)
    loads: bool = True


COMMITS = {
    GOOD: _Commit("0.1.0"),
    NEWER: _Commit("0.2.0"),
    BROKEN: _Commit("0.3.0", loads=False),
    TWO_ENTRY_POINTS: _Commit("0.4.0", plugin_names=("demo", "extra")),
    RENAMED: _Commit("0.5.0", plugin_names=("renamed",)),
}


class FakeEnvironment(PluginEnvironment):
    """uv and the interpreter, simulated: commits of one repository install one distribution."""

    def __init__(self, *, installed_rev: str | None = None, fail_rollback: bool = False) -> None:
        super().__init__()
        self.packages: dict[str, InstalledDistribution] = {}
        self.calls: list[tuple[str, str]] = []
        self.fail_rollback = fail_rollback
        if installed_rev is not None:
            self._put(installed_rev)

    def _put(self, rev: str) -> None:
        commit = COMMITS[rev]
        self.packages["ableton-cli-demo"] = InstalledDistribution(
            name="ableton-cli-demo",
            version=commit.version,
            url=SOURCE.url,
            commit=rev,
            plugin_names=commit.plugin_names,
        )

    def installed(self) -> list[InstalledDistribution]:
        return list(self.packages.values())

    def install(self, requirement: str, *, unpinned=()) -> None:
        self.calls.append(("install", requirement))
        if self.fail_rollback and len(self.calls) > 1:
            raise AppError(
                error_code=ErrorCode.PLUGIN_INSTALL_FAILED,
                message="network down",
                exit_code=ExitCode.EXECUTION_FAILED,
            )
        self._put(requirement.rsplit("@", 1)[1])

    def uninstall(self, distribution: str) -> None:
        self.calls.append(("uninstall", distribution))
        del self.packages[distribution]

    def probe(self) -> list[dict]:
        entries = []
        for package in self.packages.values():
            loads = COMMITS[package.commit].loads
            for name in package.plugin_names:
                entries.append(
                    {
                        "name": name,
                        "state": "loaded" if loads else "failed",
                        "error": None if loads else {"code": "PLUGIN_LOAD_FAILED"},
                    }
                )
        return entries
