# Naming & project structure — conventions for a long-lived tune

A tune outlives any single session: months later you may chase a different target curve, or re-tune after swapping/installing hardware. For that to be cheap, names and structure must be **legible and stable**. This file holds the *conventions* (reusable grammar); this car's specific channel codes live in `autosound_context.md §5` (the canonical glossary, loaded into both chats), and the canonical step path lives in `process-phases.md`.

## 1. Project hierarchy

```
PROJECT  = one car + one install (drivers, DSP, amps, wiring). Lives for years.
  └ SESSION = tuning toward ONE target curve. May span days (a Mac restart wipes the chat).
      └ PHASE −1–7 (process-phases.md): intake (new project) → baseline → crossovers/level/delay+nono-targets → hygiene-EQ/joint-phase/voicing → verdict → center/rear → listening → client voicing → wrap-up/feedback
          └ STEP (the user's path) → GENERATOR↔CRITIC cycle (≤3 rounds) → Arbiter
```

The **path defines the process** — the ordered steps the user described, refined by experience (`process-phases.md`). Keep it; that ordering (delays → phase → EQ; raw-sweep refs; MMM-for-magnitude / sweep-for-phase) is hard-won.

## 2. What triggers work — and whether raw data survives

A "new project run" isn't always from scratch. Classify it first; it decides how much you re-measure:

| Trigger | Foundation (Phase 0–1) | Raw data | What to (re)do |
|---|---|---|---|
| **New target curve, same hardware** | valid, reuse | **same raw still valid** | Phase 2 only (per-channel EQ + level to the new shape). Voicing preset swap if using base+voicing. |
| **Component swap** (amp / one driver / damping) | partly invalid | **re-measure the affected channels** (and its joints) | redo the touched part of Phase 0–1, then Phase 2 |
| **New / re-done install** | rebuild | **raw from scratch** | full process from Phase 0 |

This is the practical face of "the foundation is curve-agnostic" (SKILL.md → Session lifecycle): hardware defines the instrument, the curve only voices it.

## 3. Measurement naming (REW)

Measurement name = **`<channel|pair|combo|joint>[ <modifier>]_<version>`**, optionally with a method suffix.

- **Channel / pair / combo / joint codes** → `autosound_context.md §5` (this car: `sw`, `w-L/R`, `m-L/R`, `tw-L/R`, `r-L/R`, `c-H/c-L`; pairs `Ws/Ms/TWs`; combos `ALL`, `ALL+C`; joints `SW+Ws`, `L w+m`, `R m+tw`; full side `L`/`R`).
- **Method suffix:** `(rta)` = MMM RTA (for magnitude/tone) · `(sw)` = acoustic sweep (for phase/timing/distortion).
- **Modifiers:** `FX` = measured with Helix FX on; `c` / `c FX` = front without / with FX.
- **Transient experiment tags** — while A/B-testing a candidate change, tag the variant in the name (`i`/`INV` = inverted polarity, `+Δτ` = an added delay trial, etc.) so the two readings don't get confused. The tag is **temporary**: once the change is **baked into the base** it drops from the name (the measurement is just `_N+1` at the new config). **`dsp-state-current` is the source of truth for what's in the base** — the name tags only the experiment in flight, not the committed state.
- **Version suffix `_N`** = the **DSP config version the measurement was taken under**. `tw-L_7` = tweeter-L at config v7; `ALL_25` = full front at v25. **Bump N whenever the DSP config changes.** This is what lets the changelog line up "before vs after a change" (e.g. `ALL_17` vs `ALL_18` shows what an EQ import moved). A measurement with no `_N` is ambiguous — avoid it.

### Capture plan per phase — `sw` vs `rta` (take BOTH in one solo pass)

Rule of thumb: **magnitude / tone / summation / target → `(rta)`**; **phase / time / IR / distortion → `(sw)`**. In a solo pass, capture BOTH types so you never re-measure just to get the other. Type→purpose detail: `analysis-playbook.md`.

