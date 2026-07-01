# Helix DSP Ultra S — filled-in DSP checklist (intake §4)

Ready answers to the capability checklist `project-intake.md §4`. Detail — in the three references: `helix-vcp-workflow.md` (architecture/gain/AKM) · `helix-eq-export.md` (EQ exchange) · `helix-phase-allpass.md` (phase).

| Question | Helix DSP Ultra S |
|---|---|
| Processing layers | **2: VIRTUAL (groups Front L/R, Center, Rear; Link L+R) + OUTPUT** (per-channel) → the base+voicing architecture works fully; RealCenter pulls its signal from the virtual layer |
| EQ | **30 bands/channel**, types PK / LS_Q / HS_Q + **AP1/AP2** (all-pass, several allowed). **File import ✓** — Audiotec-Fischer format (REW Equaliser = "Audiotec-Fischer") → never enter by hand (the bank can't be seen all at once) |
| Crossovers | BE2-8 / BW1-8 / LR2-8; HP/LP independent per channel; accuracy to 0.01 Hz |
| Delays / polarity / phase | Delay per channel (ms, fine step); Polarity NORM/INV per channel; **Phase 0–360°** = 2nd-order all-pass at the crossover frequency (for the sub — from the LPF), not visible in the EQ bank; **not applied to the midbass** (the reference); alignment order: midbass → sub → mid → tweeter |
| Presets | Several; ⚠️ **switching can silently reset the INPUT to another card** — check the input after every switch (Pre-session #4) |
| Inputs | RCA/LineIN · optical S/PDIF · BT HD (module) · USB expansion cards; **ISA** (Input Signal Analyzer) = real-time clip check |
| Gain staging | **Method (universal):** min amp gain + max DSP level → raise to the first THD jump (RTA) → back off ~10%. ⚠️ **`−6 dB` Output is RIG-specific, NOT a default:** it follows from the Ultra S's 8 V outputs + the sensitivity of the author's SPECIFIC amps (≈4 V). A different DSP / different amps → a different number; derive it by YOUR own measurement, don't copy −6 dB blindly |
| Native rate | **96 kHz** — measure the main mic rig at it |
| Config file | `.pct6` — **encrypted** (RESTORE-only, can't be parsed). ✅ Proven 2026-06-14: `AT` header + entropy 7.92 b/byte, 0 archive magic, no decompressor; two versions differing by a few parameters → a shared prefix of only **3 bytes** + 2% matches (random level) = a cipher with a per-save IV, NOT an archive/compression. Not reversible. → a backup map is mandatory (`naming-and-structure.md §4a`); the PC-Tool file version ≠ our `vN`. **The only readable path is via the EQ export (text, Audiotec-Fischer, `helix-eq-export.md`)** — and even that is only the EQ bank, not crossovers/TA/gain/routing (those come from measurement OR a **screen-read off the PC-Tool screen**, `references/tooling/screen-read-dsp.md`) |
| Software | PC-Tool is **Windows-only** (on Mac → Parallels; the courier step = the EQ export via a shared folder) |
| Other | **AKM DAC filter** (ACO Features → AKM Config): SQ recommendation **Short Delay Slow Roll Off** — *Short Delay* = minimum-phase → no pre-ringing → a tighter attack; *Slow Roll-Off* = gentle → less ringing (a tiny roll-off near Nyquist, unimportant). This is taste/SQ-philosophy, not dogma. ⚠️ **Changing the DAC filter → do NOT redo TA** (global + uniform across all channels → relative timing intact; the time effect is near Nyquist ~20k+, not in the joint band) — just an aural sanity-check of transients. FX/Virtual X affects the measurement (the `FX` suffix in names) |

## EQ transfer — two paths

1. **Canonical (Helix): file import** of Audiotec-Fischer → `helix-eq-export.md`. Advantage: in REW you immediately see the filters' effect on the curve. ⚠️ If file import is inconvenient (e.g. the path through Parallels/VM on Mac — feedback from a live test) → you can try path 2 on the **Helix PC-Tool window** too (the keystroke approach is generic; PC-Tool field compatibility is **provisional, not verified on Helix**).
2. **Alternative (and the path for DSPs without import): REW-EQ-CopyPaste-Assistant** (github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) — a Windows/PowerShell helper: "Copy" in REW's EQ section → the tool converts the clipboard into keystroke sequences and types the bands into the DSP software's window itself (click the first band → auto-entry). **30+ platforms**: Musway TUNEST_PC (verified by the skill author), ESX, Zapco, Goldhorn, Ground Zero, Nakamichi-K, etc. Claude can prepare a filter package for copying the same way it prepares an Audiotec-Fischer file (via REW or `rew_tool`).
