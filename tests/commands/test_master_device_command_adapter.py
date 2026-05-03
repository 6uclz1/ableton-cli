from __future__ import annotations

import json


class _ClientStub:
    def master_volume_set(self, value: float):  # noqa: ANN201
        return {"volume": value}

    def master_panning_set(self, value: float):  # noqa: ANN201
        return {"panning": value}

    def master_device_load(self, target: str, position: str):  # noqa: ANN201
        return {"target": target, "position": position, "device": 0}

    def master_device_move(self, device_index: int, to_index: int):  # noqa: ANN201
        return {"device": device_index, "to_index": to_index}

    def master_device_delete(self, device_index: int):  # noqa: ANN201
        return {"device": device_index, "deleted": True}

    def master_device_parameters_list(self, device_ref):  # noqa: ANN201, ANN001
        return {"device": 0, "parameter_count": 1, "parameters": [{"index": 0, "name": "Gain"}]}

    def master_device_parameter_set(self, device_ref, parameter_ref, value: float):  # noqa: ANN201, ANN001
        return {"device": 0, "parameter": 0, "value": value}

    def master_effect_keys(self, effect_type: str):  # noqa: ANN201
        return {"effect_type": effect_type, "keys": ["gain"], "key_count": 1}

    def master_effect_set(self, effect_type: str, device_ref, parameter_ref, value: float):  # noqa: ANN201, ANN001
        return {"effect_type": effect_type, "device": 0, "parameter": 0, "value": value}

    def master_effect_observe(self, effect_type: str, device_ref):  # noqa: ANN201, ANN001
        return {"effect_type": effect_type, "state": {"gain": value if (value := 0.5) else 0.5}}


def _payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def test_master_write_and_device_commands_output_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import master

    monkeypatch.setattr(master, "get_client", lambda _ctx: _ClientStub())

    volume = runner.invoke(cli_app, ["--output", "json", "master", "volume", "set", "0.85"])
    panning = runner.invoke(cli_app, ["--output", "json", "master", "panning", "set", "--", "0.0"])
    load = runner.invoke(
        cli_app,
        ["--output", "json", "master", "device", "load", "query:Audio Effects#Utility"],
    )
    move = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "master",
            "device",
            "move",
            "--device-index",
            "2",
            "--to-index",
            "0",
        ],
    )
    delete = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "master",
            "device",
            "delete",
            "--device-index",
            "3",
            "--yes",
        ],
    )

    assert volume.exit_code == 0, volume.stdout
    assert panning.exit_code == 0, panning.stdout
    assert load.exit_code == 0, load.stdout
    assert move.exit_code == 0, move.stdout
    assert delete.exit_code == 0, delete.stdout
    assert _payload(volume.stdout)["result"]["volume"] == 0.85  # type: ignore[index]
    assert _payload(load.stdout)["result"]["target"] == "query:Audio Effects#Utility"  # type: ignore[index]
    assert _payload(delete.stdout)["result"]["deleted"] is True  # type: ignore[index]


def test_master_device_parameter_and_effect_wrappers_output_json(
    runner,
    cli_app,
    monkeypatch,
) -> None:
    from ableton_cli.commands import master

    monkeypatch.setattr(master, "get_client", lambda _ctx: _ClientStub())

    parameters = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "master",
            "device",
            "parameters",
            "list",
            "--device-index",
            "0",
        ],
    )
    parameter_set = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "master",
            "device",
            "parameter",
            "set",
            "--device-index",
            "0",
            "--parameter-key",
            "gain",
            "--",
            "-1.5",
        ],
    )
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

    assert parameters.exit_code == 0, parameters.stdout
    assert parameter_set.exit_code == 0, parameter_set.stdout
    assert keys.exit_code == 0, keys.stdout
    assert effect_set.exit_code == 0, effect_set.stdout
    assert observe.exit_code == 0, observe.stdout
    assert _payload(parameter_set.stdout)["result"]["value"] == -1.5  # type: ignore[index]
    assert _payload(keys.stdout)["result"]["keys"] == ["gain"]  # type: ignore[index]
