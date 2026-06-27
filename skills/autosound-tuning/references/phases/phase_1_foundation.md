# Phase 1 — Crossovers, Levels & Preliminary Delay

This phase establishes the physical foundation of the tune: crossovers, preliminary level balance, raw driver timing, and band-specific targets.

## Core Objectives
1. **Raw Measurement (User):** Capture individual channel sweeps and MMM RTAs.
2. **Gross Time-Alignment (TA):** Align the arrival of direct sound from all drivers using the Impulse Response (IR).
3. **Crossover Selection:** Propose acoustic crossover frequencies and slopes.
4. **Band-Specific Targets:** Generate per-channel targets using the Nono Tuning Tool (NTT).

---

## Step-by-Step Runbook

### 1. Collect Raw Measurements
The user takes measurements for each isolated channel using protective HPFs:
* **MMM RTA:** For frequency response (FR) magnitude.
* **SWEEP (with physical Loopback):** For impulse response, phase, distortion, and group delay.

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
  * For crossover tradeoffs, refer to [filter-types-car-audio.md](file:///skills/autosound-tuning/references/filter-types-car-audio.md).

### 4. Review and Discussion
Format a Generator proposal package (per the data contract §3) and send it to the Critic. Refine the levels, timing, and crossovers. Upon agreement, the user applies these values to the DSP.

* **How to apply & save to the DSP (Arbiter):**
  1. Open Helix PC-Tool and load your **existing active baseline setup** (the current active profile you are starting from). Do *not* assume a `.pct6` file of version `v0` exists on disk if this is a fresh start.
  2. Enter the new parameters (protective/preliminary crossovers, delays, and level adjustments) exactly as agreed in the final proposal.
  3. Save the modified profile as `<prefix>_v1_foundation.pct6` locally on your computer in the workspace directory **`rew_analitic/dsp-config/`** (so it can be committed to Git and tracked properly).
  4. Write/flash this configuration into an active, safe slot of your physical Helix DSP to make it active before running any sweeps.

### 5. Generate Band-Specific Targets (Step 5b)
Once crossovers are locked, generate per-band target curves using [nonotuningtool.com](https://nonotuningtool.com).
* **Acoustic Summation:** The tool computes targets that are lowered in overlap regions so their acoustic sum reconstructs the house curve without a joint-hump.
* **Stereo Configuration:** Ensure drivers are configured as "Stereo" in the tool prior to exporting.
* **Verify exports:** `_SUM` targets (for L+R pairs) should be +3 to +6 dB hot compared to non-SUM (single-side) targets. Mono channels (sub) should have identical SUM and non-SUM targets.
* Save targets into `rew_analitic/target-curves/<name>/` and load them into REW. Use these targets for Phase 2a hygiene EQ.

Once completed and verified, transition to **Phase 2**.
