# Reading DSP parameters off the SCREEN (screen-read) — when the file/export is unavailable

**When:** the DSP config can't be read from a file (e.g. the Helix `.pct6` is **encrypted**, proven) and there's no readable export of the CURRENT state → we read the parameters (crossover / TA / EQ / gain / polarity) **off the DSP software's screen** via screenshot + vision. DSP-agnostic (any software on screen). It complements the black-box-DSP branch: **intent from the screen, the acoustic result from REW**.

## Prerequisites (what to set up if you need this)
1. **macOS "Screen Recording"** for the terminal: System Settings → Privacy & Security → **Screen Recording** → enable your terminal (Terminal/iTerm) → **restart the terminal**. Without it, `screencapture` fails with `could not create image from display`. For on-demand reading this is the **ONLY thing needed**.
2. **The screen's logical resolution** (for the `-R` coordinates): `osascript -e 'tell application "Finder" to get bounds of window of desktop'` (e.g. 1800×1169 @2x Retina; physically 3600×2338). The `-R` coordinates are in logical points.
3. The DSP software is **visible on screen** (Parallels window / native), not minimized.
4. *(Only if you ever need to CONTROL the interface, NOT for reading):* `brew install cliclick` + the **Accessibility** permission (+restart). ⚠️ In Parallels synthetic **keystrokes don't reach the guest** (cliclick/System Events arrow keys are ignored); only a synthetic **Cmd+Tab** and the mouse work. So a **human** steps through the bands/channels; the tool only reads.

## Method (read-on-demand)
**Simplest (the MAIN path, confirmed in practice): the user takes the screenshot of the needed area themselves** (macOS `Cmd+Shift+4`, or `+Space` for a whole window) and hands over the file/path → Claude reads it with vision. The human knows what matters and frames it precisely — **no coordinate tiles** (no need to over-engineer the scanning).

*Alternative (when Claude needs to capture it itself, without switching):*
1. The user **navigates to the needed screen/parameter** in the DSP software.
2. Capture a **NATIVE-resolution area** (not the whole screen!): `screencapture -x -R x,y,w,h /tmp/cap.png`.
   - **Tile ≤ ~900 px wide.** A full screen (3600 px) is downscaled to the vision limit (~1500 px) → small text and LEDs die. A small area = native resolution = readable.
   - Check the size: `sips -g pixelWidth -g pixelHeight /tmp/cap.png`.
3. Read the tile with vision → extract the values.
4. Unclear (a digit/LED) → a **tighter crop** of the same area and re-read.

## Reading checklist (MANDATORY — against missing a state)
Before naming a VALUE — read IN THIS ORDER:
1. **Bypass/Enable of EVERY section** (highpass, lowpass, EVERY EQ band): the Bypass button with an LED — red/lit = the **section is OFF**, its values don't apply → say so explicitly. ⚠️ **The most-often-missed thing** (the crossover/band Bypass was overlooked several times in a row — do NOT repeat).
2. **Polarity / Mute** of the channel (red LED = inverted / muted).
3. **APF order** (1st / 2nd) on an all-pass — a button with an LED.
4. **Type** (Fine / Parametric / High-Low Shelf / Allpass) → and only THEN the numbers (dB / Hz / Q).
> Rule: **no value without its enable/bypass state alongside.** Numbers without "on/off" are unreliable.

## Critical gotchas (proven in practice 2026-06-14)
- **Downscaling:** a large frame gets compressed → always work in small tiles, not the full screen.
- **Small colored LEDs = STATE; read them deliberately, zoomed in:** **Mute** red = muted; **Bypass** red = the filter/band is OFF; the **APF order** button (1st/2nd order). In a downscale they vanish — this is a source of typical reading errors.
- **Parallels VM:** synthetic keystrokes don't reach the guest → a human steps through; Cmd+Tab and the mouse work.
- **The EQ band panel differs by TYPE:** Fine / Parametric → `dB·Hz·Q`; High/Low Shelf → `dB·Hz·Q(slope)`; **Allpass → `Hz·Q`, no dB**. **Parametric/Allpass show the band NUMBER** — a useful sync checkpoint.
- Band values are shown **one at a time** (a selector/arrow) → a full EQ dump = stepping through the bands (for now, by a human).

## Full sweep — DEFERRED, on-demand for now
If you ever need to capture ALL bands/channels systematically → the **STEP-CONFIRM** algorithm: the human steps linearly (only →); on each step the tool captures + **checks the change (`md5`)** (catches a skipped/double step LIVE) + numbers it, cross-checking against the band number on the Parametric/Allpass panel. **Not implemented as automation** (synthetic keystrokes don't reach Parallels, live narration is impossible, dedup gets confused on non-linear navigation). Keep it as a plan; for now — on-demand.

## Related
- `.pct6` is encrypted (can't be parsed) → `knowledge/dsp/helix-dsp-ultra-s.md`. The only partially-readable Helix file = the AF **EQ export** (text) → `helix-eq-export.md`.
- Integration into tuning: intent from the screen + acoustics from REW → `diagnostic-techniques.md`, `analysis-playbook.md`.
