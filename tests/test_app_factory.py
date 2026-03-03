from __future__ import annotations

from typer.testing import CliRunner

import ableton_cli.app_factory as app_module


def test_create_app_returns_new_instances() -> None:
    first = app_module.create_app()
    second = app_module.create_app()

    assert first is not second


def test_command_registration_happens_only_during_factory(monkeypatch) -> None:
    register_calls = 0
    original_register = app_module.setup.register

    def wrapped_register(app) -> None:  # noqa: ANN001
        nonlocal register_calls
        register_calls += 1
        original_register(app)

    monkeypatch.setattr(app_module.setup, "register", wrapped_register)

    cli_app = app_module.create_app()
    assert register_calls == 1

    runner = CliRunner()
    first = runner.invoke(cli_app, ["--output", "json", "config", "show"])
    second = runner.invoke(cli_app, ["--output", "json", "config", "show"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert register_calls == 1


def test_public_command_registry_excludes_internal_modules() -> None:
    module_names = [
        command_module.__name__.rsplit(".", maxsplit=1)[-1]
        for command_module in app_module._COMMAND_MODULES
    ]

    assert all(not module_name.startswith("_") for module_name in module_names)
