# <DSP model> — capability profile (fill from `project-intake.md §4`)

> **Copy this file to `knowledge/dsp/<dsp-slug>.md` and fill it for the project's DSP.**
> The point: capture the DSP's **capabilities** once, so the skill knows which tools/paths apply — and a fresh session doesn't re-derive them. The filled worked example is `helix-dsp-ultra-s.md`; the rest of the skill is DSP-agnostic.
> ⚠️ **Capabilities ≠ project numbers.** Anything that depends on the AMPS / install (e.g. an Output gain like `−6 dB`, the actual crossover values) is **project state** (`autosound_context.md`), not a DSP fact — derive it by measurement, never copy another rig's number.

| Question | <DSP model> |
|---|---|
| **Processing layers** | Is there a **virtual/group layer above** the per-channel one? → the base+voicing architecture works (`diagnostic §6`). None → voicing = L=R linked on the output EQ (careful with joint phase; voicing presets cost more). |
| **EQ** | Bands/channel? · types (PK / shelf / all-pass)? · **file import + format**? (none → REW-EQ-CopyPaste-Assistant, below). |
| **Crossovers** | Types (LR / BW / BE)? · orders? · independent HP/LP per channel? · frequency accuracy? → which sets from `filter-types-car-audio.md` are realizable. |
| **Delays / polarity / phase** | Delay step + limits? · polarity NORM/INV per channel? · a **phase control (all-pass)**? at which frequency / order? → the phase method. |
| **Presets** | How many? · ⚠️ **what resets on a switch (the INPUT!)** — the "silent input reset" trap (`competition.md`, Pre-session #4). |
| **Inputs** | RCA / optical / coax / BT / USB? · a **separate input for the measurement signal**? → Pre-session #4 for this car. |
| **Gain staging** | Universal method: min amp gain + max DSP level → raise to the first THD jump (RTA) → back off ~10%. ⚠️ The resulting Output number is **RIG-specific** (DSP output voltage × amp sensitivity) — measure it, don't copy. |
| **Native sample rate** | ? → measure the main mic rig at it where possible. |
| **Config file** | Parseable, or binary/encrypted (RESTORE-only)? → if not parseable, a **backup map** is mandatory (`naming-and-structure §4a`); the tool's file-version ≠ our `vN`. |
| **Software / transport** | OS? · same host as REW, or a VM → one **courier step** for the EQ export via a shared folder? |
| **Other** | DAC filter / FX / sound-field (a surround DSP **opens a surround preset** — capability-driven, `preset-strategy.md`) / any quirk worth a line. |

## EQ transfer — the two paths

1. **File import** (if supported) → in REW set the Equaliser to the DSP's format, export, import into the DSP. Advantage: you see the filters' effect on the curve in REW first. (Helix = Audiotec-Fischer → `helix-eq-export.md`.)
2. **No file import → REW-EQ-CopyPaste-Assistant** (github.com/IvanBakhmutov) — clipboard → keystrokes typed into the DSP software's own window; **30+ platforms** (Musway, ESX, Zapco, Goldhorn, Ground Zero, Nakamichi-K…). Claude prepares the band package the same way (via REW or `rew_tool`).

> **Deep per-DSP workflow** (only if you use this DSP heavily): create `references/<dsp>-workflow.md`, the equivalent of the Helix trio `helix-vcp-workflow` / `helix-eq-export` / `helix-phase-allpass` (layer architecture, gain staging, EQ exchange, phase). For most projects this capability profile is enough.
> **Source:** the project's `autosound_context.md` §4. De-identify before sharing (`feedback-loop.md`): the DSP class + capabilities, no personal data.
