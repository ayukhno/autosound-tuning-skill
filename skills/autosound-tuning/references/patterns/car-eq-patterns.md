# Common acoustic problems and EQ in car audio

> 🧩 **PATTERN REPOSITORY — starting hypotheses, not rules.** Everything here is "in similar conditions this often worked": a **starting point**, validated by measurement/ear, never a mandate. See [`knowledge-architecture.md`](file:///skills/autosound-tuning/references/core/knowledge-architecture.md).

> ⚠️ **These are starting heuristics** — typical patterns and ballpark ranges from practice, not dogma. Validate every move by measurement (peak-vs-null `diagnostic §2`, mic-shift `§13`) and by ear; tune the numbers to the system. A SPECIFIC car's anomalies → the project profile (`autosound_context.md`), not this file. Which channel is the "hotter" side depends on LHD/RHD and geometry — the examples below are written from an LHD cabin.

## The main principle: transparency = minimum processing

> "The fewer EQ points it takes to reach the target curve, the more 'air' stays in the system."

**Rule for dips:**
- Narrow deep dips (< 5 dB wide) are phase cancellation. **Don't raise EQ!** The amp burns power, but no sound appears.
- Wide shallow dips > 10 dB — you can carefully raise them, up to +4..6 dB at most.

**Rule for peaks:**
- Peaks — cut them. A cut is always better than a boost.
- Narrow peaks (Q > 4) — a sharp notch filter.
- Broad rises — a gentle correction or a shelf.

---

## Judge deviations by AUDIBILITY, not by the trace — catch what the ear hears, leave what it doesn't

This is a whole-spectrum, both-scales discipline, not a rule about any one band. The same idea plays
out in the **bass, mids, and highs**, and at both the **macro** scale (a broad tilt/offset across a
region) and the **micro** scale (a single narrow feature). The numbers in the examples below are
**illustrations, not targets** — in another car the same case sits at a different frequency and width.
The job is never "flatten the trace"; it is **match what the ear actually weights to the target, and
don't touch what it doesn't.** Two opposite ways to fail — both are "not listening to what matters":

**Fail A — MISS an audible deviation (under-correct).** The ear hears a deviation by **how wide** it
is, not by its peak dB. A **broad tilt/offset from target** (macro) hides in plain sight: it isn't a
peak, it barely moves RMS, and it sounds fine in a 30-second A/B — then tires you on a long listen. It
can live anywhere: a warm lower-mid hump, a shy or bloated bass shelf, a forward presence tilt, a
rolled or hot top octave. **To catch it, integrate the deviation over half-decade bands vs the target**
(`analysis-playbook.md`) instead of reading peak dB / RMS — a trace can be a "good" 1.5 dB RMS and
still be **voiced wrong** because the residual that matters is the slope, not the wiggles.

**Fail B — OVERCORRECT what the ear ignores or that can't be fixed (kills transparency/liveliness).**
The opposite sin, and the more damaging one: EQ-ing narrow features the ear doesn't weight, or that
aren't even electrically fixable — **phase-cancellation dips** (boosting burns amp power for no sound),
**off-axis / dispersion dips** the mic sees but the ear doesn't (`analysis-playbook.md` RTA-dip≠heard-
dip), **single-mic HF comb**, narrow reflection notches. Chasing these flat makes the sound **dry,
clinical, dead** — it strips the air/liveliness. This is the "transparency = minimum processing" rule
above: the fewer points it takes to reach the target, the more life stays in. **When unsure whether a
feature is audible-and-correctable, leave it** — a small honest deviation beats a filter that kills the
sound.

**The weighting, in one line:** weight every deviation by **audibility = bandwidth × region-the-ear-
cares-about × is-it-minimum-phase-correctable × dispersion context** — not by dB and not by how ugly
the trace looks. Broad beats narrow at equal dB; a correctable broad tilt beats an uncorrectable narrow
null; a region the ear leans on (presence, vocal band) beats one it doesn't (deep sub, extreme air).

