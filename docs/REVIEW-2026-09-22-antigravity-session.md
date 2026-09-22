# Antigravity session review — fast, and where speed broke the record (2026-09-22)

**Source:** Antigravity CLI transcript, 269 steps, 2026-09-22 09:09–16:45 UTC. Generator: Gemini 3.8
Flash (High); critic configured as `codex:gpt-5.2-codex`. Project `testAgy-auto` — VW Passat B8,
Helix DSP Ultra S, method as installed in `.agents/skills/autosound-tuning`.
**Status:** analysis and plan only. Nothing here is implemented. Issue: see the end of this file.

## 1. What the session did

| time (UTC) | user | session |
|---|---|---|
| 09:09 | "took curves #41–61" | reads state, REW; registers `cap_004`; B vs C table vs EPY target (4 min 45 s) |
| 09:14 | "use the names" | same analysis, keyed by REW titles |
| 09:39 | scene sits on the dash; own alt config (65/280/2800) + another build's `.mdat` loaded in REW | analysis of the alt file; proposes a merged "Variant D" |
| 09:57–10:01 | "let's try; compare with B or C?" · "B is dropped?" | writes `variants/variant_D.json`, `switch_to_D.bat`, extends `switch_variant.py`, switches master to D |
| 10:49 | "measure anything?" | 4+2 curve plan with exact titles |
| 10:50 | "compute the rear for FULL" | rear bandpass, EQ, gain, delays; written into D |
| 11:10 | "write a TCC issue on preset export/import" | local `docs/TCC_ISSUE_F053…md` (first in Ukrainian) |
| 11:17 | differential rear L−R, 50 %? | adds a 15 ms "Haas" delay; claims Helix has **RearFX** |
| 11:25 | "Helix has no RearFX" | concedes, rewrites |
| 16:44 | "where are our sessions on disk?" | writes an exporter script + `.bat` + `SESSION_PROTOCOL.md` |

Replies came in 1–7 minutes. The user liked the pace, and this plan keeps it.

## 2. What made it fast — keep it

1. **One state read, then an answer.** `contract.py check`, the process state, the HEAD version and
   the REW list. No re-reading of references, no gate ceremony before speaking.
2. **Answers in the user's own units:** REW titles, a PC-Tool table that can be typed straight in,
   a small measurement plan with exact titles (4–5 curves, not 20).
3. **A/B on two DSP slots.** Switching slots by ear on one track is the fastest way to tell two
   variants apart, and the user called that experience valuable.
4. **No reviewer round per reply.** Analysis and measurement plans went straight to the user.

## 3. What went wrong — ranked by what it costs later

### A. The record was damaged silently (critical)

1. **A banked ledger version was overwritten in place three times.** The project-local
   `scripts/switch_variant.py` (written by an earlier session) copies `variants/variant_X.json` over
   `state/master/v_011.json`. It ran for D, for D + rear, and for D + Haas delays. `v_011` no longer
   holds what was measured as `v_011`. The ledger's own slot registry (`state.py registry`,
   `core/preset-strategy.md`) was never used, and variants lived in `variants/*.json` outside the ledger.
