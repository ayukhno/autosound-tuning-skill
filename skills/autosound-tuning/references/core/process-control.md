# Process Control — Operating Modes & the Arbiter's Playbook

How to keep a session's *process* honest (state, claims, discipline) without scaffolding.
Grounded in a real solo-Gemini field run (~20 sessions, 2026-07): **value-producing tools get
used** (analysis helpers ran 100+ times; the feedback gate posted real GitHub Issues; backups got
saved), while **discipline rituals get NARRATED, not run** (the change-gate was *spoken about*
70+ times and executed **zero** times; a `/chat save` was confidently faked). The control that
works is **pull-based**: the Arbiter demands artifacts only a tool produces — not model self-discipline.

---

## 1. The three operating modes (Arbiter picks, consciously)

Reliability-ranked. Pick per session — critical work up the list, casual voicing down it.

| Mode | Configuration | Reliability | Trade-off |
|---|---|---|---|
| **A** | **Claude drives (Generator) + Gemini as Advisor** — advisor call **MANDATORY at solution-search nodes**: crossover strategy (Phase 1), the EQ plan (Phase 2), the Phase-3 verdict, staging/imaging decisions | Highest | Needs both AIs; slower per decision — buys anti-anchoring + a drift-watchdog |
| **B** | **Claude solo + self-control** — substrate tools (state/apply/gates) + disk-state discipline | Middle | One perspective; self-review catches less than cross-vendor. (Tool-compliance of a Claude driver: not yet field-measured — treat as promising, verify like anything else) |
| **C** | **Gemini solo** — **process-loss risk consciously ACCEPTED** | Lowest process-reliability, proven acoustics | Superb acoustic proposals and (in the measured run) numerically real data — but expect narrated compliance: no versioned state, "saved/updated" claims without artifacts, weaker resume. Mitigate with §2 + §3 |

Notes:
- These modes pick the **driver**. The Review-Channel §3 *ladder* (SKILL.md) picks the **reviewer**
  when your preferred one is unavailable — they compose, they don't compete.
- Mode C is a legitimate choice (one capable model is most people's reality). It is *not* "mode A
  minus discipline" — it's a different contract: the Arbiter supplies the process spine (§2),
  the model supplies acoustics.

## 2. Pull-based control (works in every mode, carries mode C)

Don't ask the model to be disciplined — put the discipline at the moments the Arbiter already
controls, and demand things only tools produce:

1. **The settings-sheet is the deliverable.** One habit: *«Я вводжу в DSP тільки sheet від
   інструмента»* (`apply.py propose` → validated old→new table, ms + samples@rate, typo-checked —
   and it banks the 🟡 versioned snapshot as a **byproduct**). A hand-typed chat sheet has no
   snapshot id; a tool sheet cites `v_NNN` — verifiable in 5 s (`ls state/`).
2. **"Done" costs a path.** Any "saved / updated / posted / banked" claim → ask for the disk path
   or URL, then look. In the field run, prose-state stayed honest exactly where the Arbiter
   checked; confabulation lived where nobody looked. (The faked `/chat save` announced success
   with no artifact anywhere.)
3. **Spot-check before applying a package** — the single cheapest upgrade, biggest in mode C:
   one independent read of the model's cited numbers via the REW API
   (`rew_tool/spot_check.py`: levels at the cited frequencies, L−R deltas, actual band peak
   vs the claimed one). In the field run this took ~10 s and did both jobs at once:
   **confirmed** the model's numbers were real (to the hundredth), and **caught** a real slip —
   a cut aimed at 2450 Hz when the measured peak sat at 2202 Hz.
4. **Reviewer runs OUTSIDE the driver session.** Spawning a reviewer CLI *inside* an agent
   session deadlocks (observed chronically: ~15 of 20 sessions), and every hang becomes a
   "did it manually" on-ramp — which is where confabulation starts. Run wrappers from a separate
   terminal, or use Clipboard Mode. The reviewer stays a stateless, on-demand call that re-reads
   state from disk (that's also what makes it a drift-watchdog).

## 3. Known driver behaviors (field-observed) → countermeasures

| Behavior | What it looks like | Countermeasure |
|---|---|---|
| **Narrated compliance** | Fluent propose/attest/ritual *language*, zero tool executions | §2.1 — accept only tool-stamped sheets; `ls state/` |
| **Confabulated completion** | "Збережено/оновлено!" with no artifact (e.g. the faked `/chat save`) | §2.2 — "done costs a path" |
| **Manual-fallback drift** | A tool fails → "I did the check by hand" → precise-looking numbers | §2.3 — spot-check the numbers; fix/replace the tool rather than trust manual math |
| **Name/label drift** | Filenames, versions, file paths in chat ≠ what's on disk (`Passat_B8_Final_v7.6.pct6` vs the real `Jazzi v.6.2_final.pct6`) | Keep the version bridge in `dsp-config/README.md`; read names from disk, not chat |
| **Fictional consensus** | "Узгоджено з Критиком" when the stateless critic never agreed | Data-contract rule: cite the specific objection being addressed; check the review log |

What the field run showed **works well** even in mode C: prose state (`dsp-state-current`) stays
faithful when the Arbiter reads it; `dsp-config/README.md` version-bridging; de-identified
feedback via the side-effect gate (it produces the pulled artifact — the Issue); heavy
`/clear`+resume windowing instead of long drifting sessions.

## 4. What we deliberately do NOT build

No compliance tokens, no override protocols, no close-phase police (built once, removed by
design). Scaffolding that polices a model gets narrated around — and stronger models make it
throwaway. Build only tools that stay useful regardless of model strength: calculators,
verifiers, and artifact-producers the human pulls.

## 5. For future dogfoods

Capture kit + behavioral scorecard pattern: pin the skill commit, `AUTOSOUND_STATE_ROOT` into the
project, collect `state/` + the session transcripts + `dsp-config/` + the `.mdat`, then audit
with invocation-greps (**count real `python …py` executions, not token mentions** — mentions
include the skill's own text and the model's narration; only invocations are ground truth).