**Worked example of Fail A — the over-EQ ⇄ mud seesaw (read the Hz as an instance, not the rule).**
Automated RTA-driven high-Q cuts in the lower mids (here ~80–300 Hz) over-tame cabin reflections and
**strip body/"meat"** → dry, clinical, hollow (upright bass loses woody resonance, a female voice loses
chest register). The right instinct is to **relax those cuts ~2–4 dB** (wide Q, minimal depth unless a
peak is truly severe) — but **relaxing by ear to restore body overshoots easily** into a broad hump
that now rides *above* target: fine in the moment, muddy/tiring after 20 minutes. So the relax is only
half the job: **relax for body, then re-check the band-integrated level vs target** so you don't tilt
into fatigue. (In a bright car the mirror case is relaxing HF cuts into a fatiguing presence tilt — same
seesaw, different band.) This is why the DONE gate needs the broadband-vs-target scan
(`phase_3_control.md §2`) and the ear pass needs a long/fatigue listen (`phase_4_listening.md`) — the
error shows up as fatigue, not as a peak, so a spot-check / RTA-flat chase / peak-RMS read walks past it.

> **Field evidence (Passat B8 · Jazzi) — one instance, not the general number.** Ear-relaxed lower-mid
> cuts to cure dryness (correct move) overshot to **+1.5 dB over Jazzi across a broad 160–630 Hz** — a
> macro tilt. It sounded fine at the moment but muddy/tiring on a long listen; the overall 1.5 dB RMS
> "looked done," and a peak/narrow read passed it. Caught only by integrating deviation-vs-target per
> band. Fix = gentle tilt down over the hump + up over the light midbass (~2 dB swing around the pivot),
> re-fit level, confirm by ear on vocals + kick — **wide and small, never narrow and deep.**

---

## Tweeter (HF)

### Typical problems

**Peak 7–9 kHz (more often on the right channel)**
- Cause: reflection off the windshield
- Symptom: "spitting" or "graininess" on cymbals, images pull to the right
- Fix: PK 7500–8500 Hz, −4..−6 dB, Q=3–4

**Peak at 12–16 kHz**
- Cause: the tweeter's natural response or a reflection
- Fix: HSF (High Shelf) 11000–13000 Hz, −3..−4 dB, Q=1–1.5
- **Don't touch above 10 kHz with narrow filters** — it sounds worse than the problem

**L/R asymmetry in the treble:**
- The right one (closer to the glass) is almost always brighter
- Compensation: an HSF on the right channel, or a lower gain on the right tweeter
- Never compensate with different crossover types/orders!

### Treble transparency

"Transparency" isn't the amount of treble — it's the absence of phase trash in the 2–5 kHz region.

If the airiness vanished after EQ:
1. Disable all filters above 5 kHz on both channels
2. If the airiness came back — you found the cause
3. Gently lower the tweeter level via Gain, without engaging EQ

---

## Midrange (mid) in a pod

### Typical problems

**Peak 2–3 kHz (pod resonance or a reflection off the glass)**
- The most common problem
- Symptom: "shoutiness", "harshness" on female vocals
- Diagnosis: does the peak change when you loosen the driver's mounting → if yes, it's enclosure vibration; if no → cabin acoustics
- Fix: PK 2300–2500 Hz, −5..−7 dB, Q=4–5

**Cone break-up (4–5 kHz)**
- A mechanical resonance of the cone
- Fix: PK 4500–5000 Hz, −3..−5 dB, Q=6–8
- If the crossover already cuts here — it may not be needed

**Dip 600 Hz – 1 kHz**
- Phase cancellation from a dash/glass reflection
- **DON'T TOUCH** — raising EQ won't help, it'll only muddy the sound

**Peak 150–300 Hz (small-pod resonance)**
- The driver plays into a closed volume → the air's compliance raises Fs
- Fix: PK 200–250 Hz, −3..−4 dB, Q=1.5–2, or LSF (Low Shelf)

### Cause of the peak: why a pod "rings"

