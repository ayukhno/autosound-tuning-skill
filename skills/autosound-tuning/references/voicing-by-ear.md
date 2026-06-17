# Voicing by ear — symptom→fix + curve→character (Phase 6, client preferences)

An applied base for by-ear voicing: when the base is technically correct (Phases 0–3), and you need to **tune the character to the client's taste** (Phase 6) or quickly translate an ear complaint into an EQ move. Sources: the installer "Arkadij Avtozvuk's" experience + Peter/pssound + curve→character. ⚠️ **These are by-ear heuristics (starting directions), not dogma** — judge every move by ear, verify on your own system; the numbers are approximate.
> ⚠️ **If a tip here CONTRADICTS our measurements/conclusions — don't discard it, keep it as a VARIANT.** A different geometry/cabin/situation can make it right, and an unexpected tip sometimes unlocks a solution (proven in a real session — a contradictory move gave the way out). Mark "(variant — conflicts with X, try when Y)", don't delete.

## Tonal balance — how to read it
- **Bass <100 Hz — read it as is; mids up to 1.5k — by the upper peaks; treble >1.5k — by the average.** (Consistent with the anchor methods, `diagnostic §1`.)
- **Equal-loudness:** quiet → you need more bass+treble; loud → less. The voicing is calibrated to the listening level (`staging-depth §3`).
- Align the midbass↔mid joint where **L and R (w and m) are equal and level at 400–500 Hz** — otherwise the stage is crooked.
- After EQ corrections near the crossovers — **re-check the delays**.

## Curve → character (choosing for the client's taste)
| Curve | Character | For whom |
|---|---|---|
| **Audiofrog** | natural/neutral, slightly warm; ~−1dB/oct after 100 | reference/SQ start |
| **ResoNix Accurate** | almost a reference, a touch warmer than Audiofrog | SQ start/calibration |
| **ATF** | very flat, a slight tilt, studio — can be "thin" | reference, like on monitors |
| **Harman** | universal, +3dB@100, roll-off to −6dB@10k | any music, "headphone-like" |
| **Jazzi** | soft/airy, a rise at 100–200 and 8–10k, "creamy" wide stage | jazz/soul/vocal |
| **Jazzi v2** | less low end, more mids, better vocal articulation | SQ with a vocal accent |
| **EPY** | a Harman/Jazzi hybrid, dense/natural | vocal/acoustic |
| **JBL** | brighter/more aggressive, presence 3–5k — can fatigue | pop/guitar/female vocal |
| **Whitledge** | warm/dense, **strongly raised bass** (a big low-end presence), a soft top | someone who deliberately wants a bass-forward "live" sound — rock/blues |
| **Half Whitledge** | the same warm character, **the bass rise ~half as much** → closer to neutral/the target, lighter/faster | "Whitledge warmth without the heavy bass"; **the default for "enjoyment without a bass bias"** (not just "without a sub") |
| **ResoNix Laid-Back** | calm, a roll-off after 2k, "blanket-like" | long trips/jazz |
| **RAW-Cat** | dense/bassy, −10dB to 1k, dark/massive | fun/EDM/hip-hop |

**See/compare the curves visually:** **https://nonotuningtool.com/** — enter the house curve + crossovers → it shows the shape (the per-channel Nono targets are generated there too, `process-phases.md` step 5b). **Give the user the LINK, don't pile on explanations.** The curves have authors (ResoNix — Nick, Audiofrog — Wehmeyer…) → keep the attribution.
> For a taste of "enjoyment without a bass bias" leaning toward Whitledge warmth — start with **Half Whitledge** (closer to the target), not full Whitledge; the full one — only when a heavy low end is deliberately requested. *(by-ear, a variant — not dogma.)*

**The taste-audit method:** flatten the system (±1 dB) → apply each curve in turn as an EQ profile → listen to a familiar track (e.g. Diana Krall "Temptation" = vocal+bass · Dire Straits "Private Investigations" = stage+dynamics · Daft Punk "Giorgio by Moroder" = electro+impulse) → compare depth/density/brightness. The client chooses → that's their voicing preset.

## Taste axes → EQ move
- **"Drier" (lighter/faster):** sub+midbass ↓, mid(~1.5k)+treble ↑. **"Fuller":** sub+midbass ↑, mid ↓, don't touch the treble.
- **Stage height (given vertical phasing):** RAISE = dry the bass + raise the treble; LAY it on the dash = raise the bass + lower the treble.
- **Voice closer/farther:** level 0.8–1.7k (higher=closer); push back = 1.2–1.4k −2–3 dB, bring forward = raise it.
- **"Crystalline":** EQ >16k +6–8; 10–12.5–15k ↑ (peak at 12.5); a step 3→4k = crystalline-ness/sparkle (good at medium volume, cuts at loud). **A softer top:** treble level, reduce (but keep) the 3→4k step.
- The stage is more affected by **delays at the lower frequencies + levels at the higher ones**.

