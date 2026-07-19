# Releasing

Releases are fully automated: merging a version bump to `main` triggers the
`Release` workflow (`.github/workflows/release.yml`), which creates the git tag
and the GitHub Release with built `sdist`/`wheel` artifacts attached. No manual
tagging is required.

There is a single version for the whole repository: the CLI package version
(`ableton_cli.__version__`) and the Remote Script version
(`REMOTE_SCRIPT_VERSION`) must always be equal. A unit test enforces this.

## Steps

1. In a PR, bump the version in both places to the same `X.Y.Z`:
   - `src/ableton_cli/__init__.py` — `__version__` (single source for the
     package version; `pyproject.toml` reads it via `[tool.hatch.version]`)
   - `remote_script/AbletonCliRemote/command_backend_contract.py` —
     `REMOTE_SCRIPT_VERSION` (kept as a literal because the Remote Script runs
     standalone inside Ableton Live and cannot import `ableton_cli`)
2. Refresh version strings in doc examples if they reference the old version:
   - `skills/ableton-cli/SKILL.md` (ping example payload)
   - `docs/skills/examples/ping.json`
3. Refresh the lockfile and run the checks:

   ```bash
   uv lock
   uv run python -m ableton_cli.dev_checks
   ```

4. Merge the PR into `main`.

## What the workflow does

On every push to `main`:

1. `check` job reads `__version__` and looks for an existing `vX.Y.Z` tag.
   If the tag exists (no version bump), the workflow stops — normal merges are
   a no-op.
2. `release` job (only when the tag is new):
   - verifies package version == Remote Script version
   - runs `ableton_cli.dev_checks`
   - builds sdist + wheel with `uv build`
   - asserts the wheel bundles `remote_script/` and `skills/` assets under
     `ableton_cli/_bundled/` with no bytecode
   - smoke-tests the wheel: `uv tool install`, `--version`,
     `install-remote-script`, `install-skill --dry-run`
   - creates the tag and the GitHub Release (`gh release create vX.Y.Z dist/*
     --generate-notes`)

## Verifying a release

```bash
uv tool install git+https://github.com/6uclz1/ableton-cli@vX.Y.Z
ableton-cli --version
```
