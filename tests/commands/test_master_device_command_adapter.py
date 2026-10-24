from __future__ import annotations

import json


class _ClientStub:
    def master_volume_set(self, value: float):  # noqa: ANN201
        return {"volume": value}

    def master_panning_set(self, value: float):  # noqa: ANN201
        return {"panning": value}

    def master_effect_keys(self, effect_type: str):  # noqa: ANN201
        return {"effect_type": effect_type, "keys": ["gain"], "key_count": 1}

    def master_effect_set(self, effect_type: str, device_ref, parameter_ref, value: float):  # noqa: ANN201, ANN001
        return {"effect_type": effect_type, "device": 0, "parameter": 0, "value": value}

    def master_effect_observe(self, effect_type: str, device_ref):  # noqa: ANN201, ANN001
        return {"effect_type": effect_type, "state": {"gain": value if (value := 0.5) else 0.5}}


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def test_master_write_commands_output_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import master

    monkeypatch.setattr(master, "get_client", lambda _ctx: _ClientStub())

    volume = runner.invoke(cli_app, ["--output", "json", "master", "volume", "set", "0.85"])
    panning = runner.invoke(cli_app, ["--output", "json", "master", "panning", "set", "--", "0.0"])
    assert volume.exit_code == 0, volume.stdout
    assert panning.exit_code == 0, panning.stdout
    assert _payload(volume.stdout)["result"]["volume"] == 0.85  # type: ignore[index]


def test_master_effect_wrappers_output_json(
    runner,
    cli_app,
    monkeypatch,
) -> None:
    from ableton_cli.commands import master

    monkeypatch.setattr(master, "get_client", lambda _ctx: _ClientStub())

    keys = runner.invoke(cli_app, ["--output", "json", "master", "effect", "utility", "keys"])
    effect_set = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "master",
            "effect",
            "utility",
            "set",
            "0.4",
            "--device-query",
            "Utility",
            "--parameter-key",
            "gain",
        ],
    )
    observe = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "master",
            "effect",
            "utility",
            "observe",
            "--device-query",
            "Utility",
        ],
    )

    assert keys.exit_code == 0, keys.stdout
    assert effect_set.exit_code == 0, effect_set.stdout
    assert observe.exit_code == 0, observe.stdout
    assert _payload(keys.stdout)["result"]["keys"] == ["gain"]  # type: ignore[index]


def test_master_device_subcommands_are_removed(runner, cli_app) -> None:
    result = runner.invoke(cli_app, ["--output", "json", "master", "device", "parameters", "list"])

    assert result.exit_code != 0
