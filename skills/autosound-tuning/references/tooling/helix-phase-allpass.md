# Helix DSP — phase control (all-pass) and phase alignment

## What this control is
Each output channel of the Helix Ultra S has its own **Phase** control (0–360°, fine step — e.g. `174.375°`) in the **"Phase, Polarity & Time"** block, next to Polarity (NORM/INV) and Delay. It is **NOT polarity** and is **separate** from the EQ.

- Technically it's a **2nd-order all-pass filter** tied to the channel's **crossover frequency**. Helix computes the coefficients **automatically** from the crossover value — for the **sub, from the LPF**. So the APF parameters **don't show up** in the EQ.
- Side effect: the APF **adds delay to everything above** the turn frequency. So it isn't a "free" phase rotation — it drags the timing of the upper part of the range.
- ⚠️ **An all-pass does NOT fill a magnitude null.** It's flat in FR — it rotates only the PHASE. A single-source magnitude dip (a solo channel falling into a notch at the listening position = a positional / path null) **cannot be lifted** by phase rotation. An all-pass is useful only to **detune the SUMMATION of two overlapping sources** at a joint (shift where/how much they add), not to fix the shape of one. "An all-pass to fill a null" is physically empty (peak-vs-null applies here too). A single-source null is moved only by physics (re-aiming the driver / treating the reflection).

## Phase-alignment methodology
- **Midbass is the reference.** The Phase control works for the **sub, mid, tweeter** and is **not applied to the midbass** — we don't rotate its phase.
  - ⚠️ **This "reference" is the PHASE-tuning anchor (the channel you DON'T all-pass) — it is NOT the arrival-TA reference.** The arrival-TA reference is the **measured latest-arriving driver** (`process-phases.md` Phase 1), which is often NOT the midbass (it frequently arrives early). Two different "midbass = reference" roles — don't conflate them (a real bug: the midbass was pinned as the TA zero and everyone else delayed, when the midbass was actually the EARLY arriver that needed delaying).
- Rule: **of the 4 drivers you adjust only 3.**
- **Order:** from the midbass (the reference) → first the **sub** (the sub↔midbass joint is the most important) → then the **mid** → then the **tweeter**.
- **How to set it:** with **RTA** on, watching the **overlap region at the joint**, rotate the channel's phase to **maximum summation** (the dip disappears) at the crossover frequency. The sub↔midbass joint is the most critical.
- Phase problems most often sit in the **crossover region** and in the **midbass range**.

## Practice for our system (Passat B8)
In the first successful configuration (AYA) the phase control is set: sub `174.375°`, left mid `33°`, the rest `0°`; the midbasses — no rotation (the reference). See `autosound_context.md` §4A.

## Explicit AP1/AP2 bands in the EQ bank (vs the auto Phase knob) — hardware-verified
Besides the auto Phase control above, the PEQ bank accepts explicit **AP1/AP2 bands at an arbitrary f0/Q** (several allowed; `helix-eq-export.md`). Facts established 2026-07 on the Ultra S:
- **The AP2 implementation matches the textbook 2nd-order all-pass** (phase `−2·atan2((f/f0)/Q, 1−(f/f0)²)`). Verified by the **same-session single-variable A/B protocol**: sweep → change ONLY the APF in the DSP (mic untouched) → sweep; the complex ratio isolates the hardware filter. The free fit recovered the entered parameters (f0 4386 / Q 3.82 / correct sign vs 4414 / Q 4.0 entered; 31° RMS residual). An allpass-only change must also ratio to **0 dB magnitude** — the protocol's built-in sanity check.
- ⚠️ **Verify with a HIGH-Q setting.** A low-Q APF over a band-limited ratio is nearly degenerate with delay+offset — the fit cannot separate them (a Q1 "mismatch" was this degeneracy, not hardware).
- **Rotation reach scales as ~f0/Q:** a Q4 APF at 4.4 kHz barely rotates at 3.2 kHz. Check the APF's phase AT THE JOINT frequency, not at f0 (`diagnostic-techniques.md §25`).
- Joint-repair APF choices must be **jitter-robust**, not razor-optimal (`diagnostic-techniques.md §24`).

## Sources
- DIYMobileAudio: "Using the phase adjustment in Helix DSP"; "Helix DSP phase VS delay adjustment"; "Let's Phac our Helix DSP — how to set Phase degree/AllPass".
- PASMAG: Helix P-DSP review (Signal Delay & Phase Control).
- The order (midbass→sub→mid→tweeter) and "doesn't work on the midbass" — from the user; consistent with forum practice.

> ⚠️ Compiled from forums + the user's practice, **not the official Helix manual**. If an official Helix guide turns up — confirm the APF parameters (frequency/Q) and the order.
