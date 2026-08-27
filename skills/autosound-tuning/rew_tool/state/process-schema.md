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
               "at": "…", "phase": "2", "step": "2.3", "outcome": "apply",
               "review": "process/reviews/2026-08-06T21-33-10-critic.md",  // SCR-027: WHAT was argued
               "mode": "api"},                                            //   api | cli | clipboard
  "targets": {"FULL": "ResoNix", "SQ": "Jazzi #1"},  // pointer per preset; the curve lives elsewhere
  "capture": {                                      // SCR-034: the OPEN capture round, or null.
    "id": "cap_002", "n": 2,                        //   Every round that ever happened is in the
    "phase": "0", "version": "v_003",               //   journal; only the live one is here, the
    "issued": "…", "closed": null,                  //   same way only the active phase is.
    "expected": ["tw-L_1 (sw)", "tw-L_1 (rta)"],    // what `naming.expected_groups` asked for
    "step": "0.1",                                  // SCR-040: the plan step this round satisfies
    "taken": {"tw-L_1 (sw)": {"at": "…", "planned": true,     // planned=false: not on the list
      "verified": {"ok": true, "exists": true,      // SCR-040: what the arithmetic said
                   "uuid": "9ff4deb9-…",            //   REW's own id — the title is NOT identity
                   "at": "…", "issues": []}}},
    "skipped": {"c_1 (sw)": {"at": "…", "reason": "centre not wired yet"}}
  }
}
```

## journal.jsonl

One JSON object per line, oldest first: `{"at": …, "type": …, …}`. Types:
`phase_entered` · `step_added` · `attempt_started` · `step_skipped` · `step_done` ·
`step_blocked` · `critic_called` · `config_change` · `capture_task_issued` · `capture_taken` ·
`capture_skipped` · `capture_round_closed` · `capture_verified` · `session_started` ·
`user_decision` · `written_by`.

`user_decision` is the Arbiter's half of the conversation, recorded as the answer rather than as
prose about it. `invalidates` carries the same shape as `config_change.impact`, so a ruling that
supersedes a measurement is legible to the same reader — but a ruling is not a config change, and
forcing it into that event would lie about where the fact came from.

`session_started` is the one event a front-end writes rather than the model: only it knows a
session was attached at all. Without it a journal whose first entry is a `step_done` cannot tell
a session that recorded nothing from a session that never happened.

`written_by` is the header: `{"at": …, "type": "written_by", "skill_sha": "<40 hex>"}` — which
checkout of the method wrote what follows (autosound-hub HUB-002). Written by the journal itself,
not by a caller, and **not once at creation**: the file grows across runs, so a header stamped when
it was born would only say which method STARTED it, while the question that has to be answerable is
whether two runs came from the same method. It is written before the first event of a run *and only
when the sha differs from the last one recorded* — a car tuned over a weekend on one version carries
one header, not one line per event. `""` means the writer was asked and could not be told (no
repository, no git); a journal with no header at all predates anyone asking. The whole forty
characters, the same spelling `dsp_profile.json` carries and the same number the companion app shows
for that checkout — see `rew_tool/provenance.py` for why it is the sha and not the version string.

## Invariants (enforced in code, not by discipline)

- **Steps are never deleted.** Superseding marks `skipped` and leaves the step visible, so the
  attempt history stays legible instead of a plan that quietly rewrites itself. `skip_step` is the
  only way to retire one.
- **`step_done` requires evidence that RESOLVES** (SCR-035) — a capture name in the grammar
  (`tw-L_1 (rta)`, method suffix included), a ledger version that exists, or a project file that
  exists. Prose may ride along; prose alone is refused. This is what makes resume trustworthy: the
  reconciler compares each done step against disk, and a done step with nothing checkable is
  indistinguishable from a model that merely said so — which one did, for four phases, with an
  empty project folder. `unevidenced_done_steps()` and `unbacked_done_steps()` are those checks.
- **A step that asked for captures is done when they PASSED, not when they exist** (SCR-040).
  `finish_step` refuses while the round bound to that step has an expected capture that is
  missing, unchecked, or checked and bad. Checking is arithmetic (`verify.py`) and needs no model;
  a verdict pins REW's `uuid`, because re-taking a measurement keeps its title and changes its
  data — a verdict keyed by title would outlive the graph it judged. A capture the tuner decided
  against is skipped, and a recorded decision is not re-litigated by the gate.
- **A skipped capture needs a reason** (SCR-034). Skipped and not-yet-taken looked identical
  before, so a tuner who decided a capture was unnecessary had no way to say so and the next
  session proposed it again. `skip_capture` raises without one.
- **Captures belong to a ROUND, not to a version.** The ledger version names the config a
  measurement was taken under; it cannot tell two passes at the same config apart, and "this
  session's task" is what the Arbiter asks about. Opening a round while one is open closes the
  first — a round nobody closed ended when the next one began.
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
