# Mastering Commands

The mastering surface is split into offline analysis (the `analysis` plugin), master-track
primitives, and remix workflow commands.

## Offline analysis

Loudness, spectrum, band-share and reference measurement run through ffmpeg in the
[`analysis` plugin](https://github.com/6uclz1/ableton-cli-analysis), not in the core. Install
it with `ableton-cli plugins install https://github.com/6uclz1/ableton-cli-analysis`; it needs
`ffmpeg` and `ffprobe` on `PATH` and fails explicitly (`ANALYSIS_FFMPEG_NOT_AVAILABLE`,
`CONFIG_INVALID`) without them. Its README documents every metric and spectrum profile.

To feed `remix mastering qa`, write the render's reports with `--report-out` and register
each one in the remix manifest:

```bash
uv run ableton-cli --output json analysis loudness analyze --path ./renders/remix.wav --report-out ./proj/reports/remix_loudness.json
uv run ableton-cli --output json analysis spectrum analyze --path ./renders/remix.wav --profile anime-club --report-out ./proj/reports/remix_spectrum.json
uv run ableton-cli --output json remix mastering report add --project ./proj/remix_project.json --kind loudness --report ./proj/reports/remix_loudness.json
uv run ableton-cli --output json remix mastering report add --project ./proj/remix_project.json --kind spectrum --report ./proj/reports/remix_spectrum.json
uv run ableton-cli --output json remix mastering qa --project ./proj/remix_project.json --render ./renders/remix.wav
```

`remix mastering report add --kind loudness|spectrum|reference_compare --report <json>`
records the report against the audio it measures (`path`, or `candidate` for a reference
comparison), which is how `remix mastering qa --render` finds it. It fails with
`INVALID_ARGUMENT` when the report is missing, is not a JSON object, or lacks a field QA
reads (loudness: `integrated_lufs`, `true_peak_dbtp`, `crest_db`, `clipping_sample_count`;
spectrum: `bands`, `stereo`, `warnings`).

### Per-track band diagnosis

```bash
uv run ableton-cli --output json session capture-tracks --track-index 0 --track-index 4 --track-index 9 --start 304 --bars 8 --bypass-main-devices
uv run ableton-cli --output json analysis spectrum shares --stem Kick=<captures[0].file_path> --stem Bass=<captures[1].file_path> --stem Lead=<captures[2].file_path> --resolution third-octave --focus Lead
```

`session capture-tracks` solos each listed track in turn and records the main output into a
temporary audio track (input Resampling, volume 0), which it deletes afterwards. The recorded
files stay in the Set's `Samples/Recorded` folder and are listed in `captures`. With
`--bypass-main-devices` it turns off every active main-track device first, so the master
chain does not color the measurement. Solos, the temporary track, and bypassed devices are
restored even when a capture fails. It refuses to start while any track is soloed, because
that track would leak into every capture. Captures run in real time: one bar of pre-roll
plus `--bars` at the Set's tempo, per track.

Both capture commands record from exactly `--start`. Live ignores a playhead moved while
stopped, and firing a clip from a stopped transport restarts the song at beat 0, so the
capture starts playback, moves the playhead one bar before `--start`, and fires the clip:
Live's launch quantization (1 Bar) begins the recording at `--start`. `--start` must
therefore be at least one bar. Each capture reports `recorded_start_beat` (the stop position
minus the file's length) and fails with `step: verify_recorded_start` when the recording
began more than half a beat away from `--start`, e.g. under another launch quantization.

Pass each capture's `label` and `file_path` to `analysis spectrum shares --stem LABEL=PATH`
to see which track owns each band.

## Master track primitives

```bash
uv run ableton-cli --output json master volume set 0.85
uv run ableton-cli --output json master panning set -- 0.0
uv run ableton-cli --output json device insert Utility --main
uv run ableton-cli --output json device move --to-index 0 --main --device-index 2
uv run ableton-cli --output json device delete --main --device-index 3
uv run ableton-cli --output json device parameters list --main --device-index 0
uv run ableton-cli --output json device parameter set-display --main --device-name Utility --parameter-name Gain -- -1.5
uv run ableton-cli --output json master effect limiter set 0.4 --device-query "Limiter" --parameter-key ceiling
```

Main-track devices are edited with the `device` commands and `--main`; results report
`"track": {"kind": "main"}`. `device insert` takes native Live device names and needs
Live 12.3+. `remix mastering apply` inserts its planned chain with `device_insert` on the
main track, so it needs Live 12.3+ as well.

`device delete` is destructive. Live API unsupported operations fail
with `not_supported_by_live_api`; the CLI does not add fallback execution paths.

## Judgment rules

- Measure after render before planning a chain.
- Do not increase global gain when true peak is near the ceiling.
- Do not use limiting alone to chase a LUFS target.
- Treat large bass, presence, or air deltas as mix/stem issues before master EQ.
- Run `remix mastering apply --dry-run` before applying with `--yes`.
