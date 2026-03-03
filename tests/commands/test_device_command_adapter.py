from __future__ import annotations


def test_device_run_client_command_spec_passes_method_kwargs(monkeypatch) -> None:
    from ableton_cli.commands import device

    captured: dict[str, object] = {}

    class _Client:
        def set_device_parameter(  # noqa: ANN201
            self,
            track: int,
            device: int,
            parameter: int,
            value: float,
        ):
            return {
                "track": track,
                "device": device,
                "parameter": parameter,
                "value": value,
            }

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(device, "get_client", _get_client)
    monkeypatch.setattr(device, "execute_command", _execute_command)

    device.run_client_command_spec(
        ctx=object(),
        spec=device.DeviceCommandSpec(
            command_name="device parameter set",
            client_method="set_device_parameter",
        ),
        args={"track": 1, "device": 2, "parameter": 3, "value": 0.5},
        method_kwargs={
            "track": 1,
            "device": 2,
            "parameter": 3,
            "value": 0.5,
        },
    )

    assert captured["command"] == "device parameter set"
    assert captured["args"] == {"track": 1, "device": 2, "parameter": 3, "value": 0.5}
    assert captured["result"] == {"track": 1, "device": 2, "parameter": 3, "value": 0.5}
