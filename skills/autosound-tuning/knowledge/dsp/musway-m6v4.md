# MUSWAY M6V4 (non-512K) — filled-in DSP checklist (intake §4)

Ready answers to the capability checklist `project-intake.md §4`, folded from the onboarding
contribution `autosound-tuning-skill#14` (2026-09-01).

> **Where these answers come from, said once so no row has to repeat it.** Two sources: a tuner's
> reading of the **MUSWAY PC software (demo build, no unit connected)** and the **vendor datasheet**
> (`musway.de/assets/m6v4.pdf`, 40 pp., "TECHNICAL SPECIFICATIONS"). Nothing here was measured on
> hardware — **this processor is in no run of ours** (autosound-hub `#26`). Where the two sources
> disagree, both are recorded and the field stays `null` in the machine profile; a plausible bound
> written into a machine-readable profile becomes a limit code enforces and nobody re-questions.
>
> ⚠️ **The 512K variant is different silicon** (ADAU1466 vs ADAU1452) whose published DSP
> specification block is **byte-identical**. Do not read this file as covering it.

| Question | MUSWAY M6V4 (non-512K) |
|---|---|
| Slot counts per tier (`max_count`) | **Outputs: 8** — 6 amplified + 2 RCA pre-out |
| Processing layers | **One.** No virtual/group tier above the channels → the base+voicing architecture (`diagnostic §6`) is **not available**: voicing is L=R linked output EQ, and joint phase has to be watched by hand |
| EQ | **31 bands/channel, PK only** — no shelf, no all-pass. 20–20 000 Hz · ±15 dB · Q 0.1–10. Steps: F **1 Hz**, Q **0.01**, G **0.1 dB**. **No file import** → path 2 below. **No EQ bypass**: to A/B against flat you zero the bands or park a flat preset |
| Crossovers | Independent HP/LP per output, 20–20 000 Hz, **1 Hz step**. The menu offers **Bessel / Butterworth / Linkwitz, each at 6/12/18/24/30/36/42/48 dB/oct**. ⚠️ **A true Linkwitz-Riley alignment exists only at EVEN orders.** The machine profile therefore lists LR at 12/24/36/48 only — the odd-order LR entries are vendor menu labelling whose actual phase behaviour nobody has measured, and a search space is not the place to find out (the Helix precedent: an unidentifiable family is excluded from the search, not fed into it) |
| Delays / polarity / phase | Per output. Step **0.021 ms** = one sample at 48 kHz (the datasheet's own "Fine Set 0.02 ms"). Polarity NORM/INV only — **no continuous all-pass phase control**, so the phase method is limited to slope + delay + polarity. **Maximum delay: unresolved** — see the last row |
| Presets | **6.** ⚠️ **The input selection switches with the preset** — the "silent input reset" trap (`competition.md` Pre-session #4). Practical defence: give every working preset the same input |
| Inputs | 6 hi-level · 2 aux RCA · 2 optical · Bluetooth 2ch (optional) · **no USB audio**. **Aux RCA is the measurement input**: the sweep bypasses the head unit, so nothing carries OEM EQ, loudness or level-dependent processing |
| Input routing | A full matrix (all inputs × all outputs) with a level in **every cell**, 0…−60 dB, 1 dB step. ⚠️ **There is no per-input processing row** — the level lives in the cells. So the measurement input's row must carry identical cell levels across any channels being compared; an unequal cell reads as a level error that looks acoustic |
| Gain staging | Per output −59.9…0 dB plus a master 0…−59 dB. **Attenuation only — no positive gain**, so all headroom management is downward and a quiet channel cannot be trimmed up. The universal method still applies (min amp gain + max DSP level → first THD jump → back off ~10%); the resulting number is rig-specific |
| Native rate | **48 000 Hz — derived, not vendor-stated.** The datasheet prints only `DIGITAL SIGNAL PROCESSOR (64 bit Clock speed: 295 MHz)`; that is the Analog Devices SigmaDSP ADAU145x core clock 294.912 MHz = 6144 × 48 kHz. Corroborated independently by the delay fine step being exactly 1/48000 s. *Generalizable:* any DSP quoting a ~295 MHz clock is an ADAU145x at 48 kHz |
| Config file | Not established here |
| Software / transport | MUSWAY PC software, Windows. The EQ path below types into its window, so the DSP host and the REW host are the same machine (or one courier step) |
| Other | ⚠️ **Two speeds of sound are implied by the vendor's own numbers**: the datasheet step pairs (0.08 ms = 2.8 cm; 0.02 ms = 0.7 cm) imply **350 m/s**, while the software's 425 cm ↔ 12.5 ms limit implies **340 m/s**. → **Never hand-convert between the app's cm readout and ms.** Propose time alignment in ms and let the app derive centimetres |
| **Unresolved — do not treat as settled** | **Maximum delay.** Datasheet says `0–17 ms` **and** `0–692 cm`, which contradict each other (692 cm at the datasheet's own 350 m/s is 19.8 ms). The demo build showed **425 cm = exactly 12.50 ms at 340 m/s**, and a demo build may not expose a connected unit's limits. `delay.max_ms` stays `null`. Practical impact is near zero — in-car TA rarely exceeds ~8 ms — but the library must not record 17 ms as fact. Also inferred, not confirmed: the optical input takes PCM up to 96 kHz / 24 bit per the datasheet and is *presumed* sample-rate-converted to the 48 kHz core |

## EQ transfer — no file import

Path 2 of the template: **REW-EQ-CopyPaste-Assistant**
(github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) types REW's filter values into the MUSWAY
window. Consequence for any filter proposal: it must be expressible as **REW PK filters on the grid
F = 1 Hz / Q = 0.01 / G = 0.1 dB**, within **31 bands per channel** — and PK only, since this
processor has neither shelf nor all-pass bands.

## What this file does not answer

The machine-readable twin is `profiles/musway-m6v4.json`; `open-questions` run against it lists
every remaining `null` plus the notes above. Nothing here replaces a measurement: the moment this
processor appears in a real run, the delay maximum, the odd-order Linkwitz entries and the optical
input's rate conversion are the three things to settle first.
