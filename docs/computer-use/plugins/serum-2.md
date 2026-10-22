# Serum 2

Verified with Serum 2 (VST3, Xfer Records) in Ableton Live 12.4.

## Load

    uv run ableton-cli --output json browser search Serum --item-type loadable
    uv run ableton-cli --output json browser load <track> <uri-from-search>

Right after loading, `device parameters list` reports only `Device On`. Everything below needs
Computer Use until the parameters are configured
(see [../ableton-live.md](../ableton-live.md#expose-plug-in-parameters-configure)).

## Load a preset

1. Open the plug-in window and click the browser icon to the left of `MENU` in the header.
2. Narrow the list down using one of these:
   - Click a category tag (`Pad`, `Pluck`, `Bass`, ...).
   - Pick a folder in the `Factory` tree.
   - Type in the search field and press Return. The list does not filter until Return is pressed.
3. Double-click a preset to load it. The header shows its name.
4. Click the browser icon again to return to the synth view.

Factory naming prefixes help when choosing: `BA` bass, `PD` pad, `PL` pluck, `LD` lead, `ARP`
arpeggio, `FX` effects.

## Edit macros and FX

- The eight macros sit at the lower left of the `OSC` view. Presets name them (for example
  `FM`, `DETUNE`, `VERB`). The preset name gets a `*` once it has been modified.
- The `FX` tab shows the preset's internal effect rack (distortion, compressor, EQ, and so on).
  Adjust drive and mix there rather than adding duplicate Live devices.
- After editing, expose the macros you want to automate through Configure, so later passes can run
  through the CLI.

## Patterns that worked

- Bass: a reese preset, with the `FM` and `DETUNE` macros raised. Then a Live Compressor sidechained
  to the drums (CLI), and a Live LFO mapped to a configured filter macro.
- Automation: expose a macro with Configure, then draw an arrangement ramp on it across a section.
  `set automation write` cannot target plug-in parameters.
