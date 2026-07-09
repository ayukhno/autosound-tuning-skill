# Review loop — independent review of your own work

Two wings of one discipline: **check yourself through someone else's eyes, and keep order.** Born in a real project (car-audio, 2026-06) where the pattern proved its worth twice: a cross-session review caught a 7-day drift of the canon; cold-start audits by another model found what the team had missed for 10+ rounds (an unused tool, accumulated regression, a self-harming fix).

> This file holds the **generic review process**; the rest of the `autosound-tuning` skill holds the **domain specifics** — its wrapper scripts (`scripts/gemini_*.sh`), the package/contract format (`assets/data-contract-template.md`), the domain judges (measurement + the ear), and the memory-file paths. Read this before the first review round of a session.

---

## Wing 1 — SELF-REVIEW (project hygiene)

### The truth model (the foundation)
Every living project must have a **declared** answer to "where the truth lives", or the documents quietly diverge:
- **Canon** = the stable distillation (system, conventions, key conclusions, disproven hypotheses). Updated **at milestones**, not every session.
- **Live state** = separate files (the config state, a changelog with a resume block, the detailed round log, the decision audit-trail). Updated every session.
- Mirrors / fallbacks — explicitly marked ("SNAPSHOT", "mirror of the canon") with a pointer to the original.
- The truth model is **written identically at every entry point** (canon, the README, the skill) — a new session, from any side, sees the same scheme.

### Cross-session / cold-start audit (fresh eyes)
Periodically (at milestones, on reversals, or when "we've tried everything") run an audit **without your own anchors**:
- **Who:** another session, ideally **another model** (a cold-start sub-agent). A fresh look carries none of your biases and sees what you've grown used to.
- **The mandate (the wording is critical):** "challenge our conclusion · find what's missed · every point falsifiable (how to check it) · if the data contradicts our picture, say so plainly · don't restate what's known".
- **Give it:** the raw data / access + the log + the current conclusion as the object to attack. Do NOT hand it your interpretation as the frame of the question.

### The "brief → fix → verify" cycle
1. The auditor writes a **brief**: the problem · authoritative sources (read them, don't trust a retelling) · concrete deltas · readiness criteria · out of scope.
2. The executor in the project **VERIFIES THE BRIEF FIRST, then acts.** An auditor from another session didn't see everything (a typical case: "the files don't exist" — but they're in another folder / memory, just outside its view). False claims in the brief are corrected, not executed.
3. Execution → a report with corrections to the brief.
4. **Verification on a third pass** (the auditor, or yet another session, checks the result). Residual remarks — close them or consciously accept them.

---

## Wing 2 — MULTI-AI ORCHESTRATION (Critic / Advisor / Arbiter)

### Roles (vendor-agnostic — the role matters, not the vendor)
| Role | Essence | When |
|---|---|---|
| **Generator** | analyzes, forms the proposal | you (the main agent) |
| **Critic-Advisor** <br>*(Критик-Радник)* | Unified reviewer: stress-tests physical hypotheses (falsifiable acoustic objections) AND provides constructive architectural advice + maintains process consistency and session memory; **does not praise** | checking proposals, guiding state transitions, preventing infinite loops |
| **Arbiter** | the human: the final word on disagreement, ear / domain truth | always |
| **Cold-auditor** | another model, cold-start, full history | milestones, reversals, "tried everything" |

Periodically **swap Generator ↔ Critic** (anti-bias). Any AI drops into a role via a thin wrapper (CLI / API) — the wrapper injects the contract + context and logs the audit-trail.

### Tone protocol (all levels)
Collaboration, not competition. Don't characterize a colleague's answer ("a weak objection") — convey the technical content and your own technical position. A colleague is right → "X is right: [reason]", without "partly". You disagree → "my position: [argument]". You were wrong → "I was wrong: [exactly what]", without softeners. With the Arbiter — don't agree automatically: if there's a technical argument against, say it plainly.

### TWO-PASS — anti-anchoring (the key protocol)
**The symptom of the disease:** a reviewer who "fully agrees" round after round is ratifying your frame, not checking it. The anchor sits in the **conclusion baked into the question**, not in memory.
1. **Pass 1 — OPEN:** the raw data + neutral facts + an **open question WITHOUT your conclusion / hints** ("what's your read?") → an independent diagnosis.
2. **Reconcile:** compare its read with yours → form the proposal.
3. **Pass 2 — CRITIQUE:** the proposal goes to the Critic ("objectively, don't invent").
- **Keep** the reviewer's memory / history (otherwise it re-derives and wastes rounds on the already-rejected) — facts yes, conclusions no.
- **Validation signal:** if in Pass 1 the reviewer itself caught what you deliberately withheld, the convergence can be trusted.

### Session-memory discipline (for the Advisor)
A persistent file, injected into every call; after a round, append: the gist of the package → the advice → the decision / measurement. **Hard-separate CONFIRMED vs OPEN** — history should inform, not pre-decide an open question. Honest OVERTURNED entries: mark the disproven, don't erase it (a record of the error = protection against repeating it).

### Loop rules
1. Max **3 rounds** per question; the `[Iteration N/3]` counter is on you.
2. **Agreement** = no new falsifiable objection.
3. `3/3` with no agreement → a disagreement table for the Arbiter: Parameter | Generator's position | Critic's position | what's at stake. The Arbiter decides in ~30 s.
4. After agreement / verdict → a **ready-to-apply artifact** (not prose) + an audit-trail entry (ID, decision, key objection, verdict). The artifact goes straight into the chat as a legible settings-sheet — see the **Interactive Presentation Rule** in `SKILL.md` (never make the Arbiter open files to find the values).

### Audit-trail
The canonical decision log, append-only: each round — a stamp (date, role, model, package); at milestones — a consolidated block of verdicts. Without it, decisions get "banked" in chats and lost on restart.

> After a CLI / vendor migration — **smoke-test the channel with a real micro-package** before working ("nothing needs changing" has historically not held up — `setup-critic-channel.md`).
