from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import typer

from ableton_cli.config import Settings
from ableton_cli.output import OutputMode
from ableton_cli.runtime import RuntimeContext, execute_command, get_client


def _context(*, quiet: bool) -> SimpleNamespace:
    runtime = RuntimeContext(
        settings=Settings(),
        platform_paths=object(),
        output_mode=OutputMode.HUMAN,
        quiet=quiet,
        no_color=False,
    )
    return SimpleNamespace(obj=runtime)


def test_execute_command_quiet_suppresses_custom_human_formatter(monkeypatch) -> None:
    emitted: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    monkeypatch.setattr(
        typer,
        "echo",
        lambda *args, **kwargs: emitted.append((args, kwargs)),
    )

    with pytest.raises(typer.Exit) as exc_info:
        execute_command(
            _context(quiet=True),
            command="doctor",
            args={},
            action=lambda: {"summary": {"pass": 1, "warn": 0, "fail": 0}, "checks": []},
            human_formatter=lambda _: "Doctor Results",
        )

    assert exc_info.value.exit_code == 0
    assert emitted == []


def test_execute_command_not_quiet_emits_custom_human_formatter(monkeypatch) -> None:
    emitted: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    monkeypatch.setattr(
        typer,
        "echo",
        lambda *args, **kwargs: emitted.append((args, kwargs)),
    )

    with pytest.raises(typer.Exit) as exc_info:
        execute_command(
            _context(quiet=False),
            command="doctor",
            args={},
            action=lambda: {"summary": {"pass": 1, "warn": 0, "fail": 0}, "checks": []},
            human_formatter=lambda _: "Doctor Results",
        )

    assert exc_info.value.exit_code == 0
    assert len(emitted) == 1
    assert emitted[0][0][0] == "Doctor Results"


def test_get_client_reuses_client_for_same_runtime(monkeypatch) -> None:
    created_with: list[Settings] = []

    class FakeClient:
        def __init__(self, settings: Settings) -> None:
            self.settings = settings
            created_with.append(settings)

    monkeypatch.setattr("ableton_cli.runtime.AbletonClient", FakeClient)

    ctx = _context(quiet=False)
    first = get_client(ctx)
    second = get_client(ctx)

    assert first is second
    assert created_with == [ctx.obj.settings]
