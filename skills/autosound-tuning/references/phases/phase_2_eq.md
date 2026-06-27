# Phase 2 — Linearization & Acoustic Alignment

This is the core technical execution phase. All operations **MUST** be performed in this exact chronological order: Hygiene EQ (2a) → Joint Phase Alignment (2b) → Summed Alignment (2c) → Final Technical EQ (2d).

---

## 2a — Hygiene EQ of Each Channel
Linearize each individual channel to its own band-specific Nono Tuning Tool target.

### Rules of Action
1. **Min-Phase Peaks Only:** Cut narrow and wide minimum-phase peaks.
2. **Never Fill Nulls:** Do **NOT** EQ-boost acoustic nulls/dips. If a dip is deep and narrow, it is a phase cancellation or diffraction effect (non-minimum-phase). Equalizer boosting into nulls wastes amplifier headroom and introduces physical distortion.
   * *Example:* The VW Passat B8 left midbass has a null at ~150 Hz due to door diffraction. It is non-minimum-phase; EQ is strictly forbidden. Check the excess-phase curve in REW to separate minimum-phase from non-minimum-phase.
3. **L=R is a Trend, Not a Clone:** Cabin acoustics force natural asymmetry. Align the general shape/trend, but do not force identical per-channel curves where physics forbids it.
4. **Generate PEQ Files:** For more than 3 bands, build the EQ in REW and export the filter set. For Helix DSP, use the Audiotec-Fischer export format via `rew_tool/atf_eq.py` to allow clean, one-shot file import. Do **not** input 30-band auto-banks. Conscious, minimal EQ beats excessive bands.

---

## 2b — Joint Phase Alignment (Fine Delay)
Align the relative phase response of the channels in their overlap regions.

### Refined Phase Flow
1. **Raw Sweep:** Capture the phase of the raw signals (after gross TA, before crossover filters) as a reference.
2. **Crossover Filters applied:** Compare with crossovers enabled to analyze phase rotation introduced purely by the filters.
3. **Fine Alignment:** Align joints in the following physical sequence:
   $$\text{Midbass (Reference)} \longrightarrow \text{Subwoofer} \longrightarrow \text{Midrange} \longrightarrow \text{Tweeter}$$
   Then, align Left ↔ Right for mono summation.
4. **Tools & Methods:**
   * Align joints using **All-pass filters (APF)** or Helix Phase controls rather than shifting raw channel delays, which can break the gross time arrival.
   * The sub-to-midbass joint (~60 Hz) yields the largest subjective SQ gain. Verify carefully.
   * The final verdict at any joint is determined by **SUMMATION** (uninverted vs. inverted polarity), not single-position phase values.

---

## 2c — Summed Curve Alignment
Align the summed acoustic groups to match the target.

### Verification Steps
Measure and analyze the MMM RTA of the following combinations:
* **Ws, Ms, TWs** (L+R sums of each band pair).
* **L vs. R** (full left side vs. full right side, excluding the subwoofer).
* **SW + Ws** (subwoofer plus both midbasses).

### Correction Rules
* **Band-to-band alignment:** Adjust levels so they sum smoothly. An overlap hump is a summation issue, not a hot driver.
* **L vs. R Balance:** Match the **SHAPE** in the critical imaging region ($200\text{ Hz}$ to $1.5\text{ kHz}$). "Take from the louder side and add to the quieter side" to balance levels without altering the average target alignment.
* **Summation Checks:** Use REW's trace arithmetic ($A+B$) to predict summation outcomes prior to applying changes.

---

## 2d — Final EQ to Target
Shape the technical response of the entire summed system to the session's target curve.

### Rules of Action
* Apply **broad, smooth acoustic moves** (tilts, shelves, high/low Q shaping).
* Work primarily on the **Virtual Layer** (L=R linked, identical on both sides).
* Since the Virtual Layer sits above crossovers in the DSP routing chain, its phase shifts are identical for both sides, **never breaking the acoustic joints** set in Step 2b.
* Save client-preference voicing requests for Phase 6. This layer is purely technical target accuracy.

Once the final curve is aligned and verified, transition to the **Phase 3** control gate.
