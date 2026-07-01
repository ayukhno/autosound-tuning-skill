# Impedance / Thiele-Small — measuring drivers & enclosures (REW Impedance jig)

When: characterize a raw driver (for box design), QC installed drivers (L/R match, Fs vs crossover), verify a built enclosure (Fc/Qtc), or sanity-check a unit against datasheet. REW: **Measure → Impedance → Sweep**, reference-resistor method (`unit=ohm` on the measurement; pull with `get_fr`). The jig measures ELECTRICAL impedance — pair it with the ear/acoustic for anything velocity-dependent.

## What impedance gives — and the second measurement you still need
- **Free-air sweep → Fs + Re ONLY.** Box volume needs the FULL T/S (Qts, Vas). Get them with a SECOND measurement: **added-mass** (known mass on the cone → new Fs) OR **known-volume** (driver in a test box of known volume → Fc) + Sd. REW computes the rest. Alternative: datasheet T/S + a box modeler, with the free-air sweep as a QC cross-check (driver healthy, ≈ the spec sample).
- **Installed sweep →** (a) **L/R match** (a pair must agree — phantom centre); (b) **installed Fs vs the planned HP** (cross above it; the installed Fs is the real number, better than datasheet free-air).

## Trust map — what survives a bad jig, what doesn't  ⚠️ CORE
A jig's ABSOLUTE magnitude is often unreliable. **Scale-invariant (trust even on a mis-scaled jig): Fs, Fc, Q as a RATIO (r0=Rmax/Re), Mms (from the frequency shift).** **NOT trustworthy (DMM only): absolute Ω, Re, absolute Qms/Qes.**
- **`|Z|min < DCR` = instant proof the cal is wrong.** Impedance magnitude can never dip below the DC resistance (from DMM/datasheet). Curve minimum below Re → the magnitude axis is mis-scaled — fix the cal, don't trust the ohms.
- **A jig is often NOT repeatable in absolute magnitude between sweeps** — the SAME driver swept twice can read a different Re/peak. So an **L/R "asymmetry" in absolute Ω ≠ different drivers**: first check **Fs+Q (scale-invariant)** — if they agree, the pair matches and the magnitude gap is the rig. Confirm Re match with a DMM, not the jig.
- **Validate the rig with a KNOWN 1% resistor**, not an ASSUMED driver DCR (you fool yourself if the real DCR isn't what you expect). Cal can err BOTH ways; a re-cal can overshoot. Confirm R_SENSE vs R_REF agree.
- **Low-Z coils (1–2 Ω) need a SMALL reference resistor** (~10 Ω). A ~100 Ω reference puts only ~1 % of signal across a 1–2 Ω load → reads low/noisy.

## Setup hygiene (free-air + added-mass)
- **Rigidly fix the DUT** (clamp to a massive stand / suspend). A driver just sitting on its magnet → basket/bench vibration feeds back into the cone → jagged noise on the peak skirt, a suppressed Qms / collapsed peak.
- **The added mass must move as ONE with the cone** (Blu-tack / modeling clay / a bag of salt — conformal, around the dustcap). A loose mass resonates → a **spurious impedance peak that wasn't on the baseline** (diagnostic: a peak that appears ONLY with the mass = the mass rattling) and it **underestimates Mms** (partial decoupling → a smaller Fs shift).
- **Order: rigidity FIRST, then mass.** Target a **20–30 % Fs drop** (lower math error). A 15–17 % shift gives ~5–8 % Mms — fine as a coarse check only.

## DVC drivers
- Published T/S is for ONE specific wiring; **the spec Re tells you which** (series / parallel / single coil).
- A **single-coil sweep (other coil OPEN) reads Qes ~2× the both-coils value** (series AND parallel both halve it) → its Qts comes out higher → **sweep the wiring you'll actually run.** Fs, Mms, Vas are wiring-independent.

## Installed impedance → enclosure QC (a use the rest of the skill doesn't cover)
Datasheet free-air vs the installed sweep gives: (1) **loading / box size** from Fc/Fs (a big rise = a small tight volume); (2) **L/R enclosure match** (Fc + passband of the pair); (3) **wall resonances** = ripples / secondary peaks IN the crossover PASSBAND; (4) **the enclosure's Qtc peak vs the crossover** (the resonance should sit under the HP — a steeper / higher cross removes it). Pattern depends on box TYPE:
- **Sealed pod (mid):** one clean peak + Qtc; scan the passband for wall modes.
- **Tweeter:** the rear chamber is usually built into the driver — nothing external to tune, just Fs vs the cross.
- **Door midbass:** look for **correlated L↔R in-band micro-dips** = panel / structural modes (low-frequency, λ≫box → panel, not cavity). **Correlation L↔R rejects noise** (a feature in both at the same Hz = real).
- ⚠️ If the deadening is already done, small residuals are the practical floor — leave them. **EQ does not fix a resonance** (a notch leaves the ringing; address it mechanically or accept it).

## Verifying a built sealed box (impedance = one peak at Fc)
- Read **Fc** (peak) and **Qtc** (same r0/bandwidth method as Qts). **A clean sealed box obeys `Fc/Fs = Qtc/Qts`** — when the two ratios match, the box is airtight (no leak); a leak lowers/broadens the peak.
- **Effective Vb = Vas / ((Fc/Fs)² − 1).** Use the driver's CURRENT (measured) Vas, not the datasheet, if it isn't broken in — a stiff suspension reads a lower Vas, so the datasheet number makes the box look "too big".

## What impedance CANNOT see
- **A low-level sweep doesn't engage velocity-dependent damping** (aperiodic vents / volume fill / wall felt). The peak reads near-"sealed" even in a well-damped box → judge that treatment **acoustically (nearfield + CSD) at a working level**, not by impedance.
- **Break-in is excursion-driven, not hours.** A gently used (low-level SQ) driver stays partly un-broken-in for months → a measured Fs above datasheet (within the ±10–15 % tolerance) is usually that, not a fault. **Design the box on the datasheet (the long-term state)**, then fine-tune acoustically. You don't need an impedance re-measure to track break-in (which often means pulling the sub — avoid); the acoustic measurement already reflects the current state.

## Crossovers from impedance + slope↔goal
- Each HP **above** the driver's installed Fs; the **margin scales with the slope** — a steep LR4 needs little headroom, a gentle 12 dB leaves more output near Fs (cross higher).
- ⚠️ **Coincident resonances of neighbours** (e.g. a sealed sub's Fc ≈ a door midbass's installed Fs) → do NOT cross there, only above.
- **Slope TYPE maps to the GOAL** (a by-ear variant, confirmed working in the field): **LR4 on every joint + time-align by IR first-arrival = a precise STAGE** (strict imaging rulesets); **gentle / Bessel = wider overlaps, a natural blend = "beautiful"** (where the stage is less demanding). Detail / starting sets → `filter-types-car-audio.md`.
