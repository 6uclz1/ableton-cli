# Ableton Live 12 GUI Playbooks

Verified with Ableton Live 12.4 on macOS.

## Open a plug-in window

- Select the track. The device view shows the plug-in.
- Click the wrench icon in the plug-in's device title bar. `browser load` usually opens the window
  automatically.
- To close the window, click its close button. The first click often only focuses the window, so a
  second click may be needed.

## Expose plug-in parameters (Configure)

1. Select the track and click the fold triangle in the plug-in's title bar to show its parameter
   panel.
2. Click `Configure`.
3. Open the plug-in window and touch each knob you want to expose. Wait about 0.7 s between
   knobs: touching knobs back to back registers only the first one.
4. Close the window and click `Configure` again to leave Configure mode.
5. Verify through the CLI:

       uv run ableton-cli --output json device parameters list --track-index <track> --device-index <device>

   The exposed parameters are listed after `Device On` and can now be set with
   `device parameter set`.

## Map a modulator

1. Load the modulator through the CLI, for example `browser search LFO`, then `browser load`.
   Set its rate, shape, and depth with `device parameter select` and `device parameter set-display`.
2. In the device view, click `Map` until it is filled orange (armed).
3. Click the target parameter's slider or knob. Clicking its label only selects the device.
4. Confirm that the `Map` slot now shows the target parameter's name.

## Draw arrangement automation

1. Switch to Arrangement view (`Tab` with the main window focused).
2. Turn on View -> Automation Mode. Single-key shortcuts can be swallowed, so the menu is more
   reliable.
3. In the track's automation chooser, pick the device and then the parameter.
4. Click directly on the automation line to add a breakpoint. A click off the line only moves the
   insert marker.
5. Add points at the section boundaries, then drag the inner point to the target value. Drags
   overshoot easily, so hold the mouse button, zoom to read the value tooltip, adjust, then release.
6. Check feedback-type targets (delay feedback, resonance) for runaway values above 100%.

## Save the set

1. Press `Cmd+S`. A new set opens the Save dialog.
2. Choose the folder and type a file name. Live creates a `<name> Project` folder next to it.
3. Verify the result offline:

       uv run ableton-cli --output json set lint --path "<saved set>.als"

## Return to arrangement playback

`session capture` leaves its take in the session slot and lights Back to Arrangement, so the take
plays over the arrangement on the next play.

1. Stop the take on the CLI: `uv run ableton-cli session stop-all-clips`.
2. Take a screenshot, find the lit (orange) Back to Arrangement button, and click it.
3. Confirm the button is unlit before the next playback.

## Input tips

- Knobs and sliders: use `left_mouse_down`, several small `mouse_move` steps, then `left_mouse_up`.
  A single fast `left_click_drag` is often ignored.
- Screenshots report a hidden helper process for plug-in windows. They still render, and no extra
  access grant is needed.
- After a GUI change, read it back through the CLI wherever possible instead of trusting the
  screenshot alone.
