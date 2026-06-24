# REW API quirks (localhost:4735) — empirically verified

Gotchas when driving the REW API over Python/urllib (REW 5.40 Beta 126, API 0.9.4). `rew_tool/` already encodes these correctly — this file exists so a fresh session doesn't re-derive them or re-introduce a bug after a refactor.

## Encoding & endpoints
- **Data is BIG-ENDIAN float32** (`struct.unpack('>'+n+'f', ...)`). Little-endian (`<f`) returns garbage that grows ~×4 per step. Applies to magnitude / phase / IR / GD. `rew_tool/rew_api.py` decodes correctly.
- **FR endpoint:** `/measurements/{id}/frequency-response` → keys `magnitude`, `phase` (RTA measurements have **no** phase; sweeps do). Not `/spl`.
- **Two frequency spacings — handle both or RTA crashes.** Log-sweeps return `ppo` (points-per-octave) + `startFreq` → `freq[i] = startFreq·2^(i/ppo)`. RTA / linear measurements return **`freqStep`** + `startFreq` → `freq[i] = startFreq + i·freqStep` (no `ppo`). Assuming `ppo` only → `KeyError` on every RTA pull. `rew_tool/rew_api.py:freq_axis()` picks the right one.
- **IR:** data is under key `data` (not `impulseResponse`). Timing reference is the **`startTime`/`delay`** field — read it, don't reconstruct timing from the array (it's junk; see "Timing" below). **GD:** values under key `magnitude` (not `groupDelay`).
- **Address measurements by NAME, never by numeric index/position.** `get_measurements` returns a dict keyed by REW's ordinal (`"1"`,`"15"`,…) — that index→measurement mapping is **NOT stable across calls** (REW reorders; a sort / delete / new sweep reshuffles it). Reusing `ms['15']` from an earlier call attaches the WRONG data to a channel → a real bug (m-R data pulled under the `m-L` label → a spurious "inverted"/swapped result). **Resolve the target by matching the `title`** (the channel name, e.g. `m-L_01 (sw)`) — or the stable `uuid` — **immediately before each pull**; never cache/reuse a numeric index. This is the skill's "**the name is the only stable identity**" hygiene (`naming-and-structure §3a`) — it binds the **model's API access**, not just the user's GUI discipline.

## Writing filters
- **`set_filters` takes ONE filter per call** (PUT an object, not an array): `{'index':1,'type':'PK','enabled':True,'isAuto':False,'frequency':X,'gaindB':Y,'q':Z}`. An array → `400 "must have index"`.
- The gain field is **`gaindB`**, not `gain` — using `gain` silently sets 0 dB.
- **Crossover types:** `get_crossover_types` → BE2-8, BU1-8, L-R2/4/6/8. Audiotec-Fischer EQ band types: PK / LS_Q / HS_Q + AP1/AP2 (all-pass, several allowed).

## Targets & optimisation
- **Per-band targets (Nono #2-9) carry garbage values OUT of band** (the slice rolls toward −∞) → sample only *in band* and filter `|val| > 200`. Anchor levels to the **full** target (e.g. Jazzi #1), not per-band sub-targets.
- **Match Target / optimise does NOT trigger over the API** (no endpoint) — compute PEQ yourself (RBJ biquad) and upload.
- **A target imported from txt (freq+dB, e.g. Jazzi #1) is MAGNITUDE-ONLY — no phase.** Pulling it must **tolerate** the missing phase (don't crash, don't substitute 0/flat as "phase"). Magnitude voicing (the usual case) needs no target phase → fine. If target phase IS needed (complex / joint comparison) → take it from the **per-band components** (#2–9, built WITH the crossovers → they carry crossover phase), **not** from the full txt curve; and **never fabricate min-phase from the magnitude** (Hilbert) and pass it off as the target's phase — that's only the *assumption* "target is min-phase", not the specified phase. A downloaded **Nono export** reads directly via `rew_tool/nono_curves.py` (full target = `freq mag`; per-band #2–9 = `freq mag phase` — confirmed on real exports).

## Timing (inter-channel TA from the IR) — usable with the right method, NOT a blanket "go manual"
The API IR gives valid **relative** inter-channel timing **IF** you avoid two real failure modes — don't reflex-punt to the GUI (that's needless manual work). The modes (and their fixes):
1. **Global max-abs ≠ the direct sound.** The largest |sample| can land on a fixed late buffer index (~96000) = a **reflection** (a few ms after onset), not the direct peak. → detect the **direct-sound FIRST ARRIVAL (leading edge / onset)**, NOT the global max.
2. **A floating per-measurement reference** makes `startTime` jump (~5 ms even between adjacent measures). → measure every channel against a **consistent shared loopback reference / fixed Time Offset** (≈ the arrival, e.g. ~8.4 ms) so relative timing is preserved. **Not** each measurement to its own peak (that erases the arrivals). Without a shared reference, inter-channel timing genuinely IS meaningless — that's the "garbage" the old note meant.
- **Policy:** with both handled (loopback ref + leading-edge first-arrival), **take the API TA into work BY DEFAULT** after a quick **sanity-check** — relative delays physically plausible (cm-scale, sane L/R geometry), stable across a repeat, clean direct peak (no reflection inside the gate). **Re-measure only when the sanity-check FAILS** (clipped/noisy IR, no clean direct arrival, jumpy `startTime` even with a shared ref) — NOT as a standing "always read the GUI" rule. GUI read / summation / ear = cross-check, not the only path.
- (`startTime`/`delay` IS the timing field — never reconstruct time from sample-0 of the array; THAT part stays junk.) Full method → `diagnostic-techniques.md §10` (⚠️ reconcile §10 to this nuance — it may still say GUI-only).

## Process hygiene
- **cwd bug:** run from `/tmp` and reach `rew_api` via `PYTHONPATH` or inline urllib — the project cwd sometimes throws `PermissionError` on import.
- **Save-all when the UI fails:** there is an API path to save every measurement — see project memory `rew-api-save-all`.
