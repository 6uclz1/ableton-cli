from __future__ import annotations

from pathlib import Path


def test_remote_script_entrypoint_has_create_instance() -> None:
    init_file = (
        Path(__file__).resolve().parents[1] / "remote_script" / "AbletonCliRemote" / "__init__.py"
    )
    source = init_file.read_text(encoding="utf-8")

    assert "def create_instance" in source
