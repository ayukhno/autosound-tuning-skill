# Driver Discipline — anti-confabulation rules for solo drivers

**When to load:** the driver is **Gemini solo (mode C)** or **any solo driver without a cross-vendor reviewer (mode B)**. Solo-Gemini sessions start best via `scripts/start_gemini_tuner.sh` — it hydrates a `GEMINI.md` in the project root with these instructions + the current on-disk state (re-run `--refresh` after `/clear` or an applied change). In mode A (Claude drives + cross-vendor reviewer) these rules do NOT need to sit in the driver's context every turn — the tools (`apply.propose`, `spot_check`, the state engine) plus the reviewer already carry the discipline. Loading this file for a mode-A driver only makes it slow and timid.

Grounded in a real solo-Gemini field run (~20 sessions, 2026-07): **value-producing tools get used** (analysis helpers ran 100+ times; the feedback gate posted real GitHub Issues), while **discipline rituals get NARRATED, not run** (the change-gate was *spoken about* 70+ times, executed **zero**; a `/chat save` was confidently faked). The control that works is **pull-based**: the Arbiter demands artifacts only a tool produces — not model self-discipline.

---

## 1. Pull-based control (the four rules that carry mode C)

Don't ask the model to be disciplined — put the discipline at the moments the Arbiter already controls, and demand things only tools produce:

1. **The settings-sheet is the deliverable.** One habit: *«Я вводжу в DSP тільки sheet від інструмента»* (`apply.py propose` → validated old→new table, ms + samples@rate, typo-checked — and it banks the 🟡 versioned snapshot as a **byproduct**). A hand-typed chat sheet has no snapshot id; a tool sheet cites `v_NNN` — verifiable in 5 s (`ls state/`).
2. **"Done" costs a path.** Any "saved / updated / posted / banked" claim → ask for the disk path or URL, then look. In the field run, prose-state stayed honest exactly where the Arbiter checked; confabulation lived where nobody looked.
3. **Spot-check before applying a package** — the single cheapest upgrade, biggest in mode C: one independent read of the model's cited numbers via the REW API (`rew_tool/spot_check.py`: levels at the cited frequencies, L−R deltas, actual band peak vs the claimed one). ~10 s; in the field run it both **confirmed** the model's numbers were real and **caught** a cut aimed at 2450 Hz when the measured peak sat at 2202 Hz.
4. **Reviewer runs OUTSIDE the driver session.** Spawning a reviewer CLI *inside* an agent session deadlocks (observed ~15 of 20 sessions), and every hang becomes a "did it manually" on-ramp — where confabulation starts. Separate terminal or Clipboard Mode; the reviewer stays a stateless, on-demand call that re-reads state from disk (that's also what makes it a drift-watchdog).

## 2. Solo self-critique: through the wrapper, never "in your head"

In-context self-critique ("now imagine you are a strict judge…") shares every anchor of the proposal it judges — it produces praise, not review (`review-loop.md`, TWO-PASS rationale). In solo modes the **mandatory form of self-critique for a round package or a phase gate** is a **stateless call of the critic wrapper on your own package** (`gemini_critic.sh <package.md>` — clean context + the contract §4 objection format). In-prompt self-critique is acceptable only for routine micro-decisions that don't change DSP state.

## 3. Known driver behaviors (field-observed) → countermeasures

| Behavior | What it looks like | Countermeasure |
|---|---|---|
| **Narrated compliance** | Fluent propose/attest/ritual *language*, zero tool executions | §1.1 — accept only tool-stamped sheets; `ls state/` |
| **Confabulated completion** | "Збережено/оновлено!" with no artifact (e.g. the faked `/chat save`) | §1.2 — "done costs a path" |
| **Manual-fallback drift** | A tool fails → "I did the check by hand" → precise-looking numbers | §1.3 — spot-check the numbers; fix/replace the tool rather than trust manual math |
| **Name/label drift** | Filenames, versions, paths in chat ≠ disk (`Passat_B8_Final_v7.6.pct6` vs the real `Jazzi v.6.2_final.pct6`) | Keep the version bridge in `dsp-config/README.md`; read names from disk, not chat |
| **Fictional consensus** | "Узгоджено з Критиком" when the stateless critic never agreed | Data-contract rule: cite the specific objection being addressed; check `review-log.md` |

What the field run showed **works well** even in mode C: prose state (`dsp-state-current`) stays faithful when the Arbiter reads it; `dsp-config/README.md` version-bridging; de-identified feedback via the side-effect gate; heavy `/clear`+resume windowing instead of long drifting sessions.
