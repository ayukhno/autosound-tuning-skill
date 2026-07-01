# Phase 6 — Client Voicing & Subjective Taste

This is the final sound shaping phase. It layers subjective preference on top of the technically correct, measured base established in Phases 1–3.

## 🎯 Goal-node

**Purpose:** layer **subjective taste** on top of the locked technical base (Phases 1–3) — as a separate, reversible voicing preset.

**Questions this phase answers:** which taste axes (warm↔bright, bass↔neutral, forward↔laid-back, analytical↔fun)? which target curve does the user prefer **by ear**? which symptom→fix moves close the remaining gaps?

**Required evidence:** the **Preference Profile** (taste axes, loudness, genres); curve auditions on familiar tracks; symptom→fix ear checks.

**✅ Quality gate → Phase 7:** taste mapped (Preference Profile); a curve chosen by ear; symptom→fix moves applied **only on the virtual layer**; saved as a **separate voicing preset** (technical base untouched).

**⚠️ Failure modes:** editing the output/base layer for taste (breaks joints/TA) · voicing before the technical base is locked · not keeping a separate preset (loses the reference A/B).

**🧩 Refs:** [`voicing-by-ear.md`](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md) · [`preference-profile.md`](file:///skills/autosound-tuning/references/core/preference-profile.md) · [`preset-strategy.md`](file:///skills/autosound-tuning/references/core/preset-strategy.md).

---

## Step-by-Step Runbook

For detailed subjective adjustment guidelines and installer secrets, refer to [voicing-by-ear.md](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md).

### 1. Map Subjective Taste
Audit the user's preferences across the following classic sound-staging axes:
* **Warm** (rich midbass, gentle treble) ↔ **Bright** (detailed, crisp highs).
* **Bass-Heavy** (powerful low-end) ↔ **Neutral** (even, flat low-frequency response).
* **Forward** (performers close to the glass) ↔ **Laid-Back** (performers deep behind the dash).
* **Analytical** (reveals every detail and recording flaw) ↔ **Musical/Fun** (forgiving, smooth, enjoyable).

Also note the typical listening volume and primary music genres.

### 2. Curve Auditions
* Set up 2 or 3 distinct target curves (e.g., ResoNix Accurate, Harman, Jazzi, or Audiofrog) as EQ profiles in the DSP.
* Guide the user to audition these profiles using highly familiar tracks (e.g., Diana Krall "Temptation", Dire Straits "Private Investigations", or Daft Punk "Giorgio by Moroder").
* Ask the user to identify which target curve aligns best with their expectations.

### 3. Subjective Symptom-to-Fix Mapping
Apply minor EQ adjustments to resolve specific listening symptoms. Common examples include:
* **"Boomy, muddy bass":** Notch gently in the $125\text{ Hz}$ to $200\text{ Hz}$ range.
* **"Harsh vocals / sibilance":** Notch gently around $3.2\text{ kHz}$ to $4.0\text{ kHz}$ or $6.0\text{ kHz}$.
* **"Stage height is too low":** Boost the upper-midrange/presence region on the virtual EQ layer, or review tweeter levels.
* **"Lack of transient bite/snap":** Check for summation issues around $2.0\text{ kHz}$ to $3.0\text{ kHz}$.

### 4. Maintain the Two-Layer Config (Base vs. Voicing)
* **The Base Layer (Output EQ):** Keeps the individual speaker linearizations, crossover slopes, and time delays intact. **Never edit output-layer parameters for subjective taste.**
* **The Voicing Layer (Virtual EQ):** Apply subjectivevoicing moves **exclusively on the Virtual Layer** (linked L=R EQ). Since virtual moves do not introduce phase discrepancies between left and right channels, they are safe and will not break the crossover joints or time alignment.
* **Save as a Separate Preset:** Save the final client-voiced profile as a separate DSP preset (e.g., Preset 2: "Enjoyment/Voiced"), leaving the technical baseline untouched on Preset 1 ("Reference/Technical") for easy comparison and A/B testing.

Once the voicing preset is finalized and saved, proceed to the wrap-up in **Phase 7**.
