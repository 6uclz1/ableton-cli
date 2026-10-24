# Remix Workflow

The remix layer is manifest-first. The Python CLI owns project state, asset paths, analysis metadata, arrangement plans, QA, and provider integration. Ableton Live receives only explicit primitive commands or batch steps.

## MVP Flow

```bash
uv run ableton-cli remix init --source /abs/anime_song.wav --project ./proj
uv run ableton-cli audio asset add --project ./proj/remix_project.json --role vocal --path /abs/vocal.wav
uv run ableton-cli audio asset add --project ./proj/remix_project.json --role instrumental --path /abs/instrumental.wav
uv run ableton-cli audio sections import --project ./proj/remix_project.json --sections "intro:1-8,verse:9-24,pre:25-32,chorus:33-48"
uv run ableton-cli remix plan --project ./proj/remix_project.json --style anime-club
uv run ableton-cli remix apply --project ./proj/remix_project.json --dry-run
uv run ableton-cli remix apply --project ./proj/remix_project.json --yes
uv run ableton-cli remix vocal-chop --project ./proj/remix_project.json --source vocal --section chorus --slice 1/8 --create-trigger
uv run ableton-cli remix qa --project ./proj/remix_project.json
```

## Rights Metadata

`rights_status` is stored in `remix_project.json`. Use this layer for cleared material, private test material, or original material metadata. The CLI does not grant copyright, neighboring-rights, arrangement, translation, or master-use permission.

## Planning Boundary

`remix plan` writes an arrangement plan into the manifest and does not contact Ableton Live. `remix apply --dry-run` returns the batch steps. `remix apply --yes` sends the stored steps to `execute_batch`.
