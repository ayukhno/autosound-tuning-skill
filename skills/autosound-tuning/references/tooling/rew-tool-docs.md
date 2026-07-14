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
  * **Measurement-processing (free, not Pro-gated — `POST /measurements/{id}/command`):** `excess_phase_version(mid)` / `minimum_phase_version(mid)` create the `-EP`/`-MP` versions (read excess phase back via `get_fr` — the authoritative min-vs-non-min decision, REW's own Hilbert); `set_smoothing(mid, '1/6')` applies REW's own smoothing before a pull; `measurement_command(mid, cmd, params)` is the low-level entry.
* **`rew_tool/analysis.py`**
  * FR/phase/IR/GD analysis + PEQ suggestions
  * `first_arrival` (leading-edge, not the global peak) + `relative_delay_xcorr` (L ↔ R delay, shape-robust)
  * Verify setup: `python3 analysis.py --selftest`
* **`rew_tool/joint_analysis.py`** — within-session summation / TA / phase decisions (magnitude-safe where in-cabin phase is not trustworthy)
  * **Quality / drift:** `flag_remeasure_candidates` (pre-echo vs the CLEANEST version of the SAME driver → which sweeps to redo), `timing_drift_audit` (Δstart vs waveform xcorr → REW label-drift vs a real TA change), `impulse_polarity` (leading-edge sign)
  * **Classify:** `joint_summation_check` (measured pair vs incoherent power ref → phase cancellation vs tonal dip; never boost a null), `phase_trust_gate` (do the complex solos reproduce the pair? if not, BLOCK delay/APF/polarity)
  * **Correct (drift-immune, relative):** `align_by_summation` (polarity + relative delay maximizing the coherent sum = the TA you can enter in the DSP), `allpass_for_residual_null` (2nd-order APF F/Q on the residual), `shelf_vs_bell` (broad tilt = shelf, gentler phase; else keep the bell)
  * `perceptual_smooth`, `midband_level_anchor`, `shape_deviation`. Verify: `python3 joint_analysis.py --selftest`
* **`rew_tool/xover_select.py`** — crossover-realization + joint-alignment API distilled from the v3 acoustic-target experiment (the rules live in `filter-types-car-audio.md` §Acoustic-plan-first)
  * `realize_driver` (acoustic target → electrical XO + trim + EQ, boost-budgeted), `select_neighbor_pair` (adjacent bands as a PAIR by acoustic-sum quality — per-driver-optimal picks can leave a >10 dB pair hole), `align_joint` (analytic delay/polarity), `repair_joint_apf` (APF2 tried on BOTH branches; may return None when delay already absorbs a low-Q rotation; **`robust=True` default** — scores by the jitter-robust worst null per `diagnostic §24`, `robust=False` only to reproduce legacy razor runs), `repair_joint_apf_multi` (several same-day snapshots of the joint → selection by **MIN of the robust score across snapshots**; field lesson: even robust single-snapshot optima didn't transfer across an hour; returns `per_snapshot_db`), `lr_phase_tracking` (the L/R acoustic-symmetry metric)
  * `dsp_math.robust_worst_null` + `ROBUST_PERT` (±20 µs / ±0.5 dB) — THE objective for any joint-phase decision; `apf_search(robust=…)` underneath
  * deps: numpy + **scipy** (via `dsp_math.py`); fixed fs=96 kHz. Verify: `python3 xover_select.py --selftest`
* **`rew_tool/dsp_math.py`** — REW-exact filter math shared by `xover_select` (BU/BE/L-R crossovers — scipy Bessel with `norm="mag"`; PK/LS_Q/HS_Q ≡ RBJ; `apf2_response` hardware-verified on the Helix Ultra S, `helix-phase-allpass.md`)
* **`rew_tool/curve_view.py`** — the "three distances" discipline for reading any dB curve (a response, an L−R difference, a new-vs-old delta): `report(freqs, mag_db, band, source='sweep'|'mmm')` = band window → MACRO trend (1/3 oct ≈ critical band, band-anchored medians → voicing territory) → FINE residual (1/24 − macro) with detected features (FWHM width, extremum). **Every feature is ROUTED to the doctrine that owns it**: >2/3 oct → voicing (§6); <1/6 oct on a sweep → verify-first via MMM/mic-shift (§13); medium peak → point-EQ cut (§21/§2); medium dip → null-suspect, no boost until eq_gate/excess-phase clears it (§2/§13). `source='mmm'` skips the verify-first arm (already spatially averaged). Answers "what am I allowed to do about this?", not just "what is there". Verify: `python3 curve_view.py --selftest`
* **`rew_tool/eq_gate.py`** — measurement-driven EQ-**boost**-ability gate (the peak-vs-null doctrine, `diagnostic §2`, made quantitative). `ExcessPhaseGate(freqs, mag_db, excess_phase_deg, trust)` from a driver's sweep + REW's native excess-phase version (`rew_api.excess_phase_version`); `.check(f0, q)` → ALLOW / WARN (→ mic-shift cross-check, §13) / BLOCK; `.as_boost_gate()` plugs into `greedy_eq_fit(boost_gate=…)` / `realize_driver(boost_gate=…)`. Blocks only where a **deep local dip ∧ phase anomaly ∧ the filter delivers gain** coincide — phase alone over-blocks (cabin mids are phase-rough over 30-50 % of the band), depth alone can't tell cancellation from a fillable deficit. ⚠️ Calibration (Z 4.5/6.0, dip 4 dB) is **provisional — validated 7/7 on ONE build's boost history**; taste zones (de-esser) stay manual. Verify: `python3 eq_gate.py --selftest`
* **`rew_tool/spot_check.py`** — independent verification of a model's CITED numbers against live REW (driver-discipline §1.3; run it before applying a proposed package)
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
  * Main CLI entry point. Two modes:
    * **Interactive** (no args) — deep dive on **one** measurement at a time (FR + GD + IR + distortion + target).
    * **`analyze-batch "<pattern>"`** — **mass analysis** of every measurement whose title contains `<pattern>` (e.g. `analyze-batch "_2 (rta)"`) in **one** consolidated deviation matrix: per-driver band-mean deviation vs its per-band target, plus an `anchor` column (300–3000 Hz offset — subtract from the bands to read pure shape) and `ripple` (post-anchor spread). One `get_measurements` + one **FR-only** `get_fr` per driver (not the 5-endpoint interactive fan-out), so a whole batch is ~5× fewer round-trips and one review-ready table instead of N dumps. Use it for the **mass read** in Phase 1 §5 (all `_2` drivers vs targets) and **Phase 2a hygiene** (diagnose every channel in one pass) — then drill into a specific driver interactively if a cell looks off. `--no-targets` = band levels only.
    * **`analyze-joints --joint "lo,hi,fc[,pair]" …`** — **mass joint analysis** (Phase 2b): walks every adjacent joint in one pass and renders one table (polarity · drift-immune delay from `align_by_summation` · residual null · APF f0/Q), reusing `joint_analysis.py` unchanged. **Honest by construction** — a computed delay/polarity/APF is emitted **only** when a measured `pair` reproduces the complex solos (`phase_trust_gate` passes ✓); if the pair is missing → row flagged **UNVERIFIED** (confirm by summation before entering); if the gate trips → **BLOCK**, no delay emitted, fall back to the magnitude power-sum verdict + "flip polarity, re-measure". `--ver N` picks the solo version (`<ch>_N (sw)`, default 2), `--band-oct` sets the ±octave joint window. **`--from-state`** auto-derives the whole joint map (adjacent driver pairs + crossover freqs) from the **active slot's** crossovers in `state/` (no hand-typed `lo,hi,fc`) — works against the active registry slot by default (multi-slot guardrail), `--preset`/`--state-ver` to override; a manual `--joint` then supplements/refines (e.g. attaches a measured `pair` to one joint). Examples: `analyze-joints --from-state` · `analyze-joints --from-state --joint "sw,w-L,60,SW+Ws_2 (rta)"` · manual: `analyze-joints --joint "w-L,m-L,400" --joint "m-L,tw-L,3000"`.
    * `python3 rew_tool.py selftest` = offline check of both batch + joints paths (no live REW).

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
