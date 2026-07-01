# Phase 1 — Crossovers, Levels & Preliminary Delay

This phase establishes the physical foundation of the tune: crossovers, preliminary level balance, raw driver timing, and band-specific targets.

## 🎯 Goal-node

**Purpose:** establish the physical foundation — crossovers, raw driver timing (arrival TA), preliminary level balance, per-band targets — so Phase 2 EQ works on a correctly-aligned system.

**Questions this phase answers:**
- Who arrives latest (the TA reference), and what is each driver's true acoustic arrival?
- What crossover frequencies/slopes/types suit these drivers + this cabin geometry?
- What per-band targets sum to the house curve without a joint hump?

**Required evidence:** per-channel MMM RTA (FR) + sweep-with-loopback (IR/phase/GD) for every isolated driver; the active DSP delay state during measurement.

**✅ Quality gate → Phase 2:** arrival TA set from **manually-inspected IR onsets** (not REW auto-estimates); L/R-symmetric crossovers agreed via the review loop and applied to the DSP; per-band NTT targets generated, verified (`_SUM` +3…6 dB vs single) and loaded; `<prefix>_v1_foundation.pct6` saved to `rew_analitic/dsp-config/`.

**⚠️ Failure modes:** trusting REW auto-delay (locks onto reflections / prior DSP offsets) → inspect IR onset by hand · assuming the midbass is latest → measure it · detuning crossovers L/R to fix a cabin asymmetry (kills the phantom center) → fix with EQ instead.

