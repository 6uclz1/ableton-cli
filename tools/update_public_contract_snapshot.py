from __future__ import annotations

import json
from pathlib import Path

from ableton_cli.contracts import build_public_contract_snapshot


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    snapshot_path = repo_root / "tests" / "snapshots" / "public_contract_snapshot.json"
    payload = build_public_contract_snapshot()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
