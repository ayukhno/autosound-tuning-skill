# REW API — Pulling Data & Python Tooling

This document outlines how to interact with Room EQ Wizard (REW) via its API and describes the structure of the built-in Python tools available in this skill.

## API Connectivity

REW exposes its API at `localhost:4735`, reachable **from the host where Claude/Gemini run** — pull data live, no port-forwarding.

> [!NOTE]
> **Setup-dependent workflow:** If the DSP's software runs on a different OS/VM than REW (e.g., REW on macOS + the Helix PC-Tool in a Parallels Windows VM), there's **one courier step** — handing the REW EQ export to the DSP via a shared folder; a native same-OS DSP tool skips even that.

---

## Tool Directory Layout

The Python tool ships **inside this skill** at `<skill-dir>/rew_tool/` (uses standard library only — no external dependencies, no project data). The modules import flat, so run it from its own directory:
```bash
cd <skill-dir>/rew_tool && python3 rew_tool.py ...
```
Or add `<skill-dir>/rew_tool` to your `PYTHONPATH`.

### Module Overview

* **`rew_tool/rew_api.py`**
  * `get_measurements`, `get_fr`, `get_group_delay`, `get_impulse_response`, `get_distortion`
  * `get_filters`/`set_filters`, `get_equaliser`/`set_equaliser`
  * `get_crossover_types`, `get_slopes`
  * `get_target_settings`/`response`
  * `find_measurement_id(name)` / `get_measurement_by_name(name)` — **resolve title ↔ id FRESH before every pull** (never use a cached index)
* **`rew_tool/analysis.py`**
  * FR/phase/IR/GD analysis + PEQ suggestions
  * `first_arrival` (leading-edge, not the global peak) + `relative_delay_xcorr` (L ↔ R delay, shape-robust)
  * Verify setup: `python3 analysis.py --selftest`
* **`rew_tool/joint_analysis.py`** — within-session summation / TA / phase decisions (magnitude-safe where in-cabin phase is not trustworthy)
  * **Quality / drift:** `flag_remeasure_candidates` (pre-echo vs the CLEANEST version of the SAME driver → which sweeps to redo), `timing_drift_audit` (Δstart vs waveform xcorr → REW label-drift vs a real TA change), `impulse_polarity` (leading-edge sign)
  * **Classify:** `joint_summation_check` (measured pair vs incoherent power ref → phase cancellation vs tonal dip; never boost a null), `phase_trust_gate` (do the complex solos reproduce the pair? if not, BLOCK delay/APF/polarity)
  * **Correct (drift-immune, relative):** `align_by_summation` (polarity + relative delay maximizing the coherent sum = the TA you can enter in the DSP), `allpass_for_residual_null` (2nd-order APF F/Q on the residual), `shelf_vs_bell` (broad tilt = shelf, gentler phase; else keep the bell)
  * `perceptual_smooth`, `midband_level_anchor`, `shape_deviation`. Verify: `python3 joint_analysis.py --selftest`
* **`rew_tool/spot_check.py`** — independent verification of a model's CITED numbers against live REW (process-control §2.3; run it before applying a proposed package)
  * pair mode: levels at cited freqs + A−B deltas + actual band peak vs the **claimed** peak (flags a claim >1/12 oct off)
  * target mode: shape-anchored deviation vs a loaded target at cited freqs
  * `python3 spot_check.py "L_09 (rta)" "R_09 (rta)" --at 160,2540 --peak 2000-3000 --claim 2543.8` · `--selftest`
* **`rew_tool/target_curves.py`**
  * Handles loading and interpolating target curves.
* **`rew_tool/nono_curves.py`**
  * Parses Nono Tuning Tool curve exports:
    * `full` = `freq` & `mag`
    * `per-band` = `freq`, `mag`, & `phase`
* **`rew_tool/level_offsets.py`**
  * Preliminary per-channel LEVEL offsets from geometry (off-axis piston directivity + distance). Cut-only starting balance for Phase 1 §3.5, verified by RTA/ear. Inputs (distance/angle/piston radius/`n`) are project data. `--selftest`.
* **`rew_tool/target_bands.py`**
  * Generates per-driver (per-band) target curves locally: house curve + crossovers + two-speaker summation offset + asymmetric L/R compensation + per-channel gains. Change a crossover → regenerate in one shot (no NTT-web round-trip). Phase 1 §5. `--selftest`, `--demo`.
* **`rew_tool/equal_loudness.py`**
  * Equal-loudness (ISO 226:2003) **sub-bass targeting**: a flat sub sounds bass-light because ear sensitivity at LF depends on listening level (Fletcher-Munson). Anchor to one measured sub freq+SPL → calibrate the phon contour → read per-freq target SPLs → `target − measured` = the EQ adjustment (cut-only + master up). Field-validated (helped win an AYA round). `--anchor F SPL --measure f=spl…`, `--selftest`.
* **`rew_tool/atf_eq.py`**
  * Parses and generates the Audiotec-Fischer (Helix) 30-band EQ bank (validated on real exports; parses an existing bank, formats and emits only the bands you decided).
* **`rew_tool/verify_measurements.py`**
  * Verification script for REW sweep data. Analyzes impulse response peaks, calculates initial time alignment delays, and detects exact acoustic crossover intersection frequencies.
* **`rew_tool/make_plot.py`**
  * Visual RTA plotting utility that generates comparative charts (L/R measurements vs. house/target curves) for visual-acoustic analysis.
* **`rew_tool/rew_tool.py`**
  * Main CLI entry point.

---

## Working Guidelines

1. **Numerical Data over Screenshots:** Prefer pulling data numerically over reading screenshots.
2. **Analysis Protocol:**
   * To decide what REW measurement (FR, GD, IR, etc.) to pull for a given task, refer to [analysis-playbook.md](file:///skills/autosound-tuning/references/core/analysis-playbook.md).
   * For advice on interpreting data (anchor-to-mids, peak-vs-null, power-sum summation, joint-phase checks, etc.), refer to [diagnostic-techniques.md](file:///skills/autosound-tuning/references/core/diagnostic-techniques.md).
3. **API Quirks & Gotchas:**
   * Watch out for big-endian float32 encoding, the requirement to `set_filters` one-by-one with `gaindB`, addressing measurements strictly by NAME instead of index, IR timing usability details, and out-of-band target curve garbage.
   * Check [rew-api-quirks.md](file:///skills/autosound-tuning/references/tooling/rew-api-quirks.md) for full documentation. (The `rew_tool/` codebase already handles these quirks).
4. **Fallback:** If the API cannot be reached from the host, fall back to the user's exported `.mdat` / CSV (e.g., `rew_analitic/measurements-*.mdat`) or screenshots.
