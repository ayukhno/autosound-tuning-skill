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
- **Impedance measurement** (REW Impedance + a precision resistor / CLIO): a box resonance = an anomaly on the curve. A more objective and cheaper proof than the acoustic one. A built sealed box reads ONE peak at Fc; `Fc/Fs=Qtc/Qts` confirms it's airtight (a leak lowers/broadens it). Full method (T/S extraction, the trust map, DVC, enclosure QC, what impedance can't see) → `impedance-ts.md`.

## 4. After ANY physical change to the box/position

A full channel retune (XO/TA/EQ) + a check of the joint summation with the neighbors + the lateral. The old calibration for this channel is invalid (see `naming-and-structure` "is the raw data still valid").

## 4b. Near-field vs in-car: separating the driver from the cabin (2026-08-20)

The cheapest decomposition in the whole method, and it settles arguments that otherwise
run for months. **One near-field capture per driver (7–15 cm, on axis, pointed at the
cone) beside the in-car capture from the listening position.** Near-field is dominated by
direct sound by 20+ dB, so it measures the DRIVER; the difference between the two is what
the cabin does to it. Level is not comparable between them — normalise at a band where
both are well behaved (40–80 Hz for a woofer) and read the SHAPE.

Worked example, and the reason to bother (VW Passat B8, door woofers):

- **Near-field: the two door woofers are a matched pair** — 1.55 dB RMS apart over
  40 Hz–2 kHz once a 1.8 dB level difference is removed. Nothing wrong with either driver.
- **In-car minus near-field**, normalised at 40–80 Hz: the **near** door (beside the
  listening position) runs **+9.9 dB at 100 Hz, +6.3 at 125, −8.9 at 160** — nineteen
  decibels of swing inside half an octave; the **far** door is flat at the bottom and
  **shelved down 9–19 dB from 250 Hz up** (−19 at 400).

Two identical drivers, mirrored placement, one cabin, and acoustically they are not the
same instrument. **This is why a stereo-minded auto-tuner finds no consistent solution on
some cars** — the two channels it expects to be each other's mirror are different systems.
Measure it before spending a session trying to match them.

**Corollary for the enclosure question:** if near-field in the car ≈ near-field outside the
car, the pod and its damping are exonerated and the argument is over. Measured on the same
car: every soft-material treatment (mat, ring, wadding in the tail) moved the mid's
near-field response by **0.23–0.27 dB RMS** — i.e. nothing. What DID move it was hard
geometry: removing the mid's grille gained **+4.1 dB at 7.7 kHz**, and removing the
tweeter's A-pillar cover dropped raggedness **1.94 → 1.43 dB RMS** with up to **7.1 dB at
3.25 kHz**. The install damage lives in the first few centimetres, and it lands on the
tweeter far harder than on the mid — the trim edges are comparable to a tweeter's
wavelength and small against a mid's.

⚠️ One car, and the near-field captures were hand-held. Shape and raggedness are
trustworthy at that quality; absolute levels are not. Treat the numbers as the shape of
the effect, not as constants.

**Opening a sealed pod is a trade, not a gain.** Same car: a pod opened with a hole gained
**+4 dB at 250–315 Hz and lost 10 dB at 125** — rear radiation escaping and subtracting.
It also makes excursion worse where it matters: less output for the same cone motion below
200 Hz. And the ceiling of any enlargement is fixed by the driver: with free-air Fs 110 Hz
and 195 Hz installed, `Vas/Vb = 2.14`, so doubling the volume buys Fc 158 Hz and an
infinite sealed volume buys 110 Hz — all of it near and below Fc, i.e. below where a mid is
usually crossed. **Decide it with an impedance sweep, not by ear**: one clean peak below
the old Fc means the new volume works as a sealed box; a smeared or double peak means the
cavity is coupled to the cabin and you built a vent.

## 5. An independent audit by a fresh model (a practice that paid off)

A cold-start audit by ANOTHER model (a sub-agent without our anchors) on the full measurement history found what we'd missed over 10+ rounds: an unused ETC, a progressive EQ regression of presence across versions, our own filter that deepened a cabin null. Method: give the raw data + the log + a direct mandate "challenge our conclusion, find what was missed", each point falsifiable. Run it on big reversals or when "we've already tried everything".

## 6. Regression across versions (the full history as a tool)

- **The defect's stability in the RAW measurements across all versions** = the verdict "physics vs DSP": it sits unchanged at a fixed frequency in all raw sets → install; it appeared/moves with a version → DSP.
- **Cumulative EQ drift**: cuts that accumulate across versions quietly slide the tone (case: presence v17 −2 → v29 −7 vs its own midline = "no air"). Periodically compare the current version's ALL with 2–3 older ones and with the target — not just with the previous one.
- **Check your own filters against the cabin map**: a filter derived from one set may cut INSIDE a cabin null on the LP (you deepen the hole yourself). A bypass test of the suspect ones — 2 minutes.
