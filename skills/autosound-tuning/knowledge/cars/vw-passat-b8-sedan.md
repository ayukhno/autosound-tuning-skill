# VW Passat B8 sedan — a SINGLE-BUILD CASE STUDY (NOT a reference of facts)

> **How to read this file.** It's the record of **one real build** (the skill author's: Helix DSP Ultra S, 3-way front + sub + center + rear; LHD, 2026) — so you don't re-diagnose a known **body class** from scratch, and as a structural template. It is **NOT facts about the car in front of you** and **NOT a starting recipe.**
>
> Two parts — treat them differently:
> - **PART A — body-class physics** → transfers as an *expectation* to any Passat B8 sedan (confirm by measurement anyway, but you may reason from it).
> - **PART B — the record of THIS build** → ⛔ **VERIFY ONLY. Never cite it as fact, never offer it as a starting point.** Driver placement, drivers, enclosure, crossovers, gains **vary from build to build even on the same body** → every item is phrased as a **check** on purpose. Never "your X = Y" from PART B — only "let's check whether your car also shows X".
> - **A different car?** The scope is EXACTLY this body. Don't name "Passat" to the user, don't pull PART B's numbers; at most the *general* sedan room-gain tendency from PART A transfers. Full rule → `SKILL.md → knowledge/cars`.

## PART A — body-class physics (expected on any B8 sedan; confirm anyway)

- **Sedan room gain** — a gentle low-frequency rise, typically **+10..15 dB below ~50 Hz** in the cabin; budget for it, don't "flatten" it blindly.
- **A room-gain hump ~190 Hz** (sedan cabin) — expect a slight rise here.

> Everything else — driver positions/coplanarity, SBIR notches, door-null, **enclosure type/volume**, crossovers, gains — is **install/gear-specific → PART B (verify only).**

## PART B — the record of THIS build — ⛔ VERIFY ONLY (check on the car; not fact, not a starting point)

Each line: *what the author's build showed* → **how to check it on yours.** Don't carry the numbers into a proposal or into a "your X = Y" answer.

**Mounting geometry — check by measurement/question, don't assert:**
- □ **A left-midbass dip ~150 Hz?** The author's build had one (left-door geometry/diffraction; NOT minimum-phase → EQ boost forbidden; work with delays / the joint with the sub). → measure your own left door; don't assume the Hz.
- □ **Mid/tweeter coplanarity and SBIR on the A-pillar?** In the author's: mids on the A-pillar → SBIR notches R~645 / L~850 Hz (source-side, proven by moving the source; EQ boost forbidden; relocation within the dash is dead — only the center is clean, where stereo doesn't live; the path = DSP within limits + center-fill); the mid ≈ coplanar with the tweeter = the most forward geometry → a **ceiling on stage depth** (`staging-depth.md §4`). → on yours, both the notch frequencies and **whether the drivers are coplanar** depend on YOUR install — measure; **never assert coplanarity as fact** (that is the recurring leak).
- □ **Anti-correlated L/R midbass punch?** In the author's (B8 doors): w-L null ~150 / peak 90–127, w-R mirror-opposite. Don't "treat" one side to match the other blindly. → check your own L vs R.
- □ **An L/R mid phase gap 230–320 Hz (~40°)?** In the author's, parallel mounting; micro-delays didn't collapse it — BUT the summation showed coherent addition there (verified 2026-06-05, don't panic). → judge by YOUR own summation, not by the number.

**Drivers / enclosure — from the user's intake or the datasheet, NOT from here:**
- □ The sub enclosure in the author's build = a **sealed box ~35 L** in the trunk (worked well). → your enclosure type/volume is whatever the user actually has; **don't assume "35 L" or "sealed"**.

**The crossovers that won in the author's build — DATA, not your starting table:**
> ⚠️ These are *one build's measurement results*, not recommendations. Derive a specific car's crossovers from baseline + summation (`process-phases` Phase 1). Do **NOT** present these as candidates before measuring.
- mid↔tweeter **BE4** (close together, ~coplanar on the pillar in that build): mid LPF 3k2 BE4 + tweeter HPF 5k0 BE4 (~4k acoustically, through the Bessel overlap) — the key to the AYA win (junior group).
- midbass↔mid **LR4** ~300 Hz electrical (≈250 acoustic through the B8 midbass roll-off) — spaced-apart drivers.
- sub: LP ~60–63 LR4; subsonic 20 BE1/BW2 (that build was sealed); judge the SW+Ws joint by summation.

**Techniques (more transferable, still verify by ear/measurement):**
- Heavy midbasses in the doors → align to **100% of the IR peak**, not the nose (`car-eq-patterns.md`). [Phase-1 TA]
- Deliberate L/R asymmetry of levels/delays (LHD: the left channels quieter and more delayed) → centering.

> Source: the skill author's project (Helix DSP Ultra S). Full history — in the author's `autosound_context.md`.