**🧩 Common patterns (hypotheses):** filter type by driver spacing (BE4 close/coplanar · LR4 far-apart) → [`filter-types-car-audio.md`](file:///skills/autosound-tuning/references/core/filter-types-car-audio.md); heavy midbass → align to IR peak → [`car-eq-patterns.md`](file:///skills/autosound-tuning/references/patterns/car-eq-patterns.md).

---

## Step-by-Step Runbook

### 1. Use the Phase-0 per-driver baseline
Phase 0 already captured each isolated driver raw (`<ch>_1 (sw)` + `<ch>_1 (rta)`, protective HPFs, clean `v0`) — the sweep carries IR/phase/distortion/GD, the MMM carries FR magnitude. **Analyze that baseline here; do not re-collect it.** (Only re-measure a driver if its baseline is missing or the install changed.)

> [!IMPORTANT]
> **Set a consistent Time Offset on the sweeps BEFORE reading phase:**
> Set a shared Time Offset ≈ the physical arrival of the reference speaker, applied to all sweeps. This keeps the phase flat and readable (especially at HF) instead of wrapping into a dense linear ramp. Read `rew-api-quirks.md` "Timing" for details.

### 2. Gross / Arrival Time-Alignment (TA)
Equalize the physical flight times of sound from each driver to the microphone.
* **⚠️ CRITICAL RULE: NEVER BLINDLY TRUST REW'S AUTOMATED DELAY ESTIMATES (Lesson 2026-06-27):**
  * **The situation is always such that we MUST inspect the impulse response graphs manually in the REW GUI, rather than trusting REW's automated numbers, because REW's internal estimation logic is fixed (фіксована логіка).**
  * REW's automatic delay-estimation logic easily locks onto strong late reflections (windshield, floor, or console) instead of the true direct sound, or can be skewed by pre-existing active DSP delays.
  * **How to manually inspect/verify:** Open the Impulse Response (IR) graph in the REW GUI. Locate the true geometric beginning of the impulse (**onset** — the very first deviation of the leading edge from the zero-amplitude line).
  * **Accounting for DSP offsets:** Always check if any time delays or phase adjustments were active in the DSP during measurement. If the DSP had active delays (e.g., from a prior tune), the acoustic arrival will be measured on top of those existing delays. We must manually subtract/account for those pre-existing delays to find the true physical acoustic paths.
* Use the **IR FIRST FRONT** (leading edge, NOT the global peak) of each solo channel.
* **Reference Selection:** The latest-arriving driver gets `0.00 ms` added delay, and every earlier driver is delayed to match it. Find "who is latest" from the measurements — do **not** assume it is the midbass.
* *Note:* Absolute IR time is crossover-independent and should be set early. Joint phase alignment is a separate, second step done in Phase 2.

### 3. Crossover & Slope Selection
* **L/R Symmetry is the default:** Crossover type, slope, and frequency must be identical on both sides. Cabin acoustic asymmetries are corrected using output EQ, not by detuning crossovers, which destroys the phantom center.
* **Asymmetry as a variant:** Asymmetric crossovers are used only as a Hashimoto by-ear variant when symmetric setups fail to image (`method-hashimoto.md`).
* **Selection Guidelines:** Propose filter types based on physical driver characteristics and cabin geometry:
  * **Bessel (BE4):** Exceptional for close, coplanar drivers (e.g., midrange ↔ tweeter on A-pillars).
  * **Linkwitz-Riley (LR4):** Preferred where drivers are physically far apart (e.g., midbass in door ↔ midrange on A-pillar), as it minimizes overlap.
  * For crossover tradeoffs, refer to [filter-types-car-audio.md](file:///skills/autosound-tuning/references/core/filter-types-car-audio.md).

### 3.5 Preliminary Level Balance (computed from geometry — a starting hypothesis)
Set an initial **cut-only** per-channel level from physics, then verify by RTA/ear (a start, not a verdict). The nearer / more on-axis driver is louder at the reference seat → cut it.
* **Method** ([`rew_tool/level_offsets.py`](file:///skills/autosound-tuning/rew_tool/level_offsets.py)): per driver, off-axis loss = band-averaged far-field piston directivity `D(f,θ)=2·J1(ka·sinθ)/(ka·sinθ)`, plus distance loss `10·n·log10(d)`; offsets normalized cut-only (loudest driver cut most). This is why the mid can differ from the tweeter/woofer — the directivity integral depends on the driver's radius, band, and angle.
* **Inputs are PROJECT data — ASK the user** (store in `autosound_context.md`, Engineering Profile): per-driver **distance** to the reference ear, **off-axis aiming angle** (pods/pillars: on-axis / cross-fired / to centre), **effective piston radius** (≈ cone/dome size; the **enclosure** sets the LF band edge), cabin **distance exponent `n`** (2 = free field; lower if reverberant).
* The computed gains are the **start**; the summed RTA (§5 / Phase 2c) and the ear confirm/trim them. Never treat the number as final.

### 4. Review and Discussion
Format a Generator proposal package (per the data contract §3) and send it to the Critic. Refine the levels, timing, and crossovers. Upon agreement, the user applies these values to the DSP.

* **How to apply & save to the DSP (Arbiter):**
  1. Open Helix PC-Tool and load your **existing active baseline setup** (the current active profile you are starting from). Do *not* assume a `.pct6` file of version `v0` exists on disk if this is a fresh start.
  2. Enter the new parameters (protective/preliminary crossovers, delays, and level adjustments) exactly as agreed in the final proposal.
  3. Save the modified profile as `<prefix>_v1_foundation.pct6` locally on your computer in the workspace directory **`rew_analitic/dsp-config/`** (so it can be committed to Git and tracked properly).
  4. Write/flash this configuration into an active, safe slot of your physical Helix DSP to make it active before running any sweeps.

### 5. Generate Band-Specific Targets (Step 5b)
Once crossovers + levels are set, generate the per-driver targets **locally** with
[`rew_tool/target_bands.py`](file:///skills/autosound-tuning/rew_tool/target_bands.py) — feed it the
project's house curve + the per-channel config (crossovers/types + the gains from `level_offsets.py`).
It bakes in the crossover roll-off, the two-speaker **summation offset** (~6 dB LF → ~3 dB HF), and the
**asymmetric compensation** (so an asymmetric L/R sum still reconstructs the house curve).
* **The payoff:** change a crossover or a level → **regenerate in one shot**, no manual web round-trip.
* **Sanity check:** `_SUM` (L+R pair) targets sit ~+3…6 dB above a single side; the mono sub has no summation offset.
* Save into `rew_analitic/target-curves/<name>/`, load into REW, and use them for Phase 2a hygiene EQ.
* *(Alternative — manual:* [nonotuningtool.com](https://nonotuningtool.com) does the same in a web UI with a "Stereo" config — mention it to the user as an option.)

Once completed and verified, transition to **Phase 2**.
