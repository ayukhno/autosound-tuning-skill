# Stage imaging — width, height, depth, and side-to-side evenness

> 🧩 **RESEARCH / CRAFT MATERIAL, not doctrine — and NOT one trust register.** Unlike
> [`resonalyze-virtual-dsp.md`](references/tooling/resonalyze-virtual-dsp.md), where every number is a
> named constant read from code, this file mixes **measurement, literature, and craft**, and the
> firmness of each piece is labelled. Read it that way; do not level the pieces into one confidence.
> **What of this becomes advice the method GIVES is a decision only the user makes** — nothing here is
> a recommendation to do anything to a live car. From a conversation the fork session had with the
> author, 2026-08-25; the measured parts were run through the skill's own `curve_view` on live REW.

| property | how firm |
|---|---|
| side-to-side evenness | **measured**, mechanism clear |
| height | a **documented** mechanism (directional bands) — but the numbers are literature-from-memory |
| width | mechanism clear, hard to measure |
| depth | **softest**, much folklore |

## 1. Side-to-side evenness — the one thing actually measured

**Mechanism.** If L and R differ in magnitude **differently in different bands**, the parts of one
sound pull to different sides: the body of a voice (350–700 Hz) and its articulation (1.4–3.6 kHz)
land in different places. The image is not a point — it is stretched. This is NOT the same as an
overall level tilt: the level can be perfectly matched and the stage still "wanders".

**How to measure it (run on live data, 2026-08-25):** feed the L−R difference in dB through
[`curve_view.py`](references/tooling/rew-tool-docs.md) — `report(freqs, magL - magR, band,
source="sweep")`, which the docstring already anticipates ("Works on any dB curve … a new-vs-old
delta"). It routes features by width, and the routing is the point: a feature `< 1/6 oct` on a
single-point measurement is **verify-first** — it must survive MMM / a mic shift before it is acted
on at all.

**What a real competition tune gave (block `_50`, 2026-08-25):** 34 features over 2 dB in L−R, **33
of them routed to verify-first**, none to voicing.

> **The conclusion worth carrying into the method: a single-point measurement gives no basis for ANY
> narrow L/R correction.** Not because there is nothing there — because from one point you cannot tell
> whether it is in the system or only in that point. This turns "the multi-position (ellipsoid) capture
> debt" from hygiene into **the thing that actually unblocks side-evenness work.**

Two corrections, both load-bearing:
- **(cockpit, confirmed)** smoothing makes a feature **lower and wider, never narrower** — so features
  measured as narrower than 1/6 oct *already under smoothing* are at least that narrow unsmoothed; and
  `find_features` counts only what clears the 2 dB threshold, which smoothing lowers, so **34 is a lower
  bound on the count**, not the number. (This is exactly why the double-smoothing trap —
  `curve_view` refusing a pre-smoothed input — works IN FAVOUR of this conclusion, not against it.)
- **(the tune session)** a broad macro move is easy to over-read: a claimed "8 dB midrange tilt" was partly an
  already-recorded local feature (the `m-R` 670–1800 comb that survives MMM, `action=leave`). The
  numbers were measured right; the reading was too wide. **Before calling a macro move a tilt, check it
  against what is already known about that specific driver.**
- *modes:* below ~300 Hz (the localisation floor Resonalyze itself uses) a large L−R spread with a
  **sign that flips** is the signature of cabin modes, not a tilt — it does not affect the image, it
  affects the tone.

## 2. Height — a real mechanism, but the numbers are unverified

**Blauert's directional bands.** For a single source, lifting a narrow band shifts the apparent
direction **regardless of where the source actually is**:

| band | pulls |
|---|---|
| ~300–600 Hz | back |
| ~1 kHz | back |
| ~3 kHz | forward |
| **~8 kHz** | **up** |
| ~10 kHz | back |

⚠️ **Source: literature, from memory, NOT checked against the original this session.** The numbers are
approximate, and the effect is weaker on broadband material than in those experiments. **Verify against
Blauert, _Spatial Hearing_, before this becomes method advice.**

**Two physical levers that dominate in a cabin** (craft, not literature): where the tweeter sits and
where it points; and the windscreen reflection, which raises the apparent source.

## 3. Width

- **magnitude symmetry between sides, per band** — the same as §1; asymmetry at a frequency narrows
  the image at exactly that frequency
- **lateral early reflections widen the apparent source (ASW)** — established in hall acoustics; a door
  window ~30 cm to the side makes the reflection strong, so it both widens and blurs
- **inter-channel decorrelation** — but that is a property of the material, not the tune

## 4. Depth — the softest, and where to hold back

- direct-to-reflected ratio: more direct = closer
- **a dip in the presence band (2–5 kHz) pushes back, a rise pulls forward** — the same logic as §2
- transient cleanliness: a sharp front reads as a defined place, not a smear

**What is NOT claimed, and should not be:** that depth can be "tuned". In a cabin, depth is largely the
**absence of cues** shouting "driver in the door" — remove the cues and depth appears.

## 5. What this implies for TUNING — the most useful part

**A broad tilt is fixed by a broad, low-Q correction. A narrow correction from one point is not.**

This is the same boundary as Resonalyze #91: DIMOSUS independently arrived at **Q ≤ 6** for automatic in-cabin EQ,
because narrower is a property of the mic position, not the system. Wehmeyer: five positions in an 18 cm
circle — nearly identical below 200 Hz, a transition 200 Hz–1 kHz, **above 1 kHz a spread of 25 dB and
more**. So side-evenness work must be **macro-scale until a multi-position measurement exists** — and
that is not caution, it is what the skill's own `curve_view` says when asked.

The failure mode this guards against is concrete: when the per-side EQ corrects **different
frequencies** at high Q, the left and right errors change independently as the listener moves, the L/R
balance drifts, and the stage does not hold still. High-Q per-side correction from a single point is
what makes that happen; a broad, low-Q move does not.

## Where this connects in the method

The L−R-through-`curve_view` read is the same instrument as everywhere else; the routing that sends
narrow single-point features to verify-first is `curve_view`'s own doctrine (`§13`, mic-shift). The
`Q ≤ 6` boundary and the multi-position spread are the measured backing for the ellipsoid capture in the
[`virtual-first`](references/phases/virtual-first.md) Phase 0 (block 3) and for `diagnostic §13`'s
spatial-validity Q ceiling. The Blauert bands and the depth/width craft are NOT wired into any tool —
they stay here as material until the user rules on them.
