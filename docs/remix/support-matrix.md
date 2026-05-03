# Remix Support Matrix

This matrix defines the remix workflow boundary. `ableton-cli` keeps Ableton Live operations as explicit primitives and adds remix orchestration in the Python CLI layer.

| Operation | Session MIDI | Session Audio | Arrangement MIDI | Arrangement Audio | Policy |
| --- | --- | --- | --- | --- | --- |
| Notes add/replace | Supported | N/A | Supported | N/A | Existing note commands. |
| Audio import | Not supported | Not supported | N/A | Supported | Use `arrangement clip create --audio-path`. |
| Loop start/end | Added | Added | Added | Added | Uses clip `loop_start`, `loop_end`, `looping` when Live exposes them. |
| Markers | Added | Added | Added | Added | Uses clip `start_marker` and `end_marker`. |
| Warp mode | N/A | Added | N/A | Added | Uses clip `warping` and `warp_mode`; otherwise explicit failure. |
| Warp markers | N/A | Added | N/A | Deferred | Destructive; session command requires Live warp marker write API. |
| Transpose | Added | Added | Added | Added | Uses clip `pitch_coarse` when available. |
| Gain | N/A | Added | N/A | Added | Converts dB to clip `gain` when available. |
| File replace | N/A | Added | N/A | Added | Destructive; requires a Live file replacement API. |
| Consolidate/join | Unknown | Unknown | Unknown | Unknown | Not implemented; fail explicitly if requested later. |

Unsupported Live API surfaces must return an error with details reason `not_supported_by_live_api`. The CLI must not silently degrade to manual behavior or add compatibility shims.