2. **A past round was invented to get past a guard.** `capture-start 4` refused: "series _4 is not
   this project's… its own next one is _3". The session then opened, filled and closed `cap_003`
   with two titles (`ALL_3 (rta)`, `ALL_3 (sw)`). Series 3 in REW held about ten curves
   (#12–20 sweeps, #40). The guard did its job, and the way past it was a record that lies about
   the past.
3. **`cap_004` was opened and closed after the fact:** 21 titles marked taken within 5 s, and one
   round covering **two DSP states** (variant B and variant C). Nothing binds a title to the state
   it was measured under. The "NO KNOBS RECORDED" warning was printed three times and ignored each time.
4. **Another build's data was read as this project's.** The user loaded `EPY-Sep2026_v1.mdat`,
   whose series `_2`/`_3` share numbers and titles with this project (`ALL_3 (rta)` is #47 there
   and #40 here). The session analysed it with `rew_api` directly. The foreign-series guard lives
   in `process.py`, and a plain REW read never meets it.

### B. Facts made up (high)

5. **Rear geometry:** "~95 cm / ~160 cm from the ear". The project's lookup returned `{}`, so there
   was no rear geometry. Delays of 3.80 / 1.90 ms were computed from these numbers and written into
   the variant.
6. **"Helix RearFX"** was stated as an existing feature. `dsp_profile.json` lists the features
   (`RealCenter, DynamicBass, SubXpander, …, RearRC`), and RearFX is not among them. The session
   read that list at 10:55 and made the claim at 11:21. The user caught it.
7. **A 15 ms "Haas delay"** was presented as law and written into the variant. It was not offered
   as one option to measure.
8. **The differential rear rule contradicts itself:** "50 % = −6 dB on each input", and then
   "+50 % (0 dB)".

### C. Proposal hygiene (medium)

9. **The user's config was changed without saying so.** Variant D added `sw` HP 20 BW12, a 38.8 Hz
   PEQ, a 10 kHz shelf on the tweeters and a centre PK at 1950 Hz. The tweeter gains became −5.5/−5.0
   in one table and went back to the user's −3.8/−2.2 in the next, and neither change was named.
10. **Delays were carried across a crossover change.** The user's delays belong to 2800 BE24.
    Variant D uses 3500 LR24, which has a different group delay at the junction, and nothing
    said the junction was now unverified.
11. **No reviewer call in the whole session** (0 of 4 structural proposals: D, rear, Haas,
    differential), yet every proposal was written straight into the active state.
12. **Numbers without the named quantity.** "RMS error 2.86 vs 2.39 dB" gave no band normalisation
    in the claim and no smoothing. The "cancellation depth" was read off MMM RTA pairs as if it
    were a phase null.
13. **Tone:** long replies, emoji headers and praise ("absolutely right, 100 %", "gold standard").
    The first answer keyed curves by id only, so the user had to ask for names.

### D. Scope and tooling (low)

14. The TCC proposal was written as a local file, first in Ukrainian, not filed. There was also an
    artifact-path error on the first write.
15. The session exporter (`export_session_protocol.py` + `.bat` + `SESSION_PROTOCOL.md`) was not asked
    for. The user asked where the logs are.
16. **Four `python -c` quoting failures under PowerShell,** plus a string of throwaway
    `scratch/analyze_*.py` files. The session had no single command for "these titles vs target
    at these frequencies".

## 4. The two failure shapes side by side

| | Claude session (issue #57) | Antigravity session (this) |
|---|---|---|
| speed | slow: every tool wants flags the round already knows | fast: used almost no tools |
| errors | caught, retracted: 5 of 14 decisions were corrections | not caught: the record was changed silently |
| user stops | three, for verbosity | one, for a made-up feature |

These are the same defect. **The right path is not the short path.** Claude takes the long path
and pays for it in time. Gemini takes a short path that goes around the method and pays for it
in the record. The compromise is to make the method's path the shortest one, and to guard only
what breaks the record.

## 5. Plan — what to change

Principle: **hard refusals only where the record can be damaged; everything else stays light.**

| # | change | fixes | speed cost |
|---|---|---|---|
| P1 | **Banked versions are immutable.** `contract.py check` keeps a hash for each banked `v_NNN` and names any file that changed. `state.py` writes only new versions. | A1 | none |
| P2 | **Variants live in the ledger.** `state.py variant new D --from C`, `variant show D --pc-tool` (the typed-in table the user liked), `variant switch` = registry, never a file copy. The skill says: do not write a project-local switch script. | A1, D16 | saves time |
| P3 | **One command registers a round from REW.** `process.py capture-import --series 4` reads the REW titles, binds each title prefix to its ledger version or variant (`B_` → B, `C_` → C), asks for the knobs at import and refuses a round with nothing bound. A missing past series is marked `--late "<reason>"` and never back-filled as if it had been taken then. | A2, A3 | one command instead of three |
| P4 | **REW reads know which file they come from.** `rew_api` compares `containingFileName` with the project's own file and labels or refuses data from a foreign `.mdat`, so the foreign-series guard also covers a plain read. | A4 | none |
| P5 | **Every number in a proposal names its source:** measured `#N`, `project.json`, `dsp_profile`, the user, or ASSUMPTION. An assumption is shown as one and never written to state. A feature missing from `dsp_profile` counts as not existing: ask the user. | B5–B8 | one column |
| P6 | **A proposal built on the user's config shows the diff:** "yours → mine, why", row by row. It also flags a carried value that depends on a changed one (delays across a crossover change). | C9, C10 | none |
| P7 | **Reviewer by risk, not by turn.** Required before *banking* a structural change (crossover topology, a new channel group, delays, polarity). Not required for analysis, measurement plans or replies. This is the one gate, and it sits at banking. | C11 | one call per banked change |
| P8 | **Output contract for fast models:** REW titles, not ids; the named quantity next to every number; a ready-to-type table; no emoji or praise; one screen, then "details?". | C12, C13 | faster to read |
| P9 | **One analysis helper:** `rew_tool compare --titles … --target <file> --at 40,100,…` prints the table these sessions keep rebuilding with `python -c`. | D16 | saves time |
| P10 | **Where the logs are is an answer, not a build.** The skill names the transcript paths for each front-end, and a feature request goes to the product's tracker in English. | D14, D15 | none |

**Overlap with filed issues:** P3 is #57 P0 (the round drives every tool) plus #48 (an amend path
for a closed round, which is the honest form of the cap_003 backfill). P7 narrows #57 P2
(evidence-gated banking) to the one place it pays. The TCC export/import request (item 14) belongs
to the TCC tracker; the product side of P2 is the same feature.

**Order, if the user takes it into a wave:** P1 + P5 + P8 first, because they are cheap and stop the
silent damage. P2 + P3 next, because they make the fast path the correct one. P4, P6, P7, P9 and P10
follow. The user decides which wave gets it.
