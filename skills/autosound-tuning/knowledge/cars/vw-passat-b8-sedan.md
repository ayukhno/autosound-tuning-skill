# VW Passat B8 sedan — a SINGLE-BUILD CASE STUDY (NOT a reference of facts)

> **How to read this file.** It's the record of **one real build** (the skill author's: Helix DSP Ultra S, 3-way front + sub + center + rear; LHD, 2026) — so you don't re-diagnose a known **body class** from scratch, and as a structural template. It is **NOT facts about the car in front of you** and **NOT a starting recipe.**
>
> Two parts — treat them differently:
> - **PART A — body-class physics** → transfers as an *expectation* to any Passat B8 sedan (confirm by measurement anyway, but you may reason from it).
> - **PART B — what this build's cabin and install DO** → ⛔ **VERIFY ONLY. Never cite it as fact, never offer it as a starting point.** Every item is phrased as a **check** on purpose. Never "your X = Y" from PART B — only "let's check whether your car also shows X".
> - **A different car?** The scope is EXACTLY this body. Don't name "Passat" to the user, don't pull PART B's numbers; at most the *general* sedan room-gain tendency from PART A transfers. Full rule → `SKILL.md → knowledge/cars`.
>
> ⚠️ **What this file does NOT collect: solutions.** No crossover corners, delays, EQ bands,
> polarities or levels that somebody dialled — not even ones that won a competition, and not even
> labelled "verify only". A tune's settings are **project state**; this file holds **physics** (what
> the cabin and the drivers do) and **the install** (how the build is put together). The rule and
> why it was bought: `references/core/knowledge-architecture.md`. Where the settings live: the
> project — its ledger and its `autosound_context.md`.

## PART A — body-class physics (expected on any B8 sedan; confirm anyway)

- **Sedan room gain** — a gentle low-frequency rise, typically **+10..15 dB below ~50 Hz** in the cabin; budget for it, don't "flatten" it blindly.
- **A room-gain hump ~190 Hz** (sedan cabin) — expect a slight rise here.

> Everything else — driver positions/coplanarity, SBIR notches, door-null, **enclosure type/volume** — is **install/gear-specific → PART B (verify only).** Crossovers, delays, EQ and gains are neither: they are the tune's state and live in the project.

## PART B — what this build's cabin and install DO — ⛔ VERIFY ONLY (check on the car; not fact, not a starting point)

Each line: *what the author's build showed* → **how to check it on yours.** Don't carry the numbers into a proposal or into a "your X = Y" answer.

**How this build is PUT TOGETHER — the install, and it is logic, not physics:**
- □ **Mid/tweeter placement and coplanarity?** In the author's: mids on the A-pillar, the mid ≈ coplanar with the tweeter = the most forward geometry → a **ceiling on stage depth** (`staging-depth.md §4`). Relocation within the dash is dead in that car — only the centre position is acoustically clean, and stereo does not live there. → on yours, **whether the drivers are coplanar** depends on YOUR install — ask or measure; **never assert coplanarity as fact** (that is the recurring leak).
- □ **Passive filters in the path?** None in this build — every driver is actively fed from its own DSP output. → ask; a passive between amp and driver changes what every electrical setting downstream means.

