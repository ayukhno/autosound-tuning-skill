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
     "evidence": ["m-L_10 (sw)", "v_007"],      // REQUIRED once status is done
     "covers": ["project.json:amps.front.gain_db"]}   // WHAT the step closes; the name names it
  ],
  "reviewer": {"vendor": "Gemini", "model": "Gemini 3.1 Pro (High)",
               "at": "…", "phase": "2", "step": "2.3", "outcome": "apply",
               "review": "process/reviews/2026-08-06T21-33-10-critic.md",  // SCR-027: WHAT was argued
               "mode": "api"},                                            //   api | cli | clipboard
  "targets": {"FULL": "ResoNix", "SQ": "Jazzi #1"},  // pointer per preset; the curve lives elsewhere
  "capture": {                                      // SCR-034: the OPEN capture round, or null.
    "id": "cap_002", "n": 2,                        //   Every round that ever happened is in the
    "phase": "0", "version": "v_003",               //   journal; only the live one is here, the
    "version_kind": "ledger",                       //   ledger | series | null — WHICH counter
    "under": "v_010", "under_note": null,           // #57 P0: the ledger version the series was taken
                                                    //   UNDER (`--under`); null when nobody said --
                                                    //   never guessed from the active slot
    "level": {"value": "-25 dB rel. max",           // S-026: the level as a QUANTITY, and how it is
              "read_as": "7 lamps on the Conductor"},  //   read off the device; null when not given
    "issued": "…", "closed": null,                  //   same way only the active phase is.
    "expected": ["tw-L_1 (sw)", "tw-L_1 (rta)"],    // the list, flat: `groups` flattened (skill #77)
    "groups": [{"kind": "solo", "label": "Solo (sw)", "method": "sw",   // skill #79/#83: the columns a
                "names": ["tw-L_1 (sw)"]}, ...],                        //   front-end draws, in the order
                                                    //   the car is taken in -- never the phase plan
    "optional": ["Ws_1 (sw)"],                      // skill #80: on the list, not a gap when left
    "setup": {"first": "sw", "from": "m-L_0 (sw)",  // skill #78: the method taken first and why;
              "switches": 1},                       //   at most one switch of tripod/driver
    "step": "0.1",                                  // SCR-040: the plan step this round satisfies
    "taken": {"tw-L_1 (sw)": {"at": "…", "planned": true,     // planned=false: not on the list
      "superseded_by": null,                        // S-039: a row recorded under a WRONG title
                                                    //   stays, dimmed, naming what it was
                                                    //   corrected to. Never deleted, and counted
                                                    //   nowhere as taken (N17)
      "verified": {"ok": true, "exists": true,      // SCR-040: what the arithmetic said; `exists`
                   "uuid": "9ff4deb9-…",            //   null when REW's list was not read. REW's own
                   "at": "…", "issues": []}}},      //   id — the title is NOT identity
    "checks": {"tw-L_1 (sw)": {"ok": true, "exists": true, "applicable": true,   // #134 (T-1): the last
                               "uuid": "9ff4deb9-…", "at": "…", "issues": []},   //   check of EVERY title,
               "tw-L_1 (rta)": {"ok": false, "exists": false,                     //   held or not -- what
                                "applicable": true, "uuid": null, "at": "…",      //   `verified` holds on a
                                "issues": ["No measurement titled 'tw-L_1 (rta)' (REW holds 4)"]}},  // taken row
    "skipped": {"c_1 (sw)": {"at": "…", "reason": "centre not wired yet",
                             "planned": true}},    // planned=false: never on the list
    "reconciled": {"at": "…", "rew": true,          // skill #77 rule 3: the list read against REW's
                   "matched": 4, "extra": ["sw_1 (sw)"],   //   list before closing -- taken is what REW
                   "renames": {"Ms_01 (rta)": "Ms_1 (rta)"},  // holds (`as_in_rew` on a row spelled
                   "missing": ["tw-L_1 (sw)"], "missing_optional": []},  // differently there)
    "closed_against": {"rew": true, "missing": [...], "extra": [...], "renames": {...}}  // or {"rew": false}
  }
}
```

## journal.jsonl

One JSON object per line, oldest first: `{"at": …, "type": …, …}`. Types:
`phase_entered` · `step_added` · `attempt_started` · `step_skipped` · `step_done` · `capture_reconciled` ·
`step_blocked` · `critic_called` · `config_change` · `capture_task_issued` · `capture_taken` ·
`capture_skipped` · `capture_round_closed` · `capture_verified` · `session_started` ·
`session_closed` · `session_reopened` · `user_decision` · `written_by`.

`user_decision` is the Arbiter's half of the conversation, recorded as the answer rather than as
prose about it. `invalidates` carries the same shape as `config_change.impact`, so a ruling that
supersedes a measurement is legible to the same reader — but a ruling is not a config change, and
forcing it into that event would lie about where the fact came from.

`session_started` is the one event a front-end writes rather than the model: only it knows a
session was attached at all. Without it a journal whose first entry is a `step_done` cannot tell
a session that recorded nothing from a session that never happened.

`session_closed` is written by `session-close` on a clean stop, and only then; `session-close --check`
asks the same question and writes nothing. `session_reopened` (`{reason, closed_at}`) takes a close
back (S-084): it follows the close and never replaces it, and is refused unless the last of
`session_started` / `session_closed` / `session_reopened` is a close. **The session is closed when
that last event is `session_closed`** (`Process.session_closed`); a reopening or a new start after
it means open.

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
- **A step's content is a LIST, not a count** (S-031). `covers` holds the facts the step closes —
  dotted paths, exactly as `project.py open-questions` / `dsp_profile.py open-questions` print
  them — and `add_step` composes the NAME from them: the first three plus `+N`. Generated, not
  typed, because the failure was a plan that read `Закрити відкриті поля: project.json (8) і
  dsp_profile.json (5)` in the Arbiter's window: thirteen facts, named nowhere he could see, in
  the one artefact he acts on. `covers_summary()` is the single renderer; a window expands the
  full list and a session ticks it off.
- **A capture under the wrong title is SUPERSEDED, not deleted** (S-039) — the same move the plan's
  steps have had since SCR-004. A ghost `r-R_1 (se)` stayed in a round after the typo was fixed in
  REW, because the only states were «taken» and «never mentioned». The row keeps its place with
  `superseded_by`, the corrected title is recorded in the same breath, and `_outstanding` stops
  counting the ghost as a capture that exists. A round that quietly loses a row is a round nobody
  can audit. **Nothing counts a superseded row as taken** (N17, #134): not the step gate
  (`unusable_captures`), not `capture_round_closed`'s `taken`, not the counts `session-close` and
  `capture-close` print, not the setup a next round starts from, not a channel the round captured,
  and not the read against REW: `reconcile_captures` skips the row when REW still holds its title, so
  it is no title held, no rename and no `extra` taken beyond the list (`reconciled`, `closed_against`).
  `capture-check` prints it `UNUSABLE <title> — superseded by <right title>`. Before, a row checked
  and passed under the wrong title counted as a usable capture.
- **A check reads; it does not take** (#134, audit T-1). `capture-check` records every title's
  verdict in the round's `checks` (`{title: verified}`, `exists` true, false, or null when REW's
  list was not read), and creates a `taken` row only for a title REW holds — the rule `capture-close`
  closes by (skill #77); a row already there gets the new verdict. A title REW does not hold stays
  outstanding. It used to become a `taken` row with a failed verdict: a capture the round took,
  outstanding nowhere. `capture-check` reads a title's line from its `taken` row, else from
  `checks`. With REW not answering it records nothing and exits 69 (below).
- **Nothing is cleared over work that is only in the chat** (S-044). `handoff` answers one question
  — is everything the NEXT session needs on disk — and REFUSES while it is not: no phase recorded,
  an open capture round, a plan step left `todo`/`in_progress`, a done step whose evidence resolves
  to nothing, no ledger snapshot, a `tuning-changelog` with no ▶️ CONTINUE block, or one it cannot read (another code
  page, a file that cannot be opened: named, where it read as no changelog). It writes nothing
  either way (which evidence closes a step is a decision), and when it passes it prints the resume
  line: what to say next, and what must stay open.
- **A round says WHICH counter its version is, and a ledger version must exist** (TCC-022). The two
  are different counters and neither is derived from the other: a **series** `_N` numbers a set of
  measurements, a **ledger version** `v_NNN` is the configuration they were taken under. So the
  ledger is a precondition of a LEDGER-BOUND round, not of the capture flow — a Phase-0 baseline is
  measured before anything is banked, opens at `_1`, and records `version_kind: "series"`, which is
  the round saying it is not ledger-bound. Naming a `v_NNN` with no snapshot on disk is refused, and
  the refusal carries both ways on: bank the state (`apply.propose`), or open the round at its
  series number. Bought on a project made by TCC's Copy car — which carries `project.json` and the
  profile and deliberately no `state/`: four rounds opened in a row at a `v_001` that did not exist,
  while the flow's other half, `apply.propose`, failed silently on the same fact and never said
  what was missing.
- **A skipped capture needs a reason** (SCR-034), and carries `planned` the way a taken one does —
  `expected[]` is not a closed set, so a reader cannot assume everything in `skipped` was ever asked
  for. `contract.py`'s `round_verdict` reports every skip and names the unplanned ones
  (`skipped_unplanned`); it used to intersect them with `missing`, so a skip outside the list
  vanished from the report entirely (TCC-022). Skipped and not-yet-taken looked identical
  before, so a tuner who decided a capture was unnecessary had no way to say so and the next
  session proposed it again. `skip_capture` raises without one.
- **Captures belong to a ROUND, not to a version.** The ledger version names the config a
  measurement was taken under; it cannot tell two passes at the same config apart, and "this
  session's task" is what the Arbiter asks about. Opening a round while one is open closes the
  first — a round nobody closed ended when the next one began. It closes once the new round has passed every refusal
  (#134, H I-3): a refused `capture-start` (a `--plan` with no glossary, say) writes nothing, where it appended the
  first round's `capture_round_closed` while the state kept it open; and `capture-import` checks every bind against
  the ledger before its first round, so a bad one is refused with nothing imported.
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
p.add_step("-1.2", "Закрити відкриті поля",         # name gets ": a, b, c +N" composed from covers
           covers=["project.json:sources.sweep_input", "project.json:amps.front.gain_db"])
p.start_attempt("2.3")
p.finish_step("2.3", ["m-L_10 (sw)", "v_007"])     # raises without evidence
p.record_reviewer("Gemini", "Gemini 3.1 Pro (High)", step="2.3")

state = p.load()                # a file that cannot be read is an empty process here
state = p.load(strict=True)     # ... and here it raises project_io.Unreadable (see the read rule below)
p.plan_for("2", state)          # steps of one phase
p.unevidenced_done_steps()      # resume drift check
```

