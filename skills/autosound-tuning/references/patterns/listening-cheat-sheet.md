# Listening cheat sheet — the words for what you hear, and where each one goes

> 🧩 **PATTERN REPOSITORY — and the ONE home of the listening vocabulary.** A one-page sheet for the
> listener, meant to be open on a phone or in a TCC panel while a track plays. Every phrase that says
> how a characteristic *sounds right* or *sounds wrong* lives in the table below and nowhere else:
> [`test-tracks.md`](test-tracks.md) holds the tracks and, per track × characteristic, only what is
> specific to that track (a timecode, a cue); a route is an ordered list of such pairs. Tools read all
> three through `rew_tool/listening.py`, by the ids in the first columns — so the ids are the seam,
> and a changed id breaks the suite, not the panel in the car. Translations
> (`listening-cheat-sheet.<lang>.md`) carry the same ids with the text in that language. Agreed with
> the author 2026-08-25.

## Before any track — three things the session must know

1. **Which library you actually have.** Every track named in a listening check carries its library
   (`CarMus #NN` · `Chesky Ch.NN` · `EMMA` / `AYA` disc · the mono set · streaming with the exact
   version). A bare track number is not a track. If you have none of the known libraries, say so:
   the session then works from **your own favourite tracks** and from a description of the material
   (deep bass · female vocal · acoustic guitar · dense rock · orchestra) instead.
2. **What "was" means for you.** Comparing with the previous tune is possible only if you came in
   with one (its slot was kept at intake) — or on a second pass of Phase 4, where "was" is the
   first pass. A tune built from nothing has no "was".
