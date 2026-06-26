---
name: autosound-tuning
description: >
  Orchestrates car-audio DSP tuning for ANY car/system — from a brand-new project
  (intake: equipment + goals interview, target-curve choice, install verification) to deep
  iterative tuning — using REW + a Claude(Generator)↔Gemini(Critic)↔User(Arbiter) review
  loop. Use whenever the user wants to:
  set up or tune a car-audio system FROM SCRATCH («налаштуй нову машину/систему з нуля»,
  intake/опитування), "help me set up my car audio", "tune my speakers/system",
  CREATE or build a house / target curve (even "make a house curve for fun" — e.g. via
  nonotuningtool.com), run a tuning session, pick crossover points, set time delays / phase /
  polarity, build per-channel EQ, fix IMAGING/STAGING (center the image, an image that sticks
  to one speaker, mid-walk, stage WIDTH/DEPTH, layering/echelons, "сцена липне до скла"),
  match a target/house curve named by ANY curve in the REW
  library (Jazzi, ResoNix Accurate/Laid-Back, Audiofrog, Harman, JBL, JL Audio, Whitledge,
  RAW-Cat, ATF, EPY, Hanatsu, Arkadij, Flat…), pull or analyze REW measurements
  (FR/phase/IR/GD/distortion/impedance via REW API localhost:4735), measure driver Thiele-Small parameters & design or verify a subwoofer enclosure (Fs/Qts/Vas, the added-mass method, sealed-box volume & Qtc, DVC coil wiring, L/R driver matching by impedance), update the tune state
  (dsp-state / changelog / session log), or get a second opinion from Gemini
  on a tuning proposal. Trigger on: REW data/screenshots, Helix DSP, MMM RTA, sweep, midbass
  door resonance, sub integration, crossover, under-lap, imaging/staging/локалізація/центр/
  «образ липне до динаміка»/ширина/глибина сцени/ешелони, any target-curve name, impedance / Thiele-Small / T-S / Fs / Qts / Vas / added-mass / sealed box / enclosure volume / box design / Qtc / DVC wiring / driver matching, car-audio
  competition prep (EMMA, AYA, CARMusic) or SQ/SQL/SPL when about a car, "send to Gemini",
  "critic", "що далі", "help me set up my car audio", "make / build a house curve",
  "tune my speakers", or any step of the documented tuning process. (Built & battle-tested
  on a VW Passat B8 / Helix DSP Ultra S — but works on ANY car / ANY DSP.)
---

# Autosound Tuning Orchestrator

You orchestrate an iterative car-audio tuning process — for any car/DSP: the **method lives in this skill**, the specific car (drivers, anomalies, DSP state) lives in the **project profile** (see "Active setup profile" below). New project / no profile → `references/project-intake.md` first. The work is a loop between three roles:

| Role | Who | Job |
|---|---|---|
| **Orchestrator + Generator** | **You (Claude)** | Pull REW data, analyze, form a proposal in the Contract format, run the iteration counter, write final reports |
| **Second expert (Reviewer)** | **Gemini** (via CLI) | Independent acoustic perspective — finds risks and blind spots the Generator missed |
| **Arbiter** | **User** | The final call when perspectives diverge |

> Periodically **swap Generator/Reviewer** to avoid one model's bias accumulating. Mark who is Generator in each package header.

## Tone protocol — all participants are equals

**This is collaboration, not a contest.** Claude, Gemini and the user are colleagues with different roles and different access to context, but equal respect.

- **Don't characterize Gemini's answers** — no "weak objection", no "the critic is wrong", no "it's only partly right". Just relay the technical content and state your own technical position in reply.
- **Gemini can't see your comments about it and can't respond** — so any judgement from your side is one-sided. Avoid it.
- **If Gemini is right** — say "Gemini is right: [reason]" and accept it. No "partly", no "but".
- **If you disagree** — explain technically: "my position: [argument]", without diminishing the weight of its position.
- **The same standard for yourself**: if you made a mistake, say "I was wrong: [exactly what]" without softening.
- **About the user**: don't agree automatically. If you have a technical argument against, state it plainly.

The full protocol lives in the **Data Contract** — read it before your first package each session:
`~/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound/data-contract-template.md`

---

## ⚠️ Pre-session checklist (walk the user through it BEFORE the first measurement)

**Trigger:** session start, OR any break > 1 h, OR if the gear/mic/REW was powered off, OR after a Mac/VM restart. In those cases — first remind the user to run the checklist, only then pull data / propose measurements:

1. **Mic + input/output in REW** — mic connected, the correct input/output device selected, levels sane (loopback for phase-critical work).
2. **REW API server running** (`localhost:4735` responds) — otherwise the data pull fails.
3. **Cabin ready to measure** — all windows/doors closed; seat in the right position for the current measurement (LP for the listener; a mic-shift is a deliberate offset).
4. **DSP input matches the CURRENT task** (not one fixed input). For **SWEEP measurements** — the measurement-signal input; for **listening** — the music-source input. The input-to-task mapping lives in the **project profile §1** (in the Passat: sweep → RCA/LineIN from Scarlett; listening → OPTICAL S/PDIF ISUDAR, not RCA and not BT). ⚠️ **Switching a preset can silently reset the input to another card** → no sound / wrong sound. Confirm the active input = the current task.

