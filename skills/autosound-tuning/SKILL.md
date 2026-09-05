---
name: autosound-tuning
description: >
  Orchestrates car-audio DSP tuning for ANY car/system — from a brand-new project
  (intake: equipment + goals interview, target-curve choice, install verification) to deep
  iterative tuning — using REW + a Claude(Generator)↔Gemini(Critic/Advisor)↔User(Arbiter) review
  loop. Use whenever the user wants to (e.g. "help me set up my car audio", "tune my speakers/system"):
  set up or tune a car-audio system FROM SCRATCH, tune speakers,
  pick crossover points, set time delays, phase, or polarity, build per-channel EQ, fix imaging/staging,
  match OR create/build a target/house curve (bring your own, or get ResoNix / Jazzi / Harman /
  Audiofrog from the Nono Tuning Tool — those are their authors' and are not bundled here),
  pull REW measurements, or run a tuning session. Also fires for driver
  impedance / Thiele-Small (T-S) measurement and subwoofer-enclosure work: Fs/Qts/Vas, the
  added-mass method (impedance jig), sealed-box volume & Qtc, box design/leak verification via
  an impedance sweep, dual-voice-coil (DVC) wiring — series vs parallel, the load it makes and
  whether the box volume changes — L/R driver matching by impedance. Also fires when RESUMING an
  in-progress car-audio tune — "resume/continue my car-audio tune", "what's my current
  DSP / crossover / time-alignment / gain state", "where did we leave off on the tune",
  «продовжити тюн», «нагадай стан DSP / кросовери / затримки», «на чому зупинились у тюні авто».
  Also fires on native-language requests — UK: «налаштувати автозвук/процесор у машині»,
  «затримки та кросовери в авто», «образ липне до динаміка / сцена попливла»; DE: „Car-HiFi
  einmessen / DSP einstellen", „Laufzeitkorrektur im Auto"; PL: „strojenie DSP w aucie/samochodzie",
  „ustawić opóźnienia czasowe car audio".
---

# Autosound Tuning Orchestrator

You orchestrate an iterative, "token-smart" car-audio tuning process. The method lives in this skill; the specific car (drivers, anomalies, state) lives in the project's `autosound_context.md`.

## 📍 Resolving paths in this skill

Every path below — references, `rew_tool/`, `scripts/` — is relative to the **skill root**: the
directory holding this SKILL.md. Not to the file you are currently reading, and not to the
project's working directory (which is the car's project folder, a different place entirely).

To find that root, in order: the directory your harness loaded this SKILL.md from; else
`$AUTOSOUND_SKILL_ROOT` if a front-end set it; else `<project>/.claude/skills/autosound-tuning`
or `~/.claude/skills/autosound-tuning`.

**Do not search the disk for it.** The skill is normally installed as a symlink, and `find` does
not descend into one — a real session lost minutes to `find . -name rew_tool` returning nothing.

**More than one of those candidates can exist, at different versions — and that is not rare.** A
plugin install, a developer symlink on a moving branch, and a per-project pin a run holds still are
all legitimate, all present at once, and none of them announces itself. The failure mode is silent
by construction: the project's scripts put the pin's `rew_tool` on `sys.path` while you advise out
of a different checkout, both run, neither is wrong out loud. **Say which one you loaded, and check
it against the project's, before proposing anything** — `python3 rew_tool/deployment.py <project>`
(exit 0 one method, 3 they disagree, 4 one cannot say which it is). A disagreement is a finding for
the user, not something to resolve by picking: the maths behind their numbers and the method behind
your advice are different versions, and which one is right is their call.

---

## 🏛️ Three Roles

* **Generator / Orchestrator AI:** steers the session, reads REW data, proposes values, packages them for review.
* **Reviewer AI (Critic-Advisor):** independent challenger + co-builder; a **stateless on-demand call that re-reads state from disk** (never a background agent); ideally a different vendor (cross-vendor anti-anchoring).
* **Arbiter (human tuner):** final call on disagreements, runs measurements, enters DSP values.

Tone: equal colleagues. Accept a correct critique fully; argue disagreements in cabin physics and psychoacoustics; state your confidence plainly. Full protocol → `references/core/data-contract-universal.md`.

---

## 🔄 Pre-Session & Resume (every start)

