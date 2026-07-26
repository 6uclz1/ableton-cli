from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
# Running this as a script puts tools/ on sys.path, not the repo root.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.command_surface import build_command_surface_snapshot  # noqa: E402


def main() -> int:
    repo_root = _REPO_ROOT
    snapshot_path = repo_root / "tests" / "snapshots" / "command_surface_snapshot.json"
    payload = build_command_surface_snapshot()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