3. **What you compare against.** Tuning for yourself: A/B with the previous tune is worth doing, the
   slot is next to you. Tuning for competition: compare with a **reference** — your own experience, a
   good home system, or the prize-winning cars you have sat in. Sound itself cannot be remembered
   for long; **remember the emotion** the reference gave you and compare the emotion, not the
   detail (the author's own practice; a better recipe is welcome).

## First listen — hear your system before any verdict (5 minutes)

Right after the technical lock, before the formal pass — the `first` route below:

1. **One favourite, well-known track of yours.** No verdict — this is you meeting the system.
2. **A real mono track from streaming** (`mono/merrill` or `mono/byrds` in `test-tracks.md`). One
   question: **where is the image?** A tight point at the centre, at dash height, that does not
   drift — that is the centre of the stage, and it is the first real achievement to take home.
3. **`CarMus#01`** (if you have it): scale, space, resolution, macrodynamics — "the system's level
   right away".

Then go for a drive. Listening tires; the passes below are **meant to be split into short
sittings** — listen, drive, come back, listen again. Ears reset on the road.

## Characteristics — the vocabulary

`label` is the short form for a menu; `name` the full one. `sounds right` and `sounds wrong` are two
free-standing phrases, written to be dropped into a sentence. `route` is the step of the method a ✗
goes to (desk 1.3 = the joints, 1.4 = levels, 2.1 = the coarse EQ, 3.3 = the fine EQ over MMM). A
characteristic marked `next league` is not for the first pass.

| id | label | name | sounds right | sounds wrong | where a ✗ goes |
|---|---|---|---|---|---|
| c01 | mono centre | Mono centre — the L/R foundation | a tight point at the centre, at height, that stays put | smeared, wanders left or right, wide, or changes place with the note | the foundation: L/R level, arrival, polarity (desk 1.3 / 1.4) — never imaging EQ |
| c02 | positions | Positions L · LC · C · RC · R | each instrument is one point in its own place | positions squeezed towards the centre, or two share a place | L/R levels; crossover slopes in the mid overlap (1.2 / 1.4) |
| c03 | focus | Focus and image size | a size hierarchy — the bass biggest, the triangle smallest; a vocal keeps its size across notes | every image the same size; a vocal grows or drifts on some notes | the mid↔tweeter joint (1.3); levels (1.4) |
| c04 | balance | Tonal balance | instruments play together, nothing sticks out, no blanket over the speakers | thin, thick or muddy, bright or shouty, a blanket over the speakers | a broad tilt against the MMM target (3.3); a harsh band gets one surgical cut (3.3) |
| c05 | punch / seam | Punch and the sub↔midbass seam | the hit lands in the chest, the sub does not fall away under it, two basses read separately | limp, smeared, over-dried, the low bass detaches from the kick, or mush | the sub↔midbass joint (1.3); L/R midbass 100–200 Hz (1.3) |
| c06 | sub <40 | Sub below 40 Hz | holds, controlled, still musical at the limit | drones, dries up, or makes non-musical noises at the limit | sub low-pass and level (1.2 / 1.4); driver protection |
| c07 | top / sibilants | Top and sibilants | "s" and "sh" natural, neither detaching nor vanishing; cymbals a sustained shimmer | sibilants detach or disappear; cymbals like chewed foil or a dull "pssh" | surgical cuts in the virtual layer (3.3); the mid↔tweeter joint (1.3) |
| c08 | voice cutters | Voice — cutters in the mids | a natural voice with chest and no pressure | drills the ears, presses, or sounds anorexic with no body | the cutter's own band (3.3) — not the foundation |
| c09 | depth | Depth and space | the stage behind the hood, layers read, a whisper under a solo still reads | a flat picture with everything forward | the mid↔tweeter joint (1.3), or a top hotter than the bass (3.3) |
| c10 | separation | Separation under load | micro-events stay separate when the mix is dense | mush, boring, or oppressive | usually too much EQ — remove some (2.1 / 3.3); rarely a joint (1.3) |
| c11 | attack | Attack and transients | the start of a hit is crisp, drums taut | starts smeared, drums soft | amplifier and driver control, not EQ; the midbass↔mid joint (1.3) |
| c12 | universality | Universality across recordings | different recordings sound different | "the next one on the radio" — everything alike | a tilt, or EQ overreach (3.3) |
| c13 | long listen | The long listen — an album, 15–20 min, relaxed | stays easy and inviting | tires you: thick, bright or dark (a tilt), or dead, dry, clinical (over-correction) | a tilt → a broad tilt against MMM, never narrow notches; dead → remove EQ, do not add (3.3) |
| c14 | LF texture | Low-frequency texture — the double bass | springy, with body and detail | bloated, boomy, or dried out and thin | levels and the sub↔midbass seam (1.3 / 1.4); a broad tilt (3.3) |
| c15 | height / width | Stage height and width — next league | the stage sits at dash height and reaches past the A-pillars with clean edges | drops to the floor on some notes, or the edges are ragged and the stage collapses | the mid↔tweeter joint (1.3); L/R levels (1.4) — a second visit to Phase 4 |
| c16 | dynamics | Dynamics at volume — headroom | quiet to loud without strain, peaks stay clean | peaks squash or distort, the sound closes up as it gets loud | gain structure and driver limits — not EQ; the protection filters (1.2) |

Order matters: **c01 – c03 first.** If the centre or the positions fail, the rest is too early to
judge.

## Routes — ordered pairs of track and characteristic

A route is just an order. The words come from the table above; where to listen in the track comes
from its link row in `test-tracks.md`. `first` is the five-minute meeting; `short` fits one sitting
between drives; `full` is for closing or before a competition, split over several sittings, with the
long listen as its own drive.

| route | # | track | characteristic |
|---|---|---|---|
| first | 1 | own/favourite | c04 |
| first | 2 | mono/merrill | c01 |
| first | 3 | CarMus#01 | c04 |
| short | 1 | mono/merrill | c01 |
| short | 2 | CarMus#02 | c04 |
| short | 3 | CarMus#26 | c05 |
| short | 4 | CarMus#06 | c07 |
| full | 1 | mono/merrill | c01 |
| full | 2 | EMMA/positions | c02 |
| full | 3 | CarMus#07 | c03 |
| full | 4 | CarMus#02 | c04 |
| full | 5 | CarMus#26 | c05 |
| full | 6 | CarMus#25 | c05 |
| full | 7 | CarMus#24 | c06 |
| full | 8 | CarMus#06 | c07 |
| full | 9 | CarMus#08 | c08 |
| full | 10 | CarMus#07 | c09 |
| full | 11 | CarMus#15 | c10 |
| full | 12 | CarMus#10 | c11 |
| full | 13 | CarMus#17 | c12 |
| full | 14 | CarMus#11 | c14 |
| full | 15 | own/album | c13 |
| league | 1 | Ch.23 | c15 |
| league | 2 | Ch.05 | c09 |
| league | 3 | Ch.29 | c16 |

## How to report what you hear

Say the characteristic, the direction, and the track: *"CarMus#07 — the double bass bloats; the
vocal holds"* — that is a full report. Binary is fine: 🟢 / ❌ per pair. The session records every
verdict in the project journal the moment it is said (`process.py listening-verdict`, several pairs
and your own words in one entry, stamped with the ledger version you were listening to), and routes
every ❌ to its step; most fixes are made at the desk from the solos already captured — a new
capture is needed only when the hardware or the install changed. Looking back is a filter over the
journal: all verdicts for one track or one characteristic, across versions.
