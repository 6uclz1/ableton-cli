from __future__ import annotations

import io
import json
import subprocess
from importlib.metadata import EntryPoint, EntryPoints
from pathlib import Path

import pytest

from ableton_cli.errors import AppError
from ableton_cli.plugins.environment import PluginEnvironment
from ableton_cli.plugins.github import GitHubSource
from ableton_cli.plugins.host import PluginSource
from ableton_cli.plugins.probe import main as probe_main
from ableton_cli.plugins.probe import probe_report
from tests.fixtures.plugins.demo_plugin import PLUGIN as DEMO

SOURCE = GitHubSource(owner="someone", repo="ableton-cli-demo")


class _Dist:
    def __init__(self, name, version, *, direct_url=None, plugins=()):
        self.metadata = {"Name": name}
        self.version = version
        self._direct_url = direct_url
        self.entry_points = EntryPoints(
            EntryPoint(name=plugin, value=f"{name}:PLUGIN", group="ableton_cli.plugins")
            for plugin in plugins
        )

    def read_text(self, filename):
        if filename == "direct_url.json" and self._direct_url is not None:
            return json.dumps(self._direct_url)
        return None


DISTS = [
    _Dist("Typer", "0.15.0"),
    _Dist(
        "ableton_cli_demo",
        "0.1.0",
        direct_url={
            "url": "https://github.com/someone/ableton-cli-demo.git",
            "vcs_info": {"vcs": "git", "commit_id": "a" * 40},
        },
        plugins=("demo",),
    ),
    _Dist("typer", "0.1.0"),  # shadowed: later on sys.path
]


def _environment(run=None) -> PluginEnvironment:
    return PluginEnvironment(
        python="/env/bin/python",
        run=run or (lambda argv: subprocess.CompletedProcess(argv, 0, "", "")),
        list_distributions=lambda: DISTS,
    )


def test_installed_reads_pep610_urls_and_plugin_entry_points() -> None:
    found = _environment().find_by_source(SOURCE)

    assert found is not None
    assert (found.name, found.commit, found.plugin_names) == (
        "ableton_cli_demo",
        "a" * 40,
        ("demo",),
    )
    assert [
        dist.version for dist in _environment().installed() if dist.name.lower() == "typer"
    ] == ["0.15.0"]


def test_install_pins_every_other_installed_package() -> None:
    seen: dict[str, object] = {}

    def run(argv):
        seen["argv"] = list(argv)
        seen["constraints"] = Path(argv[argv.index("--constraint") + 1]).read_text(encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    _environment(run).install("git+https://example/x@abc", unpinned=("ableton-cli-demo",))

    assert seen["argv"][:5] == ["uv", "pip", "install", "--python", "/env/bin/python"]
    assert seen["argv"][-1] == "git+https://example/x@abc"
    assert seen["constraints"] == "Typer==0.15.0\n"


def test_probe_parses_the_report_of_a_fresh_interpreter() -> None:
    calls = []

    def run(argv):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, json.dumps({"plugins": [{"name": "demo"}]}), "")

    assert _environment(run).probe() == [{"name": "demo"}]
    assert calls == [["/env/bin/python", "-m", "ableton_cli.plugins.probe"]]


def test_an_unreadable_probe_report_is_plugin_install_failed() -> None:
    run = lambda argv: subprocess.CompletedProcess(argv, 0, "Traceback ...", "")  # noqa: E731

    with pytest.raises(AppError) as exc_info:
        _environment(run).probe()

    assert exc_info.value.error_code == "PLUGIN_INSTALL_FAILED"


def test_missing_uv_is_config_invalid() -> None:
    def run(argv):
        raise FileNotFoundError(argv[0])

    with pytest.raises(AppError) as exc_info:
        _environment(run).uninstall("ableton-cli-demo")

    assert exc_info.value.error_code == "CONFIG_INVALID"


def _noisy_plugin_loader():
    print("plugin says hello on import")
    return DEMO


def test_probe_report_keeps_stdout_a_single_json_document(monkeypatch) -> None:
    sources = (PluginSource(name="demo", load=_noisy_plugin_loader),)
    monkeypatch.setattr("ableton_cli.plugins.probe.discover_plugin_sources", lambda: sources)
    stdout = io.StringIO()

    assert probe_main(stdout) == 0

    payload = json.loads(stdout.getvalue())
    assert [(entry["name"], entry["state"]) for entry in payload["plugins"]] == [("demo", "loaded")]
    assert payload == json.loads(json.dumps(probe_report(sources), sort_keys=True))