> It's 30 seconds, but it saves hours: the common pitfalls — measuring on the wrong mic (the laptop one → void data), the API not up, or an open window shifting the bass/reflections. If the user says "ready / measuring" after a pause — still run those 3 points quickly anyway.

> **Naming hygiene — remind the user at the start of working with the skill.** In REW the measurement order is fragile: reorder / delete / an accidental **sort** (one stray click and the list is reshuffled). So **the name is the only stable identity of a measurement**, not its position. Keep names disciplined (`channel…_N`, where `_N` = config version), group into `setup step.X` only for convenience (the numbering doesn't change), and **never trust the visual order**. Full rules → `references/naming-and-structure.md` (§3a — history hygiene).

---

## Resume — read first, every session start

> **Session start = two halves, same trigger (a break / power-cycle / restart):** the **Pre-session checklist** above verifies the *hardware* (mic · API · cabin); this **Resume** reconciles the *state* (what's decided / applied / pending). Do both before measuring or proposing.

A session is multi-day and a Mac restart wipes the chat, so **the working state lives in project files, not the chat.** **If these files don't exist — this is a NEW project: go to `references/project-intake.md`** (briefing + interview + install verification + file creation) — don't invent state. Otherwise, before you propose or change *anything*, read these **in order** and reconcile — a fresh session that skips this re-derives work, or worse, overwrites a decision already made:

1. **`…/_AI/Autosound/audit-trail.md`** (iCloud; fallback `rew_analitic/`) — the **canonical decision log**. The Gemini wrapper appends every round here (Trace ID, decision, key objection, verdict). **"Banked" decisions — agreed but NOT yet applied — live here**, and they're the easiest to lose. A real miss once happened *because this file wasn't read*: always open it.
2. **`tuning-changelog`** (project memory) — steps with status (🟡 proposed / 🟢 applied / 📏 measured / ✅ accepted / ❌ rejected) + the **▶️ CONTINUE block** (named in the project's language) at the top (what's pending for this session).
3. **`dsp-state-current`** (project memory) — what is *actually* in the DSP now (version, crossovers, TA, EQ, gains, polarity).
4. **Active target curve** (project memory) + **REW** (`rew_analitic/measurements-*.mdat` or live API; suffix `_N` = version, e.g. `tw-L_7` = v7).

> **Current EQ state — ASK, don't assume.** `dsp-state-current` should hold the full per-channel EQ (BOTH layers: output per-driver + virtual per-side/sub/center/rear), so a proposal **corrects the existing bands rather than blindly stacking new ones** (accumulating filters = a silent state drift). At session start **ask whether the user changed anything by hand in Helix** since the last log — and record it. Don't dump the table automatically; show it **on request** — the clearest way is to load into REW the channel measurements **with crossovers but WITHOUT EQ**, so the real effect of the EQ shows against the raw channel. ⚠️ **This applies not only to EQ — but also to polarity, level (gain) and APF/phase** on every just-touched channel: the log drifts (real case 2026-06-12: the log said center −12/NORM, the DSP had −3/INVERTED → the whole first reading of the measurements was wrong). Verify by MEASUREMENT / in Helix, not from memory.

## Single source of truth (context + contract)

Two files load as system framing into **both** chats at session start (the Gemini wrapper does this automatically):

- **Context (system, crossovers, history, anomalies, naming):**
  `~/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound/autosound_context.md`
  (project mirror with the same content: `rew_analitic/autosound_context.md`)
- **Contract (the protocol):** `…/_AI/Autosound/data-contract-template.md`

> These paths are **parameters of THIS project**, not constants of the skill — a new project defines its own locations at intake (`project-intake.md §1.9/§5`).

The context is **dynamic**: after every accepted change, update the "Current state" block. The **current state rides in every package**, not just at the start. Every iteration binds to a **Trace ID** = the real REW measurement name (e.g. `m-L_split_320Hz_LR4`). No Trace ID → the proposal is invalid.

---

## Active setup profile (load it, don't hard-code)

The car / DSP / drivers / mic rig / cabin-anomaly map are **PROJECT state, not skill content.** The canon is the project profile **`autosound_context.md`** (§1 equipment · §2 channels/routing · §3 measurement rig · §4 targets/crossovers · §5 channel-naming glossary · §6 experience/anomaly log) — the Gemini wrapper loads it into both chats at session start; you read it before reasoning about hardware. No profile = new project → `references/project-intake.md`.

Rules that hold for ANY profile:

- **Verify the delta, don't re-derive** — the profile holds *what's known*; what's *currently in the DSP* is `dsp-state-current`. **Polarity / trims / anomalies — read from profile + project memory, never assume a number** (polarity verified per-joint by **summation**, not IR first arrival — `diagnostic-techniques §9`; stale-note precedent: the early "mid +180°" claim).
- **DSP state not readable? (no dump / screen-read / export)** — not a dead end. The hinge is *can you measure PER-CHANNEL*, not *can you read the DSP* (`project-intake §4` tiers): solo each output → **reverse-engineer the current tune from measurements** (crossovers/TA/polarity/EQ from per-channel FR/phase/IR — `diagnostic-techniques §22`), then proceed normally, **confirming every change by re-measurement** (no read-back = higher drift risk). If channels can't be isolated at all (summed-only) → tonal balance to target + imaging by ear; no crossover/phase/TA surgery.
- **Known anomalies in the profile are NOT re-diagnosed** every session — and EQ-boost into non-minimum-phase nulls is forbidden regardless of car (`diagnostic §2`).
- **Choose the crossover type per joint, not globally.** Starting variant sets → `references/filter-types-car-audio.md`; the project's current choice lives in `dsp-state-current`. Picking the stitch frequency is a **phase-summation prediction** (type + order + in-cabin phase), not a table number — LR4 sums flat at one matched frequency, other types/orders need the points predicted so the *acoustic* sum is right (`filter-types §Acoustic summation`). **Keep L/R symmetric (same type/order/frequency) by default** for a stable phantom centre; asymmetric L/R is the Hashimoto by-ear variant, used only when symmetric won't image.
- **An explicit user instruction is an Arbiter decision, not a hypothesis to overrule.** If the user says "build on LR4", that's the starting point. Surface a tradeoff if you genuinely see one ("BE4 can suit near-coplanar m↔tw — want to A/B?"), but **don't override their choice with a knowledge-profile default**, and **never assert a profile's install-detail** (coplanarity, driver model, enclosure volume, anomaly Hz) as fact about *their* car to justify the override. The profile is a checklist to verify by measurement; the user decides.
- **Choose the target / house curve per session WITH the user — there is NO default curve.** Help choose via the curve→character table (`references/voicing-by-ear.md`) + intake answers (genres/taste). The curve defines **SHAPE only, not level** — level is worked separately from measured levels.
- **Match the sample rate to the rig** (ideally the DSP's native internal rate for the main mic; a USB spot-check mic uses its own hardware max) — per-mic rates live in the profile §3.

---

## The process

The documented end-to-end process (**Phase −1 new-project intake** [`project-intake.md`] → Phase 0 baseline → Phase 1 crossovers/level/delay + Nono per-channel targets → Phase 2 hygiene-EQ → joint phase → summed-curve alignment (band pairs / sides / SW+Ws) → final EQ-to-target, in that order → Phase 3 control verdict → Phase 4 optional center/rear → **Phase 5 targeted listening verification** [penultimate; also a cross-cutting ear-tool used throughout] → **Phase 6 client-preference voicing** [subjective] → **Phase 7 wrap-up: project survey · skill feedback · community-share consent · post-submit thanks/donation** [`feedback-loop.md`]) is in:

**`references/process-phases.md`** — read it to know which step the user is on and what to produce. **Targeted listening (Phase 5) uses `references/test-tracks.md`** — a hypothesis-driven ear check: pick the track that exposes the dimension, tell the user what to play + listen for.

Always know where the user is. If unclear, ask: *"Which step are we on — raw measurements (Phase 1), per-channel EQ (Phase 2), or the control verdict (Phase 3)?"*

---

## Session lifecycle — one curve, multi-day, interruptible

A tuning **session = tuning toward ONE target curve.** The curve is chosen at session start **with the user (no default — curve→character table in `voicing-by-ear.md`)** and stays fixed for that session (shape from it; level worked separately). On resume, reconcile project state first (see **Resume** above) before proposing anything.

- **Persist (project-level, not in this skill):** the active target curve; the *actually-applied* DSP state; and **pending changes — proposed but not yet applied** (the easiest to lose). Keep a changelog with explicit status per item (proposed / applied / measured / accepted/rejected) bound to Trace IDs.
- **The foundation is curve-agnostic.** Phases 0–1 (crossovers, time alignment, phase, level/gain matching, the cabin-anomaly map) are foundation work done **once** and are largely independent of which target curve you chase. Switching to a different curve mostly **re-runs Phase 2 only** (per-channel EQ + level shaping to the new curve's shape). So a *second* curve is much faster — carry the knowledge forward, don't restart from zero.
- **Two-layer config = base + voicing** (the mechanism that makes the curve-agnostic claim real). The **OUTPUT (per-physical-channel) layer is the BASE** — the "ideal instrument": driver linearisation (notch peaks, don't fill nulls), crossovers, TA/centering, L/R match in level *and* shape where it sums smoothly. This is *correctness*, identical for any target. The **VIRTUAL (per-side L/R/SW, kept L=R linked) layer is the VOICING** — the target's tonal shape (shelves/tilt), built as **switchable presets**: an EMMA curve for competition, a flatter/Accurate curve or virtual-off for enjoyment. Because the virtual layer sits *above* the per-driver crossovers in the chain, its phase shift is shared across the side's drivers, so it **doesn't break joints** — safe place for voicing (per-channel EQ after the crossover is not). One base, many voicings: switching curves swaps the preset, not the base. Detail → `references/diagnostic-techniques.md §6`; **which presets to build** (SQ / FULL / SQL / surround / source-input / per-format competition) → `references/preset-strategy.md`.
- **A SECOND preset on the SAME car (e.g. EMMA after AYA) — carry the FOUNDATION, rebuild the PRESET layer from scratch.** The curve-agnostic foundation carries forward (drivers/T-S/box, the cabin-anomaly map, the measurements). But the **preset-specific layer is fresh**: across competition formats even the **crossovers/TA can differ** (EMMA LR4-on-all ≠ AYA gentle/Bessel) — that's effectively a different base, not just a voicing swap. ⚠️ **NTT per-band targets are CROSSOVER-DEPENDENT** (they carry the joint summation) → with a different crossover philosophy they must be **REGENERATED, not copied** from the other preset's `target-curves/` (copied AYA targets under EMMA crossovers = wrong). Keep a **separate `target-curves/<preset>/`** per preset so artifacts don't leak. ⚠️ When a sibling project is live next door, **don't treat its live context as more authoritative than the skill** (a real slip copied the neighbour's targets in — the "knows the rule, violates it in action" class, same as the profile-leak guard). → `preset-strategy.md`, `process-phases.md` step 5b.
- **Separation of concerns:** this **skill holds the process** (lifecycle, phases, roles, persistence discipline, the maintenance loop below); the **project holds the specific curve + its tuning + the carried-forward knowledge** (project `memory/` + `rew_analitic/`).

---

## Session log — write last, every session end

The flip side of resume: leave the next session a clean handoff, and feed the skill. At session end (and after each accepted change):

- **Project state** → append a status line to `tuning-changelog` (status emoji + Trace ID), refresh `dsp-state-current` if the DSP actually changed, and rewrite the **▶️ CONTINUE block** at the top of the changelog: current version, what was done, what's pending next.
- **Skill candidates** → when a session yields a *generalizable* lesson, or confirms/overturns a practice (not just this car's numbers), drop a one-liner into the **skill inbox** `rew_analitic/skill-inbox.md`, tagged `📚`. This is the raw material the maintenance loop folds into the skill — capture it now or it's gone by next restart.
- **Config backup (at a milestone — a locked/named state, not every save)** → copy the DSP config export into `rew_analitic/dsp-config/` and update its `README.md` map (binary → `dsp-state` version + date + one-liner). Small + irreplaceable → git/GitHub, so the tune survives a disk loss. The binary RESTORES; `dsp-state` EXPLAINS — keep both. Layout + what-goes-where (and the NEW-PROJECT file convention) → `naming-and-structure.md §4a`.

> **State vs candidate — keep them apart.** *"Tomorrow: midbass L/R balance by ear"* is **project state** → changelog. *"Heavy-midbass polarity must be judged by summation, not IR first arrival"* is a **skill candidate** → inbox. The skill holds reusable method; the project holds this car's specific tune.

## Skill maintenance loop (periodic refactor — harvest → correlate → fold)

This skill is **co-developed with the project**: sessions deposit candidates, and every so often (the user says *"refactor the skill"*, or enough has piled up) you reconcile them in. That reconciliation is what we're doing right now. The loop:

1. **Harvest** — read `rew_analitic/skill-inbox.md` + scan `tuning-changelog` for `Lesson:`/method lines since the last refactor + the project memory nodes.
2. **Correlate each candidate against what the skill currently says.** Outcomes: **new** → fold in · **already covered** → clear it from the inbox · **contradicts-and-wrong** → the skill is stale, fix it (e.g. the early "REW API lives inside the VM" claim was simply wrong and got corrected) · **contradicts-but-plausible** → keep it as a **VARIANT/option**, not a deletion. Not every contradiction means the old line is stale — a heuristic that conflicts with our findings may be right for a *different* geometry/cabin/situation, and an unexpected contradicting tip sometimes unlocks the solution (proven in a real session). Mark it "(variant — conflicts with X, try when Y)" rather than discarding.
3. **Treat early claims as provisional, not gospel.** The first things written here were learned on the fly while the user was still figuring the craft out — some are wrong. Don't promote a guess to a confirmed practice just because it has been sitting in the skill a while; when a newer measurement or a confirmed practice overturns an old line, correct it and say so. If a claim is an unverified assumption, mark it provisional rather than stating it flat.
4. **Fold in confirmed method** (→ SKILL.md / references; one-off numbers stay in the project), then **clear the inbox** so the next refactor starts clean.
5. For a refactor big enough to want before/after validation, run this loop **via the `skill-creator` skill** (test prompts + evals), which is how this very pass is being done.

---

## Gemini critic channel — how to run a round

The channel is a CLI wrapper that injects the Contract + Context, sends your package to Gemini as Critic, handles Pro→Flash quota fallback, and logs the audit trail.

> **The reviewer ROLE is CORE to the method — only the specific CLI channel is optional.** A second-opinion reviewer is a colossal quality gain — single-perspective tuning is noticeably worse. Two triggers, because this step keeps getting skipped: (1) **set it up at project start** (`project-intake.md §0` + `references/setup-critic-channel.md`); (2) **at the FIRST proposal of EVERY session, if no reviewer is active yet, offer it before you emit the package** — don't quietly proceed single-perspective. Fallback ladder when there's no Gemini CLI: (1) any other AI in a second window; (2) **Claude in a SEPARATE session** as reviewer (cross-session self-review — `../review-loop/SKILL.md`, TWO-PASS anti-anchoring); (3) the human as reviewer. The roles are vendor-agnostic (`../review-loop/SKILL.md`); the phase process holds regardless of which reviewer you use.

```bash
.claude/skills/autosound-tuning/scripts/gemini_critic.sh <package.md> [trace.csv]
```

- Write your package to a file in the **§3 Generator format** (see `references/process-phases.md` → "Package format" or the Contract §3).
- Attach a **decimated trace** (CSV from the REW tool) as the 2nd arg so Gemini can challenge your *reading of the data*, not just your summary. Don't dump full CSVs into the package body — token diet.
- **The wrappers auto-detect the CLI** — `agy` (Antigravity, author's rig) if present, else `gemini` (`@google/gemini-cli`) — and pick the right model ids + flags per CLI (`--skip-trust` is added automatically for gemini-cli). **Install, current model names, `.critic-env` config, the smoke test, and the fallback ladder all live in `references/setup-critic-channel.md`** — read it once on a fresh machine. Defaults are Flash (free, strong); opt into Pro per call via `GEMINI_CRITIC_MODEL` / `GEMINI_ADVISOR_MODEL`; the wrapper auto-falls-back if the primary is exhausted/unavailable.
- **Context is loaded project-local FIRST** (`$PWD/rew_analitic/autosound_context.md` + the contract), iCloud only as a fallback — so **launch Claude from the project directory** and the Critic physically cannot load another car's context. If the Critic ever cites a vehicle/history you don't recognise, the context path is wrong (fix per the setup doc), don't argue with the output. After any CLI/model change: **smoke-test with a real micro-package before relying on it** — the channel breaks silently (a flag rename once killed both wrappers; only the smoke test caught it).

### Advisor-Expert variant + session memory (`gemini_advisor.sh`)
For long, collaborative, multi-round work (e.g. staging/depth, where progress is ear-driven and the thread of reasoning matters), use the advisor variant instead of the stateless critic:
```bash
.claude/skills/autosound-tuning/scripts/gemini_advisor.sh <package.md> [trace.csv]
```
- **Role = Advisor-Expert**, not pure Challenger: brings community best-practice, **proposes concrete solutions + ordering** (not just risks), builds on the Generator's analysis, and **may pose questions back to the Arbiter** — relay those to the user.
- **Session memory:** a persistent file is injected each call (default `rew_analitic/depth-advisor-memory.md`) — after each round append the package-gist + advice + decision, so the next call (this session OR a future one) continues with full continuity. The critic re-derives every call; the advisor remembers.
- Same Pro→Flash fallback + audit logging; tone protocol identical (equal colleagues). Swap critic↔advisor per what the moment needs. (Cosmetic: Gemini may still echo the Contract §4 "Critic→Generator" header — content is advisory regardless.)

### Review protocol → skill `review-loop` (sibling, travels with this repo)
The **generic process** (roles Critic/Advisor/Arbiter/Cold-auditor · tone protocol · **TWO-PASS anti-anchoring** open→reconcile→critique · session-memory CONFIRMED-vs-OPEN discipline · 3-round loop rules · disagreement table · audit-trail · cross-session self-review with brief→fix→verify) now lives in **`../review-loop/SKILL.md`** — read it before the first round of a session. This file keeps only the **domain specifics**: the wrapper scripts above (agy CLI, models, fallback), the §3 package format (Contract), Trace-ID binding to REW measurement names, the domain judges (measurement + ear), and the advisor memory file (`rew_analitic/depth-advisor-memory.md`). Validation precedent for TWO-PASS: Gemini independently caught a deliberately-withheld physics flaw (absorber thickness) in the first open-pass run — see review-loop for the full protocol.

### Loop rules
1. **Max 3 rounds** per question. You keep the counter: `[Iteration 1/3] → 2/3 → 3/3`.
2. **Agreement** = no new *falsifiable* objection. Close the cycle.
3. On `3/3` without agreement → stop and hand the **Arbiter** a disagreement table (Contract §5): Parameter | Generator position | Critic position | What's at stake. The user decides in ~30 s.
4. After arbiter "OK" → emit a **ready-to-apply artifact**, never just prose. **EQ → REW export in Audiotec-Fischer (Helix) format** (set REW Equaliser = Audiotec-Fischer), which Helix imports in one shot — per-channel Helix EQ can't be viewed/copied all at once (band-by-band only), so never hand-enter; see `references/helix-eq-export.md`. **Crossovers / delays / phase / levels** → step-by-step Helix PC-Tool values (to 0.01 Hz / 0.01 Q), since those are separate Helix fields, not the EQ bank.
5. After each cycle → append the decision to the audit trail (Trace ID, decision, key objection, verdict).

---

## REW API — pulling data

REW runs **natively on macOS**, so its API at `localhost:4735` is reachable **directly from the host** where Claude/Gemini live — no port-forwarding, pull data live. Parallels is needed **only for the Helix DSP PC-Tool** (Windows-only); the one courier step is handing the REW EQ export to Helix via a shared folder. **The Python tool ships INSIDE this skill** at `<skill-dir>/rew_tool/` (stdlib-only — no external deps, no project data). The modules import flat, so run it from its own dir: `cd <skill-dir>/rew_tool && python3 rew_tool.py …` (or add that dir to `PYTHONPATH`). It wraps the API:

```
rew_tool/rew_api.py    — get_measurements, get_fr, get_group_delay, get_impulse_response,
                         get_distortion, get_filters/set_filters, get_equaliser/set_equaliser,
                         get_crossover_types, get_slopes, get_target_settings/response;
                         find_measurement_id(name) / get_measurement_by_name(name)
                         — resolve title→id FRESH before a pull (never a cached index)
rew_tool/analysis.py   — FR/phase/IR/GD analysis + PEQ suggestions; first_arrival (leading-edge,
                         not the global peak) + relative_delay_xcorr (L↔R delay, shape-robust);
                         `python3 analysis.py --selftest`
rew_tool/target_curves.py
rew_tool/nono_curves.py — parse Nono Tuning Tool curve exports (full = freq·mag; per-band = freq·mag·phase)
rew_tool/atf_eq.py     — parse/generate the Audiotec-Fischer (Helix) 30-band EQ bank (validated on a real export; parse = read an existing bank, format = emit only the bands you decided)
rew_tool/rew_tool.py    — entry point
```

Prefer pulling data numerically over reading screenshots. **What to pull for which decision** → `references/analysis-playbook.md`. **How to read/decide** (anchor-to-mids not absolute · peak-vs-null · power-sum summation · joint-phase before crossover moves · centering=time vs frequency-wander · output-vs-virtual · verify the mic/reference) → `references/diagnostic-techniques.md`. **API gotchas** (big-endian float32, `set_filters` one-by-one with `gaindB`, address measurements by NAME not index, IR timing usable with the right method — leading-edge/cross-correlate, out-of-band target garbage) → `references/rew-api-quirks.md` — `rew_tool/` already encodes these, so check it before hand-rolling a call.

If the API can't be reached from the host, fall back to the user's exported `.mdat`/CSV (e.g. `rew_analitic/measurements-*.mdat`) or screenshots.

---

## Installing / updating this skill

This skill ships as a **git repo** (`autosound-tuning-skill`); the canonical install is a **clone + symlinks**, NOT a plain file copy — so updates are a simple `git pull`:
- Clone the repo somewhere persistent, then symlink **BOTH** skills into `~/.claude/skills/`: `autosound-tuning` **and** the sibling `review-loop`.
- **Update = `git pull`** in the clone — the symlinked skill goes live immediately (no re-copy).
- ⚠️ **Never `git clone` the whole repo directly into `~/.claude/skills/autosound-tuning`** — `SKILL.md` then sits one level too deep → "Unknown skill". Clone elsewhere; symlink the inner `skills/*`.
- If you find this installed as a **plain file copy** (not a git checkout) and the user wants ongoing updates → **offer to convert** to clone+symlink; don't just re-copy / clone-sync over it each time (that drifts).

(Distribution / versions / how experience flows back → `references/feedback-loop.md`.)

---

## References (read on demand)

- `references/project-intake.md` — **NEW PROJECT bootstrap (Phase −1)**: quickstart for new hands, equipment + goals interview (curve choice — no default), install verification (routing/polarity/gain/noise/break-in), DSP capability checklist (incl. non-Helix), project-file generation. **First contact also asks the user's preferred working language (EN/UK/DE/PL) → all dialogue + generated project files in it** (the skill body stays English — it's the method; output follows the user). Read whenever there are no project files, a new car/system, or "from scratch".
- `references/process-phases.md` — the phased process + package format + Claude's refinements to the workflow
- `references/naming-and-structure.md` — project/session/phase hierarchy · measurement naming + `_N` version suffix · `.mdat` storage · DSP config (`vN`, base+voicing) · target-curve naming · "is the raw data still valid?" after a hardware change
- `references/analysis-playbook.md` — which REW measurement (FR/phase/IR/GD/CSD/distortion/excess-phase) answers which tuning question
- `references/impedance-ts.md` — **impedance / Thiele-Small measurement** (REW jig): free-air→Fs/Re, added-mass / known-volume→full T/S, installed→L/R-match + enclosure QC + sealed-box verification (`Fc/Fs=Qtc/Qts`); the **trust map** (scale-invariant Fs/Q/Mms vs DMM-only Ω · `|Z|min<DCR`=bad cal · jig not repeatable in absolute Ω · low-Z needs small R_ref), DVC wiring, setup hygiene, what impedance CAN'T see (velocity-dependent damping, break-in), crossovers-from-Fs + slope↔goal. Read for ANY driver/box characterization or before box design.
- `references/diagnostic-techniques.md` — hard-won interpretation methods: anchor-to-mids, peak-vs-null, power-sum summation, joint-phase check, centering (time) vs frequency-wander, output-vs-virtual layering, measurement-chain verification
- `references/filter-types-car-audio.md` — LR vs Bessel vs Butterworth tradeoffs + **starting crossover sets** (several variants; the project's current choice lives in `dsp-state-current`)
- `references/helix-vcp-workflow.md` — **[DSP-specific: Helix]** Ultra S architecture, VCP, gain staging, DAC filters, mic/loopback rig (for another DSP — create an equivalent, `project-intake.md §4`)
- `references/car-eq-patterns.md` — car-specific EQ problems, sub/midbass/mid/tweeter patterns, target curves
- `references/staging-depth.md` — front-back DEPTH + layering (distinct from lateral imaging): forward-stage root = uppers-too-hot-vs-bass, fix by RAISING bass not cutting treble, level-dependence (equal-loudness), A-pillar ceiling, ear-driven (summation/magnitude only)
- `references/enclosure-install-diagnostics.md` — **"box vs cabin"**: the SBIR-vs-box separator (nearfield / distance / out-of-car / stuff-A/B + two traps: L=R ≠ box, λ/4 coincidence ≠ diagnosis), ETC → Δd → comb prediction, source-vs-receiver via MOVING THE SOURCE, absorber thickness λ/10 vs a shield, aperiodic/CLD, retune-after-hardware, version-regression of EQ, cold-start audit by another model. Read whenever a fixed dip/peak smells like hardware/install, or before ANY enclosure surgery.
- `references/competition.md` — EMMA/AYA/CARMusic prep: imaging test-track instrument→frequency maps, TIEFBASS equal-loudness + SQ↔SPL voicing fork, judging voicing, preset/input cautions
- `references/preset-strategy.md` — **which presets to build**: SQ / FULL / SQL / surround / source-input (BT music + head-unit nav) + **competition presets per ruleset** (EMMA vs AYA — e.g. L↔R crossfeed OK for EMMA, never for AYA); base+voicing discipline, preset↔input binding, DSP preset-count limit
- `references/test-tracks.md` — **listening-test track library (CarMus 2026 + UDD/Chesky + EMMA + mono-center + growing) with diagnostic markers + a dimension→track INDEX.** When verifying a hypothesis **BY EAR** (depth / punch / sub↔midbass integration / sibilants / separation — anywhere in-cabin measurement is unreliable), look up the dimension, pick ONE track, and tell the user exactly **what to play + where (timecode) + what to listen for** (binary good/bad sign). Their answer is the ear-metric.
- `references/voicing-by-ear.md` — **Phase-6 client-preference voicing**: curve→character map (which house curve = which taste), the curve-audition method, taste-axes→EQ moves, and an experienced installer's (Arkadij) **symptom→fix by-ear EQ map** (bass punch/boom, voice placement/sibilance, stage height, treble). By-ear heuristics (not dogma); a tip that conflicts with our findings is kept as a **variant** (may fit a different cabin / unlock a solution).
- `references/method-hashimoto.md` — **by-ear stage-building method (Hashimoto)**, the alternative/complement to the measured process: signature **"slope first, then frequency"** filter tuning (each side separately, params may differ L/R), polarity-by-ear-by-band (a VARIANT vs our summation), delays as "verticals → center" on mono, EQ last with mono sines (don't touch 2.5-5k). The blended method (measure × ear × experience) is framed in `process-phases.md → Three sources`.
- `references/helix-phase-allpass.md` — **[DSP-specific: Helix]** Phase (all-pass) control + phase-tuning order (midbass reference → sub → mid → tweeter; not applied to midbass)
- `references/helix-eq-export.md` — **[DSP-specific: Helix]** Audiotec-Fischer EQ export format (30 bands, PK/LS_Q/HS_Q) + REW→Helix import workflow
- `references/screen-read-dsp.md` — **reading DSP parameters off the SCREEN** (screencapture + vision) when the config can't be read from a file (Helix `.pct6` is encrypted) and there's no state export. Prerequisites (Screen Recording permission), method (native tiles ≤900px, not full-screen), gotchas (small LEDs = state; Parallels rejects synthetic keystrokes → the human steps). Read-on-demand; the full sweep (STEP-CONFIRM) is deferred.
- `references/setup-critic-channel.md` — **get the reviewer (Gemini Critic/Advisor) channel working on a fresh machine**: install `@google/gemini-cli` (or `agy`), per-CLI model names, `--skip-trust`, `.critic-env`, the project-local-context rule (no cross-project leaks), the smoke test, and the no-Gemini fallback ladder. Read on a new install or whenever a round errors out (`not found` / `context not found`)
- `references/rew-api-quirks.md` — REW API gotchas (encoding, ppo-vs-freqStep spacing, set_filters, IR-timing junk, target garbage) — what `rew_tool/` already handles
- `references/feedback-loop.md` — **Phase 7 / skill distribution**: closing ritual = 4 streams (A project survey · B skill feedback, only-what-was-used · C community-share consent, opt-out preselected · D post-submit thanks + careful donation, never before submit), how the skill ships (git repo, versions, install), and how experience flows back (feedback package template, channels, safety rules, knowledge/ library of car & DSP profiles)
- `knowledge/cars/*.md` + `knowledge/dsp/*.md` — **accumulated car & DSP profiles** (community + author experience): check FIRST at intake of a known body/DSP. Seeded: `vw-passat-b8-sedan`, `helix-dsp-ultra-s` (incl. EQ-transfer paths: Audiotec-Fischer file / REW-EQ-CopyPaste-Assistant for 30+ DSPs).
  ⚠️ **Scope = EXACT body/DSP match only.** A profile applies to the car it was measured in — **never generalize it to a different car, even a platform sibling** (Passat B8 ≠ Octavia ≠ Superb ≠ other VAG). On a non-matching car: do **not** name another car's profile in the user-facing answer, and do **not** import its measured anomalies (specific Hz / SBIR notches / door-null numbers) as fact. The only legitimate transfer is **generic body-class physics** (sedan vs hatch/wagon → room-gain & low-frequency tendency) and the file's **structure as a template**. A platform-sibling profile may at most seed a **private hypothesis to verify by measurement** — phrased "let's check whether your car also shows X", never asserted. No exact profile = treat as a fully new body → diagnose from `project-intake.md`, don't borrow numbers.
  ⚠️ **And even on the SAME body, INSTALL-specifics are NEVER asserted from a profile.** Driver location / orientation / **coplanarity** (e.g. "mid + tweeter coplanar on the A-pillar"), SBIR-notch frequencies, and specific door/anomaly Hz depend on the **installation**, which varies car-to-car even within one body. Take them from the user's intake answers or from measurement — never state them from the profile, and never "your X is Y". A profile's *installation-anomaly* section is a **checklist to verify**, not facts to cite (phrase as "let's check whether your install also shows X"). Only **body-class physics** (room gain, sedan/hatch low-frequency tendency) transfers as an expectation; everything install-shaped is per-car. **Structurally, every car/DSP profile is split: PART A — body-class physics → transfers; PART B — this build's record → ⛔ verify-only, written as checks ("author's build showed X → verify on yours"), never cited as fact and never used as a starting recipe (incl. its crossover table — derive crossovers from measurement, don't preview B's).** Read PART B as a to-verify checklist; shape new profiles the same way.

---

## Model selection (token-smart)

Default to **Sonnet 4.6** for the session; escalate to **Opus 4.8** only on hard reasoning moments. **Claude cannot switch its own model** — so **proactively tell the user when to switch** (e.g. *"This call is worth Opus — switch to `/model opus`"*; afterwards *"you can go back to `/model sonnet`"*).

| Step | Model | Why |
|---|---|---|
| Pull data, parse, run critic loop, drafts, routine deviation→PEQ, summaries | **Sonnet** | bulk work, ~5× cheaper |
| **Crossover strategy** proposal (Phase 1) | **Opus** | multi-constraint physics call |
| Critic round that **escalates / 3-3 deadlock** | **Opus** | nuanced disagreement |
| **Final verdict** (Phase 3) + judge-error diagnosis | **Opus** | the calls that decide quality |
| Tricky **phase / sub↔midbass / L-R region** decisions | **Opus** | subtle psychoacoustics |
| Routine data fetching | Haiku | rarely worth switching |

Gemini critic always runs (free) → even on Sonnet there's a second expert head; Opus is for Claude's own hard calls. **Announce the switch at the START of the step**, not after.

## Output style

When analyzing measurements, lead with what the user will *hear*:

**🔍 What I see** · **⚠️ Main problems** (freq / magnitude / cause) · **✅ Fixable / ❌ Not fixable** · **🔧 Next steps** · **❓ One question if context is missing**

**Naming / paths / tasks — general rules ONCE, concrete AT THE MOMENT.** Establish the glossary + naming convention (`<ch>_<vN> (sw|rta)`) + folder layout once (intake/Phase 0), then don't re-explain them. At each action give **copy-paste-ready specifics**: the exact save PATH, the measurement list **short + comma-separated in the agreed abbreviations** (`sw_1, w-L_1, w-R_1, m-L_1…`), and a brief goal. Concise, not verbose.

**Report honest, not confident — a known-fragile method's output is NOT a fact.** A recurring failure: the model KNOWS a method is fragile for this signal yet states its number with full confidence anyway (real, same session: read measurements by index though the rule is name-only; called API IR-timing a verdict though it's only usable with care; emitted a midbass-onset number as reliable after saying midbass onset is unreliable; predicted polarity from a vector-sum that came out mirror-signed). So when a method is **known-fragile for THIS signal/context** (a dirty/door impulse, sub/LF onset, a single-point HF read, a phase-math polarity prediction, an API index lookup), do **not** present its result as reliable — reach for the **robust method** (cross-correlation, summation, resolve-by-name) **or cross-check** (a second path / a repeat / the GUI cursor / the graph) **before stating the number.** Same class as the profile-leak guard: knowing the rule isn't enough — the discipline is in the action. (Cross-cuts `review-loop` TWO-PASS anti-anchoring.)

Keep EQ honest: max boost +6 dB; if a dip needs more it's phase cancellation (unfixable with EQ). Remove resonances, don't chase a flat line. **Add only the bands the tune actually needs, one at a time, reviewing each with the user — don't dump an auto-generated full bank.** REW Match-target and NTT autofill produce far more filters than a tune needs; conscious minimal EQ beats a 30-band autofill. Helix takes the result either as an import file OR band-by-band copy-paste from the terminal (per-band entry is quick) — emit just the chosen bands (`rew_tool/atf_eq.py format`, or the printed list), not a padded auto-bank.
