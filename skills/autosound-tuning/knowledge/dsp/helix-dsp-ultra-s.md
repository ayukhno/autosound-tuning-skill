# Helix DSP Ultra S — filled-in DSP checklist (intake §4)

Ready answers to the capability checklist `project-intake.md §4`. Detail — in the three references: `helix-vcp-workflow.md` (architecture/gain/AKM) · `helix-eq-export.md` (EQ exchange) · `helix-phase-allpass.md` (phase).

| Question | Helix DSP Ultra S |
|---|---|
| Processing layers | **2: VIRTUAL (groups Front L/R, Center, Rear **and SUB** — a virtual sub channel exists, user-verified 2026-07; an earlier "no virtual sub" note was wrong; Link L+R) + OUTPUT** (per-channel) → the base+voicing architecture works fully; RealCenter pulls its signal from the virtual layer |
| EQ | **30 bands/channel**, types PK / LS_Q / HS_Q + **AP1/AP2** (all-pass, several allowed). **File import ✓** — Audiotec-Fischer format (REW Equaliser = "Audiotec-Fischer") → never enter by hand (the bank can't be seen all at once). **AP2 is hardware-verified** (2026-07, same-session single-variable A/B: sweep → flip only the APF → sweep): the complex ratio's free fit recovered the entered f0/Q/sign (4386/3.82 fitted vs 4414/4.0 entered, 31° RMS) — model it as the textbook/RBJ 2nd-order all-pass (`helix-phase-allpass.md`). **LS_Q/HS_Q at Q=0.7071 ≡ RBJ shelf S=1** — in REW model them with its "LS Q"/"HS Q" filter types (plain REW "Low shelf"/"High shelf" is a DIFFERENT definition). Modeling a FULL channel (crossovers+EQ) in REW → the **Generic Extended** equaliser, 20 slots (the Audiotec-Fischer preset lacks crossover filter types) — push schema in `rew-api-quirks.md` |
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

## Worked settings-sheet example (illustrates SKILL.md's presentation rule)

`SKILL.md`'s always-loaded core requires every actionable DSP change to be presented as a step-by-step, arrow-pointer (`──►`) list — samples **and** ms, never a bare file reference. This is what that looks like on THIS DSP (a different DSP profile would show its own PC-Tool/app steps; the rule itself is DSP-agnostic — see SKILL.md).

```markdown
### Крок 1. Налаштування процесора в Helix PC-Tool (Примітка: затримки розраховано для Helix 96 кГц)
1. Запустіть Helix PC-Tool на вашому Windows-комп'ютері або у віртуальній машині.
2. Перейдіть у меню Crossovers (Кросовери) та встановіть для каналів:
    • ВЧ (tw-L, tw-R): HPF = 3500 Гц | Крутизна = Linkwitz-Riley 24 дБ (LR4).
    • СЧ (m-L, m-R): HPF = 300 Гц, LPF = 3500 Гц | LR4 (24 дБ).
    • НЧ (w-L, w-R): HPF = 60 Гц, LPF = 300 Гц | LR4 (24 дБ).
    • Сабвуфер (sw): HPF (Subsonic) = 20 Гц BW2 (Butterworth 12 дБ) | LPF = 60 Гц LR4 (24 дБ).
    • Тил (r-L, r-R) та Центр (c): Тимчасово заглушіть (Mute).
3. Перейдіть у меню Time Alignment (Затримки) та введіть значення (мілісекунди — абсолютний референс, семпли наведено для 96 кГц):
    • tw-L (Канал A) ──► 626 семплів (6.52 мс)
    • tw-R (Канал B) ──► 510 семплів (5.31 мс)
    • m-L  (Канал C) ───► 633 семпли (6.59 мс)
    • m-R  (Канал D) ───► 515 семплів (5.36 мс)
    • w-L  (Канал E) ───► 522 семпли (5.44 мс)
    • w-R  (Канал F) ───► 450 семплів (4.69 мс)
    • sw   (Канал H) ────► 0 семплів (0.00 мс)
4. Перейдіть у меню Gain (Рівні) та притисніть ліву сторону для базового балансу сцени:
    • tw-L ──► -1.5 дБ | m-L ──► -2.0 дБ | w-L ──► -1.5 дБ
    • Всі праві канали та саб залишаються на 0.0 дБ.
5. Збережіть цей пресет у процесор (наприклад, у Слот 1) та збережіть файл на комп'ютер як B8_EMMA_v1_foundation.pct6.
```
