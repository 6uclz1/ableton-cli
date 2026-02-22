from __future__ import annotations

from typing import Any

import ableton_cli.output as output_module


def test_emit_human_result_suppresses_output_when_quiet(monkeypatch) -> None:
    emitted: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    monkeypatch.setattr(
        output_module.typer,
        "echo",
        lambda *args, **kwargs: emitted.append((args, kwargs)),
    )

    output_module.emit_human_result(
        command="config show",
        result={"host": "127.0.0.1"},
        quiet=True,
    )

    assert emitted == []


def test_emit_human_result_emits_output_when_not_quiet(monkeypatch) -> None:
    emitted: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    monkeypatch.setattr(
        output_module.typer,
        "echo",
        lambda *args, **kwargs: emitted.append((args, kwargs)),
    )

    output_module.emit_human_result(
        command="config show",
        result={"host": "127.0.0.1"},
        quiet=False,
    )

    assert len(emitted) == 1
    assert emitted[0][0][0].startswith("OK: config show")
