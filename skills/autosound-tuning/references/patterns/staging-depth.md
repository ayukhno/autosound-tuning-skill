# Stage depth and layering (front-back) — separate from lateral imaging

> 🧩 **PATTERN REPOSITORY — starting hypotheses, not rules.** Everything here is "in similar conditions this often worked": a **starting point**, validated by measurement/ear, never a mandate. (Physics stays firm; the prescriptions are hypotheses.) See [`knowledge-architecture.md`](file:///skills/autosound-tuning/references/core/knowledge-architecture.md).

`diagnostic-techniques.md` treats the **lateral** (L/R positions). This file is about **depth** (front-back: pushing the stage off the windshield back behind the hood) and **layering** (tiers). Different psychoacoustics, different levers. The work is mostly **ear-driven** (cabin phase/GD unreliable — see diagnostic §10; measurement here is only a sanity check: magnitude + summation).

## 1. The root of "the stage sticks to the glass / the voice juts forward / the bass magic disappears" = the TOP is too hot relative to the bass
The symptom cluster — a forward stage + a forward/thin voice + "the bass magic vanishes when everything plays" — usually has **one root: an excess of upper energy (presence/treble) relative to the bass foundation**, NOT a bass problem. The excess top simultaneously: masks the bass, pulls the stage forward (Haas — early treble energy), makes the voice prominent.
- **Diagnostic test:** play **sub+midbass SOLO.** If the bass on its own is great/dense, but **disappears/loses its magic when you add the mid+tweeter** → the top is too hot. One test isolates the root.
- **A phase/joint-coherence REPAIR raises the stage (height AND forwardness) as a side effect** *(provisional, one build 2026-07)*: after tweeter-joint repairs the summed HF energy is delivered more coherently — the stage rose above eye level even though the ALL magnitude stayed median-neutral. Don't undo the repair; rebalance the foundation (§2) instead.
- This can contradict "the tone is on target" (Jazzi, etc.): the target curve can be **forward for the STAGE**, even if it's tonally "correct". Depth wants a warmer voicing.

## 2. Treat it by BUILDING UP the bass, NOT cutting the top
The same top/bottom balance shift, but the method is critical:
- **Cutting the top (high-shelf) costs TRANSPARENCY/air** — verified by ear (an HS at 1500 cut the transparency, rejected).
- **Raise the bass (a low-shelf on the virtual bass channels, ~+3 below 150–160 Hz on virtual-L + virtual-R + virtual-sub)** — it lifts the foundation, the mid/tweeter stay full → **transparency preserved + the stage recedes**. This is also "raise the sub+midbass" with one control (a defined turnover, cleaner than tweaking gains).
- **A presence trim** as a secondary lever: a **broad PK 2–3 kHz** (e.g. PK2700/−2/Q0.9, on virtual-L+R symmetrically) cuts the forward presence hump, but **leaves the air >5k intact** (unlike a shelf, which kills the air too). It damages the tone less. The bass lift does the main work.

## 3. Depth DEPENDS ON THE LOUDNESS LEVEL (equal-loudness)
At low volume, bass perception drops (equal-loudness contours) → the top relatively dominates → **the stage goes forward when quiet**. The bass depth-voicing is **calibrated to the playback level**. → tune/listen at the level it'll be judged at (or think about loudness compensation for quiet). Derive the level-anchored sub targets with [`rew_tool/equal_loudness.py`](file:///skills/autosound-tuning/rew_tool/equal_loudness.py).

## 4. The physical ceiling: the mid's location + DEPTH LIVES IN THE RECORDING
Depth comes from a **long acoustic path to the mid** (a kick mount, the base of the windshield). **A mid on the A-pillar near-coplanar with the tweeters = the most forward geometry** → absolute depth is physically limited. The DSP **maximizes** depth within that, it doesn't lift the limit. Push it back a step or two, not "an orchestra behind the hood".
- **The key point (Wehmeyer/Audiofrog):** a 2-channel system's images lie within the **triangle** [listening position ↔ left driver ↔ right]. **Depth and width depend on the AMBIENT information in the RECORDING (early/late reflections, reverb), NOT on your settings.** A recording with no spatial information will NOT reproduce depth beyond the plane of the drivers — no matter what you tweak. → you can't "add" depth that isn't in the track; depth-voicing only STOPS destroying it (excess top/Haas) and lets what IS in the recording come through. That's why a reference track with pronounced space (an opera hall) is critical — on a "dry" track there will be no depth at all.

## 5. Deep bass and sub resonance
- **Don't boost the sub's resonance with an EQ peak** to fill a neighboring dip — it adds ringing/decay (one-note bass) + drives the cone to max excursion (distortion). Give deep weight with **LEVEL/a shelf**, not a point boost of the resonance. (Peak-vs-null applies to "don't boost the resonance" too.)
- A dip between modes in the sub — accept it as physics, don't fight it with EQ near the resonance.

## 6. Layering (tiers)
Not a separate control, but a consequence: clean joint phase + a refined (not bloated) bass + recessed presence. It develops ear-driven on tracks with pronounced hall depth. Lateral imaging tracks (EMMA) are NO good for depth — you need material with depth layers (an opera hall, acoustic). Reference tracks → `competition.md`.

> **For listening-test hypotheses — `references/patterns/test-tracks.md`** (the measure→track index + markers): depth → #07 Melody Gardot / #14 Hanne Boel; midbass punch → #26 Devil Inside / #20 Godsmack; the sub↔midbass joint → #25 Sundust / #16 Dock Funk; sub<40 → #24 Olgoi Khorkhoi. Give the Arbiter a track + timecode + what to listen for.

## 7. The method: ear-driven, measurement only as a sanity check
Cabin single-position phase/GD are unusable (diagnostic §10) — confirmed for depth too. The hypothesis "an L/R phase hole on the vocal body 230–320 eats the body" was **DISPROVED by summation** (the measured mid sum at 230–320 matched the power-sum ±1 → the body is NOT cancelled). So: depth changes **by ear**, with **summation+magnitude** as the only reliable checks. Every change reversible, in a **depth PRESET** (the voicing layer), the base untouched.

> **A provisional set of depth levers (validate in practice):** presence shaping 2–5k (less = farther) · HF tilt (rolled-off = a distant plane) · clean joint phase (opens depth) · direct/reflected (+ rear if it's engaged) · bass weight (the main one, verified).

## 8. BASS-image height and sub forward-masking live in the front's upper-bass (130–500) *(one build, 2026-07)*

LF itself has no vertical cue — the bass image sits where its **harmonics** image, and those come from the front stage. Two field-validated consequences:

- **Cutting 250–430 on the side that "shines" from the pillars steals the bass image's HEIGHT.** A hot left-side 250–430 (both midbass skirt AND pillar-mid skirt — LHD near-side gain) pulled lower mids left and boomed; the per-branch cuts fixed both diseases, but the bass image dropped from the windshield to the bottom of the dash — the pillar-height harmonic energy had been doing vertical work. **The symmetric compensator: a small in-band PK lift on the mid PAIR** (here PK 520 +1.2 Q1.8 — inside the mids' passband, NOT their skirt) restored the height ("sub on the hood") without re-adding the L/R skew. Cut the disease per-side, restore the height per-pair.
- **The front's 130–250 punch zone forward-masks the trunk sub.** Over-cutting it (see the phase-2 "summed package curve" rule) audibly unmasked the sub — it localized rearward at normal listening levels; softening the cut re-anchored the bass front. If the sub "moves back" right after front midbass EQ, suspect the front anchor before touching the sub.

## 9. A trunk sub localizes on SUSTAINED bass only — and only above its calibrated level *(one build, 2026-07-19)*

The trunk sub arrives 10–15 ms after the front (it's the delay reference; fronts can't be pushed later without eating the rear-fill delay ceiling). Transient bass rides the precedence effect → anchors front regardless. **Sustained/droning bass has no precedence cue** → localization follows the energy balance: with the sub a few dB over target the late rear field + cabin modes read as "bass from around/behind"; at the calibrated level the front re-anchors. Diagnose with the remote-knob ladder (the effect scales with the knob), THD and LPF-tail checks (both were clean — don't blame them first). Below ~50 Hz envelopment is cabin physics (non-localizable) — don't chase it. Related window (§vT1 build): the bass image holds between about ±6 dB around the calibrated sub level — below it drops to the dash, above it pulls rearward; road-noise masking (~6–10 dB at 20–100 Hz) is why an owner's road level reads as boom to a parked judge.
