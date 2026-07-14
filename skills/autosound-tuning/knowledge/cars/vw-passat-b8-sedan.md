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

**Cabin response anomalies — check by measurement; if present, LEAVE them, don't fill (interference / non-min-phase):**
- □ **An R-side cabin null ~250–375 Hz (w-R −10..−15 dB)?** Interference, not min-phase → **don't EQ-boost**; that joint is "as good as the cabin allows." → check your own R door.
- □ **Deep mid nulls ~640–1078 Hz and ~1524–1711 Hz?** Cabin interference (the ~645 region = the R-pillar SBIR above) → leave, don't fill. → check your own.
- □ **A soft dip ~160 Hz?** A **λ/4 floor/console bounce** (distinct from the room-gain region) — the sub there sits −15..−20 dB → you can't pull it back with phase or EQ; leave it. → check your own.
- □ **A 40 Hz room-mode hump?** → check your own cabin.
- □ **A tweeter dip ~5–6 kHz (seen on the RAW drivers)?** A **built-in de-esser** separating presence (~3k) from sibilance (~8–10k) — don't flatten it (`voicing-by-ear.md` Top/cymbals). → check your own raw tweeters.
- □ **An LHD level tilt — the LEFT drivers hotter in the upper bands (on-axis) → the stage pulls LEFT?** Balance it **cut-only on the left** (don't boost the right). → check which side YOUR geometry (LHD/RHD) favours; the direction flips on an RHD car.
- □ **A right-woofer resonance ~70–100 Hz? A ~190 Hz cabin boom (both sides)?** Unlike the nulls above, these are **peaks** → they ARE notchable (cut, don't leave). The author's build: R-woofer **73 Hz · −9 dB · Q 3.5**; boom **188 Hz · −5.5 dB · Q 5.0** (L) / **193 Hz · −3.0 dB · Q 6.0** (R). → measure YOUR peaks; those Hz/depth/Q are this build's — notch what your cabin actually shows, never copy these numbers.

**Install polarity & inter-channel timing — a SUMMATION result of THIS build's crossovers, NOT a rule:**
- □ **Per-driver polarity** in the author's build: **sub + midbass + tweeter INVERTED, mid NORMAL** — because the **Bessel joints summed best at opposite polarities** (tweeter flips against the mid, §9 `diagnostic`) while the **sub's BW joint did NOT flip.** ⚠️ Derive yours by **summation** (`diagnostic §9`), never copy this pattern — it's a result, not a recipe.
- □ **A midbass L/R intrinsic arrival shift ~1.2 ms** (the pair isn't symmetric — door path/mounting). → set arrival-TA from the **measured latest arriver** (`process-phases.md` Phase 1), don't assume L=R. 2026-07 re-measure: the LEFT side arrived ~1.28 ms early **consistently across all three pairs** (w 1.29 / m 1.30 / tw 1.24) — LHD geometry; zero each pair's own diff (`diagnostic §23`).
- □ **An L/R phase-shape divergence far beyond the electrical filters?** In the author's build (phase-tracking metric, 2026-07): mids ~117° weighted L/R divergence **with IDENTICAL electrical settings**, woofers ~52° — cabin/install-dominated (electrical asymmetry added only ~2°). → measure YOUR pairs' phase tracking before blaming crossovers; the mid-pair asymmetry is an install property. **Closure (2026-07-13):** the raw unwrapped mid-pair Δφ climbs ~2 full rotations = multipath; per-side APF/delay correction REFUTED by search (`diagnostic §26`) — the workable paths are physical changes or center-fill.
- □ **Pair mono-sum suckouts?** In the author's: Ws −11 dB @ 175 Hz (ties to the anti-correlated midbass pair above), Ms −6.4 dB @ ~501 Hz. L+R same-driver interference — leave unless the pair delay strategy changes. → check your own pair sums vs the power-sum.
- □ **A tweeter NON-minimum-phase zone 2100–2800 Hz?** In the author's raw tweeters: excess group delay elevated to 4.3–6.5 ms vs a ~3 ms baseline (REW excess-phase version). Joint repairs whose null sits in that zone resist APF work — expect chaos there, solve robustly (`diagnostic §24`). → run REW's excess-phase on YOUR tweeter sweeps.

- □ **Center-fill as the mid-pair remedy (validated in this build, 2026-07):** the winning config was a COMPLEMENTARY center — HPF 620 LR36 · LPF 2330 LR36 · PK 1000 −9 Q2 + PK 1450 −9 Q2 (trough over the coherent 900–1600 zone), INV + 0.74 ms vs the raw state, quiet level (~+3 dB working point), fed by a static L+R matrix (RealCenter OFF — signal-dependent steering breaks fixed calibration). Measured pocket recovery +4.4/+2.3 dB; head-turn-stable center by ear. ⚠️ The pocket frequencies/shape are THIS build's coherence map — derive yours from YOUR map (`diagnostic §26`), never copy these corners.

- □ **An in-band woofer THD spike ~160 Hz on the LEFT door (4.8 % vs <1 % elsewhere in-band)?** Found via `get_distortion` on the raw sweeps (2026-07-14); sits in the same region as the left-door null ~150 — suspect mechanical (excursion/rub at the diffraction-compensated zone). → run the THD table on YOUR raw sweeps; a spike like this is an install finding (damping/mounting check), not an EQ target.
- □ **Measured THD floors that justified this build's crossover corners:** mid-R 18 % @ 100 Hz → clean by 200 (HPF 460 = huge margin); tweeters clean from ~1250 (HPF 3625 ✓); sub best 32–63, 3.6 % @ 125 (LPF 88 ✓). → derive YOUR corners from YOUR THD table (Phase-0 flaw map item 4), never copy these.

**Drivers / enclosure — from the user's intake or the datasheet, NOT from here:**
- □ The sub enclosure in the author's build = a **sealed box ~35 L** in the trunk (worked well). → your enclosure type/volume is whatever the user actually has; **don't assume "35 L" or "sealed"**.

**The crossovers that won in the author's build — DATA, not your starting table:**
> ⚠️ These are *one build's measurement results*, not recommendations. Derive a specific car's crossovers from baseline + summation (`process-phases` Phase 1). Do **NOT** present these as candidates before measuring.
- mid↔tweeter **BE4** (close together, ~coplanar on the pillar in that build): mid LPF 3k2 BE4 + tweeter HPF 5k0 BE4 (~4k acoustically, through the Bessel overlap) — part of the **LR4+BE4 hybrid that won AYA (junior group)**. ⚠️ That win is **this car+install+gear-specific, NOT "the AYA recipe"** (the scheme + its confidence → `knowledge/approaches.md`).
- midbass↔mid **LR4** ~300 Hz electrical (≈250 acoustic through the B8 midbass roll-off) — spaced-apart drivers.
- sub: LP ~60–63 LR4; subsonic 20 BE1/BW2 (that build was sealed); judge the SW+Ws joint by summation.
- **Second data point (2026-07, the same build, acoustic-plan-first / "v3"):** an NTT acoustic plan 70/320/3500 LR4 was REALIZED by electrical sub LPF 88 BW36 · w 86/215 LR12 · m 460 BW24 + 2000 LR12 · tw 3625 BW24 (mid+tw polarity inverted — again a summation result). Attested in hardware: balance residuals ≤1.1 dB, all joints healthy, "wow, transparent" by ear. Note how FAR electrical corners sit from the acoustic plan (460 electrical → 320 acoustic) — the provenance rule (`filter-types-car-audio.md`) in the flesh.

**Techniques (more transferable, still verify by ear/measurement):**
- Heavy midbasses in the doors → align to **100% of the IR peak**, not the nose (`car-eq-patterns.md`). [Phase-1 TA]
- Deliberate L/R asymmetry of levels/delays (LHD: the left channels quieter and more delayed) → centering.

> Source: the skill author's project (Helix DSP Ultra S). Full history — in the author's `autosound_context.md`.
