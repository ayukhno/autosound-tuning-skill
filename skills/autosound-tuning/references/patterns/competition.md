# Competition prep (EMMA / AYA / CARMusic) — criteria, tracks, diagnostics

> 🧩 **PATTERN REPOSITORY — starting hypotheses, not rules.** Techniques here are "in similar conditions this often worked": **starting points**, validated by measurement/ear. (Format judging criteria are hard constraints, not hypotheses.) See [`knowledge-architecture.md`](references/core/knowledge-architecture.md).

The context when the user is preparing for judging (not just "enjoyment"). Formats: **EMMA**, **AYA**, **CARMusic** — related SQ protocols. Categories: **SQ** (sound quality), **SQL** (SQ+loudness), **SPL** (loudness). In a car context, any of these abbreviations + a format name = a strong trigger.

## Imaging diagnostics via a test track (instrument→frequency)
Judging tracks play known instruments at known stage positions. If an instrument **drifts sideways** from its position → that frequency band is **hotter on that side**. This is a quick map of L/R imbalance by band (it complements the solo measurement `m-L − m-R`).

### EMMA 2024 — the position test track (the year matters, the format changes between seasons)
**5 positions:** Left · Right · Center · Left-Center (LC) · Right-Center (RC). C/LC/RC score more precisely than L/R.
**The order of instruments at each position:**
| # | Instrument | Frequencies | DSP channel |
|---|---|---|---|
| 1 | Electronic Bass | 40–100 Hz | sub + midbass |
| 2 | Electronic Guitar | 100–250 Hz | midbass |
| 3 | Flute | 250 Hz–1 kHz | midbass(250–300) + mid(300–1k) |
| 4 | Celesta | 1–2 kHz | mid |
| 5 | Triangle | 2–4 kHz (+harmonics >20k) | mid + tweeter |
**Reading:** an instrument on LC drifts FURTHER LEFT → that band is L-hot; on RC drifts FURTHER RIGHT → R-hot. (E.g.: the celesta on LC to the left = m-L hot 1–2k; the triangle on RC to the right = the right TWEETER SKIRT 2.5–3.5k is hot — check the skirt below the crossover, not just the passband.)

