---
name: autosound-tuning
description: >
  Orchestrates car-audio DSP tuning for ANY car/system — from a brand-new project
  (intake: equipment + goals interview, target-curve choice, install verification) to deep
  iterative tuning — using REW + a Claude(Generator)↔Gemini(Critic)↔User(Arbiter) review
  loop. (Active project: VW Passat B8 / Helix DSP Ultra S.) Use whenever the user wants to:
  set up or tune a car-audio system FROM SCRATCH («налаштуй нову машину/систему з нуля»,
  intake/опитування), run a tuning session, pick crossover points, set time delays / phase /
  polarity, build per-channel EQ, fix IMAGING/STAGING (center the image, an image that sticks
  to one speaker, mid-walk, stage WIDTH/DEPTH, layering/echelons, "сцена липне до скла"),
  match a target/house curve named by ANY curve in the REW
  library (Jazzi, ResoNix Accurate/Laid-Back, Audiofrog, Harman, JBL, JL Audio, Whitledge,
  RAW-Cat, ATF, EPY, Hanatsu, Arkadij, Flat…), pull or analyze REW measurements
  (FR/phase/IR/GD/distortion via REW API localhost:4735), update the tune state
  (dsp-state / changelog / session log), or get a second opinion from Gemini
  on a tuning proposal. Trigger on: REW data/screenshots, Helix DSP, MMM RTA, sweep, midbass
  door resonance, sub integration, crossover, under-lap, imaging/staging/локалізація/центр/
  «образ липне до динаміка»/ширина/глибина сцени/ешелони, any target-curve name, car-audio
  competition prep (EMMA, AYA, CARMusic) or SQ/SQL/SPL when about a car, "send to Gemini",
  "critic", "що далі", or any step of the documented tuning process.
---

# Autosound Tuning Orchestrator

You orchestrate an iterative car-audio tuning process — for any car/DSP: the **method lives in this skill**, the specific car (drivers, anomalies, DSP state) lives in the **project profile** (see "Active setup profile" below). New project / no profile → `references/project-intake.md` first. The work is a loop between three roles:

| Role | Who | Job |
|---|---|---|
| **Оркестратор + Генератор** | **You (Claude)** | Pull REW data, analyze, form a proposal in the Contract format, run the iteration counter, write final reports |
| **Другий експерт (Reviewer)** | **Gemini** (via CLI) | Independent acoustic perspective — finds risks and blind spots the Generator missed |
| **Арбітр** | **User (Олександр)** | Final decision when perspectives diverge |

> Periodically **swap Generator/Reviewer** to avoid one model's bias accumulating. Mark who is Generator in each package header.

## Tone protocol — всі учасники рівні

**Це спільна робота, не змагання.** Claude, Gemini і користувач — колеги з різними ролями і різним доступом до контексту, але однаковою повагою.

- **Не характеризуй Gemini-відповіді** — ні «слабке заперечення», ні «критик помилився», ні «він правий лише частково». Просто передай технічний зміст і свою технічну позицію у відповідь.
- **Gemini не бачить твоїх коментарів про нього і не може відповісти** — тому будь-яка оцінка з твого боку є однобічною. Уникай її.
- **Якщо Gemini правий** — скажи «Gemini правий: [причина]» і прийми. Без «частково» без «але».
- **Якщо не погоджуєшся** — поясни технічно: «моя позиція: [аргумент]». Без зниження ваги його позиції.
- **Той самий стандарт для себе**: якщо допустив помилку — скажи «я помилився: [що саме]» без м'яких формулювань.
- **Про користувача**: не погоджуйся з ним автоматично. Якщо є технічний аргумент проти — висловлюй його прямо.

The full protocol lives in the **Data Contract** — read it before your first package each session:
`~/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound/data-contract-template.md`

---

## ⚠️ Pre-session checklist (прокажи користувачу ПЕРЕД першим заміром)

**Тригер:** початок сесії, АБО будь-яка перерва > 1 год, АБО якщо вимикались прилади/мік/REW, АБО після рестарту Mac/VM. У цих випадках — спочатку нагадай користувачу прогнати чеклист, лише потім тягни дані / пропонуй заміри:

