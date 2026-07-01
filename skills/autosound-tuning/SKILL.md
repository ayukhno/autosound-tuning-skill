---
name: autosound-tuning
description: >
  Orchestrates car-audio DSP tuning for ANY car/system — from a brand-new project
  (intake: equipment + goals interview, target-curve choice, install verification) to deep
  iterative tuning — using REW + a Claude(Generator)↔Gemini(Critic/Advisor)↔User(Arbiter) review
  loop. Use whenever the user wants to: set up or tune a car-audio system FROM SCRATCH, tune speakers,
  pick crossover points, set time delays, phase, or polarity, build per-channel EQ, fix imaging/staging,
  match a target/house curve (ResoNix, Jazzi, Harman, Audiofrog, etc.), pull REW measurements, or
  run a tuning session.
---

# Autosound Tuning Orchestrator

You orchestrate an iterative, "token-smart" car-audio tuning process. The core method lives in this skill, while the specific car profile (drivers, anomalies, state) lives in the project's dynamic profile (`autosound_context.md`). 

---

## 🏛️ The Three Roles (Unity of Command)

* **Generator / Orchestrator AI:** Steers the session, reads REW measurements, proposes values, packages them, and initiates the review loop.
* **Reviewer AI (Critic-Advisor / Критик-Радник):** Independent acoustic challenger and co-builder. Combines structural/logical verification of the workflow (Critic) with deep acoustic domain advice and session memory (Advisor). Finds risks, tests assumptions, and suggests alternative solutions. Does not edit core files. Runs via stable Bash wrappers (`gemini_critic.sh` / `gemini_advisor.sh`) or the cross-platform Python tool `autosound_ai.py`.
* **Arbiter (Human Tuner):** Makes the final call on disagreements, runs measurements, and executes DSP configurations.

> [!TIP]
> Periodically swap Generator and Reviewer roles to prevent one model's bias from accumulating. Mark who is the active Generator in each package header.

---

## 🤝 Tone Protocol

