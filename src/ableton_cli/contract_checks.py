from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import build_public_contract_snapshot


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_snapshot_path() -> Path:
    return _repo_root() / "tests" / "snapshots" / "public_contract_snapshot.json"


def _load_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_public_contract_snapshot_is_current(snapshot_path: Path | None = None) -> None:
    target = _default_snapshot_path() if snapshot_path is None else snapshot_path
    expected = _load_snapshot(target)
    actual = build_public_contract_snapshot()
    if actual != expected:
        raise RuntimeError(
            "Public contract snapshot is out of date. "
            "Run 'uv run python tools/update_public_contract_snapshot.py' and commit the result."
        )


def main() -> int:
    ensure_public_contract_snapshot_is_current()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