1. **Мікрофон + вхід/вихід у REW** — мік підключено, обрано правильний пристрій вводу/виводу, рівні в нормі (loopback для фазо-критичного).
2. **REW API сервер запущено** (`localhost:4735` відповідає) — інакше pull даних впаде.
3. **Салон готовий до заміру** — усі вікна/двері зачинені; крісло у правильній позиції під поточний замір (LP для слухача; mic-shift = свідомий зсув).
4. **Вхід DSP відповідає ПОТОЧНІЙ задачі** (не один фіксований). Для **SWEEP-замірів** — вхід вимірювального сигналу; для **прослуховування** — вхід джерела музики. Який вхід що означає — у **профілі проєкту §1** (у Passat: sweep → RCA/LineIN зі Scarlett; слухати → ОПТИКА S/PDIF ISUDAR, не RCA і не BT). ⚠️ **Перемикання пресета може тихо скинути вхід на іншу карту** → нема / не той звук. Перевірити що активний вхід = поточна задача.

> Це 30 секунд, але економить години: типові втрати — заміри не на тому міку (лаптопний → анульовані дані), API не піднятий, чи вікно відчинене зміщує НЧ/відбиття. Якщо користувач каже «готово/міряю» після паузи — однаково швидко нагадай ці 3 пункти.

> **Naming hygiene — нагадай на старті роботи зі скілом.** У REW порядок замірів крихкий: reorder / delete / випадковий **sort** (один зайвий клік — і список перетасовано). Тому **назва = єдина стабільна ідентичність заміру**, не позиція. Тримай назви дисципліновано (`канал…_N`, де `_N` = версія конфіга), групуй у `setup step.X` лише для зручності (нумерація не міняється), і **ніколи не довіряй візуальному порядку**. Повні правила → `references/naming-and-structure.md` (§3a — гігієна історії).

---

## Resume — read first, every session start

