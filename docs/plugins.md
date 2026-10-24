# Writing an ableton-cli plugin

A plugin is a Python package, in its own repository, that adds one top-level command group:
`ableton-cli <plugin> ...`. Users install it with
`ableton-cli plugins install https://github.com/<owner>/<repo>` (see README, "Plugins").

## Contract

- Import only `ableton_cli.plugin_api` (and `ableton_cli.plugin_api.testing` in tests). Every
  other `ableton_cli` module is internal and may change in any release.
- Declare the plugin API version you were written against. The host loads a plugin only when
  `Plugin.api_version == PLUGIN_API_VERSION`; anything else fails with
  `PLUGIN_LOAD_FAILED` (`load_failure: api_version_mismatch`) instead of half-working.
- One distribution provides exactly one plugin (one entry point in the `ableton_cli.plugins`
  group). `plugins install` refuses anything else.
- Do not list `ableton-cli` as a runtime dependency. The host provides it, and installs pin
  every package already present, so a runtime dependency on `ableton-cli` could only fail to
  resolve or pull in a second copy. Put it in a development dependency group for tests.

## Layout

```
ableton-cli-example/
  pyproject.toml
  src/ableton_cli_example/__init__.py
  src/ableton_cli_example/plugin.py
  src/ableton_cli_example/skills/example/SKILL.md
  tests/
```

```toml
[project]
name = "ableton-cli-example"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = []

[project.entry-points."ableton_cli.plugins"]
example = "ableton_cli_example.plugin:PLUGIN"

[dependency-groups]
dev = ["ableton-cli", "pytest"]
```

The entry-point name is the plugin name and the command group name. It must match
`^[a-z][a-z0-9-]{0,31}$`, must equal `Plugin.name`, and must not be a core command group
(`track`, `audio`, `plugins`, ...).

## The plugin object

```python
from pathlib import Path
from typing import Annotated

import typer

from ableton_cli.plugin_api import READ, WRITE, Live, Plugin, PluginApi


def register(api: PluginApi) -> None:
    @api.command("tempo show", side_effect=READ, help="Show the song tempo")
    def tempo_show(ctx: typer.Context) -> None:
        api.run(ctx, args={}, action=lambda live: live.request("transport_tempo_get"))

    @api.command("tempo nudge", side_effect=WRITE, help="Raise the tempo by --bpm")
    def tempo_nudge(
        ctx: typer.Context, bpm: Annotated[float, typer.Option("--bpm")] = 1.0
    ) -> None:
        def _action(live: Live) -> dict[str, object]:
            current = live.request("transport_tempo_get")["tempo"]
            if current + bpm > 999:
                raise api.error("TEMPO_TOO_HIGH", f"{current + bpm} BPM is above 999")
            return live.request("transport_tempo_set", {"bpm": current + bpm})

        api.run(ctx, args={"bpm": bpm}, action=_action)


PLUGIN = Plugin(
    name="example",
    api_version=1,
    register=register,
    description="Example commands",
    skills=(Path(__file__).parent / "skills" / "example",),
)
```

- `api.command(name, side_effect=..., help=...)` declares `ableton-cli example <name>`;
  spaces in `name` create subgroups. `side_effect` is `READ`, `WRITE` or `DESTRUCTIVE` and is
  required: it decides what `--read-only` blocks, what `--require-confirmation` asks `--yes`
  for, and what `--plan` reports.
- `api.run(ctx, args=..., action=...)` runs `action(live)` under the core rules: the JSON
  envelope (`command` is `"example tempo nudge"`), fixed exit codes, `--plan`/`--dry-run`
  without running the action, `--read-only` refusing non-read commands, and
  `--require-confirmation`. Return a JSON-serializable dict.
- `Live.request(name, args)` sends one Remote Script command over the documented TCP JSONL
  protocol and returns its `result`. The names are the protocol command names that `batch`
  steps use. The connection opens on the first request.
- A failed request raises `LiveError` with `error_code` (for example `INVALID_ARGUMENT`,
  `TIMEOUT`), `message`, `hint` and `details`. Catch it only to branch on a failure you
  expect (an index out of range, a device of another type); let everything else
  propagate so the core reports the original code and exit code.
- `api.error(code, message, hint=..., exit_code=...)` builds the error to raise. The code is
  prefixed with the plugin name (`EXAMPLE_TEMPO_TOO_HIGH`), and `exit_code` is one of the fixed
  `ExitCode` values (default `EXECUTION_FAILED`). Any other exception becomes
  `INTERNAL_ERROR`.
- `skills` lists skill directories, each holding a `SKILL.md`. A directory must be named after
  the plugin (`example`) or start with `example-`. `ableton-cli install-skill` copies them next
  to the core skill.

## Load failures

A plugin that fails any check is not mounted. Calling it returns `PLUGIN_LOAD_FAILED` with
`error.details.load_failure`, and `plugins list` / `doctor` report it. Core commands are never
affected.

| `load_failure` | Cause |
| --- | --- |
| `invalid_name` | the entry-point name does not match the naming rule (no stub is mounted) |
| `reserved_name` | the name is a core command group (no stub is mounted) |
| `duplicate_name` | two installed distributions provide the same plugin name |
| `import_failed` | importing the entry point raised |
| `not_a_plugin` | the entry point is not a `Plugin` |
| `name_mismatch` | `Plugin.name` differs from the entry-point name |
| `api_version_mismatch` | `Plugin.api_version` differs from the host's `PLUGIN_API_VERSION` |
| `invalid_skill` | a skill directory is misnamed or has no `SKILL.md` |
| `register_failed` | `register(api)` raised |
| `no_commands` | `register(api)` declared no commands |

## Testing

```python
from typer.testing import CliRunner

from ableton_cli.plugin_api.testing import FakeLive, create_plugin_test_app
from ableton_cli_example.plugin import PLUGIN


def test_plan_reports_a_write() -> None:
    app = create_plugin_test_app(PLUGIN)
    result = CliRunner().invoke(app, ["--output", "json", "--plan", "example", "tempo", "nudge"])
    assert '"kind": "write"' in result.stdout


def test_nudge_reads_then_sets() -> None:
    live = FakeLive({"transport_tempo_get": {"tempo": 120.0}, "transport_tempo_set": lambda a: a})
    ...  # call your action function with live
    assert [name for name, _ in live.requests] == ["transport_tempo_get", "transport_tempo_set"]
```

- `create_plugin_test_app(*plugins)` builds the full CLI with exactly those plugins loaded.
- `FakeLive(responses)` answers `request` from canned results (or functions of the args) and
  records every request; an unexpected command fails the test. A response function can
  raise `LiveError(error_code=..., message=..., exit_code=ExitCode...)` to simulate a
  failure.
- For end-to-end runs against recorded Live traffic, use the global `--record` / `--replay`
  options.

## Releasing

Users pin installs to a commit, so publish changes as tags and tell users to run
`ableton-cli plugins update <name> --ref <tag>`. When the host bumps `PLUGIN_API_VERSION`,
release a version of the plugin that declares the new version.
