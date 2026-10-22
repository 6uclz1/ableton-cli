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

`integrated_lufs`, `lra_lu`, `true_peak_dbtp`, `momentary_lufs_max`, and
`short_term_lufs_max` come from ffmpeg's `ebur128` filter (ITU-R BS.1770 K-weighting and
gating, 4x-oversampled true peak). `sample_peak_dbfs`, `rms_dbfs`, `crest_db`,
`clipping_sample_count`, and `dc_offset` are computed from the PCM samples. True peak can
sit several dB above sample peak, so check `true_peak_dbtp` against the ceiling. If ffmpeg
fails or its output has no EBU R128 summary, the command fails with `INTERNAL_ERROR`.

`audio spectrum analyze` reports, in `bands`, the RMS level (dBFS) of the mono downmix in
each band over the whole file: `sub_20_60_hz`, `bass_60_120_hz`, `low_mid_120_400_hz`,
`mid_400_2000_hz`, `presence_2000_6000_hz`, `brilliance_6000_10000_hz`, and
`air_10000_18000_hz`. ffmpeg cuts each band brick-wall in the FFT domain (`afftfilt`), so
the command needs ffmpeg and fails with `CONFIG_INVALID` without it. To compare sections
or tracks, capture each one (`session capture`) and analyze the captures.

Spectrum warnings judge tonal balance, not loudness: each band is compared, relative to
the file's full-band level, with the profile's expected share. A band more than 6 dB above
its share is `<band>_hot` and one more than 8 dB below is `<band>_low`; a file with no
signal gets `silent`. The `anime-club-balanced` shape models a spectrum whose energy per
octave falls 1.5 dB per octave (the -4.5 dB/octave slope of a per-Hz analyzer); the other
profiles are offsets from it. Treat the warnings as a first pass; a registered reference
track (`audio reference compare`) is the better guide for EQ decisions.

Spectrum profiles are diagnostic presets, not platform specifications. `broadcast-r128`
uses the EBU R128 programme loudness target of -23.0 LUFS and is separate from music
demo presets such as `anime-club-demo`.

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
