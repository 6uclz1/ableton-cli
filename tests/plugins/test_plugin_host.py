from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from ableton_cli.app_factory import create_app
from ableton_cli.plugin_api import READ, Plugin
from ableton_cli.plugins.host import PluginSource
from ableton_cli.runtime import RuntimeContext
from tests.fixtures.plugins.demo_plugin import PLUGIN as DEMO


def _source(plugin: object, name: str = "demo") -> PluginSource:
    return PluginSource(name=name, load=lambda: plugin)


def _invoke(app, *args: str):
    result = CliRunner().invoke(app, ["--output", "json", *args])
    return result, json.loads(result.stdout) if result.stdout.strip() else None


def _app(*sources: PluginSource, env: dict[str, str] | None = None):
    return create_app(plugin_sources=sources, env={} if env is None else env)


def test_plugin_command_runs_inside_the_core_json_envelope() -> None:
    result, payload = _invoke(_app(_source(DEMO)), "demo", "echo", "--message", "hi")

    assert result.exit_code == 0, result.output
    assert payload == {
        "ok": True,
        "command": "demo echo",
        "args": {"message": "hi"},
        "result": {"message": "hi"},
        "error": None,
    }


def test_plan_reports_the_side_effect_the_plugin_declared() -> None:
    result, payload = _invoke(_app(_source(DEMO)), "--plan", "demo", "tempo", "set", "120")

    assert result.exit_code == 0, result.output
    assert payload["command"] == "demo tempo set"
    assert payload["result"]["side_effect"]["kind"] == "write"
    assert payload["result"]["will_dispatch"] is False


def test_read_only_blocks_plugin_write_commands_before_they_run() -> None:
    result, payload = _invoke(_app(_source(DEMO)), "--read-only", "demo", "tempo", "set", "120")

    assert result.exit_code == 20
    assert payload["error"]["code"] == "READ_ONLY_VIOLATION"


def test_read_only_allows_plugin_read_commands() -> None:
    result, payload = _invoke(_app(_source(DEMO)), "--read-only", "demo", "echo", "--message", "x")

    assert result.exit_code == 0, result.output
    assert payload["result"] == {"message": "x"}


def test_destructive_plugin_commands_honour_require_confirmation() -> None:
    app = _app(_source(DEMO))

    refused, refused_payload = _invoke(app, "--require-confirmation", "demo", "reset")
    confirmed, confirmed_payload = _invoke(app, "--require-confirmation", "--yes", "demo", "reset")

    assert refused.exit_code == 20
    assert refused_payload["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert confirmed.exit_code == 0
    assert confirmed_payload["result"] == {"reset": True}


def test_live_requests_go_through_the_runtime_client(monkeypatch) -> None:
    requests: list[tuple[str, dict]] = []

    class _Client:
        def execute_remote_command(self, name, args=None):
            requests.append((name, args))
            return {"bpm": args["bpm"]}

    monkeypatch.setattr(RuntimeContext, "client", lambda self: _Client())

    result, payload = _invoke(_app(_source(DEMO)), "demo", "tempo", "set", "128")

    assert result.exit_code == 0, result.output
    assert requests == [("transport_tempo_set", {"bpm": 128.0})]
    assert payload["result"] == {"bpm": 128.0}


def test_plugin_errors_carry_a_code_namespaced_by_the_plugin() -> None:
    result, payload = _invoke(_app(_source(DEMO)), "demo", "fail")

    assert result.exit_code == 20
    assert payload["error"]["code"] == "DEMO_BROKEN"
    assert payload["error"]["hint"] == "Fix the demo."


def _broken_import() -> object:
    raise ImportError("no module named demo_dependency")


def _raising_register(api) -> None:
    raise RuntimeError("boom")


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        (PluginSource(name="demo", load=_broken_import), "import_failed"),
        (_source(object()), "not_a_plugin"),
        (_source(replace(DEMO, name="other")), "name_mismatch"),
        (_source(replace(DEMO, api_version=99)), "api_version_mismatch"),
        (_source(replace(DEMO, register=_raising_register)), "register_failed"),
        (_source(replace(DEMO, register=lambda api: None)), "no_commands"),
        (_source(replace(DEMO, skills=(Path(__file__).parent,))), "invalid_skill"),
    ],
)
def test_a_plugin_that_fails_to_load_answers_with_plugin_load_failed(source, reason) -> None:
    app = _app(source)

    result, payload = _invoke(app, "demo", "echo", "--message", "hi")
    planned, planned_payload = _invoke(app, "--plan", "demo", "echo")

    assert result.exit_code == 20
    assert payload["command"] == "demo"
    assert payload["error"]["code"] == "PLUGIN_LOAD_FAILED"
    assert payload["error"]["details"]["load_failure"] == reason
    assert planned.exit_code == 20
    assert planned_payload["error"]["code"] == "PLUGIN_LOAD_FAILED"


def test_a_failed_plugin_does_not_break_core_commands() -> None:
    result, payload = _invoke(
        _app(PluginSource(name="demo", load=_broken_import)), "plugins", "list"
    )

    assert result.exit_code == 0, result.output
    assert [entry["state"] for entry in payload["result"]["plugins"]] == ["failed"]


