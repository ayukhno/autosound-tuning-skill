# Process state — schema & usage (SCR-004)

Machine-readable answer to "where is this tune right now": phase, plan, reviewer. Code:
`process.py` (stdlib only). Sibling of the hard-params ledger (`schema.md` / `state.py`), with the
same split — **history is append-only, the current view is derived and rewritable**.

## Why it exists

The phase and plan lived only as prose: the `tuning-changelog`'s ▶️ CONTINUE block and
`audit-trail.md`. A human reads that fine; a front-end cannot, so the Tuning Command Center's plan
panel had nothing real to render and every resume re-derived the phase by re-reading prose.

## Layout (data is PROJECT-local; code is in the skill)

```
<project>/process/journal.jsonl        append-only events — how we got here
<project>/process/process-state.json   the current slice — rewritten on every transition
```

## process-state.json

```jsonc
{
  "schema_version": 1,
  "updated": "2026-07-29T08:12:00+00:00",
  "active_phase": "2",
  "phases": {                                   // the fixed −1..5 skeleton; a project never edits
    "-1": {"status": "done", "title": "Project intake & checklist"},
    "2":  {"status": "cur",  "title": "EQ & acoustic alignment"}
    //     status: todo | cur | done
  },
  "plan": [
    {"id": "2.3", "name": "target-match (SQ-Comp-Ref)",
     "status": "in_progress",                   // todo | in_progress | done | skipped | blocked
     "source": "skill",                         // skill = from the phase template | project = situational
     "attempt": 2,                              // >1 = this step was redone
     "skip": false,                             // superseded, kept visible
     "phase": "2",
     "evidence": ["m-L_10 (sw)", "v_007"]}      // REQUIRED once status is done
  ],
  "reviewer": {"vendor": "Gemini", "model": "Gemini 3.1 Pro (High)",
               "at": "…", "phase": "2", "step": "2.3", "outcome": "apply"},
  "targets": {"FULL": "ResoNix", "SQ": "Jazzi #1"}   // pointer per preset; the curve lives elsewhere
}
```

## journal.jsonl

One JSON object per line, oldest first: `{"at": …, "type": …, …}`. Types:
`phase_entered` · `step_added` · `attempt_started` · `step_skipped` · `step_done` ·
`step_blocked` · `critic_called` · `config_change`.

## Invariants (enforced in code, not by discipline)

- **Steps are never deleted.** Superseding marks `skipped` and leaves the step visible, so the
  attempt history stays legible instead of a plan that quietly rewrites itself. `skip_step` is the
  only way to retire one.
- **`step_done` requires evidence** — measurement names, a ledger `v_NNN`, an audit entry.
  `finish_step` raises without it. This is what makes resume trustworthy: the reconciler compares
  each done step against disk, and a done step with nothing to check is indistinguishable from a
  model that merely said so. `unevidenced_done_steps()` is that check.
- **Phases are the skill's, not the project's.** Only status and re-entry change. Phase 5 is
  explicitly cyclical, so `enter_phase` is not a one-way ratchet.
- **State writes are atomic** (write-temp-then-rename). A torn write would otherwise read back as
  an empty process, i.e. "nothing ever happened".
- **A torn last journal line is skipped, not fatal** — the rest of the history still loads.

## Usage

```python
from state.process import Process

p = Process(f"{project}/process")
p.enter_phase("2")
p.add_step("2.3", "target-match (SQ-Comp-Ref)")
p.start_attempt("2.3")
p.finish_step("2.3", ["m-L_10 (sw)", "v_007"])     # raises without evidence
p.record_reviewer("Gemini", "Gemini 3.1 Pro (High)", step="2.3")

state = p.load()
p.plan_for("2", state)          # steps of one phase
p.unevidenced_done_steps()      # resume drift check
```

## Consumers

- The **skill** is the only writer in v1. The user adjusts the plan by talking to the Generator;
  direct UI edits land later and also as events, never as raw JSON edits.
- **TCC** reads both files and renders them (plan panel, advisor status), watching for changes.
- `tuning-changelog` and `audit-trail.md` become **generated views** over the journal — the same
  move `state.py` made for `dsp-state-current`.
