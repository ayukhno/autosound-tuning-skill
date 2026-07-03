# Phase 5 — Variations (voicing presets + center & rear)

The **variations** phase: switchable presets layered on the satisfying, locked front (Phases 1–3, verified in Phase 4). Two kinds — **subjective voicing** (genre/context taste) and the optional **spatial** additions (**center**, **rear**). All optional; the front base is never touched.

## 🎯 Goal-node

**Purpose:** build **variations** on the satisfying front — switchable **voicing presets** (genre/context taste) and the optional **spatial** layers (**center**, **rear/envelopment**) — all on top of the locked base (Phases 1–3), never touching it. ♻️ **Cyclical:** return to the project **anytime** to add a new preset ("road", "jazz", "rock", enveloping) or tweak an existing one.

**Questions this phase answers:** which taste axes (warm↔bright, bass↔neutral, forward↔laid-back, analytical↔fun)? which target curve does the user prefer **by ear**? which symptom→fix moves close the remaining gaps?

**Required evidence:** the **Preference Profile** (taste axes, loudness, genres); curve auditions on familiar tracks; symptom→fix ear checks.

**✅ Quality gate (per variation):** taste mapped (Preference Profile); a curve chosen by ear; symptom→fix moves applied **only on the virtual layer**; each variation saved as a **separate preset** (technical base untouched). **Center/rear only after the front satisfies** (see the spatial section).

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
* **Each preset is its own versioned state history** — run `apply.propose` under that preset name for every voicing move (gain/virtual-EQ pointer/hard-param), so the taste variations are snapshotted, diff-able, and revertible without touching the locked base. The **A/B and "revert this idea"** you want in voicing is exactly `state.diff` / `revert` (one command), which is what makes trying a bold voicing cheap. Schema → [`rew_tool/state/schema.md`](file:///skills/autosound-tuning/rew_tool/state/schema.md).

---

## 5. Spatial variation — Center Channel (optional)

> ⛔ **Only once the FRONT satisfies** (locked + user OK) — center/rear on an unsatisfying front is wasted work. Their levels/polarities/APFs are **project state** (`dsp-state-current`) — **verify by measurement**, never assume from logs.

Integrating a center introduces a third source that can comb-filter with the L/R mids.
* **Method A — Manual L+R center:** bandwidth-limit to the core vocal range (HPF+LPF ≈ 1.0–1.2 kHz); keep it **quiet** (a subtle complement); set polarity/APF by **maximum summation at the LP**.
* **Method B — Algorithmic (e.g. Helix RealCenter):** dial the level so it anchors focus **without narrowing** width; set delay so it doesn't arrive before L/R; if the stage narrows, adjust the center's all-pass. Center tweeter (if any): HPF high (6–8 kHz), gain very low (−6…−10 dB).

## 6. Spatial variation — Rear-Fill (envelopment, optional)

Goal: a sense of **envelopment** without dragging the front stage back.
* **Differential L−R matrix** — cancels the mono vocal so it stays up front.
* **Bandwidth-limit** — HPF ≥ 300–315 Hz, LPF ≈ 4–5 kHz (avoid door/cabin resonances).
* **Haas delay** — the front→rear arrival difference **+ 8–10 ms** (precedence → localizes front, rear = ambience).
* **Level** — quiet enough to be inaudible from the front, but missed when muted.
* After: **re-check the full system by ear** (center/rear must not have dragged the front back) and log to `dsp-state-current`.

> Refs: center → [`diagnostic-techniques.md` §20](file:///skills/autosound-tuning/references/core/diagnostic-techniques.md) · rear → [`voicing-by-ear.md` §Rear](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md).

---

When the chosen variations are saved (base untouched) and the user is done, **close the session** — see Phase 4's finish (backup + experience via a GitHub Issue). ♻️ Return anytime to add or tweak a variation.