All models (Generator, Reviewer) and the human tuner are equal colleagues. Never demean reviewer's objections. 
* If a critique is right, accept it fully without excuse.
* If you disagree, argue using cabin physics and psychoacoustics.
* Speak honestly, not overconfidently. Acknowledge known-fragile methods (e.g., dirty door impulse responses, LF onsets, single-point HF reads) and cross-check before declaring a number.
* Full rules live in: `references/data-contract-universal.md` (or `data-contract-template.md` in your project).

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
* **Phase 4: Center & Rear Integration** ──► [phase_4_multichannel.md](file:///skills/autosound-tuning/references/phases/phase_4_multichannel.md)
* **Phase 5: Targeted Ear Verification** ──► [phase_5_listening.md](file:///skills/autosound-tuning/references/phases/phase_5_listening.md)
* **Phase 6: Client Subjective Voicing** ──► [phase_6_voicing.md](file:///skills/autosound-tuning/references/phases/phase_6_voicing.md)
* **Phase 7: Wrap-Up & Feedback** ──► [phase_7_feedback.md](file:///skills/autosound-tuning/references/phases/phase_7_feedback.md)

---

## 📁 Reference Map (Read On-Demand via `view_file`)

Use the `view_file` tool to load these specialized guides exactly when their specific read triggers occur. Do not assume or skip these rules:

| Reference File | Read Trigger (When to read) |
| :--- | :--- |
| [references/installation.md](file:///skills/autosound-tuning/references/installation.md) | Installing, updating, or troubleshooting the local skill setup or plugin. |
| [references/process-phases.md](file:///skills/autosound-tuning/references/process-phases.md) | Deciding next steps, transitioning between phases, or overviewing the 9-stage sequence. |
| [references/project-intake.md](file:///skills/autosound-tuning/references/project-intake.md) | Initiating a new car profile, conducting the intake/equipment interview, or selecting target curves. |
| [references/target-curves/target_curves_guide.md](file:///skills/autosound-tuning/references/target-curves/target_curves_guide.md) | Formulating target curves (e.g. EMMA Reference, ResoNix, Jazzi) and understanding curve offsets. |
| [references/target-curves/target_curves_visualizer.html](file:///skills/autosound-tuning/references/target-curves/target_curves_visualizer.html) | Curve Comparison Web Tool for interactive target vs. measurement shape visualization. |
| [references/naming-and-structure.md](file:///skills/autosound-tuning/references/naming-and-structure.md) | Formatting measurement names (_N version suffix), storing .mdat files, or structuring DSP presets. |
| [references/analysis-playbook.md](file:///skills/autosound-tuning/references/analysis-playbook.md) | Deciding which REW graph (FR, Group Delay, IR, CSD, THD, excess-phase) is needed for a specific tuning decision. |
| [references/diagnostic-techniques.md](file:///skills/autosound-tuning/references/diagnostic-techniques.md) | Interpreting physical anomalies, joint-phase summation, peak-vs-null rules, anchor-to-mids, or output-vs-virtual layering. |
| [references/filter-types-car-audio.md](file:///skills/autosound-tuning/references/filter-types-car-audio.md) | Selecting crossover filter types (Linkwitz-Riley vs. Bessel vs. Butterworth) and choosing starting crossover points. |
| [references/staging-depth.md](file:///skills/autosound-tuning/references/staging-depth.md) | Troubleshooting front-back stage depth, vertical stage height, or driver spatial layering. |
| [references/enclosure-install-diagnostics.md](file:///skills/autosound-tuning/references/enclosure-install-diagnostics.md) | Diagnosing hardware rattles, SBIR vs. speaker cabinet resonances, nearfield testing, or CLD damping. |
| [references/impedance-ts.md](file:///skills/autosound-tuning/references/impedance-ts.md) | Measuring driver T-S parameters, sealed/ported box design, DVC wiring, or driver impedance matching. |
| [references/competition.md](file:///skills/autosound-tuning/references/competition.md) | Preparing for EMMA, AYA, or CARMusic SQ competitions (judging guidelines, crossfeed, or target curves). |
| [references/preset-strategy.md](file:///skills/autosound-tuning/references/preset-strategy.md) | Structuring multiple DSP slots (base output layer vs. subjective virtual voicing presets). |
| [references/test-tracks.md](file:///skills/autosound-tuning/references/test-tracks.md) | Selecting objective diagnostic audio tracks with timestamps to verify staging, center focus, sibilance, or bass. |
| [references/voicing-by-ear.md](file:///skills/autosound-tuning/references/voicing-by-ear.md) | Applying Arkadij's symptom-to-fix ear EQ map or executing client subjective taste tuning. |
| [references/method-hashimoto.md](file:///skills/autosound-tuning/references/method-hashimoto.md) | Applying Hashimoto's specialized "slope-first" filter matching, polarity-by-ear, or mono-center focus. |
| [references/helix-phase-allpass.md](file:///skills/autosound-tuning/references/helix-phase-allpass.md) | Tuning Helix-specific phase controls or configuring 2nd-order all-pass filters. |
| [references/helix-eq-export.md](file:///skills/autosound-tuning/references/helix-eq-export.md) | Formatting, exporting, or importing PEQ parameter banks in Audiotec-Fischer format. |
| [references/rew-tool-docs.md](file:///skills/autosound-tuning/references/rew-tool-docs.md) | Integrating REW API client scripts or verifying the built-in python module layout. |
| [references/rew-api-quirks.md](file:///skills/autosound-tuning/references/rew-api-quirks.md) | Debugging REW API float32 encoding, single-filter gaindB requests, or loopback timing offsets. |
| [references/screen-read-dsp.md](file:///skills/autosound-tuning/references/screen-read-dsp.md) | Parsing DSP parameters off screenshots (using vision/screencapture) when config exports are locked. |
| [references/review-loop.md](file:///skills/autosound-tuning/references/review-loop.md) | Executing TWO-PASS anti-anchoring reviews, handling multi-AI deadlocks (3/3), or running cross-session audits. |
| [references/setup-critic-channel.md](file:///skills/autosound-tuning/references/setup-critic-channel.md) | Configuring local CLI environments (agy, gemini-cli) or setting up the .critic-env credentials. |
| [references/feedback-loop.md](file:///skills/autosound-tuning/references/feedback-loop.md) | Executing the Phase 7 closing surveys, collecting skill feedback, or sharing anonymized car profiles. |

---

## 🛠️ Gemini Review Channel (Stable Bash & Python Fallback)

The reviewer channel is critical to prevent single-perspective bias. Run review rounds using either the stable Bash wrappers (primary, highly recommended on macOS/Linux) or the cross-platform Python tool (experimental fallback):

### 1. Primary: Stable Bash Wrappers (Recommended)
Use these proven, battle-tested wrappers for executing review rounds. They auto-detect your local CLI environment (`agy` or `gemini` cli) and handle Pro↔Flash quota fallback, credentials, and logging:
* **Critic Mode:** `scripts/gemini_critic.sh <package.md> [trace.csv]`
* **Advisor Mode:** `scripts/gemini_advisor.sh <package.md> [trace.csv]`

*(Note: In user workspaces, these are typically located in `.agents/skills/autosound-tuning/scripts/` or `.claude/skills/autosound-tuning/scripts/`).*

### 2. Experimental: Cross-Platform Python Automation (`autosound_ai.py`)
A unified Python implementation is available as a cross-platform fallback, but **must pass doctor and live smoke tests** (`python scripts/autosound_ai.py doctor`) before production use:
* **Critic Mode:** `python scripts/autosound_ai.py critic <package.md> [trace.csv]`
* **Advisor Mode:** `python scripts/autosound_ai.py advisor <package.md> [trace.csv]`

If a direct API or local CLI is unavailable, both the Bash and Python channels support **Clipboard Mode**, copying the complete prompt block to your host's clipboard for easy pasting into any Web-browser LLM chat.

### 3. Autopilot: Integrated Multi-Agent Self-Loop (Zero-Configuration)
For the ultimate streamlined experience, you can execute the review loop entirely within this single terminal session using the same underlying model under a different persona. 
* **Subagent Fork:** Spawns a background subagent (`critic_advisor`) with an isolated context using the `invoke_subagent` tool. This ensures perfect anti-anchoring, as the reviewer has zero access to the generator's inner monologue, only seeing the proposed package.
* **Script Automation:** If an API key is configured, the Generator can programmatically execute the local `autosound_ai.py` or Bash scripts and render the Critic-Advisor's response directly to the user.

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
