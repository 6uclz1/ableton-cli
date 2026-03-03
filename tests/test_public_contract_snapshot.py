from __future__ import annotations

import json
from pathlib import Path


def _load_snapshot(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_contract_snapshot_matches_expected() -> None:
    from ableton_cli.contracts.public_snapshot import build_public_contract_snapshot

    expected_path = Path(__file__).resolve().parent / "snapshots" / "public_contract_snapshot.json"
    expected = _load_snapshot(expected_path)

    assert build_public_contract_snapshot() == expected