**Standing wave:** if the internal diameter ≈ λ/2 at the problem frequency → resonance. For 2.5 kHz, λ ≈ 13 cm → risk when ∅ > 6 cm.

**Refraction:** the wave from the pod's edge returns in phase at a certain frequency → a peak that doesn't depend on venting or stuffing.

**Enclosure vibration:** a stiff material (PETG CF, carbon) → little damping → the driver's basket resonates with the enclosure. Fix: rubber washers under the driver's mounting.

---

## Midbass in the doors

### Typical problems

**Peak 150–250 Hz (door resonance)**
- The most widespread problem
- Symptom: "boomy", "cardboard" bass, a "drone" on vocals
- Fix: PK 180–230 Hz, −4..−6 dB, Q=2–3

**Dip 120–180 Hz (door-card antiresonance)**
- Phase cancellation
- **DON'T RAISE** — it's closed with the right delays, paired with the sub

**Excess energy 500–1000 Hz (the midbass "sings" with the voice)**
- Symptom: the voice "splits", part of the sound comes from the doors
- Fix: HSF (High Shelf) 400–450 Hz, −4..−6 dB, Q=0.7 → helps the crossover cut faster
- Or an extra PK 700–900 Hz, −4 dB, Q=4

**Principle: the midbass plays only bass**
Play the midbass alone, with no other drivers. If you can make out the song's lyrics — the midbass plays too high. Apply EQ and an HSF until you no longer hear the lyrics from it.

### Midbass linearization strategy

1. Set the crossovers (LR4 HP 80 Hz, LR4 LP 300 Hz)
2. MMM measurement, left and right separately
3. Auto EQ in REW, limit the range to 60–400 Hz
4. Keep only the **negative** filters (remove the peaks)
5. Add an HSF 400–450 Hz, −4..−5 dB for the "extra cut"
6. Dips in the 120–180 Hz region → ignore

---

## Subwoofer in a sedan

### Sub enclosure types (general; a specific car's numbers go in the profile, from MEASUREMENT)

Choosing the enclosure is **not only acoustics**: also the install + **local roadworthiness-inspection legality** (German TÜV/HU — cutting/modifying the body may fail it).

- **Sealed / Closed Box:** the trapped air = a spring that **damps/controls** the cone's motion → tight start-stop, accurate bass; a ~12 dB/oct roll-off below Fb, gentle; rides on the cabin gain; tolerant of the driver. **The SQ/control workhorse.** A subsonic is desirable, not critical.
- **Ported / Bass-Reflex:** the port adds output near Fb (louder/SPL, more efficient), but a ~24 dB/oct roll-off below Fb + worse group delay/transient; **below Fb the driver UNLOADS → a subsonic is MANDATORY**; possible port noise. Less "tightness" than a sealed box.
- **Infinite Baffle (IB):** the driver on a **baffle** (the rear deck / a sealed trunk wall), with **the trunk = a large non-restrictive volume**. **The golden rule — 100% isolation:** the front and rear waves must NOT mix (otherwise an acoustic short → loss of bass) → you must **seal the trunk↔cabin boundary** (cut/seal the deck) → **invasive + an inspection risk (TÜV)**. It needs an **IB-suitable driver (free-air Qts >0.6)** — a low-Qts one (<0.4) gets "sloppy". **Less control than a sealed box** (no air spring; especially at volume — sealed is tighter on peaks); but it's efficient, deep, without boxy coloration, and saves space. **A subsonic/infrasonic filter is MANDATORY** (no compliance filtering → infrasound → bottoming). At moderate levels a well-built IB ≈ a sealed box for SQ; the difference at volume favors the sealed box. *(NOT an unconditional "SQ favorite".)*
- **Cabin gain (all types):** the cabin lifts the low end downward — this is **real output**, don't flatten it blindly (detail ↓ "Room Gain").
- **Midbass control** — also a sealed box / sealed-and-treated doors (a door = a "leaky" quasi-IB). IB is a **sub** topology, not for the midbass.

