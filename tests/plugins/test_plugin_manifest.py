from __future__ import annotations

from pathlib import Path

import pytest

from ableton_cli.errors import AppError
from ableton_cli.plugins.manifest import (
    ManifestEntry,
    plugin_manifest_path,
    read_manifest,
    write_manifest,
)

ENTRY = ManifestEntry(
    name="demo",
    source="https://github.com/someone/ableton-cli-demo",
    requested_ref=None,
    rev="a" * 40,
    distribution="ableton-cli-demo",
    version="0.1.0",
)


def test_missing_manifest_reads_as_empty(tmp_path: Path) -> None:
    assert read_manifest(tmp_path / "plugins.toml") == {}


def test_manifest_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "plugins.toml"
    other = ManifestEntry(
        name="ace-step",
        source="https://github.com/someone/ableton-cli-acestep",
        requested_ref='v1 "quoted"',
        rev="b" * 40,
        distribution="ableton-cli-acestep",
        version="2.0.0",
    )

    write_manifest(path, {"demo": ENTRY, "ace-step": other})

    assert read_manifest(path) == {"ace-step": other, "demo": ENTRY}
    assert path.read_text(encoding="utf-8").index("[plugins.ace-step]") < path.read_text(
        encoding="utf-8"
    ).index("[plugins.demo]")


@pytest.mark.parametrize(
    "content",
    [
        "not toml = = =",
        "other = 1",
        "plugins = 1",
        '[plugins.demo]\nsource = "x"\n',
        '[plugins.demo]\nsource = "x"\nrev = "short"\ndistribution = "d"\nversion = "1"\n',
        f'[plugins.demo]\nsource = "x"\nrev = "{"a" * 40}"\ndistribution = "d"\n'
        'version = "1"\nextra = "y"\n',
        f'[plugins.demo]\nsource = 1\nrev = "{"a" * 40}"\ndistribution = "d"\nversion = "1"\n',
    ],
)
def test_malformed_manifests_are_config_invalid(tmp_path: Path, content: str) -> None:
    path = tmp_path / "plugins.toml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(AppError) as exc_info:
        read_manifest(path)

    assert exc_info.value.error_code == "CONFIG_INVALID"


def test_manifest_path_can_be_overridden_by_environment(tmp_path: Path) -> None:
    override = tmp_path / "custom.toml"

    assert plugin_manifest_path({"ABLETON_CLI_PLUGIN_MANIFEST": str(override)}) == override
    assert plugin_manifest_path({}).name == "plugins.toml"
