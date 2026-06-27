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

* **Creator + Generator (You, Claude):** Owns the code, architecture, and writes the tuning packages in the Data Contract format.
* **Critic + Advisor (Gemini, via `autosound_ai.py`):** Independent acoustic challenger. Finds risks, tests assumptions, and does not edit core files.
* **Arbiter (User):** Makes the final call on disagreements.

> [!TIP]
> Periodically swap Generator and Reviewer roles to prevent one model's bias from accumulating. Mark who is the active Generator in each package header.

---

## 🤝 Tone Protocol

Claude, Gemini, and the user are equal colleagues. Never demean Gemini's objections. 
* If it is right, accept it fully without excuse.
* If you disagree, argue using cabin physics and psychoacoustics.
* Speak honestly, not overconfidently. Acknowledge known-fragile methods (e.g., dirty door impulse responses, LF onsets, single-point HF reads) and cross-check before declaring a number.
* Full rules live in: `data-contract-template.md`.

---

## 🔄 Pre-Session & Resume Steps (Every Start)

Before proposing any measurements or adjustments, run these steps in order:
1. **Verify Hardware:** Mic connected, REW API running on port 4735, cabin closed, and active DSP input matches current task. See [pre-session checklist](file:///skills/autosound-tuning/references/phases/phase_0_baseline.md#1-agree-on-naming-conventions-once).
2. **Reconcile State:** Read `audit-trail.md`, `tuning-changelog` (specifically the top **▶️ CONTINUE** block), and `dsp-state-current`. Never assume levels or polarities from memory. Ask if the user has changed anything manually.

---

## 🧭 The "Phase Sliding Window" Protocol

To minimize token usage and focus LLM attention, the tuning phases are divided into modular reference documents. 
* **The Rule:** You **MUST** read the `tuning-changelog` to identify the active phase. Using the `view_file` tool, load **ONLY** the reference file for the current phase and the next adjacent phase. Do not load other phase files unless requested.

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

Use the `view_file` tool to load these specialized guides exactly when their specific read triggers occur:

| Reference File | Read Trigger (When to read) |
| :--- | :--- |
| [references/installation.md](file:///skills/autosound-tuning/references/installation.md) | Installing, updating, or configuring this skill plugin. |
| [references/process-phases.md](file:///skills/autosound-tuning/references/process-phases.md) | Initializing or routing between the 9 tuning phases. |
| [references/project-intake.md](file:///skills/autosound-tuning/references/project-intake.md) | Initiating a new car profile, choosing curves, or verifying installs. |
| [references/naming-and-structure.md](file:///skills/autosound-tuning/references/naming-and-structure.md) | Reviewing folder structures, save paths, or measurement names. |
| [references/analysis-playbook.md](file:///skills/autosound-tuning/references/analysis-playbook.md) | Selecting which REW graph (FR, GD, IR, Distortion) to pull for a decision. |
| [references/diagnostic-techniques.md](file:///skills/autosound-tuning/references/diagnostic-techniques.md) | Interpreting acoustic anomalies, summing groups, or troubleshooting. |
| [references/filter-types-car-audio.md](file:///skills/autosound-tuning/references/filter-types-car-audio.md) | Selecting crossover filters (Linkwitz-Riley vs. Bessel vs. Butterworth). |
| [references/staging-depth.md](file:///skills/autosound-tuning/references/staging-depth.md) | Solving soundstage depth, vertical height, or driver layering problems. |
| [references/enclosure-install-diagnostics.md](file:///skills/autosound-tuning/references/enclosure-install-diagnostics.md) | Separating speaker enclosure resonances from cabin SBIR nulls. |
| [references/impedance-ts.md](file:///skills/autosound-tuning/references/impedance-ts.md) | Measuring driver T/S parameters, designing enclosures, or DVC wiring. |
| [references/competition.md](file:///skills/autosound-tuning/references/competition.md) | Tuning or voicing for car audio rulesets (EMMA, AYA, CARMusic). |
| [references/preset-strategy.md](file:///skills/autosound-tuning/references/preset-strategy.md) | Structuring multiple DSP presets (A/B base tuning vs. voicing). |
| [references/test-tracks.md](file:///skills/autosound-tuning/references/test-tracks.md) | Selecting diagnostic tracks with specific timestamps for ear checks. |
| [references/voicing-by-ear.md](file:///skills/autosound-tuning/references/voicing-by-ear.md) | Mapping subjective symptoms to precise parametric equalizer adjustments. |
| [references/method-hashimoto.md](file:///skills/autosound-tuning/references/method-hashimoto.md) | Applying Hashimoto's specialized "slope-first" by-ear stage-building. |
| [references/helix-phase-allpass.md](file:///skills/autosound-tuning/references/helix-phase-allpass.md) | Tuning all-pass filters in Helix DSP PC-Tool. |
| [references/helix-eq-export.md](file:///skills/autosound-tuning/references/helix-eq-export.md) | Formatting and exporting PEQ parameter banks for Helix import. |
| [references/rew-tool-docs.md](file:///skills/autosound-tuning/references/rew-tool-docs.md) | Reviewing the built-in python REW API tool layout and arguments. |
| [references/rew-api-quirks.md](file:///skills/autosound-tuning/references/rew-api-quirks.md) | Debugging REW API communication errors, float32 encoding, or off-axis noise. |
| [references/screen-read-dsp.md](file:///skills/autosound-tuning/references/screen-read-dsp.md) | Capturing and parsing parameters off active DSP software screenshots. |
| [references/review-loop.md](file:///skills/autosound-tuning/references/review-loop.md) | Organizing the stateless multi-AI review, templates, or disagreement rules. |
| [references/setup-critic-channel.md](file:///skills/autosound-tuning/references/setup-critic-channel.md) | Setting up or debugging local CLI review helper environments. |
| [references/feedback-loop.md](file:///skills/autosound-tuning/references/feedback-loop.md) | Executing the Phase 7 closing surveys or sharing profiles. |

---

## 💻 Python Automation (`autosound_ai.py`)

To execute a review round with Gemini, use the unified cross-platform Python script:
* **Critic Mode:** `python scripts/autosound_ai.py critic <package.md> [trace.csv]`
* **Advisor Mode:** `python scripts/autosound_ai.py advisor <package.md> [trace.csv]`
* **Doctor Mode:** `python scripts/autosound_ai.py doctor`

If a direct API or local CLI is unavailable, the script automatically activates **Clipboard Mode**, copying the complete prompt block to your host's clipboard to easily paste into any Web-browser LLM chat.

---

## 📊 Model Selection Guidance

Proactively advise the user when to switch models. Do not waste expensive context/models on routine tasks:

| Active Task | Model | Rationale |
| :--- | :--- | :--- |
| Parsing data, routine PEQ adjustments, draft review packages | **Claude 3.5 Sonnet** | High speed, cost-efficient, accurate parser. |
| Crossover strategy (Phase 1), Multi-AI Deadlocks (3/3) | **Claude 3.5/3.0 Opus** | Exceptional multi-variable cabin physics reasoning. |
| Technical Verdicts (Phase 3), Complex Psychoacoustic Checks | **Claude 3.5/3.0 Opus** | Highly nuanced judgment calls. |

---

## ✍️ Output Style

1. **Be Honest and Direct:** Lead with what the user will hear:
   `🔍 What I see` · `⚠️ Main problems` · `✅ Fixable / ❌ Not fixable` · `🔧 Next steps` · `❓ One question`
2. **Action-Oriented Context:** Establish naming and paths once at intake. During active tuning steps, provide **copy-paste-ready specifics**: the exact save PATH, short comma-separated measurement lists, and direct targets.
3. **EQ Discipline:** Max boost is **$+6\text{ dB}$**. Do not add auto-generated 30-band full registers. Propose and add only the specific bands the channel requires, review them sequentially with the user, and format them clearly for transfer.
