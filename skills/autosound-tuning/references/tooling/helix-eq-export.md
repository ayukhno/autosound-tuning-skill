# Helix DSP — EQ export format (Audiotec-Fischer) and REW → Helix exchange

## Goal
Don't enter EQ into Helix by hand (the per-channel EQ can't be viewed/copied all at once). Instead — **export from REW in the Audiotec-Fischer format → import into the Helix PC-Tool as a single file**.

## The canonical path
1. In REW (EQ window) set **Equaliser = "Audiotec-Fischer"** (via the API: `set_equaliser(mid, "Audiotec Fischer")`; list — `get_equalisers()`). Then REW keeps the filters within Helix's limits from the start: **30 bands**, types PK / LS_Q / HS_Q.
2. Fit the filters to the target (Method 2: Target Settings + Generic/Extended EQ) — they're already in a Helix-compatible form.
3. **Export** the filter list → a file in the format below.
4. Move the file into Parallels (shared folder) → **import into the Helix PC-Tool** on the right channel.

> Alternative — `rew_tool/atf_eq.py` (validated on a REAL export: `rew_tool/testdata/atf_full_eq_sample.txt`, `python atf_eq.py --selftest`): **`format_atf_eq()`** generates this 30-band block from computed PEQs (bypassing the REW export, deviation→PEQ), and **`parse_atf_eq()`** reads it BACK into a structure — for the black-box case (recover an existing Helix EQ from a file when the live DSP can't be read — `diagnostic-techniques.md §22`). CLI: `python atf_eq.py <file>`.
> Another option (and the main path for DSPs **without** file import — Musway, ESX, Zapco, etc.): **REW-EQ-CopyPaste-Assistant** (github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) — Copy in REW's EQ section → auto-enters the bands via keystrokes into the DSP software's window. For Helix, file import is more convenient (the filter effect shows immediately in REW), but the option exists. Detail → `knowledge/dsp/helix-dsp-ultra-s.md` §EQ transfer.

## How much EQ to transfer — minimalism > autofill
The main rule (confirmed in the user's practice): **transfer only the CONSCIOUSLY chosen, genuinely needed bands — not an auto-generated full bank.** REW "Match target" and NTT autofill throw far more filters than the tune needs (over-EQ); it's faster but worse. We build the EQ **together, step by step, only what's necessary**, reviewing each band.

Because of that, **a convenient path for Helix is copy-paste from the terminal straight into the PC-Tool, even one band at a time** (per-band entry in Helix is quick). So `atf_eq.py`:
- **`format_atf_eq(bands)`** — generate a block with ONLY the chosen bands (the rest = `None`) → file import, **or**
- `python atf_eq.py <file>` / parse-print — show the bands (freq·gain·Q·type) for manual per-band entry / copy-paste.

NTT can also generate Helix files (PC-Tool instead of REW) — faster, but the same over-EQ trap; the advantage of conscious minimalism stands.

## File format (tab-separated)
The first line is the bank header, then the column header, then **exactly 30 rows** (empty bands = `Type None`).

```
Audiotec_Fischer_Full_EQ_(30_bands)
Number	Enabled	Control	Type	Frequency(Hz)	Gain(dB)	Q	Bandwidth(Hz)	TargetT60(ms)
1	True	Auto	PK	20.0	-11.2	1.00	20.00	
2	True	Manual	LS_Q	44.3	-11.0	0.7	
3	True	Manual	HS_Q	221.0	-11.1	0.7	
4	True	Auto	PK	2504.0	-12.2	1.27	1972	
11	True	Auto	None	
30	True	Auto	None	
```

Columns:
- **Number** 1–30 (fixed at 30 bands).
- **Enabled** True/False · **Control** Auto/Manual.
- **Type:** `PK` (parametric peak), `LS_Q` (low-shelf with Q), `HS_Q` (high-shelf with Q), `None` (empty band).
- **Frequency(Hz), Gain(dB), Q.**
- **Bandwidth(Hz)** — for PK (an alternative to Q; REW writes both). Empty for shelves.
- **TargetT60(ms)** — a REW housekeeping column, irrelevant for the Helix import (often empty).

## Notes
- ≤ **30 bands** per channel; types: PK / LS_Q / HS_Q + **AP1 (1st-order all-pass) / AP2 (2nd-order all-pass)**. You can use several AP filters; they change only the phase, leaving the FR untouched.
- **Crossovers (HP/LP) are NOT in this file.** They're set separately in Helix's crossover block (type LR/BE/BW + frequency + order) → we transfer them as parameters.
- **Delays / polarity / phase** — also separate Helix fields ("Phase, Polarity & Time"), not the EQ bank.
