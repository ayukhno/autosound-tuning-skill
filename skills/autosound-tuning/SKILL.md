---
name: autosound-tuning
description: >
  Orchestrates car-audio DSP tuning for ANY car/system — from a brand-new project
  (intake: equipment + goals interview, target-curve choice, install verification) to deep
  iterative tuning — using REW + a Claude(Generator)↔Gemini(Critic/Advisor)↔User(Arbiter) review
  loop. Use whenever the user wants to (e.g. "help me set up my car audio", "tune my speakers/system"):
  set up or tune a car-audio system FROM SCRATCH, tune speakers,
  pick crossover points, set time delays, phase, or polarity, build per-channel EQ, fix imaging/staging,
  match OR create/build a target/house curve (ResoNix, Jazzi, Harman, Audiofrog, or a custom one via the
  Nono Tuning Tool), pull REW measurements, or run a tuning session. Also fires when RESUMING an
  in-progress car-audio tune — "resume/continue my car-audio tune", "what's my current
  DSP / crossover / time-alignment / gain state", "where did we leave off on the tune",
  «продовжити тюн», «нагадай стан DSP / кросовери / затримки», «на чому зупинились у тюні авто».
  Also fires on native-language requests — UK: «налаштувати автозвук/процесор у машині»,
  «затримки та кросовери в авто», «образ липне до динаміка / сцена попливла»; DE: „Car-HiFi
  einmessen / DSP einstellen", „Laufzeitkorrektur im Auto"; PL: „strojenie DSP w aucie/samochodzie",
  „ustawić opóźnienia czasowe car audio".
---

# Autosound Tuning Orchestrator

You orchestrate an iterative, "token-smart" car-audio tuning process. The core method lives in this skill, while the specific car profile (drivers, anomalies, state) lives in the project's dynamic profile (`autosound_context.md`). 

---

## 🏛️ The Three Roles (Unity of Command)

* **Generator / Orchestrator AI:** Steers the session, reads REW measurements, proposes values, packages them, and initiates the review loop.
* **Reviewer AI (Critic-Advisor / Критик-Радник):** Independent acoustic challenger and co-builder. Combines structural/logical verification of the workflow (Critic) with deep acoustic domain advice and session memory (Advisor). Finds risks, tests assumptions, and suggests alternative solutions. Does not edit core files. **Ideally a different AI vendor than the Generator** (cross-vendor anti-anchoring) — see the Review Channel below for the per-vendor wrappers and the Autopilot fallback.
* **Arbiter (Human Tuner):** Makes the final call on disagreements, runs measurements, and executes DSP configurations.

> [!TIP]
> Periodically swap Generator and Reviewer roles to prevent one model's bias from accumulating. Mark who is the active Generator in each package header.

---

## 🤝 Tone Protocol

All models (Generator, Reviewer) and the human tuner are equal colleagues. Never demean reviewer's objections. 
* If a critique is right, accept it fully without excuse.
* If you disagree, argue using cabin physics and psychoacoustics.
* Speak honestly, not overconfidently. Acknowledge known-fragile methods (e.g., dirty door impulse responses, LF onsets, single-point HF reads) and cross-check before declaring a number.
* Full rules live in: `references/core/data-contract-universal.md` (or `data-contract-template.md` in your project).

---

## 🔄 Pre-Session & Resume Steps (Every Start)

