# Test tracks for listening checks (ear-driven verification)

> 🧩 **PATTERN REPOSITORY — starting hypotheses, not rules.** A catalog of useful diagnostic tracks: **starting points** for ear checks, not a mandatory list. See [`knowledge-architecture.md`](references/core/knowledge-architecture.md).

A curated library with **diagnostic markers** — to verify hypotheses BY EAR where measurement is unreliable (cabin phase/GD = junk, diagnostic §10; depth/punch/integration/sibilants — ear-driven, staging-depth §7).

**Where the words live.** This file holds the **tracks** (library, number, artist, title, version) and, per
track × characteristic, only what is specific to that track — a timecode, a cue. The phrases that say how
a characteristic *sounds right* / *sounds wrong*, and the ordered routes (`first` · `short` · `full` ·
`league`), live in ONE place: [`listening-cheat-sheet.md`](listening-cheat-sheet.md) (ids `c01`…`c16`).
Tools read both files through `rew_tool/listening.py` by id; its selftest fails the suite on an id that
exists in one file and not the other. Do not repeat a *sounds right / wrong* phrase here.

## How to use this (workflow)
When you (Claude) have a **hypothesis to check by ear**:
1. Identify the **characteristic** (what you're testing): `c06` sub <40, `c05` the sub↔midbass seam, `c09` depth, `c07` sibilants, `c10` separation under load…
2. Look at the **links below** → pick a track that **exposes exactly this characteristic**.
3. Tell the Arbiter **specifically:** "play **[library + number + artist — title]**, listen at **[timecode if any]** — **[the cue]**. The question: **[sounds right] vs [sounds wrong]**?" (the two phrases from the cheat sheet). Streaming → give artist — title — the exact version, e.g. the MONO mix.
4. The Arbiter listens → states the result → that's your **reliable ear-metric** (instead of single-position phase). Record it the moment it is said: `process.py listening-verdict` (several pairs and the Arbiter's own words in one entry).

> Don't dump the whole list. Pick 1 (max 2) track targeted at the hypothesis and give a clear "what to listen for". One cue at a time.

## Which library does the user have? — establish FIRST (project data)

**Propose ONLY tracks the user can actually play.** Ask at intake which they have; store it in the project profile; **every track you name states its Library.**
- **A loaded compilation** — CarMus Test&Demo 2026 (`CarMus#NN`) · Chesky Ultimate Demo Disc (`Ch.NN`) · an EMMA / AYA competition disc (`competition.md`) · the mono set — cite the track by number **and** library.
- **Streaming** (Tidal / Spotify / Apple Music) — you can't cite a disc `#` blindly: give **Artist — Title — the exact version** you need (the **MONO** mix · a specific album / year / remaster), because masters differ and a **stereo copy silently breaks a mono-center test**. Confirm the user opened the right version before trusting the result.
- **None of the above** — the `own/*` rows: the user's own favourite tracks and a description of the material (deep bass · female vocal · acoustic guitar · dense rock · orchestra). The cheat sheet's words still apply; the cue is whatever the user knows in that track.

## Tracks

`version` matters for streaming (`the MONO mix`, a remaster); for a disc it is the disc. Library tags:
`CarMus` = CarMus Test&Demo 2026 (order easy → hard/heavy, "listen to music, not to sounds") · `Chesky` =
Ultimate Demo Disc, streaming (in each pair the even track is a narrator, the odd one the music) ·
`EMMA` = the competition discs (`competition.md`; the year matters, formats change between seasons) ·
`mono` = true MONO recordings (L = R) · `own` = the user's own material.