## The command line: verbs, flags, exit codes (#134; #138 I-15)

`python3 process.py <process-dir> <verb> [args]`. `process.py --help` (or `<process-dir> --help`) prints the whole
usage on stdout, exit 0.

| exit | means |
|---|---|
| 0 | done, or yes |
| 1 | refused, or no: the reason on stderr (`error: …`); REW answering with an error (`error: REW answered with an error: <REW's words> -- nothing was written`), or with any other state but "unavailable" -- something the method cannot read (`protocol`), `write_mismatch`, `not_found`, `ambiguous`, `config` -- (`error: <its words> -- nothing was written`); a typed mistake in a value the verb parses itself (a leg, a series) |
| 2 | usage: an unknown verb, a flag the verb does not take, a flag's value missing (one of the verb's flags, `-h` or `--help` in its place, or nothing after it: a value flag left last), a value on a flag that takes none, one of the verb's flags with its hyphens autocorrected to a dash, `--help` or `-h` after other arguments, too few arguments |
| 69 | REW did not answer, and nothing was written (sysexits' `EX_UNAVAILABLE`) |
| 70 | an unexpected error, a bug: Python's traceback on stderr, then `error: unexpected <type>: <message>` (`EX_SOFTWARE`) |
| 75 | the project busy: reserved for the lock (J2b, W-9), not raised yet (`EX_TEMPFAIL`) |

- **Each verb takes its own flags, and only those.** `VERB_FLAGS` in `process.py` is the table, one string literal
  per flag, and `_FLAG_TAKES_VALUE` says of each whether it takes a value (the selftest holds the two to each other).
  A flag is `--`, an ASCII letter and no whitespace -- after an `=`, whitespace is the value's only when the name
  before it is one of the verb's flags (`--invalidates=w-L_1 (sw)`). Any other `--<word>` is a usage error,
  exit 2, with the flags the verb takes named on stderr and nothing written; it used to become a title, a reason or a
  piece of evidence (TCC's N19). Text that only begins with two dashes is a word, not a flag: `--бас гуде`, `--bass
  hums`, `--bass=45 Hz hums?`, `-- note`, as well as a bare `--` and a negative number. Where a flag stands, one of the
  verb's flags whose two hyphens an editor autocorrected to a dash -- a word that starts with an em or an en dash and
  names the flag past its dashes (`—origin`, `–origin=other:49`) -- is a usage error, exit 2: `<verb>: —origin looks
  like --origin with its dashes autocorrected; type two hyphens`; as a word it opened a round expecting `—origin`.
  After a flag that takes a value, such a word is the value. `--flag value` and `--flag=value` are the same: the
  value is taken as it stands, whatever it looks like (`--text --loud`, `--note=--loud`), with one exception in both
  forms -- a value that is one of the verb's own flags, `-h` and `--help` among them (`capture-start 1 --optional
  --plan`, `amp-gain sw=+3 --note=--measured`, `--text=-h`; the name before any `=` counts), is no value: the value is
  missing, exit 2. A branch that scans for its flags read `--note=--measured` as the flag `--measured` and recorded no
  note. A flag that takes a value and stands last, with nothing after it, is refused the same way before the verb
  runs (`_check_value_flag_last` sweeps every one): taken as unset, `decision <q> <a> --invalidates` recorded the
  decision without its link and `capture-import <N> --bind` asked REW. capture-protective's legs `--hp` and `--lp`
  (`_LEG_FLAGS`) are the exception: the verb parses their three values and says what is wrong, exit 1 -- `--hp needs
  three values: f type slope, e.g. --hp 100 LR 24` (fewer, or a flag among them), `--hp: 'abc' is not a number`
  (`100Hz`, `nan` too), `--hp: '24.5' is not a whole number`. They exited 70, a bug's code. Each value is checked as
  well (R47b, R48), and each of these was recorded: a frequency not above 0, a slope not above 0, a type that is none
  of `_LEG_TYPES` -- `dsp_math.MODELLABLE_FAMILIES` (LR, BW, BE) and CH, the Chebyshev a Helix and TCC's dialog
  offer, recorded as typed -- an empty type included (`--hp: 'XX' is not a filter type: LR, BW, BE or CH`). A leg's
  values are the leg's, not the verb's arguments: legs with no channel are too few, exit 2.
  `capture-import`'s series is read the same way before REW is asked: `capture-import: '1a' is not a number`, exit 1.
  With no titles (R47a), `capture-import <N>` imports what REW holds of series N and the project has not on record
  (taken in a round, superseded there, or held by REW under its own spelling of one): none held is exit 1, `REW holds
  no measurement of series _N; nothing was imported`; all on record is exit 0, `nothing new`. A flag that takes no
  value (`--plan`,
  `--session`, `--json`, `--check`, `--no-rew`, ...) takes no `=`. The refusal's words never contain `usage:
  process.py`, which a front-end reads as "this method is too old".
- **Too few arguments are a usage error.** A verb needs the arguments its line in the usage names in `<...>`
  (`_VERB_ARGS`): `target <preset> <curve>`, `capture-skip <title> <reason>`, `done <id> <evidence>`; `skip` needs its
  `<id>`, then a reason or `--superseded-by`, which `skip_step` checks. Fewer is exit 2, naming them, and the verb
  does not run. It raised IndexError -- "list index out of range", exit 1 like a refusal with no reason; an
  IndexError raised inside a verb is a bug now, exit 70 with its traceback.
- **`<verb> --help`** (or `-h`), right after the verb, prints that verb's lines of the usage and the exit table on
  stdout, exit 0, and reads and writes nothing. It ran the verb: `session-close --help` recorded a close,
  `capture-start --help` opened a round at `--help`. After other arguments, `--help` and `-h` are a usage error,
  exit 2: `-h` was data there (`capture-start 1 -h` opened a round expecting a capture titled `-h`).
- **The command line is answered first**: `--help`, an unknown verb, an unknown flag and too few arguments come
  before the strict read below, so on a state that cannot be read they still answer 0 or 2, not 1.
- **REW down is 69, nothing written.** `capture-check` with REW not answering (any title `reachable: false` in
  `verify`'s verdicts) records no verdict, no round change and no event; REW not answering a verb that asks it
  itself (`capture-import`, for a series' titles) exits 69 too. REW answering such a verb with something the method
  cannot read (`rew_state` "protocol") is exit 1, REW's words and `-- nothing was written`: REW's answer, not a bug;
  so is REW answering it with an error -- an `HTTPError`, its 4xx/5xx, or a class whose `rew_state` is "error" --
  said `error: REW answered with an error: <REW's words> -- nothing was written`, where it was a bug's 70. Every
  other state but "unavailable" is exit 1 the same way, read off the exception's class (R47c): `write_mismatch`,
  `not_found`, `ambiguous` and `config` (a `REW_API_URL` that is no address), which no verb meets there today.
  `capture-close` still closes on the record alone with REW down, exit 0, and says which it met, with what was
  raised: `REW not reached`, or `REW answered something that is not a measurement list`. REW gone between its list
  and the checks `capture-close` runs is said as what happens: the checks were not run, and the round closes on the
  record, unchecked.
- **A bug is 70, not 1.** An exception no refusal names exits 70 with its traceback, where it exited 1 like a
  refusal or escaped as a bare traceback; an IndexError too. An unreadable file (`is_unreadable`) stays a refusal,
  exit 1.

## The read rule: unreadable is not empty (#136, audit K-2)

`process-state.json` can be missing, or there and unreadable: empty, cut off, not UTF-8, not a JSON object (an array,
`null`), a folder in its place, or a file that cannot be opened. Only the first is a fresh project.

- **No file** is the empty process in every reader: a project that has not entered a phase yet.
- **Strict for every verb but three.** Each verb that writes the state or the journal (`session-start`, `decision`,
  `session-reopen`, `amp-gain`, `listening-verdict` and the `--amend` forms included), each verdict (`check`,
  `handoff`, `session-close` with or without `--check`), and `show`, which prints the state itself, read the file
  strictly before they do anything. On such a file they exit 1 with the file and the repair on stderr and the state and
  the journal as they were. They print nothing on stdout, except `handoff --json`, which answers with the keys of its
  usual answer: `ok: false` and the file and the repair in `missing`, because a front-end reads that verb's stdout.
  This comes before their own refusals, which blamed a step or a round the empty process lacked, and before any call
  to REW. Before this, the journal-only verbs appended, `check` said nothing was wrong (exit 0), `show` printed an
  empty process, `session-close` recorded a clean stop, and a verb that wrote the state put an empty process over the
  plan.
- **Lenient only for the display-only verbs: `plan`, `amp-changes` and `listening-verdicts`** (with `--bank` too).
  They write nothing. `plan` shows such a file as an empty plan; the other two read only the journal. `_DISPLAY_VERBS`
  in `process.py` is this list, and `_main` reads strictly for any verb not on it, so a new verb is strict unless it is
  added there.
- **Every writer reads strictly itself, and again before it writes.** Each writer method of `Process` (the public ones
  that call `_write` or `_append`) reads the state strictly. So do `handoff()` and the reads behind `check`'s verdict
  and `capture-close`'s count. An open refused for a moment (Windows, while another writer replaces the file) used to
  read as an empty process: the writer built on it, and the write went through once the file read again, taking the
  plan with it. `_write` and `_append` then read the file once more before they write: the last line, for a file
  damaged between the two reads. No caller puts an empty process over the state or appends beside a file that cannot
  be read, the callers outside `_main` included (`project.py record-change`, which says so with exit 1).
- **In code:** `Process.load()` stays lenient by default, for the readers outside `process.py` (`flaw_map`,
  `predict`, `eq_propose`, ...) and TCC's screen. An array or `null` there no longer raises `TypeError`, and a file
  that starts with a UTF-8 BOM is read. `load(strict=True)` raises `project_io.Unreadable` (`.path`, `.reason`,
  `.repair`), which is neither an `OSError` nor a `ValueError`: match it by its `is_unreadable` attribute, never by
  its class. `contract.py check` reports the file as there and not valid, the reason in `issues`, and the project as
  not OK.
- **The refusal names the repair:**
  - for damaged contents (empty, cut off, not JSON, the wrong type), `git -C <process-dir> checkout HEAD --
    process-state.json`, said as what it gives (H 13): the copy may be older than the journal -- a project's
    repository may hold only its first commit -- and nothing replays the events since into it; with no committed copy
    (no git repository), move `process-state.json` aside: the process starts empty, and the journal keeps every
    event;
  - for a file written in another code page, `contract.py repair-encoding <project-dir>`;
  - for a file that cannot be opened, close what holds it (an editor, a sync client, another tool) and run again;
  - for a folder in its place, move the folder aside.

  In the last two the file may be whole, and an older copy restored over it would replace a good file.
- **A state a newer method wrote** (`schema_version` an int above 3, audit T-21) is refused by every strict read with
  `ProcessError`: `<file> is schema v4; this method reads v3 -- update the method: /autosound-tuning:setup, the
  installer, or TCC's «Оновити Скіл»`. So every verb but the three display-only ones exits 1 on it and writes
  nothing, and `_write` and `_append` refuse one a newer method wrote after the writer's own read. Before, only the
  write noticed (`validate`: "unsupported schema_version 4"), and the journal-only verbs appended beside it. `load()`
  (lenient) still returns it as it is.

### The phase gates and the files beside the state (#136, audit T-10, T-11, T-13)

`enter-phase` reads by the same rule. A gate that cannot check refuses the phase; it used to let it in ("a checker
that raises must not become a wall"), on the damaged projects most of all.

- **The intake gate** (leaving −1): a `contract.py` that cannot be loaded refuses with `phase N is not entered: the
  intake check could not be loaded (<type>: <message>) -- the install is broken, not the project`; a check that raises
  refuses with `phase N is not entered: the intake check raised <type>: <message>`; a file the check found unreadable
  raises as itself, with its own repair. It still gates on `missing`; gating on `complete`, with a parity test against
  `contract.py check --gate`, is J3b (W-11).
- **The flaw-map gate** (leaving 0): a `project.json` that is there and cannot be read raises `Unreadable` with its
  repair (`git -C <project-dir> checkout HEAD -- project.json`, or `contract.py repair-encoding` for another code
  page). One holding an array stopped the gate with a traceback; a damaged one let the phase in with no map.
- **The profile gate** (into 1 and 2): a `dsp_profile.json` that cannot be read, or that a newer method wrote, raises
  `dsp_profile.load_profile`'s refusal; a `dsp_profile.py` that cannot be loaded refuses as the intake gate's does.
- **No file is still no wall:** an absent `project.json` or `dsp_profile.json` is the intake check's to name.

The files beside the state, each refused with its repair and nothing written (`error: <file> <reason> -- <repair>`,
exit 1, from `state.py`, `dsp_profile.py` and `apply.py`):

- `state/seals.json`: `verify` (it said "every sealed version is as it was banked"), `seal`, a bank and
  `repair-version`. Read as "no seals", the next bank rewrote the file holding its own seal alone. The repair:
  `git -C <state> checkout HEAD -- seals.json`, or move it aside and run `state.py --root <state> seal` to rebuild it
  from the versions as they stand.
- `project.json` where a bank stamps its `project_rev`: read as "no facts file", it stamped rev 0 into a version that
  is never rewritten.
- `dsp_profile.json` and `dsp_profile.draft.json`: `load_profile`, `load_draft` and every writer through them
  (`set-field`, `reset-field`, `start`, `finalize`, `set-setting`, `refresh`). A draft that could not be read was
  passed over -- and the good profile with it -- for a blank one, which `set-field` saved over the interview's
  answers. Two readers answer it otherwise, on purpose (ruling R26): the intake's processor change, the step that
  replaces the profile, sets it aside like any other old one, unread and byte for byte, with one line on stderr
  naming it and where it went; and the intake form's page shows it at the top with its repair instead of failing
  (a save through it is still refused).

`contract.py check` reports `seals.json`, `project.json` and `dsp_profile.json` as there and not valid, the refusal
in `issues`, and does not fail.

## Consumers

- The **skill** is the only writer in v1. The user adjusts the plan by talking to the Generator;
  direct UI edits land later and also as events, never as raw JSON edits.
- **TCC** reads both files and renders them (plan panel, advisor status), watching for changes.
- `tuning-changelog` and `audit-trail.md` become **generated views** over the journal — the same
  move `state.py` made for `dsp-state-current`.

## Front-end contract: the handoff and a corrected capture title (hub #201, TCC-028)

**`handoff` (S-044): when a front-end offers it, and what it does with the answer.**
- **The signal is the end of a phase, not its start.** Offer it when the ACTIVE phase's plan has no step left
  `todo` or `in_progress`, that is, after the `step_done` / `step_skipped` / `step_blocked` event that closed the
  last one. Right after `phase_entered` the new phase's steps are `todo` by definition, so `handoff` would refuse.
- **The machine form:** `process.py <dir> handoff --json` prints `{ok, missing: [str], phase, resume,
  warnings: [str], next_message}`, with exit 0 when ready and 1 when not. `missing` is shown to the person as it
  is: each item already names what to do. Nothing is written either way. `warnings` (S-084) never moves `ok` or
  the exit code: today it carries one case, a ▶️ CONTINUE block naming a HEAD the ledger is not at.
- **The resume line:** a front-end that can start a session starts a NEW one in the project with
  `next_message` («продовжуй») as its first message, and shows `resume` beside it (it names what must stay open,
  e.g. the REW session). A terminal prints `resume` for the person to follow.

**`capture-supersede` (S-039): a capture recorded under the wrong title.**
- `process.py <dir> capture-supersede "<wrong title>" "<right title>" [reason words …]`. Exit 0: the wrong row
  stays, marked `superseded_by`, and the right title is recorded as taken. Exit 1: refused, with the reason on
  stderr (no open round; the round never took the wrong title; the same title twice). Exit 2: usage. The reason is
  free text, and a front-end's own is fine (e.g. `renamed in REW by TCC`).
- **It works on the OPEN round.** A round registered after the fact (`capture-import`) is written with the
  titles REW holds at that moment, so a title is fixed in REW BEFORE the import.
- **Order: REW first, then the round.** Rename in REW, read REW back to confirm the right title exists and the
  wrong one does not, then run `capture-supersede`. If the rename fails, the round still says what REW holds.
  The other order leaves a round naming a title REW does not have.

## Front-end contract: stopping asked, and a close taken back (hub #227, TCC-041)

- **`session-close` is unchanged.** Exit 0 and `session_closed` recorded when nothing is open; exit 1 and the
  report, nothing recorded, while a round or a step stands. The exit code is the answer, not a failure.
- **`session-close --check`** prints the same report and exits with the same code, and writes nothing (its last
  line says so). The form for a session reconciling state; a front-end stopping a session keeps the plain form.
- **`session-reopen <reason>`** appends `session_reopened` (`{reason, closed_at}`). Exit 0 when the journal's last
  session event is `session_closed`; exit 1 with the reason on stderr when it is not, or when no reason is given.
  The close stays in the journal. A reader deciding whether a session is closed reads the LAST of
  `session_started` / `session_closed` / `session_reopened`: a reopening after a close is an open session.