## Symptom → fix (by-ear)
**Bass:**
- Punch / "in the chest": a 40 Hz hump on the sub above the lower ones (up to +10) = punchy not boomy; to add — 160 Hz +3–4 wider (not on all); **punch without shifting the stage — 160 Hz only on the RIGHT midbass** (it localizes by phase → level barely moves the image).
- Boom/droning: a double bass droning 80–100 → −2 dB; a midbass hump 100–105 (doors) Q2 −5–6 (BUT it loses "meat" — raising the treble masks the boom); a sub hump 40/50 — remove by ear.
- "Dry the bass, keep the voice full": PK 90 Hz Q1.2–1.5 −3.
- A flabby sub: 20–30 ↓, 40 ↑. A double bass sounding like a bass guitar → add sub; if it drones → sub −.
- [Peter] the bass rise for SQ ≤ 3 dB/oct from 200 Hz.
**Voice:**
- 200–500 Hz **level AND equal L/R (FR+phase)** → removes notes drifting across the stage (sometimes a crossover at 500).
- Nasal → too much upper bass, 300–400 a touch ↓; full/enveloping — 200 ↑ (only with a good install). Dry/weightless — 400–600 ↑.
- Liveliness/breath — 2–2.5k ↑ (a small hump at 2.5k = an accent on the breaths). Female-voice openness — 1.6–2k. Female voice forward — 3k ↑ (too much → electric guitars cut).
- Sibilants: "sh/ch" 4–5k; "s/z/ts" 8–9k (the mid's peak) and 12.5k.
**L/R symmetry by the voice (200–300 Hz, when the mic can't):** nasal → take off the LEFT (don't touch the right); too high/light → raise the RIGHT; to gather to center → left ↓ + right ↑ by the same amount.
- With equal delays — attenuate the left per band so the image is in front of the driver (≤3 dB; at least to unstick it from the pillar).
**Top/cymbals:** a flat 4–10k plateau = cymbals have body (treble +6 above the mid); 4k — the base of cymbals (detail, but sibilants wander); 12.5/14k — detail + embellished sibilants; "harsh top + sub" → raise the tweeters' crossover frequency + level, suppress 12.5k.

## Joint/filters (by-ear, Arkadij)
- Between mid and tweeter — **Bessel is better than LR** (air/depth); lots of treble emphasizes the bass.
- A 2nd-order APF on the right midbass at the joint frequency — to even out the L+R summation dip without EQ distortion.
- Lots of treble + you want a less emphasized bass → from BW to LR + raise the treble.

## Rear / rear-fill (envelopment, NOT a rear image)
The rear's goal in SQ = the **illusion of a bigger stage** (wider than the dash, deeper than the windshield) — diffuse *envelopment*, not a rear localization. So the rear is **not done "like the mids" (full-range)** — full-range = a different goal (a rear image) + "without the right position/processing it only hurts" (Crutchfield/F150/JDPower).

**The matrix — two schools (both valid):**
- **Differential L−R (Peter/Hafler — the default for SQ):** Rear L = 50%L−50%R (delay ~690 cm), Rear R = 50%R−50%L = −Rear L (~640 cm). L−R = the difference signal = ambience/reverb/width; **the mono center (L=R) cancels → it physically does NOT go to the rear** → the vocal/center is guaranteed to be IN FRONT (no risk of "voice behind" — no need to check). r-L=−r-R (anti-phase) → maximally diffuse/non-localizable. Consequence: **the rear's L/R balance doesn't matter** (the measured L/R difference = door acoustics, not content → don't EQ-match to it).
- **Mono sum L+R (Wehmeyer — a variant):** both rears = (L+R)/2. Simpler, a general fill, doesn't create a rear stereo image; BUT it duplicates the center behind → the vocal MAY run backward → judge with the rear on that the voice is in front.

**Band / level / delay:**
- **HPF high, above the boom zone:** bass at the rear only muddies the front + conflicts with the sub, and gives nothing spatially (bass is non-directional). ~**300–315 BW24/LR4** typically; raise it more for weak rear doors (real, P2: HP120→315 killed the rear-door boom 130–160 from 55→24 dB).
- **LPF ~4–5k:** the top at the rear localizes more easily (gives away the speakers) → cut it. `off` is left only for full envelopment with quality rears. The actual tilt ~−15 dB/oct from 400.
- Level **quiet** + delay = TA distance + ~8–10 ms (Haas, "it vanishes behind").
