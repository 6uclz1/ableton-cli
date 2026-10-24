# Mini-notation pattern grammar (v1)

`--pattern` on `clip notes add` and `arrangement clip create` compiles a small
Strudel/TidalCycles-inspired mini-notation string into `notes-json`, offline,
with zero remote round-trips. The compiler lives in
`src/ableton_cli/pattern_notation.py` (`parse` + `compile_pattern`).

## Grammar (EBNF)

```
pattern     = step , { WS , step } ;
step        = element , [ "*" , int ] ;
element     = rest | chord | group ;
group       = "[" , pattern , "]" ;
chord       = note , { "," , note } ;
note        = pitch , [ "@" , int ] ;
pitch       = note_name | midi_number ;
note_name   = letter , [ "#" | "b" ] , octave ;
letter      = "a" | "b" | "c" | "d" | "e" | "f" | "g" ;
octave      = [ "-" ] , digit , { digit } ;
midi_number = digit , { digit } ;
rest        = "~" ;
```

- **Sequence**: whitespace-separated steps fill one cycle of `--pattern-length`
  beats (default `4.0`), each step getting equal duration.
- **Note step**: a pitch name with octave (`c3`, `f#4`, `eb2`) or a MIDI
  number (`60`). Octave convention matches Ableton Live's own display:
  `C3` == MIDI 60.
- **Rest**: `~`.
- **Subdivision**: `[a b c]` — the bracketed group occupies one step,
  subdividing it equally; nesting is allowed.
- **Repeat**: `x*2` — the preceding element repeated within its slot
  (equivalent to `[x x]`).
- **Chord**: `a,b,c` (comma, no spaces) — simultaneous notes sharing the slot.
- **Per-note velocity**: `c3@90` (falls back to `--velocity`, default `100`).

Nothing else is in scope for v1: no polymeter, no `<>` alternation, no
euclidean syntax (see `clip notes euclidean` for that).

## Examples

| Pattern | Meaning |
| --- | --- |
| `c3 e3 g3 c4` | Four quarter notes (at `--pattern-length 4`) |
| `c3 ~ e3 ~` | Notes on beats 1 and 3, rests on 2 and 4 |
| `c3 [e3 g3] c4 ~` | Beat 2 subdivided into two eighth notes |
| `c4*4` | Four equal repeats filling the whole pattern length |
| `c3,e3,g3 ~ ~ ~` | A C major chord on beat 1 |
| `c3@40 c3@127` | Two notes with explicit per-note velocity |

`clip notes add 0 0 --pattern "c3 ~ [e3 g3] c4*2" --pattern-length 4` compiles
to:

```json
[
  {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100, "mute": false},
  {"pitch": 64, "start_time": 2.0, "duration": 0.5, "velocity": 100, "mute": false},
  {"pitch": 67, "start_time": 2.5, "duration": 0.5, "velocity": 100, "mute": false},
  {"pitch": 72, "start_time": 3.0, "duration": 0.5, "velocity": 100, "mute": false},
  {"pitch": 72, "start_time": 3.5, "duration": 0.5, "velocity": 100, "mute": false}
]
```

## Errors

Malformed patterns raise `INVALID_ARGUMENT` with a 1-based column number in
the error message (unclosed `[`, unknown pitch letter, missing octave,
out-of-range MIDI pitch/velocity, non-positive repeat count).

`--pattern` is mutually exclusive with `--notes-json` and `--notes-file`.
