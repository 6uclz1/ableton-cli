# CLI Gaps That Need Computer Use

Verified with Ableton Live 12.4, Remote Script 0.5.0, and Serum 2 (VST3).

| Operation | Why the CLI cannot do it | Playbook |
| --- | --- | --- |
| Pick a plug-in's internal preset | Preset browsers inside plug-ins are invisible to the Live API | [plugins/serum-2.md](plugins/serum-2.md#load-a-preset) |
| Edit plug-in sound parameters (oscillators, macros, internal FX, internal LFOs) | VST3/AU plug-ins expose only `Device On` until they are configured | [plugins/serum-2.md](plugins/serum-2.md#edit-macros-and-fx) |
| Expose plug-in parameters to Live | Configure mode is GUI-only | [ableton-live.md](ableton-live.md#expose-plug-in-parameters-configure) |
| Map a modulator (LFO, Shaper, Envelope Follower) to a parameter | The Max for Live `Map` button cannot be pressed through the API | [ableton-live.md](ableton-live.md#map-a-modulator) |
| Write arrangement automation into the open set | The Remote Script writes session clip envelopes only. Live 12 refuses envelopes on arrangement clips | [ableton-live.md](ableton-live.md#draw-arrangement-automation) |
| Save the set | `song save` fails with `not_supported_by_live_api` | [ableton-live.md](ableton-live.md#save-the-set) |

## What stays on the CLI

- Native device parameters: `device parameters list`, `device parameter set-display`, and
  `device parameter select`.
- Plug-in parameters that have been configured: they appear in `device parameters list` and accept
  `device parameter set`.
- Loading plug-ins and Max for Live devices: `browser search`, then `browser load`.
- Compressor sidechain routing: `device sidechain set`.
- Offline arrangement automation for native device parameters on a saved set: `set automation write`.

## Limits that Computer Use does not remove

- `set automation write` cannot target plug-in parameters, because they have no XML tag in the set
  file. Draw plug-in automation in the GUI instead.
- `device sidechain` works on Compressor only.
- Live 12 modulators do not change a parameter's base value, so `device parameters list` cannot
  confirm a modulator mapping. Confirm it on screen: the modulator's `Map` slot shows the target
  name.
