# Mastering Commands

The mastering surface is split into offline analysis, master-track primitives, and remix
workflow commands.

## Requirements

Offline mastering analysis with the `ffmpeg` engine requires both `ffmpeg` and
`ffprobe` on `PATH`. Without them, loudness analysis, reference comparison, and
remix mastering analysis fail explicitly with `CONFIG_INVALID`; the CLI does not
silently skip metrics or use a fallback analyzer.

## Offline analysis

```bash
uv run ableton-cli --output json audio loudness analyze --path ./renders/remix.wav --engine ffmpeg --report-out ./proj/reports/loudness.json
uv run ableton-cli --output json audio spectrum analyze --path ./renders/remix.wav --profile anime-club --report-out ./proj/reports/spectrum.json
uv run ableton-cli --output json audio reference compare --candidate ./renders/remix.wav --reference ./refs/reference.wav --metrics loudness,spectrum,stereo
```

`audio loudness analyze` reports integrated LUFS, true peak, sample peak, RMS, crest
factor, clipping count, and DC offset.

Spectrum profiles are diagnostic presets, not platform specifications. `broadcast-r128`
uses the EBU R128 programme loudness target of -23.0 LUFS and is separate from music
demo presets such as `anime-club-demo`.

## Master track primitives

```bash
uv run ableton-cli --output json master volume set 0.85
uv run ableton-cli --output json master panning set -- 0.0
uv run ableton-cli --output json master device load query:Audio\ Effects#Utility --position end
uv run ableton-cli --output json master device move --device-index 2 --to-index 0
uv run ableton-cli --output json master device delete --device-index 3 --yes
uv run ableton-cli --output json master device parameters list --device-index 0
uv run ableton-cli --output json master device parameter set --device-index 0 --parameter-key gain -- -1.5
uv run ableton-cli --output json master effect limiter set 0.4 --device-query "Limiter" --parameter-key ceiling
```

Device targets should come from `browser search` output. The CLI does not assume fixed
Browser URIs because packs, locale, Live version, and User Library contents vary.

Destructive master device deletion requires `--yes`. Live API unsupported operations fail
with `not_supported_by_live_api`; the CLI does not add fallback execution paths.

## Judgment rules

- Measure after render before planning a chain.
- Do not increase global gain when true peak is near the ceiling.
- Do not use limiting alone to chase a LUFS target.
- Treat large bass, presence, or air deltas as mix/stem issues before master EQ.
- Run `remix mastering apply --dry-run` before applying with `--yes`.