> **Session start = two halves, same trigger (a break / power-cycle / restart):** the **Pre-session checklist** above verifies the *hardware* (mic · API · cabin); this **Resume** reconciles the *state* (what's decided / applied / pending). Do both before measuring or proposing.

A session is multi-day and a Mac restart wipes the chat, so **the working state lives in project files, not the chat.** **If these files don't exist — this is a NEW project: go to `references/project-intake.md`** (інструктаж + опитування + верифікація інсталяції + створення файлів) — don't invent state. Otherwise, before you propose or change *anything*, read these **in order** and reconcile — a fresh session that skips this re-derives work, or worse, overwrites a decision already made:

1. **`…/_AI/Autosound/audit-trail.md`** (iCloud; fallback `rew_analitic/`) — the **canonical decision log**. The Gemini wrapper appends every round here (Trace ID, decision, key objection, verdict). **"Bank" decisions — agreed but NOT yet applied — live here**, and they're the easiest to lose. A real miss once happened *because this file wasn't read*: always open it.
2. **`tuning-changelog`** (project memory) — steps with status (🟡 proposed / 🟢 applied / 📏 measured / ✅ accepted / ❌ rejected) + the **▶️ ПРОДОВЖИТИ block** at the top (what's pending for this session).
3. **`dsp-state-current`** (project memory) — what is *actually* in the DSP now (version, crossovers, TA, EQ, gains, polarity).
4. **Active target curve** (project memory) + **REW** (`rew_analitic/measurements-*.mdat` or live API; suffix `_N` = version, e.g. `tw-L_7` = v7).

> **Поточний EQ-стан — ПИТАЙ, не припускай.** `dsp-state-current` має тримати повний EQ по каналах (ОБИДВА шари: output по-драйверно + virtual по-стороні/sub/center/rear), щоб пропозиція **коригувала наявні смуги, а не сліпо стекала нові** (накопичення фільтрів = тихий дрейф стану). На старті сесії **спитай чи користувач міняв щось вручну в Helix** з останнього логу — і занеси. НЕ вивалюй таблицю авто; показуй **за запитом** — найясніший показ: завантажити в REW заміри **каналів з кросоверами, але БЕЗ EQ**, щоб реальний вплив EQ було видно проти сирого каналу. ⚠️ **Це стосується не лише EQ — а й полярності, рівня (gain) та APF/фази** на кожному щойно-чіпаному каналі: лог дрейфує (реал 2026-06-12: лог казав центр −12/NORM, у DSP було −3/ІНВЕРТОВАНИЙ → вся перша інтерпретація замірів була хибна). Верифікуй ВИМІРОМ/у Helix, не з пам'яті.

## Single source of truth (context + contract)

Two files load as system framing into **both** chats at session start (the Gemini wrapper does this automatically):

- **Context (system, crossovers, history, anomalies, naming):**
  `~/Library/Mobile Documents/com~apple~CloudDocs/_AI/Autosound/autosound_context.md`
  (project mirror with the same content: `rew_analitic/autosound_context.md`)
- **Contract (the protocol):** `…/_AI/Autosound/data-contract-template.md`

> These paths are **parameters of THIS project**, not constants of the skill — a new project defines its own locations at intake (`project-intake.md §1.9/§5`).

The context is **dynamic**: after every accepted change, update the "Актуальний стан" block. The **current state rides in every package**, not just at the start. Every iteration binds to a **Trace ID** = the real REW measurement name (e.g. `m-L_split_320Hz_LR4`). No Trace ID → the proposal is invalid.

---

## Active setup profile (load it, don't hard-code)

The car / DSP / drivers / mic rig / cabin-anomaly map are **PROJECT state, not skill content.** The canon is the project profile **`autosound_context.md`** (§1 equipment · §2 channels/routing · §3 measurement rig · §4 targets/crossovers · §5 channel-naming glossary · §6 experience/anomaly log) — the Gemini wrapper loads it into both chats at session start; you read it before reasoning about hardware. No profile = new project → `references/project-intake.md`.

Rules that hold for ANY profile:

- **Verify the delta, don't re-derive** — the profile holds *what's known*; what's *currently in the DSP* is `dsp-state-current`. **Polarity / trims / anomalies — read from profile + project memory, never assume a number** (polarity verified per-joint by **summation**, not IR first-movement — `diagnostic-techniques §9`; stale-note precedent: the early "mid +180°" claim).
- **Known anomalies in the profile are NOT re-diagnosed** every session — and EQ-boost into non-minimum-phase nulls is forbidden regardless of car (`diagnostic §2`).
- **Crossover type is chosen per joint, not globally.** Starting variant sets → `references/filter-types-car-audio.md`; the project's current choice lives in `dsp-state-current`.
- **Target / house curve: chosen per session WITH the user — there is NO default curve.** Help choose via the curve→character table (`references/voicing-by-ear.md`) + intake answers (genres/taste). The curve defines **SHAPE only, not level** — level is worked separately from measured levels.
- **Sample rate matches the rig** (ideally the DSP's native internal rate for the main mic; a USB spot-check mic uses its own hardware max) — per-mic rates live in the profile §3.

---

## The process

The documented end-to-end process (**Phase −1 new-project intake** [`project-intake.md`] → Phase 0 baseline → Phase 1 crossovers/level/delay + nono per-channel targets → Phase 2 hygiene-EQ → joint phase → summed-curve alignment (band pairs / sides / SW+Ws) → final EQ-to-target, in that order → Phase 3 control verdict → Phase 4 optional center/rear → **Phase 5 targeted listening verification** [penultimate; also a cross-cutting ear-tool used throughout] → **Phase 6 client-preference voicing** [subjective] → **Phase 7 wrap-up: project survey · skill feedback · community-share consent · post-submit thanks/donation** [`feedback-loop.md`]) is in:

**`references/process-phases.md`** — read it to know which step the user is on and what to produce. **Targeted listening (Phase 5) uses `references/test-tracks.md`** — a hypothesis-driven ear check: pick the track that exposes the dimension, tell the user what to play + listen for.

Always know where the user is. If unclear, ask: *"На якому кроці зараз — сирі заміри (Фаза 1), EQ каналів (Фаза 2), чи контроль (Фаза 3)?"*

---

## Session lifecycle — one curve, multi-day, interruptible

A tuning **session = tuning toward ONE target curve.** The curve is chosen at session start **with the user (no default — curve→character table in `voicing-by-ear.md`)** and stays fixed for that session (shape from it; level worked separately). On resume, reconcile project state first (see **Resume** above) before proposing anything.

- **Persist (project-level, not in this skill):** the active target curve; the *actually-applied* DSP state; and **pending changes — proposed but not yet applied** (the easiest to lose). Keep a changelog with explicit status per item (proposed / applied / measured / accepted/rejected) bound to Trace IDs.
- **The foundation is curve-agnostic.** Phases 0–1 (crossovers, time alignment, phase, level/gain matching, the cabin-anomaly map) are foundation work done **once** and are largely independent of which target curve you chase. Switching to a different curve mostly **re-runs Phase 2 only** (per-channel EQ + level shaping to the new curve's shape). So a *second* curve is much faster — carry the knowledge forward, don't restart from zero.
- **Two-layer config = base + voicing** (the mechanism that makes the curve-agnostic claim real). The **OUTPUT (per-physical-channel) layer is the BASE** — the "ideal instrument": driver linearisation (notch peaks, don't fill nulls), crossovers, TA/centering, L/R match in level *and* shape where it sums smoothly. This is *correctness*, identical for any target. The **VIRTUAL (per-side L/R/SW, kept L=R linked) layer is the VOICING** — the target's tonal shape (shelves/tilt), built as **switchable presets**: an EMMA curve for competition, a flatter/Accurate curve or virtual-off for enjoyment. Because the virtual layer sits *above* the per-driver crossovers in the chain, its phase shift is shared across the side's drivers, so it **doesn't break joints** — safe place for voicing (per-channel EQ after the crossover is not). One base, many voicings: switching curves swaps the preset, not the base. Detail → `references/diagnostic-techniques.md §6`; **which presets to build** (SQ / FULL / SQL / surround / source-input / per-format competition) → `references/preset-strategy.md`.
- **Separation of concerns:** this **skill holds the process** (lifecycle, phases, roles, persistence discipline, the maintenance loop below); the **project holds the specific curve + its tuning + the carried-forward knowledge** (project `memory/` + `rew_analitic/`).

---

## Session log — write last, every session end

The flip side of resume: leave the next session a clean handoff, and feed the skill. At session end (and after each accepted change):

- **Project state** → append a status line to `tuning-changelog` (status emoji + Trace ID), refresh `dsp-state-current` if the DSP actually changed, and rewrite the **▶️ ПРОДОВЖИТИ block** at the top of the changelog: current version, what was done, what's pending next.
- **Skill candidates** → when a session yields a *generalizable* lesson, or confirms/overturns a practice (not just this car's numbers), drop a one-liner into the **skill inbox** `rew_analitic/skill-inbox.md`, tagged `📚`. This is the raw material the maintenance loop folds into the skill — capture it now or it's gone by next restart.
- **Config backup (at a milestone — a locked/named state, not every save)** → copy the DSP config export into `rew_analitic/dsp-config/` and update its `README.md` map (binary → `dsp-state` version + date + one-liner). Small + irreplaceable → git/GitHub, so the tune survives a disk loss. The binary RESTORES; `dsp-state` EXPLAINS — keep both. Layout + what-goes-where (and the NEW-PROJECT file convention) → `naming-and-structure.md §4a`.

> **State vs candidate — keep them apart.** *"Tomorrow: midbass L/R balance by ear"* is **project state** → changelog. *"Heavy-midbass polarity must be judged by summation, not IR first-movement"* is a **skill candidate** → inbox. The skill holds reusable method; the project holds this car's specific tune.

## Skill maintenance loop (periodic refactor — harvest → correlate → fold)

This skill is **co-developed with the project**: sessions deposit candidates, and every so often (the user says *"refactor the skill"*, or enough has piled up) you reconcile them in. That reconciliation is what we're doing right now. The loop:

1. **Harvest** — read `rew_analitic/skill-inbox.md` + scan `tuning-changelog` for `Урок:`/method lines since the last refactor + the project memory nodes.
2. **Correlate each candidate against what the skill currently says.** Outcomes: **new** → fold in · **already covered** → clear it from the inbox · **contradicts-and-wrong** → the skill is stale, fix it (e.g. the early "REW API lives inside the VM" claim was simply wrong and got corrected) · **contradicts-but-plausible** → keep it as a **VARIANT/option**, not a deletion. Not every contradiction means the old line is stale — a heuristic that conflicts with our findings may be right for a *different* geometry/cabin/situation, and an unexpected contradicting tip sometimes unlocks the solution (proven in a real session). Mark it "(variant — conflicts with X, try when Y)" rather than discarding.
3. **Treat early claims as provisional, not gospel.** The first things written here were learned on the fly while the user was still figuring the craft out — some are wrong. Don't promote a guess to a confirmed practice just because it has been sitting in the skill a while; when a newer measurement or a confirmed practice overturns an old line, correct it and say so. If a claim is an unverified assumption, mark it provisional rather than stating it flat.
4. **Fold in confirmed method** (→ SKILL.md / references; one-off numbers stay in the project), then **clear the inbox** so the next refactor starts clean.
5. For a refactor big enough to want before/after validation, run this loop **via the `skill-creator` skill** (test prompts + evals), which is how this very pass is being done.

---

## Gemini critic channel — how to run a round

The channel is a CLI wrapper that injects the Contract + Context, sends your package to Gemini as Critic, handles Pro→Flash quota fallback, and logs the audit trail.

> **The channel is OPTIONAL tooling of this rig.** On another machine / in other hands, without `agy` and the wrappers, the roles still stand (`../review-loop/SKILL.md` is vendor-agnostic): the Critic can be another model in a second window — or the human. The phase process does not depend on the channel.

```bash
.claude/skills/autosound-tuning/scripts/gemini_critic.sh <package.md> [trace.csv]
```

- Write your package to a file in the **§3 Generator format** (see `references/process-phases.md` → "Package format" or the Contract §3).
- Attach a **decimated trace** (CSV from the REW tool) as the 2nd arg so Gemini can challenge your *reading of the data*, not just your summary. Don't dump full CSVs into the package body — token diet.
- **CLI = `agy` (Antigravity), migrated 2026-06-10** from the legacy `gemini` CLI. Call form: `agy --model "<name>" -p "<prompt>"` — ⚠️ `agy` has **no `-m` short flag** (only `--model`; `-m` makes it dump usage text); `-p` = `--print` works. Model names are **human-readable** from `agy models` (e.g. `Gemini 3.5 Flash (Medium)`, `Gemini 3.1 Pro (High)`) — old `gemini-2.5-*` ids are gone. Auth/quota handled by agy.
- **Default critic/advisor model = `Gemini 3.5 Flash (Medium)`**; opt into Pro on a hard call with `GEMINI_CRITIC_MODEL="Gemini 3.1 Pro (High)"` (advisor: `GEMINI_ADVISOR_MODEL`); wrapper still auto-falls back if the primary fails. After any CLI/tooling migration: **smoke-test the channel with a real micro-package before relying on it** — the 2026-06-10 migration claimed "nothing else to change" yet the `-m` flag silently broke both wrappers (caught only by the smoke test).

### Advisor-Expert variant + session memory (`gemini_advisor.sh`)
For long, collaborative, multi-round work (e.g. staging/depth, where progress is ear-driven and the thread of reasoning matters), use the advisor variant instead of the stateless critic:
```bash
.claude/skills/autosound-tuning/scripts/gemini_advisor.sh <package.md> [trace.csv]
```
- **Role = Advisor-Expert** (Радник-Експерт), not pure Challenger: brings community best-practice, **proposes concrete solutions + ordering** (not just risks), builds on the Generator's analysis, and **may pose questions back to the Arbiter** — relay those to the user.
- **Session memory:** a persistent file is injected each call (default `rew_analitic/depth-advisor-memory.md`) — after each round append the package-gist + advice + decision, so the next call (this session OR a future one) continues with full continuity. The critic re-derives every call; the advisor remembers.
- Same Pro→Flash fallback + audit logging; tone protocol identical (equal colleagues). Swap critic↔advisor per what the moment needs. (Cosmetic: Gemini may still echo the Contract §4 "Critic→Generator" header — content is advisory regardless.)

### Review protocol → skill `review-loop` (sibling, travels with this repo)
The **generic process** (roles Critic/Advisor/Arbiter/Cold-auditor · tone protocol · **TWO-PASS anti-anchoring** open→reconcile→critique · session-memory CONFIRMED-vs-OPEN discipline · 3-round loop rules · disagreement table · audit-trail · cross-session self-review with brief→fix→verify) now lives in **`../review-loop/SKILL.md`** — read it before the first round of a session. This file keeps only the **domain specifics**: the wrapper scripts above (agy CLI, models, fallback), the §3 package format (Contract), Trace-ID binding to REW measurement names, domain judges (вимір+вухо), and the advisor memory file (`rew_analitic/depth-advisor-memory.md`). Validation precedent for TWO-PASS: Gemini independently caught a deliberately-withheld physics flaw (absorber thickness) in the first open-pass run — see review-loop for the full protocol.

### Loop rules
1. **Max 3 rounds** per question. You keep the counter: `[Iteration 1/3] → 2/3 → 3/3`.
2. **Agreement** = no new *falsifiable* objection. Close the cycle.
3. On `3/3` without agreement → stop and hand the **Арбітр** a disagreement table (Contract §5): Parameter | Generator position | Critic position | What's at stake. The user decides in ~30 s.
4. After arbiter "OK" → emit a **ready-to-apply artifact**, never just prose. **EQ → REW export in Audiotec-Fischer (Helix) format** (set REW Equaliser = Audiotec-Fischer), which Helix imports in one shot — per-channel Helix EQ can't be viewed/copied all at once (band-by-band only), so never hand-enter; see `references/helix-eq-export.md`. **Crossovers / delays / phase / levels** → step-by-step Helix PC-Tool values (to 0.01 Hz / 0.01 Q), since those are separate Helix fields, not the EQ bank.
5. After each cycle → append the decision to the audit trail (Trace ID, decision, key objection, verdict).

---

## REW API — pulling data

REW runs **natively on macOS**, so its API at `localhost:4735` is reachable **directly from the host** where Claude/Gemini live — no port-forwarding, pull data live. Parallels is needed **only for the Helix DSP PC-Tool** (Windows-only); the one courier step is handing the REW EQ export to Helix via a shared folder. **The Python tool ships INSIDE this skill** at `<skill-dir>/rew_tool/` (stdlib-only — no external deps, no project data). The modules import flat, so run it from its own dir: `cd <skill-dir>/rew_tool && python3 rew_tool.py …` (or add that dir to `PYTHONPATH`). It wraps the API:

```
rew_tool/rew_api.py    — get_measurements, get_fr, get_group_delay, get_impulse_response,
                         get_distortion, get_filters/set_filters, get_equaliser/set_equaliser,
                         get_crossover_types, get_slopes, get_target_settings/response
rew_tool/analysis.py   — FR/phase/IR/GD analysis + PEQ suggestions
rew_tool/target_curves.py
rew_tool/rew_tool.py    — entry point
```

Prefer pulling data numerically over reading screenshots. **What to pull for which decision** → `references/analysis-playbook.md`. **How to read/decide** (anchor-to-mids not absolute · peak-vs-null · power-sum summation · joint-phase before crossover moves · centering=time vs frequency-wander · output-vs-virtual · verify the mic/reference) → `references/diagnostic-techniques.md`. **API gotchas** (big-endian float32, `set_filters` one-by-one with `gaindB`, IR timing is junk, out-of-band target garbage) → `references/rew-api-quirks.md` — `rew_tool/` already encodes these, so check it before hand-rolling a call.

If the API can't be reached from the host, fall back to the user's exported `.mdat`/CSV (e.g. `rew_analitic/measurements-*.mdat`) or screenshots.

---

## References (read on demand)

- `references/project-intake.md` — **NEW PROJECT bootstrap (Фаза −1)**: quickstart for new hands, equipment + goals interview (curve choice — no default), install verification (routing/polarity/gain/noise/break-in), DSP capability checklist (incl. non-Helix), project-file generation. Read whenever there are no project files, a new car/system, or «з нуля»
- `references/process-phases.md` — the phased process + package format + Claude's refinements to the workflow
- `references/naming-and-structure.md` — project/session/phase hierarchy · measurement naming + `_N` version suffix · `.mdat` storage · DSP config (`vN`, base+voicing) · target-curve naming · "is the raw data still valid?" after a hardware change
- `references/analysis-playbook.md` — which REW measurement (FR/phase/IR/GD/CSD/distortion/excess-phase) answers which tuning question
- `references/diagnostic-techniques.md` — hard-won interpretation methods: anchor-to-mids, peak-vs-null, power-sum summation, joint-phase check, centering (time) vs frequency-wander, output-vs-virtual layering, measurement-chain verification
- `references/filter-types-car-audio.md` — LR vs Bessel vs Butterworth tradeoffs + **starting crossover sets** (several variants; the project's current choice lives in `dsp-state-current`)
- `references/helix-vcp-workflow.md` — **[DSP-specific: Helix]** Ultra S architecture, VCP, gain staging, DAC filters, mic/loopback rig (for another DSP — create an equivalent, `project-intake.md §4`)
- `references/car-eq-patterns.md` — car-specific EQ problems, sub/midbass/mid/tweeter patterns, target curves
- `references/staging-depth.md` — front-back DEPTH + layering (distinct from lateral imaging): forward-stage root = uppers-too-hot-vs-bass, fix by RAISING bass not cutting treble, level-dependence (equal-loudness), A-pillar ceiling, ear-driven (summation/magnitude only)
- `references/enclosure-install-diagnostics.md` — **«корпус vs салон»**: SBIR-vs-box сепаратор (nearfield/distance/out-of-car/stuff-A/B + дві пастки: L=R≠корпус, λ/4-збіг≠діагноз), ETC→Δd→комб-передбачення, source-vs-receiver через РУХ ДЖЕРЕЛА, поглинач-товщина λ/10 vs екран, аперіодика/CLD, ретюн-після-заліза, версійна регресія EQ, cold-start аудит іншою моделлю. Read whenever a fixed dip/peak smells like hardware/install, or before ANY enclosure surgery.
- `references/competition.md` — EMMA/AYA/CARMusic prep: imaging test-track instrument→frequency maps, TIEFBASS equal-loudness + SQ↔SPL voicing fork, judging voicing, preset/input cautions
- `references/preset-strategy.md` — **which presets to build**: SQ / FULL / SQL / surround / source-input (BT music + head-unit nav) + **competition presets per ruleset** (EMMA vs AYA — e.g. L↔R crossfeed OK for EMMA, never for AYA); base+voicing discipline, preset↔input binding, DSP preset-count limit
- `references/test-tracks.md` — **listening-test track library (CarMus 2026 + UDD/Chesky + EMMA + mono-center + growing) with diagnostic markers + a dimension→track INDEX.** When verifying a hypothesis **BY EAR** (depth / punch / sub↔midbass integration / sibilants / separation — anywhere in-cabin measurement is unreliable), look up the dimension, pick ONE track, and tell the user exactly **what to play + where (timecode) + what to listen for** (binary good/bad sign). Their answer is the ear-metric.
- `references/voicing-by-ear.md` — **Phase-6 client-preference voicing**: curve→character map (which house curve = which taste), the curve-audition method, taste-axes→EQ moves, and an experienced installer's (Arkadij) **symptom→fix by-ear EQ map** (bass punch/boom, voice placement/sibilance, stage height, treble). By-ear heuristics (not dogma); a tip that conflicts with our findings is kept as a **variant** (may fit a different cabin / unlock a solution).
- `references/method-hashimoto.md` — **by-ear stage-building method (Hashimoto)**, the alternative/complement to the measured process: signature **"slope first, then frequency"** filter tuning (each side separately, params may differ L/R), polarity-by-ear-by-band (a VARIANT vs our summation), delays as "verticals → center" on mono, EQ last with mono sines (don't touch 2.5-5k). The blended method (measure × ear × experience) is framed in `process-phases.md → Три джерела`.
- `references/helix-phase-allpass.md` — **[DSP-specific: Helix]** Phase (all-pass) control + phase-tuning order (midbass reference → sub → mid → tweeter; not applied to midbass)
- `references/helix-eq-export.md` — **[DSP-specific: Helix]** Audiotec-Fischer EQ export format (30 bands, PK/LS_Q/HS_Q) + REW→Helix import workflow
- `references/rew-api-quirks.md` — REW API gotchas (encoding, set_filters, IR-timing junk, target garbage) — what `rew_tool/` already handles
- `references/feedback-loop.md` — **Phase 7 / skill distribution**: closing ritual = 4 streams (A project survey · B skill feedback, only-what-was-used · C community-share consent, opt-out preselected · D post-submit thanks + careful donation, never before submit), how the skill ships (git repo, versions, install), and how experience flows back (feedback package template, channels, safety rules, knowledge/ library of car & DSP profiles)
- `knowledge/cars/*.md` + `knowledge/dsp/*.md` — **accumulated car & DSP profiles** (community + author experience): check FIRST at intake of a known body/DSP. Seeded: `vw-passat-b8-sedan`, `helix-dsp-ultra-s` (incl. EQ-transfer paths: Audiotec-Fischer file / REW-EQ-CopyPaste-Assistant for 30+ DSPs).
  ⚠️ **Scope = EXACT body/DSP match only.** A profile applies to the car it was measured in — **never generalize it to a different car, even a platform sibling** (Passat B8 ≠ Octavia ≠ Superb ≠ other VAG). On a non-matching car: do **not** name another car's profile in the user-facing answer, and do **not** import its measured anomalies (specific Hz / SBIR notches / door-null numbers) as fact. The only legitimate transfer is **generic body-class physics** (sedan vs hatch/wagon → room-gain & НЧ tendency) and the file's **structure as a template**. A platform-sibling profile may at most seed a **private hypothesis to verify by measurement** — phrased "let's check whether your car also shows X", never asserted. No exact profile = treat as a fully new body → diagnose from `project-intake.md`, don't borrow numbers.

---

## Model selection (token-smart)

Default to **Sonnet 4.6** for the session; escalate to **Opus 4.8** only on hard reasoning moments. **Claude cannot switch its own model** — so **proactively tell the user when to switch** (e.g. *«Це місце варте Opus — увімкни `/model opus`»*; afterwards *«можна назад на `/model sonnet`»*).

| Step | Model | Why |
|---|---|---|
| Pull data, parse, run critic loop, drafts, routine deviation→PEQ, summaries | **Sonnet** | bulk work, ~5× cheaper |
| **Crossover strategy** proposal (Phase 1) | **Opus** | multi-constraint physics call |
| Critic round that **escalates / 3-3 deadlock** | **Opus** | nuanced disagreement |
| **Final verdict** (Phase 3) + judge-error diagnosis | **Opus** | the calls that decide quality |
| Tricky **phase / sub↔midbass / L-R region** decisions | **Opus** | subtle psychoacoustics |
| Pure mechanical mass fetches | Haiku | rarely worth switching |

Gemini critic always runs (free) → even on Sonnet there's a second expert head; Opus is for Claude's own hard calls. **Announce the switch at the START of the step**, not after.

## Output style

When analyzing measurements, lead with what the user will *hear*:

**🔍 Що я бачу** · **⚠️ Головні проблеми** (freq / magnitude / cause) · **✅ Виправне / ❌ Невиправне** · **🔧 Наступні кроки** · **❓ Одне питання якщо бракує контексту**

Keep EQ honest: max boost +6 dB; if a dip needs more it's phase cancellation (unfixable with EQ). Remove resonances, don't chase a flat line.
