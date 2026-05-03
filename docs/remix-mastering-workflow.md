# Remix Mastering Workflow

Use this flow after a remix arrangement has been rendered.

Offline mastering analysis depends on `ffmpeg` and `ffprobe` when the `ffmpeg`
engine is selected. Install both tools before running `remix mastering analyze`;
otherwise the analysis command fails explicitly with `CONFIG_INVALID`.

```bash
uv run ableton-cli --output json remix mastering profile list
uv run ableton-cli --output json remix mastering target set --project ./proj/remix_project.json --profile anime-club-demo --true-peak-dbtp-max -1.0
uv run ableton-cli --output json remix mastering reference add --project ./proj/remix_project.json --path ./refs/reference.wav --role commercial-reference --id ref-main
uv run ableton-cli --output json remix mastering analyze --project ./proj/remix_project.json --render ./renders/remix.wav --reference ref-main --report-dir ./proj/reports
uv run ableton-cli --output json remix mastering plan --project ./proj/remix_project.json --target anime-club-demo --chain utility,eq8,compressor,limiter
uv run ableton-cli --output json remix mastering apply --project ./proj/remix_project.json --dry-run
uv run ableton-cli --output json remix mastering apply --project ./proj/remix_project.json --yes
uv run ableton-cli --output json song export audio --path ./renders/remix_mastered.wav
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
