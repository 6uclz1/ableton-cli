from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from live_set_builder import SetSpec, TrackSpec, read_live_set_xml

from ableton_cli.contracts.registry import get_registered_contracts

POINTS_JSON = '[{"time": 0, "value": 0.5}, {"time": 32, "value": 1.0}]'


def _spec() -> SetSpec:
    return SetSpec(tracks=[TrackSpec(name="Keys"), TrackSpec(tag="ReturnTrack", id=20)])


def _write(runner, cli_app, *args: str, global_args: tuple[str, ...] = ()):
    result = runner.invoke(
        cli_app,
        ["--output", "json", *global_args, "set", "automation", "write", *args],
    )
    return result, json.loads(result.stdout)


def _base_args(path: Path, out: Path) -> list[str]:
    return [
        "--path",
        str(path),
        "--out",
        str(out),
        "--track-index",
        "0",
        "--target",
        "mixer.volume",
        "--points-json",
        POINTS_JSON,
    ]


def test_writes_a_new_set_and_leaves_the_input_untouched(
    runner, cli_app, live_set_factory, tmp_path: Path
) -> None:
    path = live_set_factory(_spec())
    before = path.read_bytes()
    out = tmp_path / "out" / "Automated.als"
    out.parent.mkdir()

    result, payload = _write(runner, cli_app, *_base_args(path, out))

    assert result.exit_code == 0, result.stdout
    assert payload["command"] == "set automation write"
    assert payload["result"]["out"] == str(out)
    assert payload["result"]["point_count"] == 2
    assert payload["result"]["scope"] == {"kind": "track", "index": 0, "name": "Keys"}
    assert path.read_bytes() == before
    events = read_live_set_xml(out).findall(
        "LiveSet/Tracks/MidiTrack/AutomationEnvelopes/Envelopes/AutomationEnvelope/Automation/Events/FloatEvent"
    )
    assert [event.get("Time") for event in events] == ["-63072000", "0", "32"]
    assert list(out.parent.iterdir()) == [out]


def test_written_set_passes_lint(runner, cli_app, live_set_factory, tmp_path: Path) -> None:
    out = tmp_path / "Automated.als"
    _write(runner, cli_app, *_base_args(live_set_factory(_spec()), out))

    result = runner.invoke(cli_app, ["--output", "json", "set", "lint", "--path", str(out)])

    assert result.exit_code == 0, result.stdout


@pytest.mark.parametrize("case", ["exists", "same", "missing_dir"])
def test_rejects_unusable_output_paths(
    runner, cli_app, live_set_factory, tmp_path: Path, case: str
) -> None:
    path = live_set_factory(_spec())
    out = {
        "exists": lambda: live_set_factory(_spec(), name="Existing.als"),
        "same": lambda: path,
        "missing_dir": lambda: tmp_path / "nowhere" / "out.als",
    }[case]()

    result, payload = _write(runner, cli_app, *_base_args(path, out))

    assert result.exit_code == 2
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert payload["error"]["details"]["out"] == str(out)


@pytest.mark.parametrize(
    "selectors",
    [
        [],
        ["--track-index", "0", "--track-name", "Keys"],
        ["--return-track-index", "0", "--main"],
    ],
)
def test_requires_exactly_one_selector(
    runner, cli_app, live_set_factory, tmp_path: Path, selectors: list[str]
) -> None:
    path = live_set_factory(_spec())

    result, payload = _write(
        runner,
        cli_app,
        "--path",
        str(path),
        "--out",
        str(tmp_path / "out.als"),
        *selectors,
        "--target",
        "mixer.volume",
        "--points-json",
        POINTS_JSON,
    )

    assert result.exit_code == 2
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert "exactly one" in payload["error"]["message"]


def test_rejects_malformed_points(runner, cli_app, live_set_factory, tmp_path: Path) -> None:
    args = _base_args(live_set_factory(_spec()), tmp_path / "out.als")
    args[-1] = '[{"time": 0}]'

    result, payload = _write(runner, cli_app, *args)

    assert result.exit_code == 2
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert not (tmp_path / "out.als").exists()


def test_integrity_failure_writes_nothing(
    runner, cli_app, live_set_factory, tmp_path: Path
) -> None:
    def _dangle(root: ET.Element) -> None:
        ET.SubElement(root.find("LiveSet"), "PointeeId", Value="424242")

    out = tmp_path / "out.als"
    result, payload = _write(
        runner, cli_app, *_base_args(live_set_factory(_spec(), mutate=_dangle), out)
    )

    assert result.exit_code == 20
    assert payload["error"]["code"] == "SET_INTEGRITY_FAILED"
    assert not out.exists()


def test_read_only_mode_blocks_the_write(runner, cli_app, live_set_factory, tmp_path: Path) -> None:
    out = tmp_path / "out.als"

    result, payload = _write(
        runner,
        cli_app,
        *_base_args(live_set_factory(_spec()), out),
        global_args=("--read-only",),
    )

    assert result.exit_code == 20
    assert payload["error"]["code"] == "READ_ONLY_VIOLATION"
    assert not out.exists()


def test_dry_run_plans_without_writing(runner, cli_app, live_set_factory, tmp_path: Path) -> None:
    out = tmp_path / "out.als"

    result, payload = _write(
        runner, cli_app, *_base_args(live_set_factory(_spec()), out), global_args=("--dry-run",)
    )

    assert result.exit_code == 0, result.stdout
    assert payload["result"]["dry_run"] is True
    assert not out.exists()


def test_declares_a_write_contract() -> None:
    contract = get_registered_contracts()["set automation write"]

    assert contract["side_effect"]["kind"] == "write"
    assert contract["result"]["required"] == [
        "path",
        "out",
        "scope",
        "target",
        "parameter",
        "point_count",
        "replaced_point_count",
    ]
