from __future__ import annotations

import json
from typing import Any

import pytest

from ableton_cli.errors import AppError, ExitCode


def _timeout_error(*, may_have_executed: bool | None = None) -> AppError:
    details: dict[str, Any] = {}
    if may_have_executed is not None:
        details["may_have_executed"] = may_have_executed
    return AppError(
        error_code="TIMEOUT",
        message="Timed out waiting for Ableton main thread",
        hint="Retry the command while Ableton Live is responsive.",
        exit_code=ExitCode.TIMEOUT,
        details=details,
    )


class _StepClientStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._responses: dict[str, list[dict[str, Any] | AppError]] = {}

    def set_responses(self, name: str, items: list[dict[str, Any] | AppError]) -> None:
        self._responses[name] = list(items)

    def execute_remote_command(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, args))
        queue = self._responses.get(name)
        if queue:
            item = queue.pop(0)
            if isinstance(item, AppError):
                raise item
            return item
        return {"ok": True, "name": name}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> _StepClientStub:
    from ableton_cli.commands import batch

    stub = _StepClientStub()
    monkeypatch.setattr(batch, "get_client", lambda _ctx: stub)
    return stub


def _run_batch(runner, cli_app, steps: list[dict[str, Any]]):  # noqa: ANN001, ANN202
    return runner.invoke(
        cli_app,
        ["--output", "json", "batch", "run", "--steps-json", json.dumps({"steps": steps})],
    )


def test_timeout_retry_is_rejected_for_a_non_idempotent_command(
    runner, cli_app, client: _StepClientStub
) -> None:
    result = _run_batch(
        runner,
        cli_app,
        [
            {
                "name": "add_notes_to_clip",
                "args": {},
                "retry": {"max_attempts": 3, "on": ["TIMEOUT"]},
            }
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert "add_notes_to_clip" in payload["error"]["hint"]
    assert client.calls == []


def test_timeout_retry_is_allowed_for_an_idempotent_command(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses("tracks_list", [_timeout_error(), {"tracks": []}])

    result = _run_batch(
        runner,
        cli_app,
        [
            {
                "name": "tracks_list",
                "args": {},
                "retry": {"max_attempts": 3, "backoff_ms": 0, "on": ["TIMEOUT"]},
            }
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["result"]["results"][0]["attempts"] == 2


def test_default_retry_codes_exclude_timeout(runner, cli_app, client: _StepClientStub) -> None:
    from ableton_cli.commands.batch import _DEFAULT_RETRY_CODES

    assert "TIMEOUT" not in _DEFAULT_RETRY_CODES
    assert "REMOTE_BUSY" in _DEFAULT_RETRY_CODES

    client.set_responses("add_notes_to_clip", [_timeout_error(), {"ok": True}])

    result = _run_batch(
        runner,
        cli_app,
        [{"name": "add_notes_to_clip", "args": {}, "retry": {"max_attempts": 3}}],
    )

    assert result.exit_code == 12
    assert len(client.calls) == 1


def test_step_without_retry_is_executed_once(runner, cli_app, client: _StepClientStub) -> None:
    client.set_responses("add_notes_to_clip", [_timeout_error(), {"ok": True}])

    result = _run_batch(runner, cli_app, [{"name": "add_notes_to_clip", "args": {}}])

    assert result.exit_code == 12
    assert len(client.calls) == 1


def test_timeout_that_may_have_executed_is_never_retried(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses(
        "tracks_list",
        [_timeout_error(may_have_executed=True), {"tracks": []}],
    )

    result = _run_batch(
        runner,
        cli_app,
        [
            {
                "name": "tracks_list",
                "args": {},
                "retry": {"max_attempts": 3, "backoff_ms": 0, "on": ["TIMEOUT"]},
            }
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "TIMEOUT"
    assert len(client.calls) == 1


def test_step_timeout_exposes_may_have_executed(runner, cli_app, client: _StepClientStub) -> None:
    client.set_responses("add_notes_to_clip", [_timeout_error(may_have_executed=True)])

    result = _run_batch(runner, cli_app, [{"name": "add_notes_to_clip", "args": {}}])

    payload = json.loads(result.stdout)
    assert payload["error"]["details"]["may_have_executed"] is True
    assert payload["error"]["details"]["step_index"] == 0


def test_step_timeout_without_remote_signal_reports_unknown(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses("add_notes_to_clip", [_timeout_error()])

    result = _run_batch(runner, cli_app, [{"name": "add_notes_to_clip", "args": {}}])

    payload = json.loads(result.stdout)
    assert payload["error"]["details"]["may_have_executed"] is None