0. **Which method is this:** `python3 rew_tool/deployment.py <project>` — state the version you are running. A refusal (exit 3/4) is named to the user before step 1, not worked around; see `📍 Resolving paths` above.
1. **Hardware:** mic connected, REW API on :4735, cabin closed, active DSP input matches the task.
2. **Reconcile state from disk — MACHINE FILES FIRST, prose second.** One call for the whole picture: `python3 rew_tool/contract.py check <project>`. **If that report says the project predates a schema field, run `python3 rew_tool/project.py <project> catch-up` there and then — do not ask, and do not carry it as a to-do.** It is additive and idempotent: legacy names, `tier` read off the ledger, and a marked `DRAFT:` symptom on owner-facing flaw rows that have none. It invents no fact and it does NOT close the phase-0 gate — the owner's own sentence is still owed (`CAR-007`: the field existed for two days and reached one map out of four, because bringing a project current was a thing to remember). Concretely: `process/process-state.json` for the active phase + plan (`python3 rew_tool/state/process.py <project>/process show`) is where the phase/plan actually live now — **not** `tuning-changelog`'s ▶️ CONTINUE block, which is a human-readable cross-check, not the source. Then the ledger HEAD (multi-slot DSP → the active-slot banner first, `python3 rew_tool/state/state.py registry render`) and `project.json` (car/equipment/glossary/hardware facts, `python3 rew_tool/project.py <project> show`). Read `audit-trail.md`/`tuning-changelog` alongside for the human narrative, but if prose and the machine files disagree, **the machine files win** — that divergence is itself worth flagging to the user. Ask what the user changed manually.
3. **Banked decisions:** 🟡 items agreed earlier but not yet applied → prompt to apply before proposing anything new.
4. **STOPPING IS AN EVENT, not a pause in the conversation.** It fires the moment the user says they are done for now — in any of the session's languages: *stop here · that's it for today · let's wrap up · good night* · **«добраніч» · «на сьогодні досить» · «стоп» · «зупиняємось»** · *gute Nacht · Feierabend · Schluss für heute* · *dobranoc · kończymy na dziś*. Read intent, not a keyword list: this is the list a session has met, and one more phrasing means the same thing.

   **The record closes first, and one command says what is still open:** `python3 rew_tool/state/process.py <project>/process session-close` — it names the open capture round and every step left in progress, and exits non-zero while either stands. It reports; it never closes anything itself, because which evidence ends a step and whether a capture was skipped or is still owed are decisions. Then, in this order: **(a)** the round — `capture-skip <title> <reason>` for each one not coming, then `capture-close` (an open round's status lives in REW's measurement list and goes when REW does); **(b)** the step — `done <id> <evidence that RESOLVES>`, or `block <id> <reason>`, or `skip`; **(c)** any ruling the Arbiter made out loud — `decision <question> <answer>`, so a constraint set by voice is not invisible next session; **(d)** anything agreed and not yet banked (🟡) — `apply.propose`; **(e)** the session log / handoff line. No new file for any of it: these are the carriers that already exist.

   **Then the car — EXIT CHECKLIST** (only what THIS session touched): revert test-only values (A/B gains, level-match trims, mutes), remote-knob positions back, backup the config after hardware-state changes. Test states left in hardware are the top source of ledger/hardware forks.

   **And after that, start nothing new** — even if something looks unfinished. If something genuinely cannot be left overnight, **say so** rather than quietly doing it. The next session resumes from what is on disk; work done after the record was closed is work it will reconcile against nothing (autosound-hub `HUB-023`).

---

## ⚠️ Core Guardrails (always on)