| id | library | number | artist | title | version |
|---|---|---|---|---|---|
| CarMus#01 | CarMus | 01 | Eternal Eclipse | Fate Of The Clockmaker | Test&Demo 2026 |
| CarMus#02 | CarMus | 02 | Preservation Hall Jazz Band | La Malanga | Test&Demo 2026 |
| CarMus#03 | CarMus | 03 | Felix Irwan | I Don't Want to Miss a Thing | Test&Demo 2026 |
| CarMus#04 | CarMus | 04 | Elvis Presley | Fever | Test&Demo 2026 |
| CarMus#05 | CarMus | 05 | Hank Shizzoe | Your Luck Will Find You | Test&Demo 2026 |
| CarMus#06 | CarMus | 06 | Jennifer Warnes | Invitation To the Blues | Test&Demo 2026 |
| CarMus#07 | CarMus | 07 | Melody Gardot | Over The Rainbow (Live) | Test&Demo 2026 |
| CarMus#08 | CarMus | 08 | Hayley Westenra | River Of Dreams | Test&Demo 2026 |
| CarMus#09 | CarMus | 09 | Alla Turovskaya | Sunny Bunny | Test&Demo 2026 |
| CarMus#10 | CarMus | 10 | Alexander Jean | Another One Bites The Dust | Test&Demo 2026 |
| CarMus#11 | CarMus | 11 | Quadro Nuevo | Nature Boy | Test&Demo 2026 |
| CarMus#12 | CarMus | 12 | Bradley Cooper | Out Of Time | Test&Demo 2026 |
| CarMus#13 | CarMus | 13 | Vahtang | Black Betty | Test&Demo 2026 |
| CarMus#14 | CarMus | 14 | Hanne Boel | House of the Rising Sun | Test&Demo 2026 |
| CarMus#15 | CarMus | 15 | Drum Ecstasy | Oh! Empie! | Test&Demo 2026 |
| CarMus#16 | CarMus | 16 | Domenico Loparco | Dock Funk | Test&Demo 2026 |
| CarMus#17 | CarMus | 17 | AC/DC | Back In Black | Test&Demo 2026 |
| CarMus#18 | CarMus | 18 | Greta Van Fleet | Highway Tune | Test&Demo 2026 |
| CarMus#19 | CarMus | 19 | San Di EGO | Stayin' Alive | Test&Demo 2026 |
| CarMus#20 | CarMus | 20 | Godsmack | Cryin' Like A Bitch! | Test&Demo 2026 |
| CarMus#21 | CarMus | 21 | Sons Of Texas | Feed The Need | Test&Demo 2026 |
| CarMus#22 | CarMus | 22 | Gus G | Enigma of Life | Test&Demo 2026 |
| CarMus#23 | CarMus | 23 | Hi-Finesse | Andromeda | Test&Demo 2026 |
| CarMus#24 | CarMus | 24 | Loud373 & VAGAN | Olgoi Khorkhoi | Test&Demo 2026 |
| CarMus#25 | CarMus | 25 | Rodg & Veljko Jovic | Sundust | Test&Demo 2026 |
| CarMus#26 | CarMus | 26 | Vadim Shantor | Devil Inside | Test&Demo 2026 |
| Ch.03 | Chesky | 03 | Rebecca Pidgeon | Spanish Harlem | Ultimate Demo Disc — High Resolution |
| Ch.05 | Chesky | 05 | Sara K. | If I Could Sing Your Blues | Ultimate Demo Disc — Depth |
| Ch.07 | Chesky | 07 | Leny Andrade | Maiden Voyage | Ultimate Demo Disc — Atmosphere |
| Ch.09 | Chesky | 09 | Livingston Taylor | Grandma's Hands | Ultimate Demo Disc — Midrange Purity |
| Ch.11 | Chesky | 11 | Ana Caram | Correnteza | Ultimate Demo Disc — Naturalness |
| Ch.13 | Chesky | 13 | Fred Hersch Trio | Played Twice | Ultimate Demo Disc — Transparency |
| Ch.15 | Chesky | 15 | McCoy Tyner / Joe Henderson | Ask Me Now | Ultimate Demo Disc — Presence |
| Ch.17 | Chesky | 17 | Monty Alexander | Sweet Georgia Brown | Ultimate Demo Disc — Visceral Impact |
| Ch.19 | Chesky | 19 | Johnny Frigo | I Love Paris | Ultimate Demo Disc — Rhythm & Pace |
| Ch.21 | Chesky | 21 | Connecticut Early Music Festival | Vivaldi — Flute Concerto in D | Ultimate Demo Disc — Focus |
| Ch.23 | Chesky | 23 | Westminster Choir | Britten — Festival Te Deum | Ultimate Demo Disc — Holographic Imaging |
| Ch.25 | Chesky | 25 | Solisti New York | Stravinsky — Royal March (L'Histoire du Soldat) | Ultimate Demo Disc — Transients |
| Ch.27 | Chesky | 27 | Chesky Sampler v2 | Double-bass solo | Ultimate Demo Disc — Bass Resonance |
| Ch.29 | Chesky | 29 | Chesky Sampler v2 | Drum solo | Ultimate Demo Disc — Dynamics |
| mono/merrill | mono | — | Helen Merrill | You'd Be So Nice to Come Home To | the MONO recording (Cole Porter; mono vocal jazz) |
| mono/byrds | mono | — | The Byrds | So You Want To Be A Rock 'N' Roll Star | the MONO mix (Younger Than Yesterday, 1967) |
| EMMA/positions | EMMA | 2026 tr.2–6 | — | Positions L / LC / C / RC / R — 5 instruments per position | EMMA 2026 disc |
| EMMA/focus | EMMA | 2026 tr.7–11 | — | Focus — image size hierarchy | EMMA 2026 disc |
| EMMA/moving | EMMA | 2026 tr.12 | — | Moving track — width / height / depth / room | EMMA 2026 disc |
| EMMA/T8 | EMMA | 2024 T8 | — | depth and body — the piano behind and below the singer (`competition.md`) | EMMA 2024 disc |
| EMMA/T9 | EMMA | 2024 T9 | — | Hungry Bird | EMMA 2024 disc |
| EMMA/T11 | EMMA | 2024 T11 | — | stage levels — snare vs tambourine, backing-vocal separation (`competition.md`) | EMMA 2024 disc |
| own/favourite | own | — | — | a favourite, well-known track of the user's | whatever they play it from |
| own/album | own | — | — | a familiar album for the long listen (acoustic + vocal material) | whatever they play it from |

## Links — what each track exposes, and where in it

One row per track × characteristic. `timecode` is mm:ss when the cue sits at a moment; `cue` is what to
listen for in THIS track — never the generic "sounds right / wrong" phrase, that is the cheat sheet's.

| track | characteristic | timecode | cue |
|---|---|---|---|
| CarMus#01 | c04 | — | the intro: scale, space, resolution, macrodynamics — the system's level right away |
| CarMus#01 | c11 | — | the macrodynamics of the intro |
| CarMus#02 | c04 | — | many instruments: resolution, timbres, balance |
| CarMus#02 | c10 | — | the instruments stay separate in the tutti |
| CarMus#03 | c14 | — | hits on the guitar body — recognisable as wood, not dry knocks or boomy rumble |
| CarMus#03 | c10 | — | the voice separated from the acoustic guitars |
| CarMus#04 | c10 | — | studio space and resolution at low level; do the finger snaps read? |
| CarMus#05 | c08 | — | a calm vocal — not nasal, not pressing, not anorexic |
| CarMus#05 | c07 | — | the treble range with body; guitars not lost among the cymbals; any blanket on the speakers? |
| CarMus#06 | c07 | — | sibilants; treble resolution and decays |
| CarMus#06 | c04 | — | evenness of the mids |
| CarMus#06 | c08 | — | the voice in the mids |
| CarMus#07 | c09 | — | depth and space — the stage behind the hood |
| CarMus#07 | c03 | — | the vocal holds its place and size |
| CarMus#07 | c14 | — | the double bass: droning or bloated vs thin; snaps and plucks |
| CarMus#07 | c10 | 2:00 | the singer's whispering under the double-bass solo — does it read? |
| CarMus#08 | c08 | — | a high bright vocal: cutters in the fundamentals and the upper mids |
| CarMus#08 | c03 | — | the vocal does not drift or change size on different notes |
| CarMus#09 | c14 | — | double-bass texture; a warm live piano, not an electric one |
| CarMus#09 | c08 | 1:20 | the flute — cutters? |
| CarMus#09 | c04 | — | balance without accents; a different mixing principle from #07/#08 |
| CarMus#10 | c11 | — | drive, dynamics, attack not smeared |
| CarMus#10 | c10 | — | acoustic guitars — hear the strings, not "strum-strum" |
| CarMus#10 | c14 | — | no boomy low end, no lower-mid pressure; LF density |
| CarMus#10 | c08 | — | vocal cutters |
| CarMus#11 | c14 | — | the double bass — bloated or losing fullness? |
| CarMus#11 | c04 | — | live instruments, naturalness, they play together |
| CarMus#11 | c08 | — | cutters in the mids |
| CarMus#12 | c10 | — | an acoustic guitar (live) vs an electric one through an amp — the separation is heard |
| CarMus#12 | c09 | — | a concert stage; the bass and the drummer separated from the hall |
| CarMus#13 | c10 | — | beatbox with overlaid effects — layers, not flat or monotonous |
| CarMus#14 | c09 | — | a large, spacious, cohesive stage — a full panorama, not ragged, not collapsed |
| CarMus#14 | c08 | — | a strained vocal exposes flaws |
| CarMus#14 | c14 | 2:20 | bass-guitar texture; the tambourine jingles from 2:20 |
| CarMus#15 | c10 | — | drums: separation and placement; micro-events under load |
| CarMus#15 | c11 | — | macrodynamics, rate of fire |
| CarMus#16 | c05 | — | two bass guitars — sub control and the midbass↔sub integration; the lower bass does not detach; the two basses separately, not mush |
| CarMus#17 | c12 | — | after the heavy ones: not thin? balance and readability |
| CarMus#17 | c08 | — | cutters, constriction |
| CarMus#18 | c11 | — | bright, on the edge: the snare cracks out, the kick with reverb does not get lost |
| CarMus#18 | c14 | — | the bass guitar growls springily; the guitars "wzh" |
| CarMus#19 | c12 | — | a contrast in recording style with #18 — a different atmosphere, not "the next one on the radio" |
| CarMus#20 | c05 | — | the kick drum: tight, into the chest like a pile; reads separately from the bass guitar and the guitar's low notes |
| CarMus#20 | c07 | — | clamped cymbals — not into foil, especially when a hit and a cymbal land together |
| CarMus#21 | c05 | — | the bass guitar does not get lost behind the kick |
| CarMus#21 | c10 | — | a heavy, compacted, still intelligible sound |
| CarMus#22 | c08 | — | does the electric guitar cut the ears? |
| CarMus#22 | c14 | — | the bass guitar springy vs thin |
| CarMus#22 | c07 | — | cymbals sustained vs "pssh" |
| CarMus#23 | c10 | — | epic, building up — an abundance of micro-events; a weak system turns boring or oppressive |
| CarMus#24 | c06 | — | sub below 40 Hz — holds vs dries up or bloats into droning |
| CarMus#25 | c05 | — | electro: hits in the sub↔midbass joint region, hypertrophied — subs often fall away here |
| CarMus#26 | c05 | — | the midbass: hit energy higher than #25 — tight and juicy in the chest vs limp, smeared, over-dried |
| Ch.03 | c10 | — | the voice breathes with space around it; the shaker behind — each shake different (alike = no resolution); the bass deep but detailed |
| Ch.05 | c09 | — | the trumpet 10 ft from the mic — the reference for depth; Sara close, the voice filling the studio; the guitar warm and intimate |
| Ch.07 | c09 | — | a warm spacious stage with the voice direct; the bass full; drums and cymbals ethereal |
| Ch.09 | c08 | — | the finger snaps live and bodily (snap your own to compare); the voice has chest volume, not detached from the body |
| Ch.11 | c04 | — | a rainforest that envelops you; the cello resonates; her breathing palpable; no electronic glint or harshness |
| Ch.13 | c11 | — | the piano percussive — the hammer's attack obvious; the pluck of the bass; the drums behind; cymbals airy |
| Ch.15 | c02 | — | the sax to the right of centre between the speakers; breathing, key mechanics; the echo from the back wall |
| Ch.17 | c11 | — | two drum kits, two basses, brass — the different acoustics of each kit; turn it up, you should feel it |
| Ch.19 | c11 | — | the transfer of energy: the foot taps the beat — no reaction means keep looking |
| Ch.21 | c03 | — | the outline of the flute on the stage — clear, not blurred |
| Ch.23 | c15 | — | 3D on two speakers; a sense of height; the scale of a cathedral; the organ's air is not tape hiss |
| Ch.23 | c16 | — | a low level with powerful organ peaks |
| Ch.25 | c11 | — | sharp level changes; drums tight and taut; brass sharp and clear |
| Ch.27 | c06 | — | the pluck, then the body resonance; non-musical sounds at the limit reveal a construction defect |
| Ch.27 | c14 | — | a double-bass solo three feet from the mic |
| Ch.29 | c16 | — | a drum solo growing louder and louder — a stress test at realistic levels, carefully |
| mono/merrill | c01 | — | a true mono vocal: one tight point at centre, at height |
| mono/byrds | c01 | — | a mono rock mix: the whole band in one point at centre |
| EMMA/positions | c02 | — | five instruments at each of L / LC / C / RC / R — each one small point; audible in several places = 0 points |
| EMMA/focus | c03 | — | the bass the biggest → guitar → banjo → vibraphone → the triangle the smallest |
| EMMA/moving | c15 | — | the moving guitar and cowbell: size does not change mid-flight; height at eye level; room via the echo |
| EMMA/T8 | c09 | — | the piano far behind and below the singer; the vocal wander is the recording's norm, not a defect |
| EMMA/T9 | c10 | 0:03 | the jaw harp 3–4 s on the right; voices by position |
| EMMA/T11 | c15 | 2:52 | the snare vs the tambourine at different stage levels |
| EMMA/T11 | c10 | 0:46 | backing vocals separated across the stage (also 1:25, 2:00) |
| own/favourite | c04 | — | your own track: the first impression, no verdict |
| own/album | c13 | — | a familiar album, relaxed, 15–20 minutes — does it stay easy or tire you, and which way |

## Gate selection — a test that cannot fail is not a gate

- **A mono/centred gate is NOT sensitive enough to catch an L/R level overshoot — pan-extreme tests are.** A reviewer prescribed band-passed mono pink as the decisive gate for whether a far-side level change was legitimate compensation. It **passed** (image dead centre, periodic and random) while the very same state **failed** the pan test — the right-centre image overshot the reference. Mono sums both sides at the centre, where a symmetric error cancels; asymmetry only shows at the pan extremes. **For any per-side level decision, gate on a PAN track judged against a same-session reference track, not on mono centring.**
- **Gate a centre/fill level on an AMPLITUDE-PANNED track, not on natural stereo.** A statically summed L+R centre never goes silent on extreme pans, so a dash-mounted centre adds a centre component to *every* position and pulls panned images inward. On natural stereo the interchannel phase/time differences keep the summed component subordinate — which is why the defect stayed invisible for months of choir-based attestation. A five-position amplitude-panned set exposed it immediately (images collapsed inward at +3.0, correct at +2.0).
- **A moving-source track beats a static one for asymmetry.** Where a source traverses the stage (or jumps between fixed positions), the diagnostic is not *where* it is but what happens to it **on the way**: size must not change mid-flight, brightness must not step down on one half, height must hold. A one-sided HF cut shows up here before it shows up on static imaging tracks.
- **When a source jumps rather than glides, separate the author's intent from the system's error.** The jumps themselves, their count and their order are the recording. What the system owns is how far apart the positions land, whether each is a point or a smear, whether timbre holds position-to-position. Read the class from the failure shape: **all positions shifted one way by a similar amount = level**; **positions blurred or doubled rather than moved = phase/time**; **position correlating with the source's PITCH across jumps = a narrowband defect**.

## Disc identity — the number is not the track

Regional compilations borrow the category names of a well-known test disc while carrying **different music**, and numbering does not transfer between volumes or between disc and streaming. One build ran on an "AYA compilation #3" whose numbering matched the official Stockfisch discs on **zero** of four checked tracks; the same programme was later found on a streaming release under a different number again.

Consequences to design around:
- **Always cite `LIBRARY #N + artist — title`** in any listening gate. A gate citing a bare number breaks silently the day the disc or the source changes, and you cannot tell from the record whether it ever pointed where you think.
- **Ask and log the user's actual tracks; never infer content from the number** — not from the official disc's listing, not from a web search.
- **Verify the track↔criterion mapping from the ORIGINAL disc description, not a translated one.** A machine translation turned the German `Höhe` (stage height, scored in the imaging block) into "pitch", and a whole session's height gates then ran on a bass-pan track and a balance track while the judge scored height on an entirely different one — 3.5 points that no listening test was targeting.