def _plugin_entries(app) -> dict[str, dict]:
    _, payload = _invoke(app, "plugins", "list")
    return {entry["name"]: entry for entry in payload["result"]["plugins"]}


def test_plugin_names_that_collide_with_core_groups_are_refused() -> None:
    clashing = replace(DEMO, name="track")
    app = _app(_source(clashing, name="track"))

    entries = _plugin_entries(app)
    core_help = CliRunner().invoke(app, ["track", "--help"])

    assert entries["track"]["error"]["details"]["load_failure"] == "reserved_name"
    assert core_help.exit_code == 0
    assert "(failed to load)" not in core_help.stdout


def test_two_plugins_with_one_name_are_both_refused() -> None:
    app = _app(_source(DEMO), _source(DEMO))

    entries = _plugin_entries(app)
    result, payload = _invoke(app, "demo", "echo", "--message", "hi")

    assert entries["demo"]["error"]["details"]["load_failure"] == "duplicate_name"
    assert payload["error"]["code"] == "PLUGIN_LOAD_FAILED"


def test_invalid_plugin_names_are_refused_without_a_stub() -> None:
    entries = _plugin_entries(_app(_source(replace(DEMO, name="Bad_Name"), name="Bad_Name")))

    assert entries["Bad_Name"]["error"]["details"]["load_failure"] == "invalid_name"


def test_plugins_off_loads_nothing() -> None:
    app = _app(_source(DEMO), env={"ABLETON_CLI_PLUGINS": "off"})

    result, _ = _invoke(app, "demo", "echo", "--message", "hi")
    _, listing = _invoke(app, "plugins", "list")

    assert result.exit_code == 2
    assert listing["result"]["enabled"] is False


def test_an_invalid_plugin_switch_fails_every_command_with_config_invalid() -> None:
    result, payload = _invoke(
        _app(_source(DEMO), env={"ABLETON_CLI_PLUGINS": "yes"}), "plugins", "list"
    )

    assert result.exit_code == 3
    assert payload["error"]["code"] == "CONFIG_INVALID"


def test_loaded_plugin_entry_lists_commands_side_effects_and_skills() -> None:
    entry = _plugin_entries(_app(_source(DEMO)))["demo"]

    assert entry["state"] == "loaded"
    assert entry["managed"] is False
    assert entry["skills"] == ["demo"]
    assert {item["command"]: item["side_effect"]["kind"] for item in entry["commands"]} == {
        "demo echo": "read",
        "demo fail": "read",
        "demo reset": "destructive",
        "demo tempo set": "write",
    }


def test_plugin_api_rejects_malformed_declarations() -> None:
    from ableton_cli.plugin_api import ExitCode, PluginApi

    api = PluginApi("ace-step", typer.Typer())

    with pytest.raises(ValueError):
        api.command("Bad Name", side_effect=READ)
    api.command("generate", side_effect=READ)(lambda: None)
    with pytest.raises(ValueError):
        api.command("generate", side_effect=READ)
    with pytest.raises(ValueError):
        api.error("lower", "message")
    with pytest.raises(ValueError):
        api.error("OK", "message", exit_code=ExitCode.SUCCESS)
    assert api.error("GENERATION_FAILED", "m").error_code == "ACE_STEP_GENERATION_FAILED"


def test_plugin_is_exported_from_the_plugin_api() -> None:
    assert Plugin is DEMO.__class__


def test_live_request_failures_are_live_errors_with_code_and_message(monkeypatch) -> None:
    from ableton_cli.errors import AppError, ExitCode
    from ableton_cli.plugin_api import LiveError, PluginApi

    class _Client:
        def execute_remote_command(self, name, args=None):
            raise AppError(
                error_code="INVALID_ARGUMENT",
                message="device index out of range",
                hint="List devices first.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )

    def register(api: PluginApi) -> None:
        @api.command("probe", side_effect=READ)
        def probe(ctx: typer.Context) -> None:
            def _action(live) -> dict[str, object]:
                try:
                    live.request("track_devices_list", {"track": 0})
                except LiveError as exc:
                    return {"code": exc.error_code, "message": exc.message, "hint": exc.hint}
                return {}

            api.run(ctx, args={}, action=_action)

    monkeypatch.setattr(RuntimeContext, "client", lambda self: _Client())
    result, payload = _invoke(_app(_source(replace(DEMO, register=register))), "demo", "probe")

    assert result.exit_code == 0, result.output
    assert payload["result"] == {
        "code": "INVALID_ARGUMENT",
        "message": "device index out of range",
        "hint": "List devices first.",
    }


def test_fake_live_callables_can_raise_live_errors() -> None:
    from ableton_cli.plugin_api import ExitCode, LiveError
    from ableton_cli.plugin_api.testing import FakeLive

    def _out_of_range(args):
        raise LiveError(
            error_code="INVALID_ARGUMENT",
            message="device index out of range",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )

    live = FakeLive({"device_parameters_list": _out_of_range})

    with pytest.raises(LiveError) as exc_info:
        live.request("device_parameters_list", {"device": 9})

    assert exc_info.value.error_code == "INVALID_ARGUMENT"
    assert str(exc_info.value) == "device index out of range"
