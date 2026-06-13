# REW API quirks (localhost:4735) — empirically verified

Gotchas when driving the REW API over Python/urllib (REW 5.40 Beta 126, API 0.9.4). `rew_tool/` already encodes these correctly — this file exists so a fresh session doesn't re-derive them or re-introduce a bug after a refactor.

## Encoding & endpoints
- **Data is BIG-ENDIAN float32** (`struct.unpack('>'+n+'f', ...)`). Little-endian (`<f`) returns garbage that grows ~×4 per step. Applies to magnitude / phase / IR / GD. `rew_tool/rew_api.py` decodes correctly.
- **FR endpoint:** `/measurements/{id}/frequency-response` → keys `magnitude`, `phase` (RTA measurements have **no** phase; sweeps do). Not `/spl`.
- **IR:** data is under key `data` (not `impulseResponse`). **GD:** values under key `magnitude` (not `groupDelay`).

## Writing filters
- **`set_filters` takes ONE filter per call** (PUT an object, not an array): `{'index':1,'type':'PK','enabled':True,'isAuto':False,'frequency':X,'gaindB':Y,'q':Z}`. An array → `400 "must have index"`.
- The gain field is **`gaindB`**, not `gain` — using `gain` silently sets 0 dB.
- **Crossover types:** `get_crossover_types` → BE2-8, BU1-8, L-R2/4/6/8. Audiotec-Fischer EQ band types: PK / LS_Q / HS_Q + AP1/AP2 (all-pass, several allowed).

## Targets & optimisation
- **Per-band targets (Nono #2-9) carry garbage values OUT of band** (the slice rolls toward −∞) → sample only *in band* and filter `|val| > 200`. Anchor levels to the **full** target (e.g. Jazzi #1), not per-band sub-targets.
- **Match Target / optimise does NOT trigger over the API** (no endpoint) — compute PEQ yourself (RBJ biquad) and upload.

## Timing — the big one
- **IR timing over the API is unreliable.** `startTime` jumps (~5 ms even between *adjacent* measurements) and the max-abs "peak" sits on a fixed buffer index (~96000) catching a **reflection** (2.7–7.8 ms after onset), not the direct peak. So peak / centroid / GD / complex-sum / inter-channel phase are all **junk for timing**. Read inter-channel timing from the **REW GUI** (loopback ref, visible direct peak), or use summation / ear. FR magnitude & phase are fine; IR *timing* is not. Full method → `diagnostic-techniques.md §10`.
- Fix going forward: set a consistent **Time Offset with a shared reference** (≈ arrival ~8.4 ms) on all measurements → cleans phase (esp. HF), keeps relative timing. **Not** each measurement to its own peak (that erases the arrivals).

## Process hygiene
- **cwd bug:** run from `/tmp` and reach `rew_api` via `PYTHONPATH` or inline urllib — the project cwd sometimes throws `PermissionError` on import.
- **Save-all when the UI fails:** there is an API path to save every measurement — see project memory `rew-api-save-all`.
