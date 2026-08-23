# REW API quirks (localhost:4735) — empirically verified

Gotchas when driving the REW API over Python/urllib (REW 5.40 Beta 126, API 0.9.4). `rew_tool/` already encodes these correctly — this file exists so a fresh session doesn't re-derive them or re-introduce a bug after a refactor.

## Encoding & endpoints
- **Data is BIG-ENDIAN float32** (`struct.unpack('>'+n+'f', ...)`). Little-endian (`<f`) returns garbage that grows ~×4 per step. Applies to magnitude / phase / IR / GD. `rew_tool/rew_api.py` decodes correctly.
- **FR endpoint:** `/measurements/{id}/frequency-response` → keys `magnitude`, `phase` (RTA measurements have **no** phase; sweeps do). Not `/spl`.
- **Two frequency spacings — handle both or RTA crashes.** Log-sweeps return `ppo` (points-per-octave) + `startFreq` → `freq[i] = startFreq·2^(i/ppo)`. RTA / linear measurements return **`freqStep`** + `startFreq` → `freq[i] = startFreq + i·freqStep` (no `ppo`). Assuming `ppo` only → `KeyError` on every RTA pull. `rew_tool/rew_api.py:freq_axis()` picks the right one.
- **IR:** data is under key `data` (not `impulseResponse`). Timing reference is the **`startTime`/`delay`** field — read it, don't reconstruct timing from the array (it's junk; see "Timing" below). **GD:** values under key `magnitude` (not `groupDelay`).
- **IR is PEAK-NORMALISED by default — ask for `?normalised=false` whenever level matters** (verified REW 5.40 β132 / API 0.9.6, 2026-08-19). `GET /measurements/{id}/impulse-response` returns every IR with its peak at exactly ±1.0 (unit `percent`, but of the peak, not of full scale), so two channels' IRs carry NO level relation — a sub's IR peak really sits ~18 dB under a woofer's, and any summation / gain-balance built on the default arrays is built on wrong levels (this bit the 2026-08-18 Resonalyze cross-check harness). `?normalised=false` returns the raw IR in **percent of full scale** (`/100` → fraction of FS); `?unit=dBFS&normalised=false` gives the same in dBFS directly. ⚠️ `?unit=dBFS` WITHOUT `normalised=false` is a display scaling (values in −1..0) that does NOT reduce to peak dBFS by any simple rule — don't reconstruct from it. Also `?windowed=true` (windowed IR) and `?samplerate=` (resampled) exist.
- **Two REW export routes, two different formats — and one of them MUTATES the measurement** (verified 2026-08-19, REW 5.40 β132; real files in `autosound-measurements/cars/…/rew-export-samples/`). `File → Export → Impulse response as text` (normalise off, window off, headers on) is the only export that carries the absolute time base: its header states `Start time (seconds)` alongside `Peak value before normalisation` (the **interpolated** peak, ~0.002 dB above the largest sample), `Peak index`, `Response length`, `Sample interval` and `Data offset (dB)` = the SPL offset; the samples are fractions of full scale, identical to the API's `?normalised=false`. The **WAV** export carries no timing at all unless you tick **`Place t=0 at sample index N`** — then REW cuts the head so t = 0 lands on sample N exactly. ⚠️ But a WAV can only place t = 0 on a WHOLE sample, and that export **snaps the measurement's own start time to the sample grid**: `m-L_01`'s start moved from −0.997093402 s (t = 0 at 95720.967) to −0.997093750 s (95721.000) the moment it was exported that way. For sub-sample timing use the text export or the API, and do not assume a session's start times survive a WAV export unchanged.
- **REW's IR grid is anchored on the mic-IR PEAK, not on t = 0.** The served array puts the peak on an integer sample (index 96000 = 1.000 s at 96 kHz, `startTime` chosen accordingly), so the loopback reference t = 0 (`startTime`·−fs) usually falls at a **fractional** index (e.g. 95629.073). Placing several channels on one grid by rounding costs up to 0.5 sample (5 µs = 1.8 mm at 96 kHz); shift by the fraction (FFT phase ramp) when sub-sample timing matters — `rew_tool/resonalyze_ir.py` does. REW's own `delay` is its interpolated peak time (also fractional). The IR is as long as the sweep (256k sweep → 262144 samples), with the peak 1 s in and the Farina harmonic images in the pre-roll before it. `GET /measure/sweep/configuration` reports the CURRENT sweep settings (start/end Hz, length "256k"…), not a stored measurement's — the measurement object gives `startFreq`/`endFreq` only.
- **Address measurements by NAME, never by numeric index/position.** `get_measurements` returns a dict keyed by REW's ordinal (`"1"`,`"15"`,…) — that index→measurement mapping is **NOT stable across calls** (REW reorders; a sort / delete / new sweep reshuffles it). Reusing `ms['15']` from an earlier call attaches the WRONG data to a channel → a real bug (m-R data pulled under the `m-L` label → a spurious "inverted"/swapped result). **Resolve the target by matching the `title`** (the channel name, e.g. `m-L_01 (sw)`) — or the stable `uuid` — **immediately before each pull**; never cache/reuse a numeric index. This is the skill's "**the name is the only stable identity**" hygiene (`naming-and-structure §3a`) — it binds the **model's API access**, not just the user's GUI discipline. → use **`rew_api.find_measurement_id(name)` / `get_measurement_by_name(name)`** (resolve fresh; they RAISE on an ambiguous or missing title so a wrong-channel pull can't pass silently) — don't hand-roll an index lookup.

## Writing filters
- **`set_filters` takes ONE filter per call** (PUT an object, not an array): `{'index':1,'type':'PK','enabled':True,'isAuto':False,'frequency':X,'gaindB':Y,'q':Z}`. An array → `400 "must have index"`.
- The gain field is **`gaindB`**, not `gain` — using `gain` silently sets 0 dB.
- **A whole bank can go in ONE call:** `POST /measurements/{id}/filters {"filters": [...]}` → `"Filters set"` (verified 2026-07-28). The per-filter `PUT` above still works (`"Filter set"`, singular) and is the way to touch a single slot; the POST form avoids N round-trips when uploading a computed bank. Sending a bare array to either verb fails at the JSON layer (`Expected BEGIN_OBJECT but was BEGIN_ARRAY`).
- **Slot count follows the selected equaliser**, so set the equaliser BEFORE writing: Generic/Extended = 20 slots, Generic/Configurable PEQ = 31 (both observed 2026-07-28). Writing more entries than the equaliser has slots is accepted and truncated silently.
- **REW marks a measurement modified (blue in the UI) after a filter or equaliser write** — but exposes NO dirty/modified field on the measurement object, so the cue is available to the human and not to code.
- **Crossover types:** `get_crossover_types` → BE2-8, BU1-8, L-R2/4/6/8. Audiotec-Fischer EQ band types: PK / LS_Q / HS_Q + AP1/AP2 (all-pass, several allowed).
- **Modeling a FULL channel (crossovers + EQ) in REW → the "Generic Extended" equaliser** (verified 2026-07-12): select it per measurement via `POST /measurements/{id}/equaliser {"manufacturer":…,"model":…}` — the Audiotec-Fischer preset has NO crossover filter types; Generic Extended does, with **20 filter slots**. Filter schema (one FilterSetting per PUT, as above): crossovers `type "High pass"/"Low pass"` + `shape` (`"BU"`/`"BE"`/`"L-R"`) + `slopedBPerOctave`; PEQ `"PK"` (frequency/gaindB/q); shelves `"LS Q"`/`"HS Q"` (take `q`); `"All pass"` takes `q`, no gain → a 2nd-order APF is pushable.
- **Generic Extended's full type list** (user-verified in the UI dropdown, 2026-07-13): Modal · Low pass · High pass · LP Q · HP Q · Low shelf · High shelf · **LS RBJ / HS RBJ** · **LS Q / HS Q** · Notch · Notch Q · **All pass** (freq + Q — this is the 2nd-order APF) · L-T (Linkwitz Transform). Three shelf families — for Helix modeling use **LS Q/HS Q** (≡ RBJ S=1 at Q=0.71), not the plain or RBJ variants. ⚠️ **No 1st-order all-pass**: a Helix AP1 band CANNOT be mirrored in a REW panel — keep AP1 out of prescriptions where the panels-mirror-hardware invariant matters, or note the gap in the ledger.
- **Predicted response with filters = `GET /measurements/{id}/eq/frequency-response`** (mag+phase, ppo grid). ⚠️ **The measurement's UI smoothing LEAKS into this predicted trace**: read the current `smoothing`, set `None`, fetch, then RESTORE the user's value. (A "27 dB Bessel mismatch" was mostly this leak.)
- **Filter-math equivalences (all REW-verified to 0.000–0.05 dB):** scipy Bessel needs **`norm="mag"`** to match REW's BE; `"LS Q"/"HS Q"` at Q=0.7071 ≡ RBJ shelf S=1 (⚠️ REW's plain `"Low shelf"/"High shelf"` is a DIFFERENT definition — don't use it for Helix-style shelves); BU / L-R / PK are textbook-exact.

## Targets & optimisation
- **Per-band targets (Nono #2-9) carry garbage values OUT of band** (the slice rolls toward −∞) → sample only *in band* and filter `|val| > 200`. Anchor levels to the **full** target (e.g. Jazzi #1), not per-band sub-targets.
- **Match Target / optimise does NOT trigger over the API** (no endpoint) — compute PEQ yourself (RBJ biquad) and upload.
- **Capture CAN be triggered over the API — but we deliberately do NOT.** The control endpoints exist (`POST /measure/command {"command":"SPL"}` fires a sweep, `/measure/naming` names the next, `GET/POST /measure/timing/offset`), **but every write/control POST requires a REW Pro license** — on the free version they return `401 "A Pro upgrade license is required for this action"` (GET/reads are free). More decisive than the license: **the mic is placed/held by hand** (MMM = moving mic; even a loopback sweep needs the mic positioned), so auto-triggering the sweep saves nothing. **Conclusion: analysis is API-driven (GET), capture stays MANUAL** — this was explored and consciously dropped (verified REW 0.9.5, 2026-07-11).
- **Measurement-PROCESSING commands ARE free (a different namespace, NOT Pro-gated).** `POST /measurements/{id}/command` processes an EXISTING measurement and works on the free version. `GET /measurements/{id}/commands` lists them: `Minimum phase version`, `Excess phase version`, `Smooth`, `Invert`, `Add SPL offset`, … Params are a **dict**, and REW discovers them for you — a `400` lists the missing keys (min/excess-phase need `append lf tail`/`append hf tail`/`include cal`/`replicate data`; a `true` tail also needs its `… tail start`/`slope`). Wrappers: `excess_phase_version(mid)` / `minimum_phase_version(mid)` create `<name>-EP`/`-MP` (read the excess phase back via `get_fr`), `set_smoothing(mid, '1/6')` applies REW's own smoothing. **This is the authoritative excess-phase path — REW's own Hilbert, not a home-brew scan** (verified REW 0.9.5, 2026-07-11).
- **A target imported from txt (freq+dB, e.g. Jazzi #1) is MAGNITUDE-ONLY — no phase.** Pulling it must **tolerate** the missing phase (don't crash, don't substitute 0/flat as "phase"). Magnitude voicing (the usual case) needs no target phase → fine. If target phase IS needed (complex / joint comparison) → take it from the **per-band components** (#2–9, built WITH the crossovers → they carry crossover phase), **not** from the full txt curve; and **never fabricate min-phase from the magnitude** (Hilbert) and pass it off as the target's phase — that's only the *assumption* "target is min-phase", not the specified phase. A downloaded **Nono export** reads directly via `rew_tool/nono_curves.py` (full target = `freq mag`; per-band #2–9 = `freq mag phase` — confirmed on real exports).

## Timing (inter-channel TA from the IR) — usable with the right method, NOT a blanket "go manual"
The API IR gives valid **relative** inter-channel timing **IF** you avoid two real failure modes — don't reflex-punt to the GUI (that's needless manual work). But we must keep a vital rule in mind:

* **⚠️ MANUALLY INSPECT IMPULSE GRAPHS — REW NATIVE DELAY ESTIMATES ARE FIXED (Lesson 2026-06-27):**
  The situation is always such that we MUST open the Impulse Response (IR) graphs in the REW GUI and visually inspect them, rather than blindly trusting REW's native automated delay estimates or numbers. REW's native automatic delay estimation utilizes fixed mathematical logic (фіксована логіка) that easily locks onto strong late reflections (windshield, floor, or console) instead of the true direct sound. Additionally, it cannot automatically separate pre-existing DSP delays from physical acoustic paths. Always find the geometric onset (leading edge — the first deviation from zero) manually or verify the automated pick in the REW GUI, and verify whether pre-existing delays in the Helix DSP were active during measurement.

The two failure modes (and their fixes):
1. **Global max-abs ≠ the direct sound.** The largest |sample| can land on a fixed late buffer index (~96000) = a **reflection** (a few ms after onset), not the direct peak. → detect the **direct-sound FIRST ARRIVAL (leading edge / onset)**, NOT the global max (**`analysis.first_arrival(times, ir)`**).
2. **A floating per-measurement reference** makes `startTime` jump (~5 ms even between adjacent measures). → measure every channel against a **consistent shared loopback reference / fixed Time Offset** so relative timing is preserved. **Not** each measurement to its own peak (that erases the arrivals). Without a shared reference, inter-channel timing genuinely IS meaningless — that's the "garbage" the old note meant. ⚠️ **The Time Offset value is setup-specific = the measured bulk delay of YOUR rig — never a fixed number to copy.** Naming an illustrative figure has bitten a real session ("Time Offset ~8.4 ms" was read as typical and caused confusion): one rig measured **~5.18 ms**, another **~8.4 ms** — both correct, copy neither; measure it.
- **Policy:** with both handled (loopback ref + leading-edge first-arrival), **take the API TA into work BY DEFAULT** after a quick **sanity-check** — relative delays physically plausible (cm-scale, sane L/R geometry), stable across a repeat, clean direct peak (no reflection inside the gate). **Re-measure only when the sanity-check FAILS** (clipped/noisy IR, no clean direct arrival, jumpy `startTime` even with a shared ref) — NOT as a standing "always read the GUI" rule. GUI read / summation / ear = cross-check, not the only path.
- **The SUB / low frequencies are the genuine weak spot** — `timeOfIRStartSeconds` is least reliable in the bass (slow front, long wavelength) → don't pin the sub's timing on the raw IR onset; read the sub↔midbass alignment from **summation** (joint phase) instead.
- (`startTime`/`delay` IS the timing field — never reconstruct time from sample-0 of the array; THAT part stays junk.) Full method → `diagnostic-techniques.md §10` (now reconciled to this policy — usable-by-default, GUI as a cross-check).
- **Inter-channel RELATIVE delay (e.g. w-L vs w-R) → CROSS-CORRELATE the two IRs; don't threshold/onset-pick.** Cross-correlation finds the lag that maximizes match → robust to impulse SHAPE. A leading-edge/onset pick is **fragile on a DIRTY impulse** (door midbass: ragged onset + reflections) and can be off by multiples — **real bug: 3.5 ms reported vs ~0.9 ms actual on the GUI cursor.** So: first-arrival is fine for a CLEAN impulse; for dirty ones / any L↔R relative read, **cross-correlate** (**`analysis.relative_delay_xcorr(ir_a, ir_b, fs)`** — positive = B later; both helpers are in `rew_tool/analysis.py`, `--selftest`-verified) — and **always cross-check the number against the GUI cursor before stating it.** ⚠️ If the method is known-fragile for THIS signal (you said "midbass onset is unreliable"), do NOT emit its output as a confident number — robust-method-or-cross-check FIRST.

## Distortion (THD from a normal sweep — no extra measurement)
- **`GET /measurements/{id}/distortion`** returns REW's THD-vs-frequency table (fundamental dB, THD %, per-harmonic %) computed from any ordinary log sweep — wrapper **`rew_api.get_distortion(mid)`** (verified live 2026-07-14). Feeds the Phase-0 flaw map's **distortion floors**: a crossover corner wants LOW measured in-band THD with margin, not just a datasheet-Fs rule. Real payoff on the source build: mid-R measured 18 % THD @ 100 Hz and clean by 200 → the 460 Hz HPF's margin became a MEASURED fact; an in-band 4.8 % spike at 160 Hz on one woofer surfaced only through this table.
- ⚠️ Rows below the channel's HPF (or outside the driver's real band) are **noise floor, not driver distortion** — evaluate only in/near the intended passband.
- ⚠️ **THD % is fundamental-relative — a deep null inflates it.** In an interference null the fundamental collapses 20+ dB while the harmonics (2f/3f, outside the null) stay → the ratio explodes with a QUIET fundamental. Read the fundamental-dB column alongside THD %: a spike is mechanical only if the fundamental there is comparable to its neighbors. Resolution of the source-build example above: the woofer's 4.4 % @ 160 Hz sat at fundamental 53 dB (door-null floor) vs 0.2–0.5 % at 100–125 Hz at 81–84 dB — **null artifact, mechanics cleared** (2026-07-15).

## IR-start triangulation (the "where does the impulse start" question)
- **For a band-limited driver a single "correct start" does NOT exist** — REW's estimate isn't "wrong", the question is ill-posed in slow-front bands. Measured method spread (peak vs −20/−30 dB edges vs ETC peak): clean mids 0.06 ms (any method works), door midbass 2.8 ms, sub 13 ms. Use **`analysis.arrival_triangulate(times, ir)`**: it computes all four and returns a TRUSTED / ILL-POSED verdict from their spread — TRUSTED → edge/xcorr timing is safe; ILL-POSED → relative xcorr for pairs, SUMMATION for joints (never pin TA on a single onset there). `analysis.etc_envelope` (Hilbert ETC) doubles for reflection work; `analysis.step_response` is a VISUAL for LF character only — live data showed step "polarity" disagreeing between identically-polarized mids (polarity stays a summation verdict, §9).

## Process hygiene
- **cwd bug:** run from `/tmp` and reach `rew_api` via `PYTHONPATH` or inline urllib — the project cwd sometimes throws `PermissionError` on import.
- **Save-all when the UI fails:** there is an API path to save every measurement — see project memory `rew-api-save-all`.

## Notes / annotations
- **`PUT /measurements/{id}` REPLACES the notes field.** The measurement software writes its own capture information there (averaging count, input RMS, weighted levels, sweep timing reference). A bare PUT with `{"notes": "..."}` destroys it, irreversibly for that measurement — confirmed by destroying it on a real capture. **Read → filter → append → write back.** A helper that stamps system state into notes must round-trip, and should offer a `--show` audit and a `--clear` that removes only its own line.

## Timing: read the START, add the OFFSET (measured on a live REW, 2026-08-23)

Six captures in the reference car (REW #77–82, 96 kHz, loopback reference), measured rather than
inferred. Four facts, each of which changes what a caller should read.

- **`timingOffset` is folded into `delay` already.** `physical arrival = delay + timingOffset`,
  exact to the last digit on integer-sample offsets (4 ms = 384.0 samples at 96 kHz; four captures
  all gave `IRstart + offset = 254.0000000000` samples). The only residual seen was on
  7.7003 ms = 739.2288 samples, and it was precisely the fractional part — REW stores the start on
  the sample grid. **The trap: `timingReference` reads `"Loopback"` whether the offset is 0 or
  7.7 ms**, so the field that looks like the guard is not one. An offset set once and forgotten
  shifts every channel imported afterwards, and it looks like a plausible delay, not an error.
  `rew_api._ir_start_time` reads `startTime` or RAISES — see the next point for why there is no
  fallback.
- **`delay` is the ARRIVAL, not the buffer origin, and it is a whole second away.** Measured on
  six captures: `delay − startTime = 1.000000 s` every time — structurally, because REW puts the
  peak at index 96000 and 96000 / 96000 Hz = 1 s of pre-roll. So
  `delay = startTime + peakIndex / sampleRate`. Substituting one for the other on capture #78 turns
  `i0 = −startTime·fs = +96124.2` samples into **−259.8** — 96384 samples out, and indexing before
  the buffer begins. A dimensionally correct reconstruction exists
  (`startTime = delay + timingOffset − peakIndex / sampleRate`, using the reported `peakIndex`, not
  this rig's 96000) and is deliberately not used: **`delay` is exactly `timeOfIRPeakSeconds`**
  (1e-16 agreement on all six), so anything rebuilt from it inherits the peak instability below.
  Rebuilding the most load-bearing number out of the least trustworthy one is worse than refusing.
- **Anchor on the IR START, never the peak.** `timeOfIRStartSeconds` is on the integer sample grid
  and bit-stable; `timeOfIRPeakSeconds` is not a timing anchor and failed three independent ways:
  it wandered ~2.6 µs per capture, left 3.3–6.7 µs of residue after undoing a known offset, and
  **moved 3.6 ns between two reads of the SAME stored measurement** while the start stayed
  bit-identical. Three zero-offset captures of one speaker: start 254.0000 / 254.0000 / 253.0000
  samples, peak 260.1532 / 259.5590 / 258.9090. (Ours already comply: `analysis.first_arrival`
  walks the leading edge and its selftest pins that it ignores a louder later reflection;
  `resonalyze_ir` rotates on `startTime` and records the peak only as metadata. Upstream reached
  the same conclusion independently — DIMOSUS's #107.)
- **The offset is stated three times and one of them can lie.** `timingOffset`, `timingRefTime`
  (exactly its negative, verified to 2.2e-16 over six captures), and in prose inside `notes`.
  `notes` is **user-editable free text**: a hand-edited measurement read 5.0000 ms to a naive
  `with ([\d.]+) ms` while the truth was 4.0, because editing the note does not touch the numeric
  field. Cross-check the number against `timingOffset`; a structure check alone misses a
  number-only edit. RTA measurements return `null` for every timing field — they have no IR.
- **The text export is strictly worse for timing.** It carries no timing offset at all, and its
  `Start time` is rounded to the integer sample grid — −96124.000000 samples against
  −96124.166686 from the API for the same measurement, 0.167 sample (1.736 µs) of quantisation.
  Every other field matches exactly, so it is rounding, not a different definition. The notes never
  reach it: three exports taken while the notes were being heavily edited came out byte-identical.

### The repeatability floor for SEQUENTIAL per-driver measurement

Measuring one speaker repeatedly, the IR start moved **1 sample across 6 captures over 18 minutes**
— 10.4 µs, ≈3.6 mm of apparent path — and that is an upper bound, since the start is
sample-quantised. Two properties make it a method problem rather than a curiosity: the drift is
**per-capture, not per-clock** (17 idle minutes moved the arrival 0.5 µs, while consecutive
captures moved it ~2.6 µs each), and it is present with **no timing offset applied at all**, proved
with a deliberate zero-offset control block.

So when drivers are measured one after another, later channels carry accumulated drift against
earlier ones: over eight channels, order 1–2 samples. Below what matters for a woofer; **not
obviously below what matters for tweeter alignment.** State it as the floor rather than claiming
better, and **re-measure channel 1 at the end** whenever a session's inter-channel timing is
load-bearing — that control capture is what turns the floor from an assumption into a number.
