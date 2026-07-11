# Process Control — Operating Modes & the Arbiter's Playbook

How to keep a session's *process* honest (state, claims, discipline) without scaffolding.
The control that works is **pull-based**: the Arbiter demands artifacts only a tool produces —
not model self-discipline. The full anti-confabulation ruleset (pull-based control, solo
self-critique form, field-observed behaviors → countermeasures) lives in
[`driver-discipline.md`](file:///skills/autosound-tuning/references/core/driver-discipline.md)
— **load it only for modes B/C** (solo driver); mode A carries the discipline in tools + the reviewer.

---

## 1. The three operating modes (Arbiter picks, consciously)

Reliability-ranked. Pick per session — critical work up the list, casual voicing down it.

| Mode | Configuration | Reliability | Trade-off |
|---|---|---|---|
| **A** | **Claude drives (Generator) + Gemini as Advisor** — **ONE advisor call per round** at solution-search nodes: crossover strategy (Phase 1), the round's EQ plan (Phase 2), the Phase-3 verdict, staging/imaging decisions. Package the whole batch, not per-parameter calls | Highest | Needs both AIs; one extra call per round — buys anti-anchoring + a drift-watchdog |
| **B** | **Claude solo + self-control** — substrate tools (state/apply/gates) + disk-state discipline | Middle | One perspective; self-review catches less than cross-vendor. (Tool-compliance of a Claude driver: not yet field-measured — treat as promising, verify like anything else) |
| **C** | **Gemini solo** — **process-loss risk consciously ACCEPTED** | Lowest process-reliability, proven acoustics | Superb acoustic proposals and (in the measured run) numerically real data — but expect narrated compliance: no versioned state, "saved/updated" claims without artifacts, weaker resume. Mitigate with §2 + §3 |

Notes:
- These modes pick the **driver**. The Review-Channel *ladder* (SKILL.md) picks the **reviewer**
  when your preferred one is unavailable — they compose, they don't compete.
- Mode C is a legitimate choice (one capable model is most people's reality). It is *not* "mode A
  minus discipline" — it's a different contract: the Arbiter supplies the process spine
  (`driver-discipline.md`), the model supplies acoustics.
- **Model defaults** (names drift — treat as classes): driver routine = Claude Sonnet class;
  crossover strategy / Phase-3 verdicts / deadlocks = Claude Opus class; reviewer = Gemini Pro
  class for round packages and gates, Flash class only for routine advisor pings.

## 2. Discipline: where it lives per mode

- **Mode A:** the tools carry it — `apply.propose` (tool-stamped sheet + `v_NNN` snapshot),
  `spot_check.py` before applying a package, reviewer outside the driver session. No extra
  always-on rule text needed.
- **Modes B/C:** load [`driver-discipline.md`](file:///skills/autosound-tuning/references/core/driver-discipline.md)
  — pull-based control, the wrapper-only self-critique rule, and the behavior→countermeasure table.

## 3. What we deliberately do NOT build

No compliance tokens, no override protocols, no close-phase police (built once, removed by
design). Scaffolding that polices a model gets narrated around — and stronger models make it
throwaway. Build only tools that stay useful regardless of model strength: calculators,
verifiers, and artifact-producers the human pulls.

## 4. For future dogfoods

Capture kit + behavioral scorecard pattern: pin the skill commit, `AUTOSOUND_STATE_ROOT` into the
project, collect `state/` + the session transcripts + `dsp-config/` + the `.mdat`, then audit
with invocation-greps (**count real `python …py` executions, not token mentions** — mentions
include the skill's own text and the model's narration; only invocations are ground truth).