**Cabin response anomalies — the PHYSICS half: check by measurement; if present, LEAVE them, don't fill (interference / non-min-phase):**
- □ **A left-midbass dip ~150 Hz?** The author's build had one (left-door geometry/diffraction; NOT minimum-phase → EQ boost forbidden; work with delays / the joint with the sub). → measure your own left door; don't assume the Hz.
- □ **SBIR notches off the A-pillar?** In the author's: R~645 / L~850 Hz, source-side, proven by moving the source; EQ boost forbidden. → the frequencies follow YOUR install geometry — measure, never assume.
- □ **Anti-correlated L/R midbass punch?** In the author's (B8 doors): w-L null ~150 / peak 90–127, w-R mirror-opposite. Don't "treat" one side to match the other blindly. → check your own L vs R.
- □ **An L/R mid phase gap 230–320 Hz (~40°)?** In the author's, parallel mounting; micro-delays didn't collapse it — BUT the summation showed coherent addition there (verified 2026-06-05, don't panic). → judge by YOUR own summation, not by the number.
- □ **An R-side cabin null ~250–375 Hz (w-R −10..−15 dB)?** Interference, not min-phase → **don't EQ-boost**; that joint is "as good as the cabin allows." → check your own R door.
- □ **Deep mid nulls ~640–1078 Hz and ~1524–1711 Hz?** Cabin interference (the ~645 region = the R-pillar SBIR above) → leave, don't fill. → check your own.
- □ **A soft dip ~160 Hz?** A **λ/4 floor/console bounce** (distinct from the room-gain region) — the sub there sits −15..−20 dB → you can't pull it back with phase or EQ; leave it. → check your own.
- □ **A 40 Hz room-mode hump?** → check your own cabin.
- □ **A tweeter dip ~5–6 kHz (seen on the RAW drivers)?** A **built-in de-esser** separating presence (~3k) from sibilance (~8–10k) — don't flatten it (`voicing-by-ear.md` Top/cymbals). → check your own raw tweeters.
- □ **An LHD level tilt — the LEFT drivers hotter in the upper bands (on-axis) → the stage pulls LEFT?** Balance it **cut-only on the left** (don't boost the right). → check which side YOUR geometry (LHD/RHD) favours; the direction flips on an RHD car.
- □ **A right-woofer resonance ~70–100 Hz? A ~190 Hz cabin boom (both sides)?** Unlike the nulls above, these are **peaks**, and a peak is notchable where a null is not — that distinction is the transferable part. → measure YOUR peaks and notch what your own cabin shows; the author's filter values are that tune's state and are deliberately not recorded here.

**Timing and phase behaviour of this install — measured properties, not settings:**
- □ **A midbass L/R intrinsic arrival shift ~1.2 ms** (the pair isn't symmetric — door path/mounting). → set arrival-TA from the **measured latest arriver** (`process-phases.md` Phase 1), don't assume L=R. 2026-07 re-measure: the LEFT side arrived ~1.28 ms early **consistently across all three pairs** (w 1.29 / m 1.30 / tw 1.24) — LHD geometry; zero each pair's own diff (`diagnostic §23`).
- □ **An L/R phase-shape divergence far beyond the electrical filters?** In the author's build (phase-tracking metric, 2026-07): mids ~117° weighted L/R divergence **with IDENTICAL electrical settings**, woofers ~52° — cabin/install-dominated (electrical asymmetry added only ~2°). → measure YOUR pairs' phase tracking before blaming crossovers; the mid-pair asymmetry is an install property. **Closure (2026-07-13):** the raw unwrapped mid-pair Δφ climbs ~2 full rotations = multipath; per-side APF/delay correction REFUTED by search (`diagnostic §26`) — the workable paths are physical changes or center-fill.
- □ **Pair mono-sum suckouts?** In the author's: Ws −11 dB @ 175 Hz (ties to the anti-correlated midbass pair above), Ms −6.4 dB @ ~501 Hz. L+R same-driver interference — leave unless the pair delay strategy changes. → check your own pair sums vs the power-sum.
- □ **A tweeter NON-minimum-phase zone 2100–2800 Hz?** In the author's raw tweeters: excess group delay elevated to 4.3–6.5 ms vs a ~3 ms baseline (REW excess-phase version). Joint repairs whose null sits in that zone resist APF work — expect chaos there, solve robustly (`diagnostic §24`). → run REW's excess-phase on YOUR tweeter sweeps.

- ☑ **The in-band woofer "THD spike" ~160 Hz on the LEFT door — RESOLVED as a NULL ARTIFACT (2026-07-15), mechanics cleared.** The 4.4 % reading sat at a fundamental of 53 dB (the door-null floor) while at 100–125 Hz with 81–84 dB fundamentals the same driver measured 0.16–0.49 % — the fundamental collapses in the null, the harmonics (radiated outside it) don't, so the ratio explodes. → the disqualifier rule now lives in Phase-0 flaw-map item 4 / `rew-api-quirks.md` §Distortion: read the fundamental-dB column next to THD % before blaming mechanics.
- □ **A broad LEFT-side excess at 250–430 (near-side gain, LHD) carried by BOTH branches** — measured w +4.7 / m +5.2 dB L−R (2026-07-15), same cabin physics seen at ~247 Hz in an independent preset on this car. Boominess + lower-mid left pull, with narrow modal ridges (L 188, R 134) beside the door null. ⚠️ Cutting this zone drops the BASS IMAGE's height — see `staging-depth.md §8`. → your car: check both branches before assigning the excess to one.
- □ **Where does distortion put a floor under the corners?** In the author's build: mid-R 18 % @ 100 Hz and clean by 200; tweeters clean from ~1250; the sub best over 32–63 with 3.6 % @ 125. Those are driver+install properties, and they are what a corner has to clear. → derive YOUR corners from YOUR THD table (Phase-0 flaw map item 4).

- □ **A presence VALLEY 2.5–6.3k (floor ~−6 rel 200–1k, ≈−2.7 vs target), symmetric, stable across sessions?** In the author's build it looked like crossover underlap but measured COHERENT (seam coherence −1.5..−2.8 median, both skirts within −8 dB of their cores) — so the seam was not the cause, and the valley was liftable rather than a cancellation. → measure YOUR seam coherence before choosing EQ-lift vs corner-move; the decision, not the filter, is what transfers.
- □ **LEFT-side cold interference lobes ~700–880 and ~1.4–1.8k, POSITION-SENSITIVE (2–5 dB between mic setups), plus a hot L lob 990–1250?** In the author's build the seesaw (±3.5 dB per 1.5 oct) made left-of-center piano wander with pitch and the bass line drift left when the center was off; the cold lobes are interference (boost forbidden), audible in a solo mute-test but masked by the phantom in stereo. → map your own L−R at 1/6-oct across 0.7–1.8k before blaming drivers.
- □ **Bass pan collapse on a pan test (bass "from both sides"), mids panning clean?** The author's mechanism: the door-null seesaw (w solo L−R +1.9 / −9.7 / −0.3 across 90–250) + the mono sub below 88 — `diagnostic §31`; below that seesaw the rest is a modal ceiling. → run the per-band solo L−R table on YOUR car first.

**Signal chain & amplification — the map that makes `diagnostic §32` usable:**
- □ **Which channels share an amplifier knob?** In the author's build the grouping does **not** follow the crossover branches: one 4-channel amp carries **midbass + centres**, a second 4-channel amp carries **midrange + tweeters**, a 2-channel amp the rears, a mono amp the sub; of the DSP's 12 outputs, 11 are used. So "the amp knob is per-PAIR and the DSP ceiling binds on the hotter channel" (§32) couples **mid with tweeter** here — a coupling you cannot read off a crossover diagram, and the reason a tweeter trim in that build kept dragging the mid's headroom with it. → ask for YOUR amp→channel map at intake (`project-intake.md` §52) and write it down before any gain-structure work; never infer it from driver type.
- □ **Source path.** Android head unit *and* a phone over a Bluetooth HD module into the DSP, plus a remote level knob on the DSP. Two consequences seen in that build: a source swap changes the digital level reference, and the remote knob is a **global, level-dependent** control that no preset snapshots — so it has to be recorded per measurement (`process-control.md`). → establish which source was live and where the knob sat before comparing any two series.
- □ **Power/ground topology.** Battery → a single main fuse → a distribution block, one feed per amp, and a ground distribution block to the OEM chassis bolt. Speaker gauges scale with the band (sub heaviest, tweeters/centres lightest). ⚠️ Relevant to tuning only through **noise**: the RCA-pull test in §32 separates amp self-noise from ground/upstream, and that only isolates cleanly when the grounds meet at one point. → check where YOUR amps ground before chasing a hiss in the DSP.

**Drivers / enclosure — from the user's intake or the datasheet, NOT from here:**
- □ The sub enclosure in the author's build = a **sealed box ~35 L** in the trunk (worked well). → your enclosure type/volume is whatever the user actually has; **don't assume "35 L" or "sealed"**.

> **Removed 2026-09-05: "the crossovers that won in the author's build".** A block of dialled
> corners, slopes and polarities — including the pair that won an AYA round — kept here as "data,
> not your starting table". By the owner's ruling the label does not save it: **this base does not
> collect successful solutions.** A tune's settings are project state; what a competition win
> proves about a *scheme* belongs in `knowledge/approaches.md`, and how far an electrical corner
> sits from its acoustic plan is a method fact that already lives in `filter-types-car-audio.md`.

**Techniques (more transferable, still verify by ear/measurement):**
- Heavy midbasses in the doors → align to **100% of the IR peak**, not the nose (`car-eq-patterns.md`). [Phase-1 TA]
- Deliberate L/R asymmetry of levels/delays (LHD: the left channels quieter and more delayed) → centering.

> Source: the skill author's project (Helix DSP Ultra S). Full history — in the author's `autosound_context.md`.