⚠️ **A specific car's number** (e.g. "sealed ~35 L → +10–15 dB <50 Hz") goes in THAT car's profile, from **measurement**, NOT inherited from another project.

### Room Gain (cabin reinforcement)

A sedan cabin adds +10..15 dB below 50 Hz. That's normal.

**Rule:** in a sedan the sub should be **+4..6 dB** louder than the midbasses on the final FR (a psychoacoustic norm for cars).

### Typical problems

**Peak 35–50 Hz (cabin resonance)**
- Symptom: "droning" in the bass region, the sound is "heavy" and slow
- Fix: PK at the resonant frequency, −5..−8 dB, Q=3–5

**Dip 60–80 Hz (standing waves or anti-phase from the rear deck)**
- **DON'T RAISE EQ** — it's closed with the right delays with the midbass
- If you raise EQ → the amp overheats, the bass goes "cottony"

**The sub "pulls" from behind (localization)**
- Cause: the sub plays too high (above 70 Hz) or the delays are wrong
- Fix: lower the LP to 60–63 Hz; check the phase (invert 180°); set the delays

### Sub integration algorithm

1. LP: 60–63 Hz, LR4 or BW4
2. Subsonic (HP): 15–20 Hz, BW 12 dB/oct (for a sealed box)
3. EQ: remove the resonance peaks (notch)
4. HSF at the top: 85–125 Hz, −4..−6 dB — extra "tail" cut
5. **Phase:** after setting the crossovers and delays — try 0° and 180°, listen for where the bass "jumps" onto the hood
6. **Delays:** measure the physical distance with a tape measure, enter it into the DSP, then a final correction by ear

### BE4 for the sub/midbass joint

Bessel at the joint gives a "cohesive" and articulate bass:
- Sub LP: BE4, 45–50 Hz
- Midbass HP: BE4, 65–75 Hz (higher than the sub LP!)
- Check the phase: 0° or 180° on the sub
- After switching from LR4 you may need a micro-correction of the delays

---

## Target curves (house curve)

> **There is NO default curve — the choice is made WITH the user** for their genres/taste/purpose: the **curve→character** table + the audition method → `voicing-by-ear.md`; the principle "a curve = a start, not a finish" → `naming-and-structure.md §6`. Below — just the anatomy of two examples, to understand the structure.

### RAW-Cat (Andy Wehmeyer)

**Philosophy:** "Don't touch what isn't in the way." Leaves more of the drivers' natural energy.

**Structure:**
- Up to 60–80 Hz: a +8..12 dB rise (low-bass support)
- 80–300 Hz: a gentle roll-off (−6..−8 dB across the span)
- 300 Hz – 3 kHz: a slight downward tilt (−0.5..1 dB/octave) — keeps the "body" of the sound
- Above 3–5 kHz: a gentle High Shelf roll-off (−2..−4 dB)

**Character vs ResoNix Accurate** (an example of how curves DIFFER by taste, not by "correctness"): Accurate is flatter in the lower mids 300–500 Hz — more accurate, but it can sound "thinner"; RAW-Cat leaves more "body" to vocals/instruments — warmer, but darker. Which one fits — the client decides by ear.

### Harman In-Car

- A scientifically grounded curve
- A slight bass rise, a 2–4 kHz dip for comfort, level treble
- A universal "headphone-like" candidate

### How to apply it on the Virtual Layer

On your DSP's virtual/group EQ layer (Helix: the Virtual EQ tab; any DSP with a layer above the per-driver crossovers — `diagnostic §6`):

```
Low Shelf: 80–100 Hz, +6..8 dB — bass lift
Tilt EQ: a broad tilt for the overall character
High Shelf: 5 kHz, −2..−4 dB — remove harshness
```

Never try to apply the House Curve through the crossovers or the Output EQ — it will break the phase joints.

---

## Measurements: when and which

