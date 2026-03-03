from __future__ import annotations


def test_run_client_command_spec_dispatches_zero_arg_method(monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    captured: dict[str, object] = {}

    class _Client:
        def arrangement_record_start(self):  # noqa: ANN201
            return {"recording": True}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(arrangement, "get_client", _get_client)
    monkeypatch.setattr(arrangement, "execute_command", _execute_command)

    arrangement.run_client_command_spec(
        ctx=object(),
        spec=arrangement.ArrangementCommandSpec(
            command_name="arrangement record start",
            client_method="arrangement_record_start",
        ),
        args={},
    )

    assert captured["command"] == "arrangement record start"
    assert captured["args"] == {}
    assert captured["result"] == {"recording": True}


def test_run_client_command_spec_passes_method_kwargs(monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    captured: dict[str, object] = {}

    class _Client:
        def arrangement_clip_notes_get(
            self,
            *,
            track: int,
            index: int,
            start_time: float | None,
            end_time: float | None,
            pitch: int | None,
        ):  # noqa: ANN201
            return {
                "track": track,
                "index": index,
                "start_time": start_time,
                "end_time": end_time,
                "pitch": pitch,
            }

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(arrangement, "get_client", _get_client)
    monkeypatch.setattr(arrangement, "execute_command", _execute_command)

    arrangement.run_client_command_spec(
        ctx=object(),
        spec=arrangement.ArrangementCommandSpec(
            command_name="arrangement clip notes get",
            client_method="arrangement_clip_notes_get",
        ),
        args={"track": 1, "index": 0},
        method_kwargs={
            "track": 1,
            "index": 0,
            "start_time": 0.0,
            "end_time": 4.0,
            "pitch": 60,
        },
    )

    assert captured["command"] == "arrangement clip notes get"
    assert captured["args"] == {"track": 1, "index": 0}
    assert captured["result"] == {
        "track": 1,
        "index": 0,
        "start_time": 0.0,
        "end_time": 4.0,
        "pitch": 60,
    }
