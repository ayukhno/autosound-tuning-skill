# Competition prep (EMMA / AYA / CARMusic) — criteria, tracks, diagnostics

> 🧩 **PATTERN REPOSITORY — starting hypotheses, not rules.** Techniques here are "in similar conditions this often worked": **starting points**, validated by measurement/ear. (Format judging criteria are hard constraints, not hypotheses.) See [`knowledge-architecture.md`](file:///skills/autosound-tuning/references/core/knowledge-architecture.md).

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
- **Equal-loudness:** for a tone to sound equally loud, a lower one needs MORE SPL (40 Hz ≈ +6 dB over 55 at a moderate level; at loud — less). A flat SPL → the low end sounds quieter. **Check the track's real frequency (web) BEFORE EQ-ing it "flat".**
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