| Method | When to use | In REW |
|---|---|---|
| **MMM** (Moving Mic) | Main FR, House Curve | SPL → an averaged measurement with mic movement |
| **Sweep** (single point) | Time Alignment, polarity, phase | Measure → SPL&Phase → fixed mic |
| **RTA** | Quick assessment, level control | RTA → Octave/3rd-octave smoothing |
| **THD** | Gain check, finding clipping | RTA → Show THD |
| **Impulse Response** | Time Alignment, polarity | Automatically from Sweep |

**Smoothing for analysis:**
- 1/6 or 1/3 octave — the overall curve shape
- Psychoacoustic — what the brain actually hears (ignores narrow peaks)
- 1/48 — detailed resonance diagnosis (but not for making EQ decisions)

**Don't flatten the small ripples visible at 1/48** — what the mic sees, the ear often ignores. Chasing narrow peaks/dips from reflections "kills" the liveliness of the sound.

---

## A specific car's anomalies → the project profile

Persistent cabin anomalies (diffraction dips, phase gaps, SBIR notches, anti-correlated zones) are **project state**, not a general pattern: they live in the project's `autosound_context.md` profile (§4/§6) — and, de-identified, in `knowledge/cars/<body>.md` (the worked example: `knowledge/cars/vw-passat-b8-sedan.md` PART B, **verify-only**) — and are NOT re-diagnosed every session. **Don't carry one car's specific Hz onto another** (even a platform sibling — `SKILL.md → knowledge/cars`). Here — only the transferable techniques below.

### Under-lapping — the general principle

Under-lapping = deliberately spreading the LP and HP to opposite sides of a problem region.

```
Normal crossover (LR4):    Midbass LP 300 Hz ←──→ Mid HP 300 Hz
Under-lapping:             Midbass LP 250 Hz      Mid HP 350 Hz
                                          ↕ dip 250–350 Hz
                                          (a deliberate "hole")
```

**When to use it:**
- Micro-delays don't close the phase gap between adjacent channels
- There's a geometrically/acoustically driven phase gap in a certain range
- A dip in the "hole" region — an acceptable price for removing the phase conflict

**Trade-off:** a small dip in the sum in the under-lap region (example: ~250–350 Hz). Check it on the summed FR and listen — if the dip isn't noticeable subjectively, the decision is right.

### Aligning to the IR peak (heavy midbasses — a transferable technique) — ⚠️ a Phase-1/2b TA technique, NOT a baseline/pre-sweep step

A heavy driver (example: the GZNK 165SQ-K in the Passat). When aligning to the "nose" (onset) of the IR:
- The cone is only starting to move → the acoustic energy hasn't arrived yet
- The stage "collapses" — the upper tier doesn't hold

**Rule for heavy midbasses:** align to **100% of the amplitude peak** of the IR, not to the onset (the nose). By ear it gives punch and instrument body on the dash.

### Vertical stage elevate after a presence recess (2-step) — a transferable technique

A deep **presence recess** (−2…−4 dB on the mids, e.g. to push the singer behind the glass) also **lowers the perceived stage height**. Restore height with a **symmetric СЧ+ВЧ level lift, in TWO steps**:
- **+1.5 dB** first (mids and tweeters, L=R);
- **+1 dB more** *after* the per-band EQ is finished to target (elevate the final shape, not a work-in-progress).

By ear this lifts the stage back toward eye level **without** collapsing the depth the recess bought. Field-proven (EMMA/Passat).

### Physical baseline priority — don't APF door woofers for local cabin anomalies — a transferable technique

Fixing a **local door/cabin reflection** on a door woofer with an **all-pass filter (APF)** broke the soundstage — loss of focus and acoustic fatigue (real case: `w-L` APF ~159 Hz). A simple **notch** plus **physical phase symmetry** (Normal polarity, no APF) was subjectively far more stable. **Rule:** reach for a notch + physical symmetry before electrical phase tricks on the midbass. *(The VCP-over-Output placement for narrow high-Q junction cuts lives in `phase_2_eq.md §2a`.)*