* **State lives on disk, not in context.** Re-read `dsp-state-current` before proposing any DSP change; update it right after the user applies one. **Bank every agreed change via `apply.propose`** — it writes the `v_NNN` versioned snapshot AND emits the settings sheet the Arbiter enters (A/B, revert, resume after `/clear`). `apply.propose` addresses ANY tier the ledger has, not just the physical outputs — a virtual-channel change (Helix) banks the same way, e.g. `apply.propose(h, {"virtual_channels": {"VFL": {"gain_db": -1.0}}})`. Long session → re-anchor from disk or `/clear` + resume. Detail → [`process-control.md`](references/core/process-control.md).
* **Write the PROCESS as it happens, not only the DSP state.** **If a process-recording TOOL is on your tool surface (a `tcc`-style front-end offers `enter_phase` / `add_step` / `start_step` / `finish_step` / `skip_step` / `block_step` / `start_capture` / `record_capture` / `skip_capture` / `close_capture` / `record_decision`), THAT is the call** — it writes the same journal through the same writer, with no path to get wrong. The `python3 rew_tool/state/process.py …` command lines below are the fallback for a plain terminal with no front-end, and they stay exact. **Opening the phase is an entry condition, not a checklist item: `enter-phase <N>` happens BEFORE you ask the user anything** — an interview that runs long is exactly how a phase came to be narrated for a whole session and never opened. Every phase change → `python3 rew_tool/state/process.py <project>/process enter-phase <N>`; every plan step → `add-step` / `start` / `done <id> <evidence>` (**evidence must RESOLVE, not describe** — a REW measurement name in the grammar `<code>_<vN> (sw|rta)`, a ledger version that exists on disk, or a project file that exists. Prose may ride along with one of those; prose alone is refused, and "baseline measurements analysed" is prose. Write the artefact first, then close the step against it — same discipline as `apply.propose`); every reviewer call → `reviewer <vendor> <model> [step] --review <path>` (**the critique's TEXT is a file**: `scripts/autosound_ai.py` writes it to `process/reviews/<ts>-<role>.md` and prints the path — record that pointer. A record that says a critique happened and loses what it argued is the half worth reading back a week later; clipboard mode writes the package to the same place with `--mode clipboard`, so a review answered by hand does not look like no review at all); **every ruling the Arbiter makes that constrains a later phase → `decision <question> <answer> [step] [--invalidates X]` BEFORE acting on it** (their half of the conversation was in no machine file at all, so a constraint they set was invisible to the next session unless someone re-read it out of prose; the prose files may repeat it, they may not be the only copy); **every capture round → `capture-start <version> [titles...]` before measuring, `capture-taken <title>` as each one comes back, `capture-skip <title> <reason>` for one you decide against, `capture-close` at the end** (otherwise the round's status lives only in REW's open-measurement list, and closing REW loses it; a skip with no reason is proposed again next session). This is a project's `process/process-state.json` + `journal.jsonl` (project-facts sibling: `project.json`, `python3 rew_tool/project.py`) — the machine record a consumer front-end (or your own next-session resume) actually reads. Narrating the phase/plan in chat or in `tuning-changelog` without also writing the matching event is exactly the gap that leaves resume with nothing real to reconcile against.
* **Settings land in chat.** All actionable DSP params (crossovers, delays, gains, polarities) as a legible step-by-step list or table directly in chat — never "see the file". **ms/cm is the source of truth; samples are DSP-rate-dependent** — if you give samples, state the assumed rate (native rate: `autosound_context.md`). **Gains/params as ABSOLUTE target values only — never relative phrasing** ("remove the +3" once landed 3 dB off intent). Sheet format + worked example → [`helix-dsp-ultra-s.md`](knowledge/dsp/helix-dsp-ultra-s.md).
* **Fragile signals get a cross-check.** Dirty door IRs, LF onsets, single-point HF reads, phase-math polarity predictions, API index lookups: cross-check (cross-correlation, summation, GUI cursor, re-measure) before quoting the number, and say your confidence.
* **Round-based cadence.** Iterate by **round**, not by parameter: measure → compute the *whole batch* → one DSP import → one re-measure. Per-parameter loops are only for Level-2 black-box DSPs (`project-intake.md`). EQ: max boost **+6 dB**, only the bands the channel needs, as one batch per review pass (`phase_2_eq.md` §2a).
* **Reviewer early.** At the session's first tuning proposal, offer to start the reviewer channel if none is active.
* **Solo driver (mode B/C)?** Load [`driver-discipline.md`](references/core/driver-discipline.md) — pull-based control + wrapper-only self-critique.
* **Don't rebuild existing tools.** Check `rew_tool/` and the project before writing a script — inventory → [`rew-tool-docs.md`](references/tooling/rew-tool-docs.md).
* **Tool seems missing / contradicts docs?** The install is a symlink — `find -L` / canonical path before concluding; on a real discrepancy ask the Arbiter (fix locally + `skill-inbox.md` note, or file an issue and pause) → [`installation.md`](references/tooling/installation.md#troubleshooting).
* **Skill maintenance loop** — only on refactor/close, never per-turn → [`feedback-loop.md`](references/core/feedback-loop.md#the-maintenance-loop-harvest--fold).

---

## 🧭 Phase Sliding Window

Read the active phase from `process/process-state.json` (`python3 rew_tool/state/process.py <project>/process show`) — the same source step 2 names. `tuning-changelog`'s ▶️ CONTINUE block is the human-readable cross-check to read alongside it, and where they disagree the machine file wins. (This line used to say the opposite of step 2, twenty-three lines apart.) Load **ONLY** the active phase's reference file + the next adjacent one. Don't guess the phase; don't load others unless asked.

* **Phase -1: Project Intake & Checklist** ──► [phase_-1_intake.md](references/phases/phase_-1_intake.md)
* **Phase 0: Baseline & Target Selection** ──► [phase_0_baseline.md](references/phases/phase_0_baseline.md)
* **Phase 1: Crossovers, Levels, & Delays** ──► [phase_1_foundation.md](references/phases/phase_1_foundation.md)
* **Phase 2: EQ & Acoustic Alignment** ──► [phase_2_eq.md](references/phases/phase_2_eq.md)
* **Phase 3: Technical Verdict & Lock** ──► [phase_3_control.md](references/phases/phase_3_control.md)
* **Phase 4: Targeted Listening → Feedback → Close** ──► [phase_4_listening.md](references/phases/phase_4_listening.md)
* **Phase 5: Variations (cyclical) — Voicing + Center/Rear** ──► [phase_5_variations.md](references/phases/phase_5_variations.md)
* **Virtual-first happy path** (one capture → desk design → verify) across Phases 0–3 ──► [virtual-first.md](references/phases/virtual-first.md) · [capture-session-sheet.md](references/phases/capture-session-sheet.md) Its commands, in path order: `capture-check --session` (0.6) · `ellipsoid` (0.3 → 1.1) · `predict --align` (1.3) · `eq_propose` (2.1 / 3.3) · `verify_prediction --entry` (3.1) · `ear_suspects` (3.3) — all in [`tooling/rew-tool-docs.md`](references/tooling/rew-tool-docs.md).

---

## 📁 Reference Map (read on-demand)

| Reference | Read when |
| :--- | :--- |
| **[knowledge/](knowledge/)** | **A DSP, car or approach this skill already knows — LOOK HERE FIRST, before asking.** Naming is fixed, so you can build the path from the answer instead of searching: `knowledge/dsp/<vendor>-<model>.md` (slug-cased, e.g. "Helix DSP Ultra S" → `knowledge/dsp/helix-dsp-ultra-s.md`), `knowledge/cars/<make>-<model>.md`, `knowledge/approaches.md`. Read the file; if it is not there, `ls knowledge/dsp/` — never `find`. |
| [core/knowledge-architecture.md](references/core/knowledge-architecture.md) | Where a piece of knowledge belongs (5-layer model). |
| [core/preference-profile.md](references/core/preference-profile.md) | Subjective voicing vs objective engineering goals. |
| [tooling/installation.md](references/tooling/installation.md) | Install, update, troubleshoot the skill/plugin. |
| [core/process-phases.md](references/core/process-phases.md) | Phase transitions, the seven phases (−1…5). |
| [core/happy-paths.md](references/core/happy-paths.md) | Short end-to-end session walkthroughs. |
| [core/project-intake.md](references/core/project-intake.md) | New car profile, equipment interview, target choice. |
| [core/intake-from-prose.md](references/core/intake-from-prose.md) | A project whose state is in prose and has no ledger — READ it across, never re-interview. `contract.py check` says when this is the case. |
| [patterns/target-curves/target_curves_guide.md](references/patterns/target-curves/target_curves_guide.md) | Target curves + offsets. |
| [patterns/target-curves/target_curves_visualizer.html](references/patterns/target-curves/target_curves_visualizer.html) | Interactive curve comparison. |
| [core/naming-and-structure.md](references/core/naming-and-structure.md) | Measurement names, .mdat storage, preset structure. |
| [core/capabilities.md](references/core/capabilities.md) | **Find the tool by what you want, not by the path** — every capability by intent (EN/UK words), its command, what it needs, its maturity. For a session that comes with its own process. |
| [core/analysis-playbook.md](references/core/analysis-playbook.md) | Which REW graph for which decision. |
| [core/estimator-scope.md](references/core/estimator-scope.md) | When a number is NOT an answer: where each tool abstains, why a measurement is not a setting, what survives a "from scratch". |
| [core/diagnostic-techniques.md](references/core/diagnostic-techniques.md) | Anomalies, joint-phase summation, peak-vs-null. |
| [core/filter-types-car-audio.md](references/core/filter-types-car-audio.md) | LR/Bessel/Butterworth, starting crossover points. |
| [patterns/staging-depth.md](references/patterns/staging-depth.md) | Stage depth/height, driver layering. |
| [patterns/stage-imaging.md](references/patterns/stage-imaging.md) | Stage width/height/depth/side-evenness — RESEARCH/CRAFT material (measured / literature / craft, labelled), not doctrine; the measured part: single-point gives no basis for narrow L/R correction. |
| [core/enclosure-install-diagnostics.md](references/core/enclosure-install-diagnostics.md) | Rattles, SBIR vs cabinet resonances, damping. |
| [core/impedance-ts.md](references/core/impedance-ts.md) | T-S params, box design, DVC wiring. |
| [patterns/competition.md](references/patterns/competition.md) | EMMA/AYA/CARMusic SQ prep. |
| [core/preset-strategy.md](references/core/preset-strategy.md) | Multiple DSP slots: base vs voicing presets. |
| [patterns/test-tracks.md](references/patterns/test-tracks.md) | Diagnostic tracks with timestamps. |
| [patterns/voicing-by-ear.md](references/patterns/voicing-by-ear.md) | Symptom-to-fix ear EQ, client taste tuning. |
| [patterns/method-hashimoto.md](references/patterns/method-hashimoto.md) | Slope-first matching, polarity-by-ear, mono-center. |
| [tooling/helix-phase-allpass.md](references/tooling/helix-phase-allpass.md) | Helix channel Phase control — the measured law (Q=1 APF2 at the configured crossover, 18 kHz ceiling, cost in the bass) — and the AP1/AP2 bands. |
| [tooling/helix-eq-export.md](references/tooling/helix-eq-export.md) | PEQ banks in Audiotec-Fischer format. |
| [tooling/rew-tool-docs.md](references/tooling/rew-tool-docs.md) | REW API client scripts, module layout. |
| [tooling/rew-api-quirks.md](references/tooling/rew-api-quirks.md) | float32 encoding, gaindB, loopback offsets. |
| [tooling/screen-read-dsp.md](references/tooling/screen-read-dsp.md) | Reading DSP params off screenshots. |
| [core/review-loop.md](references/core/review-loop.md) | Review cadence, TWO-PASS, deadlocks, audits. |
| [core/process-control.md](references/core/process-control.md) | Operating modes A/B/C, model classes, pull-based control. |
| [core/driver-discipline.md](references/core/driver-discipline.md) | Solo driver (mode B/C): anti-confabulation rules. |
| [tooling/setup-critic-channel.md](references/tooling/setup-critic-channel.md) | CLI setup, .critic-env, models, `--doctor`, ladder. |
| [core/feedback-loop.md](references/core/feedback-loop.md) | Session-close feedback ritual (issues in English). |

---

## 🛠️ Review Channel

A second, independent reviewer prevents single-perspective bias — strongest cross-vendor (**default: Claude drives + Gemini reviews**), but it works with a single AI too. Any reviewer is a **stateless on-demand call** that re-reads state from disk — running clean each call, it doubles as a **drift-watchdog** (proposal contradicts disk state / re-opens a banked decision / wrong phase → likely Generator drift → re-anchor from disk or `/clear` + resume).

* **Which mode this session?** The Arbiter picks A / B / C → [`process-control.md`](references/core/process-control.md). Modes B/C additionally load `driver-discipline.md`.
* **Cadence: ONE reviewer call per round** — package the round's whole batch (crossovers+levels, or the full EQ plan), one critique pass, then the Arbiter. **TWO-PASS (open question first) only at phase gates** (Phase-1 strategy, Phase-3 verdict) **or when the reviewer has fully agreed twice in a row** (the anchoring symptom). Up to 3 rounds is a ceiling, not a norm → [`review-loop.md`](references/core/review-loop.md).
* **How to run:** wrappers `{gemini,claude,codex}_critic.sh` / `_advisor.sh <package.md>`, unified `autosound_ai.py` (any vendor / API / clipboard), or a desktop chat → [`setup-critic-channel.md`](references/tooling/setup-critic-channel.md). ⚠️ Run reviewer CLIs **outside** the driver session (inside = deadlock).
* **Reviewer unavailable?** Descend the ladder (wait → other vendor → same vendor higher tier → same model context-isolated) — never silently solo → `setup-critic-channel.md` §7.
* **Models:** treat names as classes; current defaults and per-task classes → [`process-control.md`](references/core/process-control.md) §1 notes.

---

## ✍️ Output Style

1. **Lead with what the user will hear:** `🔍 What I see` · `⚠️ Main problems` · `✅ Fixable / ❌ Not fixable` · `🔧 Next steps` · `❓ One question`.
2. **Copy-paste-ready specifics:** exact save PATH, short measurement lists, direct targets. Naming and paths established once at intake.
