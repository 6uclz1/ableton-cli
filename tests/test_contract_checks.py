from __future__ import annotations

import json
from pathlib import Path

import pytest

from ableton_cli import contract_checks


def _write_snapshot(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_ensure_public_contract_snapshot_is_current_passes_when_equal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    payload = {"schema_version": 1, "contracts": {"song info": {}}}
    _write_snapshot(snapshot_path, payload)

    monkeypatch.setattr(contract_checks, "build_public_contract_snapshot", lambda: payload)

    contract_checks.ensure_public_contract_snapshot_is_current(snapshot_path)


def test_ensure_public_contract_snapshot_is_current_raises_when_different(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    _write_snapshot(snapshot_path, {"schema_version": 1, "contracts": {}})
    monkeypatch.setattr(
        contract_checks,
        "build_public_contract_snapshot",
        lambda: {"schema_version": 1, "contracts": {"song info": {}}},
    )

    with pytest.raises(RuntimeError) as exc_info:
        contract_checks.ensure_public_contract_snapshot_is_current(snapshot_path)

    assert "Public contract snapshot is out of date." in str(exc_info.value)
