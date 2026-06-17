# Helix DSP Ultra S — full workflow (VCP)

## Signal-processing architecture

### Two processing layers (Output Layer + Virtual Layer)

```
Source (S/PDIF / BT HD)
    ↓
[VIRTUAL CHANNEL LAYER]  ← House Curve (RAW-CAT / Harman)
    Front L, Front R, Center (RealCenter)
    Whole-front EQ together
    ↓
[OUTPUT LAYER]           ← Crossovers + per-driver EQ
    Output A (Tweeter L)  → crossover + notch filters
    Output B (Mid L)      → crossover + notch filters
    Output C (Midbass L)  → crossover + notch filters
    Output D (Tweeter R)  → crossover + notch filters
    ... etc.
    ↓
Amplifiers → Drivers
```

**Why this order is critical:**
- Crossovers on the Output Layer introduce phase shifts. If you apply EQ after the crossovers, separately per driver, the joints break.
- EQ on the Virtual Layer affects the whole band together → the joints between drivers stay unchanged. **Mechanism:** virtual-EQ sits in the chain ABOVE the per-driver crossovers, so its phase shift is SHARED across all of the side's drivers → the mutual phase w↔m↔tw doesn't change. So put L/R asymmetry on OUTPUT, and symmetric voicing on VIRTUAL (detail — `diagnostic-techniques.md §6`).
- RealCenter takes its signal from the Virtual channels → it automatically picks up the House Curve.

---

## Measuring with loopback (Focusrite Scarlett 2i2)

If you have an external sound card with a loopback cable, it gives an **absolute time reference** and removes USB/buffer latency.

**What it gives:**
- A hardware time reference (~9.6 ms of real flight time in the Passat B8)
- Removes the systematic software-latency error
- For aligning mid/tweeter peak-to-peak → a monolithic upper tier of the stage

**Microphone and calibration:**
- **ECM8000 (main)** — connected to the Scarlett 2i2; has its own 0° and 90° cal files, derived by measuring against the UMIK-1. Used for all phase-critical measurements.
- **UMIK-1 (USB, secondary)** — has stock 0° and 90° cal files from miniDSP. It served as the reference for calibrating the ECM8000. Now used only for SPL spot-checks.
- **Why the ECM8000 is better for phase:** the UMIK-1 connects over USB — any USB latency and buffer jitter rides on top of the timing measurements. The ECM8000 through the Scarlett with a physical loopback gives hardware sync without USB jitter → more accurate phase.

**Setup:**
- Rate depends on the mic:
  - **ECM8000 + Scarlett (main rig): 96 kHz** — the Helix DSP Ultra S's native internal rate.
  - **UMIK-1 (quick measurement on the go): 48 kHz** — the UMIK-1's hardware max (44.1/48 kHz).
- Loopback: a physical analog cable (Scarlett output → Scarlett input) to sync the time axis
- Input: ECM8000 on Scarlett input 1, loopback on input 2

**Which mic when:**
| Task | Mic |
|---|---|
| Time alignment, phase measurements, IR | ECM8000 + Scarlett + loopback |
| SPL/FR (MMM) | ECM8000 or UMIK-1 |
| Quick level check (RTA) | any |

**Important — choosing the alignment point:**
- **Mid/tweeter** — align to the **peak (100% of the peak)** of the IR, not to the onset (the nose)
- **Midbass (heavy, GZNK 165SQ-K)** — also align to the amplitude peak, not to the cone's onset; heavy drivers have a delay between the start of motion and the maximum — aligning to the nose gives a diffuse attack and a "collapsing stage"

---

## Tuning order → canon in `process-phases.md`

The full process (Phases −1…6: intake → baseline → crossovers/TA → EQ → verdict → center/rear → listening → voicing) lives **only** in `references/process-phases.md`; we don't duplicate it here (an old copy of this file had drifted from the canon). The two-layer logic — OUTPUT base (asymmetry/surgery) vs VIRTUAL voicing (the symmetric curve shape, doesn't break joints) → `diagnostic-techniques.md §6`; how to apply a house curve on the virtual layer → `car-eq-patterns.md`. This file keeps only the **Helix specifics** below.

---

## Helix DSP Ultra S — specific features

### Output voltage and gain staging

**Situation:** the Ultra S puts out up to 8 V on its outputs. Most amplifiers take 4–5 V.

**Solution:** set all Output channels to **−6 dB** in the PC-Tool → this drops 8 V to ~4 V.

**Principle:**
```
Minimum gain on the amp + maximum level in the processor = better SNR
```

**Procedure for setting amp gains:**
1. All gains to minimum
2. In REW → RTA → enable the THD readout
3. Feed a sine (100 Hz for midbass, 1 kHz for the mid, 5 kHz for the tweeter)
4. Slowly raise the gain → to the first jump in THD → back off by 10%
5. Noise in the pauses = the amp gain is too high → reduce it, raise the level in Helix

### DAC Digital Filter (AKM Config)

Found in: ACO Features → AKM Config

| Mode | Character | Recommendation |
|---|---|---|
| Short Delay Sharp Roll Off | Dynamic, slightly "digital" | Default |
| **Short Delay Slow Roll Off** | Softer treble, more "air" | **Recommended for SQ** |
| Super Slow Roll Off | Most analog, gentle roll-off >18 kHz | If the treble is too bright |

### ISA (Input Signal Analyzer)

Use it to check the input signal while setting gains. Shows clipping in real time.

### Virtual Channel Processing (VCP)

- **Virtual Channels:** Front L, Front R, Center, Rear
- **Link:** tie L+R for simultaneous adjustment
- **Virtual EQ:** the same interface as on the outputs, but for the group
- **RealCenter:** an algorithm that extracts the mono component → the center channel

---

## Starting crossovers → `filter-types-car-audio.md`

The starting crossover sets (there are several, and they evolve) are consolidated in `references/filter-types-car-audio.md` §"Starting crossover sets"; **this car's current choice** → `dsp-state-current` + profile §4. Not duplicated here.
