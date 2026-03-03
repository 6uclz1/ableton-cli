from __future__ import annotations


def test_browser_run_client_command_spec_dispatches_kwargs(monkeypatch) -> None:
    from ableton_cli.commands import browser

    captured: dict[str, object] = {}

    class _Client:
        def get_browser_tree(self, category_type: str):  # noqa: ANN201
            return {"category_type": category_type}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(browser, "get_client", _get_client)
    monkeypatch.setattr(browser, "execute_command", _execute_command)

    browser.run_client_command_spec(
        ctx=object(),
        spec=browser.BrowserCommandSpec(
            command_name="browser tree",
            client_method="get_browser_tree",
        ),
        args={"category_type": "drums"},
        method_kwargs={"category_type": "drums"},
    )

    assert captured["command"] == "browser tree"
    assert captured["args"] == {"category_type": "drums"}
    assert captured["result"] == {"category_type": "drums"}
