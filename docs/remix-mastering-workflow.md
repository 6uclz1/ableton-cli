# Remix Mastering Workflow

Use this flow after a remix arrangement has been rendered.

Measuring a render needs the [`analysis` plugin](https://github.com/6uclz1/ableton-cli-analysis)
and `ffmpeg`/`ffprobe` on `PATH`; without them the `analysis` commands fail explicitly with
`CONFIG_INVALID`. Register each report it writes with `remix mastering report add` (see
[mastering.md](mastering.md)) so QA reads it.

```bash
uv run ableton-cli --output json remix mastering profile list
uv run ableton-cli --output json remix mastering target set --project ./proj/remix_project.json --profile anime-club-demo --true-peak-dbtp-max -1.0
uv run ableton-cli --output json remix mastering reference add --project ./proj/remix_project.json --path ./refs/reference.wav --role commercial-reference --id ref-main
uv run ableton-cli --output json analysis loudness analyze --path ./renders/remix.wav --report-out ./proj/reports/remix_loudness.json
uv run ableton-cli --output json analysis reference compare --candidate ./renders/remix.wav --reference ./refs/reference.wav --report-out ./proj/reports/remix_reference.json
uv run ableton-cli --output json remix mastering report add --project ./proj/remix_project.json --kind loudness --report ./proj/reports/remix_loudness.json
uv run ableton-cli --output json remix mastering report add --project ./proj/remix_project.json --kind reference_compare --report ./proj/reports/remix_reference.json
uv run ableton-cli --output json remix mastering plan --project ./proj/remix_project.json --target anime-club-demo --chain utility,eq8,compressor,limiter
uv run ableton-cli --output json remix mastering apply --project ./proj/remix_project.json --dry-run
uv run ableton-cli --output json remix mastering apply --project ./proj/remix_project.json --yes
uv run ableton-cli --output json song export audio --path ./renders/remix_mastered.wav
uv run ableton-cli --output json analysis loudness analyze --path ./renders/remix_mastered.wav --report-out ./proj/reports/remix_mastered_loudness.json
uv run ableton-cli --output json remix mastering report add --project ./proj/remix_project.json --kind loudness --report ./proj/reports/remix_mastered_loudness.json
uv run ableton-cli --output json remix mastering qa --project ./proj/remix_project.json --render ./renders/remix_mastered.wav --strict
uv run ableton-cli --output json remix qa --project ./proj/remix_project.json --include-mastering --render ./renders/remix_mastered.wav
```

The manifest schema is v2. Loading a v1 remix manifest migrates it by adding:

- `mastering_targets`
- `reference_tracks`
- `analysis_reports`
- `master_chain_plan`

`remix mastering plan` only updates the manifest. `remix mastering apply --dry-run`
returns the batch steps that would be executed. `--yes` is required before the batch path
is used.

Reference comparison recommendations intentionally distinguish `scope: mix` from
`scope: master`. Large reference deltas should usually be corrected in stems, source
balance, or arrangement decisions before a master chain is pushed harder.