| Phase | Capture (concrete names) | Type |
|---|---|---|
| **0 baseline** | each driver solo: `<ch>_1 (sw)` **+** `<ch>_1 (rta)` | **both**, one pass/driver |
| **1** (analyzes `_1`, **no new capture**) | — | TA/Time-Offset/excess-phase ← `(sw)`; crossover freq & level ← `(rta)` |
| **2** (needs the re-measured `_2`) | each driver solo post-`v1`: `<ch>_2 (sw)` **+** `<ch>_2 (rta)`; then groups `Ws_2/Ms_2/TWs_2 (rta)`, `L_2/R_2 (rta)`, `SW+Ws_2 (rta)` | **both** solo, then **rta** groups |
| **3 verify** | `<ch>_final (rta)`, `Ws/Ms/TWs_final (rta)`, `SW+Ws_final (rta)`, `L/R` sides, `ALL_final (rta)` | **rta** (+ `(sw)` spot-checks) |

- **2a** needs `_2 (rta)` (magnitude to EQ) **+** `_2 (sw)` (excess-phase → what's EQ-able); **2b** needs `_2 (sw)` (phase/summation); **2c/2d** the `(rta)` groups.

## 3a. REW history hygiene — names are the identity (tell the user early)

**REW measurement order is fragile.** You can reorder, delete, and — worst — *sort* the measurement list, and an accidental click reshuffles everything. So **position means nothing; the name is the only stable identity of a measurement.** All history work (lining up `_N` versions, before/after a change, joints) hangs on names, not row order. Practical rules:

- **Never refer to a measurement by its position** ("the 3rd one") — only by name. If a name is missing its channel/`_N`, fix the name before reasoning on it.
- **Groups are visual only.** The user collects measurements into REW groups **`setup step.X`** (X = 1..6) to keep the list workable. Grouping does **not** renumber anything — the measurement names/`_N` stay exactly the same; the group is just a folder. Don't infer meaning from which group something sits in beyond "roughly which phase it came from".
- **At the start of working with the user, surface this** (alongside the pre-session checklist): names are critical, order can be destroyed by a stray sort, so keep names disciplined and don't trust the visual order.

## 4. REW storage files

- One archive per measuring day: **`rew_analitic/measurements-YYYY-MM-DD.mdat`**. Live data comes over the API (`localhost:4735`); the `.mdat` is the dated snapshot.
- The per-measurement `_N` version lives *inside* the file, so the same day can hold several config versions. Don't encode the config version in the filename — the date groups, `_N` versions.

## 4a. Config + export backups (git → GitHub) — set up at NEW-PROJECT start

A tune is worth months of work; its artifacts must survive a disk loss. Standard layout (the skill tells the user this at project start, then keeps it fed):

```
rew_analitic/
├── dsp-config/    DSP config milestone backups → git ✓ GitHub. SMALL, and = the actual tune
│   │              (Helix .pct6 ≈ 3 KB, binary/encrypted → RESTORE-only, NOT parseable).
│   └── README.md  maps each binary → its dsp-state version + date + one-line "what it is"
│                  (without this map an unparseable binary is useless for "review later").
├── exports/       REW EQ exports (Audiotec-Fischer), decimated CSV traces, key screenshots → git ✓
├── target-curves/ house/target curve files → git ✓ — subfolder per curve (full #1 + per-band
│                  #2–9 components); README.md maps which is ACTIVE + curve↔preset; several coexist
├── *.mdat         LARGE (16–112 MB) → .gitignore, NOT backed up (re-measure if ever needed —
│                  user's call; GitHub's 100 MB/file limit rules them out anyway w/o LFS)
└── eq-set-*.md, dsp-state, changelog, target-*  analysis records → git ✓ (already)
```

Rule of thumb: **what's small + irreplaceable (config binary, analysis md, light exports) → git/GitHub; what's large + reproducible (.mdat) → local only.** Back up milestones (a locked/named state), not every save. Save the config binary **and** keep `dsp-state` readable — the binary restores, the md explains.

## 5. DSP configuration naming

- Config version = **`vN`**, monotonic, and it **matches the measurement `_N`** (config v18 → measurements `_18`). The full state of the current `vN` always lives in `dsp-state-current` (memory) — gains, crossovers, TA, EQ, polarity.
- **The DSP tool's own file-version (e.g. Helix PC-Tool `SQ_Jazzi v1.30.pct6`) is a SEPARATE numbering from our `vN`** — don't conflate. The `dsp-config/README.md` map bridges the two (which `.pct6` = which `dsp-state vN` + date). Helix saves config as `.pct6` (binary/encrypted, Audiotec-Fischer); it can't be parsed for analysis, so it's a backup/restore artifact only.
- **Base + voicing** (SKILL.md → Session lifecycle): the OUTPUT base is shared; name voicing presets by intent — `voicing:EMMA` (competition), `voicing:Accurate` (enjoyment), `voicing:off` (neutral base). A config is then "base vN + voicing:X". Switching curves swaps the voicing, not the base. Which presets are worth building (SQ / FULL / SQL / surround / source-input / per-ruleset competition) → `preset-strategy.md`.
- **Multiple active slots → one machine-checked pointer.** When the DSP holds several presets in physical slots (Helix Slot 1/2/3), which one is *loaded right now* is not a prose note — it's `rew_tool/state/registry.json` (`state.py registry set-active <preset>`). `registry render` generates the multi-slot `dsp-state-current` view (a loud active-slot banner + one isolated row per slot), and the apply gate refuses a change aimed at any non-active slot. This kills the cross-slot anchoring trap (computing filters off a neighbour slot's gains — issue #5).

## 6. Target curves & competition vocabulary

- A curve has a **name** and lives in REW as **#1 = full target** (anchor levels to this) + **#2–9 = per-band sub-targets** (garbage out of band — sample in-band only). The active curve is recorded in project memory (`target-curve-*`); the curve **files** (full + per-band components) live in **`rew_analitic/target-curves/<name>/`** — a subfolder per curve, several may coexist, a `README.md` marks the ACTIVE one + curve↔preset. One curve per session (but a project may store several to A/B). **To view/compare curves visually → https://nonotuningtool.com/.**
- **Curve library in this REW** (each is a candidate session target — naming any of these is a strong "this is a tuning task" signal): `Flat`, `Audiofrog`, `Whitledge`, `Half Whitledge`, `Harman`, `JBL`, `JL Audio`, `Jazzi`, `Jazzi v2`, `RAW-Cat`, `RAW-Cat (uni)`, `ResoNix Accurate`, `ResoNix Laid-Back`, `ATF`, `ATF EQ (Helix)`, `EPY`, `Hanatsu`, `Arkadij`, `Arkadij v2`. Some are industry curves (Harman, Audiofrog, ResoNix, JL Audio, JBL), some custom. The active one is whatever the session picks; the list grows.
- **No curve is one-size-fits-all, and the curve is a START, not a finish (ResoNix/Apicella).** The right shape depends on cabin size (bass lift), reflections (car-to-car, even location-to-location in the same car), tweeter location (A-pillar vs sail vs dash), speaker polar response (shifts with crossover + placement), and the drivers' distortion profile — two systems matched to the SAME curve can sound completely different. An RTA dip isn't always a heard dip (off-axis/dispersion). So: reach the curve, then **finish by ear** (per-band L/R level + tonality + center cohesion — see `diagnostic-techniques §17`). A car is never "done" the moment the target is met. ResoNix ships two: **Accurate** (flatter mid, less bass, more top — fidelity, can fatigue / lose to road noise) and **Laid-Back** (more bass, pulled-back upper treble — enjoyment).
- **Competition / scoring context** (drives which voicing preset, per base+voicing): formats **EMMA**, **AYA**, **CARMusic**; categories **SQ** (sound quality), **SQL** (sound quality + loud), **SPL** (loudness). When these appear in a car/autosound context they mean "prep a voicing for judging" — a tuning task, not generic audio. EMMA/AYA voicing ≈ competition preset; enjoyment ≈ Accurate/flat preset.

---

> **Where each layer is canonical:** this car's channel glossary → `autosound_context.md §5`. The step path → `process-phases.md`. Current applied config (vN) → `dsp-state-current`. Active curve → `target-curve-*`. This file holds only the reusable *rules* tying them together.
