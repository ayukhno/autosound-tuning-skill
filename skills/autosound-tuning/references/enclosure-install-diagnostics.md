# Box vs cabin: diagnosing install defects (lessons 2026-06-08..10)

When a channel has a fixed dip/peak and the question is "is this the driver, the box, or the cabin?" — here's the method. Born from a real case: a mid dip ~600 Hz was first diagnosed as a λ/4 resonance of the box's tail (the math matched perfectly: 160 mm → 536 Hz), and an experiment **disproved** it — it was a cabin SBIR. The whole of Section 1 is about not repeating that mistake.

## 1. The "box vs boundary (SBIR)" separator — MANDATORY before touching hardware

Four cheap tests; none is sufficient alone, together they're a verdict:

1. **Clean nearfield** (mic right up against the cone): a box defect shows ALREADY here; SBIR almost vanishes at a true nearfield. ⚠️ Check the measurement really is nearfield — an "nf" at 10–20 cm already catches the boundaries.
2. **Distance sweep**: measure the same driver up close / 20 cm / 50 cm / LP. A dip that GROWS with distance = interference with a boundary (SBIR), not the box.
3. **Out-of-car**: take the structure out of the car (as far as the cable reaches). Flat outside the car + a dip inside the car = the cabin, full stop.
4. **Stuff/seal A/B**: change the box's damping (pack it tight / empty it / close the vent). The dip didn't budge = not the box. ⚠️ Do NOT change the resonator's LENGTH (don't block the neck) — that shifts the frequency and ruins the comparison; test damping at the EXISTING frequency. Mic — identical position.

**The traps that fooled us:**
- **L=R identical shape does NOT prove "the box":** the same external geometry of both pillars gives the same boundary notch on both sides.
- **The λ/4 math is seductive:** a match of the physical length with c/4f can be ACCIDENTAL. A match = a hypothesis, not a diagnosis — validate with the tests above.
- In an A/B, measure **both FR and IR/decay (CSD)**: the dip and the ringing are two faces of a resonance; the time domain directly shows the transient cleanup (= perceived "detail/air").

## 2. SBIR confirmed — find WHERE and WHOSE reflection

- **ETC from the impulse** (REW GUI; we hadn't used it for years — all the analysis sat on FR): a discrete arrival with a delay τ → Δd = τ·343 m → comb nulls at n·c/(2Δd). If the predicted nulls match the measured ones — the reflector is found by distance. (Case: arrival +2.25 ms → Δd≈77 cm → nulls 667/1111 Hz = measured 645/1.1k.)
- **Gate test**: gate out the IR down to ~1.5 ms → if the FR dip filled in, late reflections are to blame.
- **Source-side vs receiver-side** (decides whether moving the driver will help): **move the SOURCE, not the mic** — a spare driver in a temporary box across positions. The notch moves/vanishes with position = source-side (geometry cures it); it stays = receiver-side (a reflection near the ear — moving the driver is pointless). Bonus: an immediate audition of candidate positions.
- **An already-installed driver of the same model in another position** (e.g. the center) = free proof: if it's clean in the problem band — the position cures it.
- **POSITION dominates over AIM:** away from the near boundary (the windshield–dash corner) is the main thing; aiming up/sideways helps only ADDITIONALLY and only far from the boundary. Near the boundary, neither aim nor direction saves you.
- **An absorber as diagnostics:** a porous one works from ~λ/10 of thickness (600 Hz → 6–14 cm). A thin felt / 20 mm at 600 Hz ≈ zero effect → it'll give a false "not confirmed". For diagnostics — a pillow/blanket 10–15 cm tight to the boundary; a rigid SHIELD at an angle is even better (the notch will SHIFT in frequency = the point is found).

## 3. If it really is the box (resonance confirmed by A/B)

- λ/4 of a closed-open tube: f=c/4L; the VELOCITY antinode is at the open/vent end → a fibrous damper is most effective there.
- The cure = a dense fill of the whole volume + a controlled resistive vent (aperiodic), NOT "seal it tighter". A symptom hint: "an unsealed driver → flatter" = an under-damped sealed system.
- Wall ringing ≠ an air resonance: don't glue on CLD/damping speculatively. Walls produce narrow peaks/a long decay in the CSD, not broad dips. Rap test + press a palm under a tone.
- **Impedance measurement** (REW Impedance + a precision resistor / CLIO): a box resonance = an anomaly on the curve. A more objective and cheaper proof than the acoustic one.

## 4. After ANY physical change to the box/position

A full channel retune (XO/TA/EQ) + a check of the joint summation with the neighbors + the lateral. The old calibration for this channel is invalid (see `naming-and-structure` "is the raw data still valid").

## 5. An independent audit by a fresh model (a practice that paid off)

A cold-start audit by ANOTHER model (a sub-agent without our anchors) on the full measurement history found what we'd missed over 10+ rounds: an unused ETC, a progressive EQ regression of presence across versions, our own filter that deepened a cabin null. Method: give the raw data + the log + a direct mandate "challenge our conclusion, find what was missed", each point falsifiable. Run it on big reversals or when "we've already tried everything".

## 6. Regression across versions (the full history as a tool)

- **The defect's stability in the RAW measurements across all versions** = the verdict "physics vs DSP": it sits unchanged at a fixed frequency in all raw sets → install; it appeared/moves with a version → DSP.
- **Cumulative EQ drift**: cuts that accumulate across versions quietly slide the tone (case: presence v17 −2 → v29 −7 vs its own midline = "no air"). Periodically compare the current version's ALL with 2–3 older ones and with the target — not just with the previous one.
- **Check your own filters against the cabin map**: a filter derived from one set may cut INSIDE a cabin null on the LP (you deepen the hole yourself). A bypass test of the suspect ones — 2 minutes.
