# Happy paths — 3 short worked walkthroughs

Skim these once to see the *shape* of a session end-to-end. They are deliberately terse — the authoritative detail lives in the phase files (`process-phases.md`) and the guardrails (`SKILL.md`). Each step names the real file/tool so you can follow the same moves.

---

## A. Brand-new project (from scratch)

> User: *"help me tune my car audio from scratch"* → **Phase -1 → 0 → 1**.

1. **Intake (Phase -1).** Interview equipment, channels, reference listener, goals; pick a target curve; confirm install verification (polarity, gain/noise). → `phase_-1_intake.md`, `project-intake.md`. Write the answers into the project's `autosound_context.md`.
2. **Propose the reviewer channel.** At the first real proposal, offer to open the Critic/Advisor channel (ideally a different vendor) — don't proceed silently single-perspective. → SKILL.md guardrail, `process-control.md` (pick mode A/B/C).
3. **Baseline (Phase 0).** Agree naming conventions once, import the target curve, take the raw baseline sweeps. → `phase_0_baseline.md`, `naming-and-structure.md`.
4. **Foundation (Phase 1).** From the baseline: crossovers + levels + gross arrival-TA. Run the Generator→Critic loop on the crossover strategy. Bank the agreed change with `apply.propose` (it emits the settings-sheet + a `v_NNN` snapshot); the Arbiter enters it and you `attest` (🟡→🟢). → `phase_1_foundation.md`.
5. **Verify** with a re-measure, then slide the window to Phase 2.

**What "good" looks like:** every entered value came from a tool-emitted settings-sheet (ms + samples@rate), state is on disk, the Critic saw the crossover plan.

---

## B. Resume after a break

> User: *"continue my tune / what's my current state"* → the skill fires on the resume triggers.

1. **Reconcile state (do NOT trust memory).** Read `audit-trail.md`, the top **▶️ CONTINUE** block of `tuning-changelog`, and `dsp-state-current`. If multi-slot, read the active-slot banner first (`state.py registry render`) and work only against that slot. → SKILL.md Pre-Session steps.
2. **Check banked decisions.** Look for 🟡 pending items agreed last time but not yet applied; prompt the Arbiter to apply them.
3. **Ask what changed.** Anything moved manually since the pause (mic, DSP, cabin)? Is REW reachable?
4. **Load only the active phase** (+ the next) per the sliding-window rule, then continue from the ▶️ NEXT STEPS list.

**What "good" looks like:** you restated the current crossovers/TA/gains from disk, not from the chat history, and surfaced any 🟡 banked item before proposing anything new.

---

## C. A single Phase 1 → Phase 2 change

> Mid-session: a crossover joint is set, now you're doing EQ.

1. **Re-read `dsp-state-current` before proposing** — including the virtual/VCP EQ layer and any existing per-channel notches (`get_filters` first; never assume a channel is raw).
2. **Diagnose, then propose one change.** E.g. a minimum-phase cabin peak → one PK cut (max boost +6 dB rule; no auto 30-band registers). Confirm it's min-phase (excess-phase read), not an interference null you must leave.
3. **Review + bank.** Critic pass on the EQ plan → `apply.propose` → Arbiter enters the sheet → `attest`.
4. **⚠️ Re-entrancy:** if the EQ move sits inside a crossover joint band (±~1 octave of a joint), it rotates local phase → **re-open the Phase-2 joint alignment gate** and re-check the summation. A passed gate is not permanent. → `process-phases.md` quality-gate note.

**What "good" looks like:** you read the channel's real filters first, proposed only the bands the channel needed, and re-verified the joint after an in-band EQ move.