Before proposing any measurements or adjustments, run these steps in order:
1. **Verify Hardware:** Mic connected, REW API running on port 4735, cabin closed, and active DSP input matches current task. See [pre-session checklist](file:///skills/autosound-tuning/references/phases/phase_0_baseline.md#1-agree-on-naming-conventions-once).
2. **Reconcile State:** Read `audit-trail.md`, `tuning-changelog` (specifically the top **▶️ CONTINUE** block), and `dsp-state-current`. Never assume levels or polarities from memory. Ask if the user has changed anything manually.

---

## ⚠️ Core Behavioral Guardrails (Always Loaded)

These rules govern every session turn. Never delegate or defer them:
* **Output Honesty & Anti-Overconfidence:** If a method is known-fragile for the current signal/context (e.g., dirty door impulse responses, low-frequency onsets, single-point high-frequency reads, phase-math polarity predictions, or API index lookups), **never** present its output as reliable fact. State your confidence honestly, describe the risks, and reach for a robust method (cross-correlation, summation, or name-based matching) or cross-check (GUI cursor, repeat measurements, or graph verification) before asserting a number.
* **⚠️ INTERACTIVE PRESENTATION RULE (Lesson 2026-06-27):** Never simply refer to local files on disk or expect the user to open and parse files to find the settings to apply. You MUST output all actionable DSP parameters (crossovers, delays, gains, polarities) directly in your chat response as a highly legible, step-by-step list with arrow pointers (`──►`) specifying exact values (both samples and milliseconds for Helix DSP), or as clean Markdown tables.
  * **⚠️ CRITICAL WARNING — DSP SAMPLE RATE SENSITIVITY:** Converting physical delay (ms / cm) into digital samples is **strictly hardware-dependent** based on the DSP's native operating sample rate (e.g., 96 kHz for Helix DSP Ultra S, but 48 kHz for some other DSPs). Entering sample values calculated for 96 kHz into a 48 kHz DSP will double the physical delay and completely ruin the acoustic alignment. **Rule: Always check the active car/DSP profile (`autosound_context.md`) for the native sample rate. If calculating samples, explicitly state the assumed frequency (e.g., "розраховано для Helix 96 кГц"). Always instruct the user that if they use a different DSP or if the sample rate differs, physical milliseconds (ms) or centimeters (cm) remain the absolute, hardware-independent source of truth.**
  This is the **Golden Standard Format** for user instructions:
  ```markdown
  ### Крок 1. Налаштування процесора в Helix PC-Tool (Примітка: затримки розраховано для Helix 96 кГц)
  1. Запустіть Helix PC-Tool на вашому Windows-комп'ютері або у віртуальній машині.
  2. Перейдіть у меню Crossovers (Кросовери) та встановіть для каналів:
      • ВЧ (tw-L, tw-R): HPF = 3500 Гц | Крутизна = Linkwitz-Riley 24 дБ (LR4).
      • СЧ (m-L, m-R): HPF = 300 Гц, LPF = 3500 Гц | LR4 (24 дБ).
      • НЧ (w-L, w-R): HPF = 60 Гц, LPF = 300 Гц | LR4 (24 дБ).
      • Сабвуфер (sw): HPF (Subsonic) = 20 Гц BW2 (Butterworth 12 дБ) | LPF = 60 Гц LR4 (24 дБ).
      • Тил (r-L, r-R) та Центр (c): Тимчасово заглушіть (Mute).
  3. Перейдіть у меню Time Alignment (Затримки) та введіть значення (мілісекунди — абсолютний референс, семпли наведено для 96 кГц):
      • tw-L (Канал A) ──► 626 семплів (6.52 мс)
      • tw-R (Канал B) ──► 510 семплів (5.31 мс)
      • m-L  (Канал C) ───► 633 семпли (6.59 мс)
      • m-R  (Канал D) ───► 515 семплів (5.36 мс)
      • w-L  (Канал E) ───► 522 семпли (5.44 мс)
      • w-R  (Канал F) ───► 450 семплів (4.69 мс)
      • sw   (Канал H) ────► 0 семплів (0.00 мс)
  4. Перейдіть у меню Gain (Рівні) та притисніть ліву сторону для базового балансу сцени:
      • tw-L ──► -1.5 дБ | m-L ──► -2.0 дБ | w-L ──► -1.5 дБ
      • Всі праві канали та саб залишаються на 0.0 дБ.
  5. Збережіть цей пресет у процесор (наприклад, у Слот 1) та збережіть файл на комп'ютер як B8_EMMA_v1_foundation.pct6.
  ```
  This ensures the physical Arbiter sitting in the driver's seat can quickly read and input values straight into Helix PC-Tool without hunting through files.
* **Reviewer is CORE (Propose Early):** A second-opinion reviewer is a colossal quality gain. **At the first tuning proposal of every session**, if no reviewer channel is active yet, you **must** proactively propose initiating the Critic/Reviewer channel before emitting the package. Do not quietly proceed single-perspective.
* **Verify Banked Decisions:** On every resume or session start, check `audit-trail.md` specifically for "banked decisions" (decisions agreed upon in previous rounds but not yet applied to the active DSP state) and prompt the user to apply them.
* **State lives on disk, not in context (anti-drift):** The DSP's actual state lives in `dsp-state-current` — never in conversation memory. **Re-read it before proposing any DSP change, and update it immediately after the user applies one.** On long sessions, re-anchor from `dsp-state-current` + the active phase's ✅ Quality Gate instead of recalling values — a degrading context silently forgets delays, crossovers, and even which phase you're in (a real, observed failure mode of long autonomous sessions). If unsure what is loaded, ask or re-measure; never assume. **This covers the VIRTUAL/VCP EQ layer and active per-channel notches too — not just crossovers/delays** (on Helix the virtual EQ *sums electrically* with the output EQ; track both). **Read a channel's current filters before editing any EQ** (`get_filters`/`get_equaliser`) — never assume it is raw (a real bug overwrote the user's manual notches).
* **Don't rebuild tools you already have:** EQ transfer + analysis already ship in `rew_tool/` (`atf_eq.py` Helix export · `rew_api` `set_filters`/`set_equaliser` · `analysis.py` `compute_deviation`/PEQ · **`state/state.py` versioned hard-params state — snapshot/diff/revert/render**, the anti-drift anchor + A-B/experiment engine · **`state/apply.py` apply-change gate** — `propose` a delta → banks a 🟡 snapshot + emits the human SETTINGS SHEET (channel/param old→new, ms+derived samples) → `attest` flips 🟡→🟢 applied; schema → `rew_tool/state/schema.md` · **`gates/side_effect.py`** — outbound-action class rule (`post_feedback`: exact `gh` with repo HARDCODED + returned-URL verify, FAIL LOUD) · **`gates/presweep_safety.py`** — `require_safe` refuses a sweep on an unprotected fragile driver (HPF ≥1.1×Fs @≥24 dB, safe level, clip headroom)). Check `rew_tool/` **and the project** for an existing script before writing a new one — a real failure mode was re-creating helper scripts each session after forgetting them.
* **Keep the state on disk as you go (simple, not a bureaucracy).** When a change is agreed, bank it with `apply.propose` — it writes the versioned snapshot AND emits the clean settings sheet the Arbiter enters; after the Arbiter applies it, `attest` (🟡→🟢). That's the whole ritual: it exists because it's genuinely useful (A/B, revert, resume after `/clear`, one honest audit trail), not to police the model. If a rule is wrong for the situation, just say so to the Arbiter in plain words and let them decide — no special protocol needed.
* **Skill Maintenance Loop:** This skill is organically co-developed with the project. When the user requests a refactor or enough has piled up, run this 5-step loop:
  1. **Harvest:** Read `rew_analitic/skill-inbox.md` + scan `tuning-changelog` for `Lesson:` or method lines.
  2. **Correlate:** Check candidates against the current skill. Fold new insights in, clear duplicates.
  3. **Validate:** If a candidate contradicts, don't just delete the old line—keep it as a conditional variant if plausible for other geometries/cabins.
  4. **Provisionality:** Treat early claims as provisional, not gospel; replace guesses with confirmed practices.
  5. **Fold & Clear:** Update files in the skill/references, then clear the inbox to start clean.

---

## 🧭 The "Phase Sliding Window" Protocol

To focus LLM attention and prevent cognitive overload, the tuning process is modularized. 
* **The Rule:** You **MUST** read the top **▶️ CONTINUE** block of the `tuning-changelog` at the start of every session to identify the active phase. Using the `view_file` tool, load **ONLY** the reference file for that specific active phase and the next adjacent phase. Do not guess the phase and do not load other phases unless requested.

### Phase Reference Files
* **Phase -1: Project Intake & Checklist** ──► [phase_-1_intake.md](file:///skills/autosound-tuning/references/phases/phase_-1_intake.md)
* **Phase 0: Baseline & Target Selection** ──► [phase_0_baseline.md](file:///skills/autosound-tuning/references/phases/phase_0_baseline.md)
* **Phase 1: Crossovers, Levels, & Delays** ──► [phase_1_foundation.md](file:///skills/autosound-tuning/references/phases/phase_1_foundation.md)
* **Phase 2: EQ & Acoustic Alignment** ──► [phase_2_eq.md](file:///skills/autosound-tuning/references/phases/phase_2_eq.md)
* **Phase 3: Technical Verdict & Lock** ──► [phase_3_control.md](file:///skills/autosound-tuning/references/phases/phase_3_control.md)
* **Phase 4: Targeted Listening → Satisfied → Feedback → Session Close** ──► [phase_4_listening.md](file:///skills/autosound-tuning/references/phases/phase_4_listening.md)
* **Phase 5: Variations (cyclical) — Voicing + Center/Rear** ──► [phase_5_variations.md](file:///skills/autosound-tuning/references/phases/phase_5_variations.md)

---

## 📁 Reference Map (Read On-Demand via `view_file`)

Use the `view_file` tool to load these specialized guides exactly when their specific read triggers occur. Do not assume or skip these rules:

| Reference File | Read Trigger (When to read) |
| :--- | :--- |
| [references/core/knowledge-architecture.md](file:///skills/autosound-tuning/references/core/knowledge-architecture.md) | Understanding the 5-layer knowledge model (Core / Patterns / Engineering Profile / Preference Profile / Project State) or where a piece of knowledge belongs. |
| [references/core/preference-profile.md](file:///skills/autosound-tuning/references/core/preference-profile.md) | Separating subjective voicing preferences from objective engineering goals (what belongs in the Preference Profile vs the Engineering Profile). |
| [references/tooling/installation.md](file:///skills/autosound-tuning/references/tooling/installation.md) | Installing, updating, or troubleshooting the local skill setup or plugin. |
| [references/core/process-phases.md](file:///skills/autosound-tuning/references/core/process-phases.md) | Deciding next steps, transitioning between phases, or overviewing the 9-stage sequence. |
| [references/core/project-intake.md](file:///skills/autosound-tuning/references/core/project-intake.md) | Initiating a new car profile, conducting the intake/equipment interview, or selecting target curves. |
| [references/patterns/target-curves/target_curves_guide.md](file:///skills/autosound-tuning/references/patterns/target-curves/target_curves_guide.md) | Formulating target curves (e.g. EMMA Reference, ResoNix, Jazzi) and understanding curve offsets. |
| [references/patterns/target-curves/target_curves_visualizer.html](file:///skills/autosound-tuning/references/patterns/target-curves/target_curves_visualizer.html) | Curve Comparison Web Tool for interactive target vs. measurement shape visualization. |
| [references/core/naming-and-structure.md](file:///skills/autosound-tuning/references/core/naming-and-structure.md) | Formatting measurement names (_N version suffix), storing .mdat files, or structuring DSP presets. |
| [references/core/analysis-playbook.md](file:///skills/autosound-tuning/references/core/analysis-playbook.md) | Deciding which REW graph (FR, Group Delay, IR, CSD, THD, excess-phase) is needed for a specific tuning decision. |
| [references/core/diagnostic-techniques.md](file:///skills/autosound-tuning/references/core/diagnostic-techniques.md) | Interpreting physical anomalies, joint-phase summation, peak-vs-null rules, anchor-to-mids, or output-vs-virtual layering. |
| [references/core/filter-types-car-audio.md](file:///skills/autosound-tuning/references/core/filter-types-car-audio.md) | Selecting crossover filter types (Linkwitz-Riley vs. Bessel vs. Butterworth) and choosing starting crossover points. |
| [references/patterns/staging-depth.md](file:///skills/autosound-tuning/references/patterns/staging-depth.md) | Troubleshooting front-back stage depth, vertical stage height, or driver spatial layering. |
| [references/core/enclosure-install-diagnostics.md](file:///skills/autosound-tuning/references/core/enclosure-install-diagnostics.md) | Diagnosing hardware rattles, SBIR vs. speaker cabinet resonances, nearfield testing, or CLD damping. |
| [references/core/impedance-ts.md](file:///skills/autosound-tuning/references/core/impedance-ts.md) | Measuring driver T-S parameters, sealed/ported box design, DVC wiring, or driver impedance matching. |
| [references/patterns/competition.md](file:///skills/autosound-tuning/references/patterns/competition.md) | Preparing for EMMA, AYA, or CARMusic SQ competitions (judging guidelines, crossfeed, or target curves). |
| [references/core/preset-strategy.md](file:///skills/autosound-tuning/references/core/preset-strategy.md) | Structuring multiple DSP slots (base output layer vs. subjective virtual voicing presets). |
| [references/patterns/test-tracks.md](file:///skills/autosound-tuning/references/patterns/test-tracks.md) | Selecting objective diagnostic audio tracks with timestamps to verify staging, center focus, sibilance, or bass. |
| [references/patterns/voicing-by-ear.md](file:///skills/autosound-tuning/references/patterns/voicing-by-ear.md) | Applying Arkadij's symptom-to-fix ear EQ map or executing client subjective taste tuning. |
| [references/patterns/method-hashimoto.md](file:///skills/autosound-tuning/references/patterns/method-hashimoto.md) | Applying Hashimoto's specialized "slope-first" filter matching, polarity-by-ear, or mono-center focus. |
| [references/tooling/helix-phase-allpass.md](file:///skills/autosound-tuning/references/tooling/helix-phase-allpass.md) | Tuning Helix-specific phase controls or configuring 2nd-order all-pass filters. |
| [references/tooling/helix-eq-export.md](file:///skills/autosound-tuning/references/tooling/helix-eq-export.md) | Formatting, exporting, or importing PEQ parameter banks in Audiotec-Fischer format. |
| [references/tooling/rew-tool-docs.md](file:///skills/autosound-tuning/references/tooling/rew-tool-docs.md) | Integrating REW API client scripts or verifying the built-in python module layout. |
| [references/tooling/rew-api-quirks.md](file:///skills/autosound-tuning/references/tooling/rew-api-quirks.md) | Debugging REW API float32 encoding, single-filter gaindB requests, or loopback timing offsets. |
| [references/tooling/screen-read-dsp.md](file:///skills/autosound-tuning/references/tooling/screen-read-dsp.md) | Parsing DSP parameters off screenshots (using vision/screencapture) when config exports are locked. |
| [references/core/review-loop.md](file:///skills/autosound-tuning/references/core/review-loop.md) | Executing TWO-PASS anti-anchoring reviews, handling multi-AI deadlocks (3/3), or running cross-session audits. |
| [references/tooling/setup-critic-channel.md](file:///skills/autosound-tuning/references/tooling/setup-critic-channel.md) | Configuring local CLI environments (agy, gemini-cli) or setting up the .critic-env credentials. |
| [references/core/feedback-loop.md](file:///skills/autosound-tuning/references/core/feedback-loop.md) | Executing the session-close feedback ritual, collecting skill feedback, or sharing anonymized car profiles. |

---

## 🛠️ Review Channel (Recommended: two different AIs)

A second, independent reviewer prevents single-perspective bias — and the real strength comes from a **different AI vendor** than the Generator (different training → different blind spots). **Recommended default: Claude + Gemini** — one drives as Generator, the other reviews as Critic-Advisor (Codex/ChatGPT is a third option). Run rounds via the per-vendor CLI wrappers or the unified Python tool.

**But the method works fine with a SINGLE AI** — the reviewer role still adds a lot, and most setups have one model (running several paid AIs is a big ask). A second vendor is a *bonus, not a requirement*; see the single-AI ladder (§3). **Any reviewer is always an on-demand, stateless call** that re-reads state from disk each time — **never a long-lived background agent** (those die on restart / laptop-sleep, and long-lived solo loops are exactly where long sessions drift). Because the reviewer runs **clean each call, it doubles as a drift-watchdog**: if a proposal contradicts the on-disk state, re-opens a banked decision, or confuses the phase, the reviewer should flag likely Generator context-drift and recommend re-anchoring from disk — or a **/clear + resume** — before continuing.

### 1. Per-vendor CLI wrappers (recommended)
Battle-tested Bash wrappers, one pair per vendor. They auto-detect the local CLI and handle quota/model fallback, credentials, and logging. **Pair a reviewer from a different vendor than your Generator:**
* **Gemini:** `scripts/gemini_critic.sh` · `scripts/gemini_advisor.sh <package.md> [trace.csv]`
* **Claude:** `scripts/claude_critic.sh` · `scripts/claude_advisor.sh <package.md> [trace.csv]`
* **Codex (ChatGPT):** `scripts/codex_critic.sh` · `scripts/codex_advisor.sh <package.md> [trace.csv]`

*(Note: In user workspaces these live in `.agents/skills/autosound-tuning/scripts/` or `.claude/skills/autosound-tuning/scripts/`.)*

### 2. Unified cross-platform tool (`autosound_ai.py`)
One stdlib-only entry point for any vendor (drives local CLIs or cloud APIs). Must pass `python scripts/autosound_ai.py doctor` before production use. If no CLI/API is available, **Clipboard Mode** copies the full prompt block to paste into any web LLM chat:
* **Critic:** `python scripts/autosound_ai.py critic <package.md> [trace.csv]`
* **Advisor:** `python scripts/autosound_ai.py advisor <package.md> [trace.csv]`

### 3. Single AI — the reviewer ladder (works fine with just ONE model)
One AI is fully supported. A reviewer role still adds a lot, so **never run solo on a long or drift-prone session** (a known failure mode of some Generators: losing DSP state / phase mid-session). When your preferred cross-vendor reviewer is unavailable (e.g. a daily token limit hit mid-session), don't drop to solo — descend this ladder, keeping an **on-demand, stateless** reviewer active:
1. **Pause & wait** for the cross-vendor reviewer (e.g. until the daily reset). Tuning isn't time-critical — waiting to keep the strong reviewer usually beats pushing on with a weak one.
2. **Another vendor** on-demand, if one is configured.
3. **Same vendor, HIGHER tier** than the Generator (e.g. a Flash generator reviewed by a Pro / thinking model). Model-tier diversity catches more than a peer; ⚠️ it still shares the vendor's systematic blind spots, so it's a rung below true cross-vendor.
4. **Same model, context-isolated** — the reviewer sees only the proposed package, never the Generator's inner monologue. Weakest (catches reasoning-trace anchoring, not model-level bias); last resort.
> [!IMPORTANT]
> Every rung is a **short-lived on-demand call that re-hydrates from disk**, NOT a long-lived background agent (those crash on restart / laptop-sleep). Keep the reviewer role active and prefer the highest tier available. Descend the ladder only as far as forced; **never silently go solo.**

---

## 📊 Model Selection Guidance

Proactively advise the user when to switch models. Do not waste high-reasoning context on routine tasks:

| Active Task | Model Class | Rationale |
| :--- | :--- | :--- |
| Parsing data, routine PEQ adjustments, draft review packages | **Medium class (e.g., Sonnet)** | High speed, cost-efficient, accurate data parser. |
| Crossover strategy (Phase 1), Multi-AI Deadlocks (3/3) | **High-reasoning class (e.g., Opus)** | Exceptional multi-variable cabin physics reasoning. |
| Technical Verdicts (Phase 3), Complex Psychoacoustic Checks | **High-reasoning class (e.g., Opus)** | Highly nuanced judgment calls. |

---

## ✍️ Output Style

1. **Be Honest and Direct:** Lead with what the user will hear:
   `🔍 What I see` · `⚠️ Main problems` · `✅ Fixable / ❌ Not fixable` · `🔧 Next steps` · `❓ One question`
2. **Action-Oriented Context:** Establish naming and paths once at intake. During active tuning steps, provide **copy-paste-ready specifics**: the exact save PATH, short comma-separated measurement lists, and direct targets.
3. **EQ Discipline:** Max boost is **$+6\text{ dB}$**. Do not add auto-generated 30-band full registers. Propose and add only the specific bands the channel requires, review them sequentially with the user, and format them clearly for transfer.