> ⏳ **Track library (being filled — the user provides names/descriptions of EMMA 2021/2024/2026 + AYA):**
> - AYA `03-TIEFBASS` — Young Jeezy "Put On" (deep-bass levels, see below)
> - AYA `22-RAUM` — Mozart, Die Zauberflöte (Drottningholm Palace) — an opera hall, the reference for HALL depth+layering+vocal body
> - *(add the rest of the descriptions as they come in)*
>
> **The general listening-test track library with markers + a measure→track index → `references/patterns/test-tracks.md`** (CarMus Test&Demo 2026 entered: sub<40 #24, sub↔midbass joint #25/#16, punch #26/#20, depth #07/#14, sibilants #06…). For ear-driven hypothesis verification.

## AYA "Authentic Audio Check" — a category system (a diagnostic frame)
AYA (Are You Authentic, ayasound.org + Stockfisch-Records) rates a system **BY CATEGORIES — each track isolates one measure.** The official SACD (19 tracks) — audiophile Stockfisch recordings; **the category scheme (German terms) is the transferable diagnostic frame**, regardless of the specific track:
| Track(s) | Category | What it rates (→ tuning measure) |
|---|---|---|
| 01 | L/R Channel | a basic L/R check/routing |
| 02 | Level Setting | the reference level |
| 03-04 | **Tiefbass** | deep bass (extension/control <40–50) → sub |
| 05 · 06 | **Bass** (06=Bass/Stage Height) | bass + stage height → midbass/sub |
| 07-08 | **Grundton** | foundation/body (lower-mid) → midbass↔mid |
| 09-10 | **Mittelton** | mids → mid |
| 11-12 | **Hochton** | top → tweeter |
| 13-14 | Balance | tonal/L-R balance |
| 15 | **Raum** (Width/Depth) | stage width+DEPTH → staging-depth |
| 16 | Focus | image focus |
| 17 | Height | stage height |
| 18-19 | Fine Dynamics | microdynamics |
> ⚠️ **Regional AYA-style discs borrow the CATEGORY NAMES** (TIEFBASS, RAUM…) **with DIFFERENT tracks.** The user's disc (`03-TIEFBASS`=Young Jeezy "Put On", `22-RAUM`=Mozart) is NOT the official Stockfisch (which has 19 tracks, other performers). What transfers is the **category→measure**, not the specific track. The user's specific tracks — ask/log, don't assume from the number.

## EMMA 2024 — music tracks (official descriptions)
EMMA judges **4 sections of tonal accuracy: Subbass · Midbass · Midrange · Highs** + imaging/staging (positions, depth, levels, separation) + dynamics. The 2024 music tracks (official description, tracks 8–11):

- **Track 8 "Auf den Flügeln des Gesangs"** (a Japanese opera singer + grand piano) — judge the **mid+treble**. Calm/melancholy, lots of dynamics (from 1:16 an unbalanced system overloads). In Japanese until 0:57, then German. The piano is in a large room, with **great DEPTH — far behind and slightly BELOW the singer**. The vocal is **NOT fixed in the center — it periodically wanders slightly L/R** (the recording's intent, NOT a defect!). Listen: naturalness of the voice + the **body of the piano**; the voice clean/powerful without harshness.
- **Track 9 "Hungry Bird"** (jazz, many instruments) — **ALL 4 sections**; the separation should be perfect. Bass: hear separately the electric bass / the lower notes of the piano (Yamaha C7) / the tuba (the start). Imaging: **3–4 s** a jaw harp on the right (2 tones, 2 close positions); **0:28–0:34** flute+harpsichord+piano in unison; the clarinet (chorus) right-center, the flute left-center; the electric guitar left-center+hall; female voice center (chorus L→R); **38 s** a male voice a bit to the left and BEHIND the female; **the kick drum is NOT punchy — soft/deep**.
- **Track 10 "Carrero"** (latino, percussion, male voice) — all 4 sections. **0:10–0:15** an organ pans L→right-center; **the male voice is always center, IN FRONT** of the others; backing vocals (10) scattered L→R; the electric guitar (distorted) **far behind** right-center..right; percussion+piano clean/fast; the e-bass soft/big.
- **Track 11 "Mama Nature"** (soul/rock) — all 4 sections + **spectral balance**. The drums punchy; the female voice center; the e-bass deep/wider; voice/choir never harsh/distorted; **0:46/1:25/2:00** backing vocals clearly separated across the whole stage L→R; **2:52 a snare and a tambourine — at DIFFERENT STAGE LEVELS** (height/depth).

> Files: `Documents/home/EMMA2024musicfiles/` (Flac96/WAV/MP3) + `LeitfadenSoundQuality1.1_UA.pdf` (the EMMA judging guide, UA) — pull the rating method from it if needed.

## TIEFBASS / deep-bass criterion — equal-loudness and the SQ↔SPL fork
- Deep-bass tracks have a foundation **below the test tones**: e.g. "Put On" — content at **25–35 Hz** (the deepest note ~16), whereas the level check plays 40–55 Hz.
- **Equal-loudness:** for a tone to sound equally loud, a lower one needs MORE SPL (40 Hz ≈ +6 dB over 55 at a moderate level; at loud — less). A flat SPL → the low end sounds quieter. **Check the track's real frequency (web) BEFORE EQ-ing it "flat".** → compute the per-frequency sub targets on your **actual listening-level** contour with [`rew_tool/equal_loudness.py`](rew_tool/equal_loudness.py) (anchor to one measured freq+SPL; realize cut-only + master up).
- **Judges rate the reproduction/authority of the deep notes, not literal equal loudness** (at 25 Hz the ear is nearly deaf — that's physics, all systems are quieter there).
- **The SQ↔SPL voicing fork:** for pure SQ the subsonic is tamed (less boom); for the deep-bass category — it's left/grown for extension. These are different **presets**, not one compromise. Dial the level/extension on the track itself (the track = the reference), at the judged loudness.

## Voicing for judging
- The foundation (Phases 0–1: crossovers/TA/polarity/L-R) is **curve-agnostic** — done once, held across targets.
- The competition voicing = a **separate preset** (the virtual layer), forked from the fixed base. Keep BOTH (the SQ-accurate + the competition/depth one) → an on-the-spot A/B with fresh ears, pick for the category/day.
- **A preset — for a SPECIFIC format, because the rules differ → the techniques can be mutually exclusive.** Example (by-practice): **crossfeed L↔R** (blending the opposite channel into the front to stabilize the stage) — applicable for **EMMA**, but **NEVER for AYA** (there natural width/separation is prized). The full preset strategy (SQ/FULL/SQL/surround/source + per-ruleset) → `references/core/preset-strategy.md`.
- ⚠️ **After switching a preset at a competition — check that the DSP input = the LISTENING source** (in this car — the **OPTICAL S/PDIF**, not RCA; RCA is only for sweep measurements). Switching a preset can reset the input to another card (BT/USB) → no/wrong sound. The most annoying loss of points.

## EMMA 2026 — the test-disc structure (SQ Judgebook 2026; the user's summary, the original on the EMMA site + NotebookLM)

> A big change vs 2024: the technical tracks are CLEARLY split by purpose (positions ≠ focus ≠ stage — separate tracks), the music material is more complex.

**Track 1 (Intro):** the first impression. The voice BIG, exactly center → a group of trumpets/instruments. Fast, clean, full.
**Tracks 2-3:** the integrity of the L/R channels.
**Tracks 2-6 — POSITIONS (positions only: L/LC/C/RC/R).** At each position, 5 instruments in turn: Electronic Bass (20–500 Hz) · Electronic Guitar (60–1200) · Banjo (160–5500) · Vibraphone (200–5000) · Triangle (2k–20k). The criterion: each instrument = ONE small point; "smeared"/audible in several places = 0 points.
**Tracks 7-11 — FOCUS (size only).** A hierarchy of sizes: the bass the BIGGEST → the guitar smaller → the banjo smaller still → the vibraphone small → the triangle the SMALLEST. Clear, within the stage.
**Track 12 — MOVING TRACK (stage: width/height/depth/room).** Stable: drums, flute, shaker, gong, trumpet, organ, piano. Moving: muted guitar + cowbell. Criteria: distance = the nearest instrument behind the windshield; height = eye/horizon level; room information via echo/reverb.
**Tracks 13-16 — TONALITY:**
- **13 "Ocean Drive"** — bass integration. 0:18 the rhythm section (the bass clear, controlled, NOT masking the mids); 0:40 female voices weave in, NOT taking the central focus.
- **14 "One Fine Day"** — vocal realism/microdynamics. 0:29 the vocal (clearly center, slightly in front of the instruments); 0:39 the bass tight, without "droning".
- **15 "Coming Back to You"** — a deep male vocal clean, without coloration; backing vocalists L and R of the soloist, the choir behind.
- **16 "Should Have Done it Like This"** — dynamics. 2:03 the choir = a test of treble clarity + width; 2:23 a trumpet (LC) and a guitar (RC) clearly SEPARATED.
**Spectral balance:** track 16 at a normal volume, then **+6 dB** — distortion/compression at loud = minus points.
**Track 17 (Zero Bit):** silence — no hiss/hum/crackle/fans (engine off).

**The guide's tip:** each instrument in the music tracks — naturally and separately, without affecting the others.

## Process rules earned at events

- **Changes to the competition preset inside 72 hours of the start need same-day measured attestation — or revert.** One build entered an ear-only filter two days before an event; it turned out to be innocent, but that was established **after** the event by calculation, when it should have been established before it by measurement.
- **Every listening verdict — yours, a judge's, a guest's — is recorded with the master volume position.** Two guest observations on one build were both tied to a level that nobody wrote down, which made it impossible afterwards to separate a balance problem from level-dependent degradation.
- **The same defect can be worth zero points in one ruleset and real points in another — check every ruleset the event runs.** One card had no standalone bass-image-height criterion (a perfect positional score while the bass image sat on the dash), so height looked free to trade away; another rulebook scores stage height on a moving track, deducting per instrument not at horizon level **at any position**, and scores height and positions separately — so a height↔position trade costs on both sides. For a combined event, resolve the trade rather than assuming the laxer ruleset.
- **Cross-validate the ledger's open risks against the judge's card after every event — it is a free external test of the process.** On one build the judge independently confirmed five items that were already open in the ledger. Keep the open-risk list explicit so this check is possible.
- **Judges calibrate the listening level with a meter** (one association's setup disc specifies 74 dB(A) / 84 dB), and publish stage-height references (dashboard height or slightly above for stereo; mirror triangles or half A-pillar height for mono per side). Recover these numbers from the official setup material rather than guessing them.

## The AYA "Sound Tracks" competition disc — 31 tracks, category by category

⚠️ **Index only — the audio is not here and is not ours to pass on.** Buy the disc from AYA. This table exists so a gate can cite a track unambiguously and so you can tell which measure a number is scoring; it does not replace owning it. Other AYA-branded volumes number differently (§ the disc-identity warning above) — check the category in the filename, not the number alone.

| # | Category | Programme |
|---|---|---|
| 01 | LEFT RIGHT Check | channel identity |
| 02 · 28 | PINKNOISE STEREO | level setting / reference |
| 03 | **TIEFBASS** | Young Jezzy — Put On |
| 04 | **BASS** | Brother Culture ft Anthony B — Champion Sound |
| 05 | **BASS** | Christine and the Queen — Christine |
| 06 | **GRUNDTON** | Nothern Lite — My Pain (Piano Session) |
| 07 | **GRUNDTON** | Sophie Zelmani — Free Now |
| 08 | **SYMMETRIE** Bass/Grundton | Petra Magoni, Ferruccio Spinetti — Roxanne (Live) |
| 09 | **MITTELTON** | Henning May, Amilli — Bang Bang |
| 10 | **MITTELTON** | Birdy — Skinny Love (Live at the Tabernacle) |
| 11 | **HOCHTON** | Balladeire — Who's that Girl & Irgendwie Irgendwo Irgendwann |
| 12 | **HOCHTON** | Percussion-Ensemble — Improvisation |
| 13 | **SYMMETRIE** Mittelton/Hochton | Tracy Chapman — Give me one Reason |
| 14 | **AUSGEWOGENHEIT** (balance) | Antoine Villoutreix — Berlin |
| 15 | **AUSGEWOGENHEIT** | Haelos — DUST |
| 16 | **TRANSPARENZ** | Henning May, Amilli — Bang Bang |
| 17 | **TRANSPARENZ** | Emeli Sande — Read All About It, Pt. III |
| 18 | **AUFLÖSUNG** Bass (resolution) | Glowal — Cries |
| 19 | **AUFLÖSUNG** Grundton/Mittelton | AIR — All I Need |
| 20 | **AUFLÖSUNG** Hochton | Percussion-Ensemble — Glockenspiel |
| 21 | **HÖHE** (stage height) | Yazoo — Ode to Boy — the scored passage is **0:50–1:23** |
| 22 | **RAUM** (width + depth) | Mozart, Die Zauberflöte — Eine schreckliche Nacht (Drottningholm Palace) |
| 23-27 | **FOKUS** C · LC · RC · L · R | Daft Punk — Giorgio by Moroder, one position per track |
| 29 | **DYNAMIK** | Ane Brun — Big In Japan (Live) |
| 30 | **DIFFERENZIERUNG** | WhoMadeWho — Ember |
| 31 | **SOUVERÄNITÄT** | Portishead — Roads |

Note the pairs: the same ensemble appears at **#12 (HOCHTON — tonal)** and **#20 (AUFLÖSUNG-HOCHTON — resolution)**, and the same song at **#09 (MITTELTON)** and **#16 (TRANSPARENZ)**. Same material, different question — don't carry a verdict from one to the other.

### Reading a FOKUS set (23-27)
Five tracks, one amplitude-panned position each. This is the gate that catches a centre/fill channel pulling panned images inward — see `test-tracks.md`. Judge them as a set: LC and RC must sit between C and the outer positions, not collapse toward the middle.

### Reading an AUFLÖSUNG (resolution) track — what the category actually asks
Measured from the #20 audio (45 note onsets, per-note dominant partial and inter-channel level), because "the bells jump around and I can't find the pattern" is the normal first reaction:

- **Pan spread across the track is wide** — about 27 dB peak to peak. The jumping is the recording.
- **Pitch does not predict position** (r = −0.13 over 45 notes). It is a percussion *ensemble* spread across the stage, not one instrument whose bars map left-to-right. Looking for a pitch→position rule is looking for something that is not there.
- **Some pitches are pinned to one place and return to it exactly** — several repeat within 0.1–0.9 dB of inter-channel level. **These are the anchors:** in the car they must not wander between repeats, because in the file there is nothing to wander.
- **Other pitches appear on BOTH sides**, up to ~17 dB apart across repeats — two similar-toned instruments placed opposite each other. **This is the resolution test proper:** can the system keep them apart as two objects in two places, or do they fuse into one smeared object near the middle?

So a resolution track is judged in two passes: anchors must hold still, and same-pitch pairs must stay separable. Neither is a localisation question, which is why a resolution track can pass an imaging gate and still score badly.
