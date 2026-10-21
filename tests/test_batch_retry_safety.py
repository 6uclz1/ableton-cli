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
        self.idempotency_keys: list[str | None] = []
        self._responses: dict[str, list[dict[str, Any] | AppError]] = {}

    def set_responses(self, name: str, items: list[dict[str, Any] | AppError]) -> None:
        self._responses[name] = list(items)

    def execute_remote_command(
        self,
        name: str,
        args: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append((name, args))
        self.idempotency_keys.append(idempotency_key)
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


def test_timeout_retry_of_a_write_reuses_one_idempotency_key(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses("add_notes_to_clip", [_timeout_error(), {"ok": True}])

    result = _run_batch(
        runner,
        cli_app,
        [
            {
                "name": "add_notes_to_clip",
                "args": {},
                "retry": {"max_attempts": 3, "backoff_ms": 0, "on": ["TIMEOUT"]},
            }
        ],
    )

    assert result.exit_code == 0
    assert len(client.calls) == 2
    assert client.idempotency_keys[0] == client.idempotency_keys[1]
    assert client.idempotency_keys[0] is not None


def test_each_step_gets_its_own_idempotency_key(runner, cli_app, client: _StepClientStub) -> None:
    step = {"name": "add_notes_to_clip", "args": {}, "retry": {"max_attempts": 2}}
    result = _run_batch(runner, cli_app, [step, dict(step)])

    assert result.exit_code == 0
    assert len(set(client.idempotency_keys)) == 2


def test_step_without_retry_sends_no_idempotency_key(
    runner, cli_app, client: _StepClientStub
) -> None:
    result = _run_batch(runner, cli_app, [{"name": "add_notes_to_clip", "args": {}}])

    assert result.exit_code == 0
    assert client.idempotency_keys == [None]


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


def test_timeout_that_may_have_executed_is_retried_under_one_key(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses(
        "add_notes_to_clip",
        [_timeout_error(may_have_executed=True), {"ok": True}],
    )

    result = _run_batch(
        runner,
        cli_app,
        [
            {
                "name": "add_notes_to_clip",
                "args": {},
                "retry": {"max_attempts": 3, "backoff_ms": 0, "on": ["TIMEOUT"]},
            }
        ],
    )

    # The Remote Script recognises the repeated key and replays its stored
    # response, so resending cannot double-apply the notes.
    assert result.exit_code == 0
    assert len(client.calls) == 2
    assert client.idempotency_keys[0] == client.idempotency_keys[1]


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


def _invalid_argument_error() -> AppError:
    return AppError(
        error_code="INVALID_ARGUMENT",
        message="track out of range",
        hint="Use a valid track index.",
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def _three_steps() -> list[dict[str, Any]]:
    return [
        {"name": "tracks_list", "args": {}},
        {"name": "set_track_volume", "args": {"track": 99, "value": 0.5}},
        {"name": "song_info", "args": {}},
    ]


def test_mid_batch_failure_reports_step_and_completed_results(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses("set_track_volume", [_invalid_argument_error()])

    result = _run_batch(runner, cli_app, _three_steps())

    assert result.exit_code == ExitCode.INVALID_ARGUMENT.value
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    details = payload["error"]["details"]
    assert details["step_index"] == 1
    assert details["step_name"] == "set_track_volume"
    assert details["completed_steps"] == 1
    assert [item["name"] for item in details["results"]] == ["tracks_list"]
    assert [name for name, _args in client.calls] == ["tracks_list", "set_track_volume"]


def test_assert_failure_reports_completed_results(runner, cli_app, client: _StepClientStub) -> None:
    client.set_responses("song_info", [{"tempo": 100.0}])

    result = _run_batch(
        runner,
        cli_app,
        [
            {"name": "tracks_list", "args": {}},
            {
                "name": "song_info",
                "args": {},
                "assert": {"source": "current", "path": "tempo", "op": "gte", "value": 120},
            },
        ],
    )

    assert result.exit_code == ExitCode.EXECUTION_FAILED.value
    details = json.loads(result.stdout)["error"]["details"]
    assert details["step_index"] == 1
    assert details["step_name"] == "song_info"
    assert details["completed_steps"] == 1
    assert details["reason"] == "comparison failed"


def test_continue_on_error_runs_every_step_and_fails_overall(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses("set_track_volume", [_invalid_argument_error()])

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--continue-on-error",
            "--steps-json",
            json.dumps({"steps": _three_steps()}),
        ],
    )

    assert result.exit_code == ExitCode.EXECUTION_FAILED.value
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BATCH_STEP_FAILED"
    details = payload["error"]["details"]
    assert details["step_count"] == 3
    assert details["completed_steps"] == 2
    assert details["failed_step_indices"] == [1]
    assert [item["ok"] for item in details["results"]] == [True, False, True]
    assert details["results"][1]["error"]["code"] == "INVALID_ARGUMENT"
    assert details["results"][1]["result"] is None
    assert [name for name, _args in client.calls] == [
        "tracks_list",
        "set_track_volume",
        "song_info",
    ]


def test_continue_on_error_skips_step_whose_previous_assert_fails(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses("set_track_volume", [_invalid_argument_error()])
    steps = _three_steps()
    steps[2]["assert"] = {"source": "previous", "path": "ok", "op": "eq", "value": True}

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--continue-on-error",
            "--steps-json",
            json.dumps({"steps": steps}),
        ],
    )

    details = json.loads(result.stdout)["error"]["details"]
    assert details["failed_step_indices"] == [1, 2]
    assert details["results"][2]["error"]["code"] == "BATCH_ASSERT_FAILED"
    assert details["results"][2]["error"]["details"]["reason"] == "previous payload is missing"
    assert [name for name, _args in client.calls] == ["tracks_list", "set_track_volume"]


def test_continue_on_error_success_marks_every_step_ok(
    runner, cli_app, client: _StepClientStub
) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--continue-on-error",
            "--steps-json",
            json.dumps({"steps": _three_steps()}),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [item["ok"] for item in payload["result"]["results"]] == [True, True, True]


def test_batch_stream_reports_failed_step_details(runner, cli_app, client: _StepClientStub) -> None:
    client.set_responses("set_track_volume", [_invalid_argument_error()])
    line = json.dumps({"id": "a", "steps": _three_steps()})

    result = runner.invoke(cli_app, ["batch", "stream"], input=f"{line}\n")

    emitted = json.loads(result.stdout.strip())
    assert emitted["ok"] is False
    assert emitted["error"]["code"] == "INVALID_ARGUMENT"
    assert emitted["error"]["details"]["step_index"] == 1
    assert emitted["error"]["details"]["completed_steps"] == 1


def test_batch_stream_continue_on_error_reports_every_step(
    runner, cli_app, client: _StepClientStub
) -> None:
    client.set_responses("set_track_volume", [_invalid_argument_error()])
    line = json.dumps({"id": "a", "steps": _three_steps()})

    result = runner.invoke(cli_app, ["batch", "stream", "--continue-on-error"], input=f"{line}\n")

    emitted = json.loads(result.stdout.strip())
    assert emitted["ok"] is False
    assert emitted["error"]["code"] == "BATCH_STEP_FAILED"
    assert [item["ok"] for item in emitted["error"]["details"]["results"]] == [True, False, True]
