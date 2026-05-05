# Remix Commands

## Manifest

```bash
uv run ableton-cli remix init --source /abs/source.wav --project ./proj [--rights-status private_test]
uv run ableton-cli remix inspect --project ./proj/remix_project.json
uv run ableton-cli remix set-target --project ./proj/remix_project.json --bpm 174 --key "F minor"
```

## Assets and Stems

```bash
uv run ableton-cli audio asset add --project ./proj/remix_project.json --role vocal --path /abs/vocal.wav
uv run ableton-cli audio asset list --project ./proj/remix_project.json
uv run ableton-cli audio asset remove --project ./proj/remix_project.json --role vocal --path /abs/vocal.wav
uv run ableton-cli audio stems list --project ./proj/remix_project.json
uv run ableton-cli audio stems split --project ./proj/remix_project.json --provider manual --out /abs/stems
```

## Analysis

```bash
uv run ableton-cli audio analyze --project ./proj/remix_project.json --detect bpm,key,downbeats,sections --manual-bpm 172 --manual-key "A minor"
uv run ableton-cli audio sections import --project ./proj/remix_project.json --sections "intro:1-8,chorus:33-48"
uv run ableton-cli audio beatgrid import --project ./proj/remix_project.json --downbeats "0.0,1.395,2.790"
```

## Arrangement and Generation

```bash
uv run ableton-cli remix plan --project ./proj/remix_project.json --style anime-club
uv run ableton-cli remix arrange --project ./proj/remix_project.json --form anime-dnb
uv run ableton-cli remix apply --project ./proj/remix_project.json --dry-run
uv run ableton-cli remix apply --project ./proj/remix_project.json --yes
uv run ableton-cli remix generate drums --project ./proj/remix_project.json --style dnb --section chorus_drop
uv run ableton-cli remix generate bass --project ./proj/remix_project.json --pattern offbeat --key "F minor"
uv run ableton-cli remix generate chords --project ./proj/remix_project.json --progression "i-VI-III-VII"
uv run ableton-cli remix vocal-chop --project ./proj/remix_project.json --source vocal --section chorus --slice 1/8 --create-trigger
uv run ableton-cli remix setup-sound --project ./proj/remix_project.json --kit club-drums --bass reese --lead supersaw
uv run ableton-cli remix mix-macro --project ./proj/remix_project.json --preset anime-club-basic
uv run ableton-cli remix setup-mix --project ./proj/remix_project.json
uv run ableton-cli remix setup-returns --project ./proj/remix_project.json
uv run ableton-cli remix setup-sidechain --project ./proj/remix_project.json
uv run ableton-cli remix device-chain apply --project ./proj/remix_project.json --chain drop-filter
```

## QA and Export

```bash
uv run ableton-cli remix qa --project ./proj/remix_project.json
uv run ableton-cli remix export-plan --project ./proj/remix_project.json --target /abs/out/remix.wav
```

## Clip Primitives

```bash
uv run ableton-cli clip props get 0 0
uv run ableton-cli clip loop set 0 0 --start 0 --end 16 --enabled true
uv run ableton-cli clip marker set 0 0 --start-marker 0 --end-marker 16
uv run ableton-cli clip warp get 0 0
uv run ableton-cli clip warp set 0 0 --enabled true --mode complex-pro
uv run ableton-cli clip warp conform 0 0 --source-bpm 174 --target-bpm 168 --profile full-mix --verify
uv run ableton-cli clip warp-marker list 0 0
uv run ableton-cli clip warp-marker add 0 0 --beat-time 33.0
uv run ableton-cli clip warp-marker add 0 0 --beat-time 33.0 --sample-time 12.345
uv run ableton-cli clip warp-marker move 0 0 --beat-time 33.0 --distance -0.5
uv run ableton-cli clip warp-marker remove 0 0 --beat-time 33.0
uv run ableton-cli clip gain set 0 0 --db -3.0
uv run ableton-cli clip transpose set 0 0 --semitones 2
uv run ableton-cli clip file replace 0 0 --audio-path /abs/replacement.wav
```

```bash
uv run ableton-cli arrangement clip props get 0 0
uv run ableton-cli arrangement clip loop set 0 0 --start 0 --end 16 --enabled true
uv run ableton-cli arrangement clip marker set 0 0 --start-marker 0 --end-marker 16
uv run ableton-cli arrangement clip warp get 0 0
uv run ableton-cli arrangement clip warp set 0 0 --enabled true --mode beats
uv run ableton-cli arrangement clip gain set 0 0 --db -6
uv run ableton-cli arrangement clip transpose set 0 0 --semitones -1
uv run ableton-cli arrangement clip file replace 0 0 --audio-path /abs/replacement.wav
```
