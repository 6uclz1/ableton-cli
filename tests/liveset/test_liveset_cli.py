from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from live_set_builder import SetSpec, TrackSpec

from ableton_cli.contracts.registry import get_registered_contracts


def _invoke(runner, cli_app, *args: str):
    result = runner.invoke(cli_app, ["--output", "json", *args])
    return result, json.loads(result.stdout)


def test_set_inspect_outputs_summary_envelope(runner, cli_app, live_set_factory) -> None:
    path = live_set_factory(SetSpec(tempo=99, tracks=[TrackSpec(name="Bass")]))

    result, payload = _invoke(runner, cli_app, "set", "inspect", "--path", str(path))

    assert result.exit_code == 0, result.stdout
    assert payload["ok"] is True
    assert payload["command"] == "set inspect"
    assert payload["args"] == {"path": str(path)}
    assert payload["result"]["song"]["tempo"] == 99.0
    assert payload["result"]["tracks"][0]["name"] == "Bass"
    assert payload["error"] is None


def test_set_inspect_rejects_invalid_file(runner, cli_app, tmp_path: Path) -> None:
    path = tmp_path / "plain.als"
    path.write_text("not gzip", encoding="utf-8")

    result, payload = _invoke(runner, cli_app, "set", "inspect", "--path", str(path))

    assert result.exit_code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SET_FILE_INVALID"
    assert payload["error"]["hint"]


def test_set_inspect_rejects_unsupported_version(runner, cli_app, live_set_factory) -> None:
    path = live_set_factory(SetSpec(minor_version="11.0_11300"))

    result, payload = _invoke(runner, cli_app, "set", "inspect", "--path", str(path))

    assert result.exit_code == 2
    assert payload["error"]["code"] == "SET_SCHEMA_UNSUPPORTED"


def test_set_lint_passes_clean_set(runner, cli_app, live_set_factory) -> None:
    path = live_set_factory()

    result, payload = _invoke(runner, cli_app, "set", "lint", "--path", str(path))

    assert result.exit_code == 0, result.stdout
    assert payload["command"] == "set lint"
    assert payload["result"]["error_count"] == 0
    assert payload["result"]["findings"] == []


def test_set_lint_fails_on_integrity_errors(runner, cli_app, live_set_factory) -> None:
    def _dangle(root: ET.Element) -> None:
        ET.SubElement(root.find("LiveSet"), "PointeeId", Value="424242")

    path = live_set_factory(mutate=_dangle)

    result, payload = _invoke(runner, cli_app, "set", "lint", "--path", str(path))

    assert result.exit_code == 20
    assert payload["error"]["code"] == "SET_INTEGRITY_FAILED"
    assert payload["error"]["details"]["findings"][0]["code"] == "pointee_ref_dangling"


def test_set_diff_outputs_deltas(runner, cli_app, live_set_factory) -> None:
    before = live_set_factory(SetSpec(tempo=120), name="a.als")
    after = live_set_factory(SetSpec(tempo=140), name="b.als")

    result, payload = _invoke(
        runner, cli_app, "set", "diff", "--from", str(before), "--to", str(after)
    )

    assert result.exit_code == 0, result.stdout
    assert payload["command"] == "set diff"
    assert payload["args"] == {"from": str(before), "to": str(after)}
    assert payload["result"]["changed"]["song"]["tempo"] == {"from": 120.0, "to": 140.0}


def test_set_commands_are_allowed_in_read_only_mode(runner, cli_app, live_set_factory) -> None:
    path = live_set_factory()

    result = runner.invoke(
        cli_app, ["--output", "json", "--read-only", "set", "inspect", "--path", str(path)]
    )

    assert result.exit_code == 0, result.stdout


def test_set_dry_run_plans_without_reading_the_file(runner, cli_app, tmp_path: Path) -> None:
    missing = tmp_path / "missing.als"

    result = runner.invoke(
        cli_app, ["--output", "json", "--dry-run", "set", "lint", "--path", str(missing)]
    )

    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["result"]["dry_run"] is True


def test_set_commands_declare_result_contracts() -> None:
    contracts = get_registered_contracts()

    assert contracts["set inspect"]["result"]["required"] == [
        "path",
        "version",
        "song",
        "tracks",
        "return_tracks",
        "scenes",
        "locators",
        "plugins",
    ]
    assert contracts["set lint"]["result"]["required"] == [
        "path",
        "version",
        "error_count",
        "warning_count",
        "findings",
        "media",
    ]
    assert contracts["set diff"]["result"]["required"] == [
        "from_path",
        "to_path",
        "added",
        "removed",
        "changed",
    ]
    for name in ("set inspect", "set lint", "set diff"):
        assert contracts[name]["side_effect"]["kind"] == "read"
