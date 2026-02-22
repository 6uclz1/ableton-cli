from __future__ import annotations

from types import SimpleNamespace

from ableton_cli import dev_checks


def test_run_default_checks_runs_commands_in_order(monkeypatch) -> None:
    commands: list[tuple[str, ...]] = []

    def _run(command: tuple[str, ...], check: bool) -> SimpleNamespace:  # noqa: ANN202
        assert check is False
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(dev_checks.subprocess, "run", _run)

    result = dev_checks.run_default_checks()

    assert result == 0
    assert commands == list(dev_checks.DEFAULT_CHECK_COMMANDS)


def test_run_default_checks_stops_on_first_failure(monkeypatch) -> None:
    commands: list[tuple[str, ...]] = []
    exits = [0, 1, 0]

    def _run(command: tuple[str, ...], check: bool) -> SimpleNamespace:  # noqa: ANN202
        assert check is False
        commands.append(command)
        return SimpleNamespace(returncode=exits[len(commands) - 1])

    monkeypatch.setattr(dev_checks.subprocess, "run", _run)

    result = dev_checks.run_default_checks()

    assert result == 1
    assert commands == list(dev_checks.DEFAULT_CHECK_COMMANDS[:2])
