# Process Control — Operating Modes & the Arbiter's Playbook

How to keep a session's *process* honest (state, claims, discipline) without scaffolding.
The control that works is **pull-based**: the Arbiter demands artifacts only a tool produces —
not model self-discipline. The full anti-confabulation ruleset (pull-based control, solo
self-critique form, field-observed behaviors → countermeasures) lives in
[`driver-discipline.md`](references/core/driver-discipline.md)
— **load it only for modes B/C** (solo driver); mode A carries the discipline in tools + the reviewer.

---

## 1. The three operating modes (Arbiter picks, consciously)

**One is recommended: A — Claude drives, a second vendor reviews.** That is the configuration this
method was built and measured on, and it is what to offer.

Everything else — B, C, a model reached through `omp`, whatever ships next month — is **the user's
choice and the user's risk**, and it is offered as such rather than ranked. Models move faster than
this file can be rewritten, so an opinion about which is better ages into a wrong recommendation
that still reads as authoritative. What does NOT age is what the DRIVER'S SEAT costs: one
perspective instead of two, and (below) how much of the process record survives. Say that, and let
the Arbiter try what they like.

| Mode | Configuration | Reliability | Trade-off |
|---|---|---|---|
| **A** | **Claude drives (Generator) + a second vendor as the reviewer** — **ONE Critic pass per round, on the round's whole batch** (the crossover strategy in Phase 1, the round's EQ plan in Phase 2, the Phase-3 verdict — at the desk after the car session by default; TWO-PASS at the Phase-1 and Phase-3 gates, an open pass before that Critic pass — `review-loop.md`), not per-parameter calls; an **Advisor** call is for an open question at a solution-search node (staging/imaging, a joint with no answer yet) — `review-loop.md` Wing 2 | Highest | Needs both AIs; one extra call per round — buys anti-anchoring + a drift-watchdog |
| **B** | **Claude solo + self-control** — substrate tools (state/apply/gates) + disk-state discipline | Middle | One perspective; self-review catches less than cross-vendor. (Tool-compliance of a Claude driver: not yet field-measured — treat as promising, verify like anything else) |
| **C** | **Gemini solo** — **process-loss risk consciously ACCEPTED** | Lowest process-reliability, proven acoustics | Superb acoustic proposals and (in the measured run) numerically real data — but expect narrated compliance: no versioned state, "saved/updated" claims without artifacts, weaker resume. Mitigate with §2 + §3 |

Notes:
- These modes pick the **driver**. The Review-Channel *ladder* (SKILL.md) picks the **reviewer**
  when your preferred one is unavailable — they compose, they don't compete.
- Mode C is a legitimate choice (one capable model is most people's reality). It is *not* "mode A
  minus discipline" — it's a different contract: the Arbiter supplies the process spine
  (`driver-discipline.md`), the model supplies acoustics.
- **Model names are not maintained here.** A heavier model for search and verdicts, a lighter one
  for routine, a different VENDOR for the reviewer — that shape holds; which model fills each slot
  is the user's call, and the app's picker is where it is made. This file gave a table of model
  classes until 2026-09-09 and it was already drifting.

## 2. Discipline: where it lives per mode

- **Mode A:** the tools carry it — `apply.propose` (tool-stamped sheet + `v_NNN` snapshot),
  `spot_check.py` before applying a package, reviewer outside the driver session. No extra
  always-on rule text needed.
- **Modes B/C:** load [`driver-discipline.md`](references/core/driver-discipline.md)
  — pull-based control, the wrapper-only self-critique rule, and the behavior→countermeasure table.

## 3. What we deliberately do NOT build

No compliance tokens, no override protocols, no close-phase police (built once, removed by
design). Scaffolding that polices a model gets narrated around — and stronger models make it
throwaway. Build only tools that stay useful regardless of model strength: calculators,
verifiers, and artifact-producers the human pulls.

## 4. For future dogfoods

Capture kit + behavioral scorecard pattern: pin the skill commit, `AUTOSOUND_STATE_ROOT` into the
project, collect `state/` + the session transcripts + `dsp-config/` + the `.mdat`, then audit
with invocation-greps (**count real `python3 …py` executions, not token mentions** — mentions
include the skill's own text and the model's narration; only invocations are ground truth).

## Recording the process — the tool or the terminal

SKILL.md's guardrail *Write the PROCESS as it happens* names the record (`process/process-state.json` +
`journal.jsonl`) and the verbs; which writer records them, and where a critique's text goes, is here.

**If a process-recording TOOL is on your tool surface (a `tcc`-style front-end offers `enter_phase` / `add_step` / `start_step` / `finish_step` / `skip_step` / `block_step` / `start_capture` / `record_capture` / `skip_capture` / `close_capture` / `capture_knobs` / `record_decision` / `set_target` / `session_close`), THAT is the call** — same journal, same writer, no path to get wrong. Its `call_critic` writes the `reviewer` record; `capture-protective` and `listening-verdict` are its GUI's, recorded in its dialogs, with no tool. A plain terminal runs the `python3 rew_tool/state/process.py <project>/process …` verbs
SKILL.md lists, exactly as written.

**The critique's TEXT is a file**: `scripts/autosound_ai.py critic|advisor <package> --record` writes it to `process/reviews/<ts>-<role>.md` and records this step; by hand only a clipboard answer, or what the door says it could not record (it prints the line). Under TCC, `call_critic` runs the door without `--record` and records the step itself; the door's last line, which TCC passes on, says so, and is not run.

## Stopping is an event, and it has a closing order

The discipline of this method is strong while work is happening — every agreed change is banked,
every phase, step, decision and capture round is written as it occurs. It had one hole, and it was
at the end: **nothing said what happens when work stops.** So stopping read as a pause in a
conversation, and the four things that were open stayed open.

The cost never lands on the session that stopped. It lands on the next one, which resumes and
reconciles against what is not there:

* **an open capture round** — this method's own warning says its status lives in REW's measurement
  list and disappears when REW is closed. Stopping without `capture-close` is how a round becomes
  unreconstructable;
* **a step left in `start`** — neither done, nor blocked, nor skipped, so the plan claims work is
  underway that nobody is doing;
* **a ruling the Arbiter made out loud** — a constraint on later phases that exists only in a
  transcript, which is exactly what `decision` was built to stop;
* **a change agreed and not banked**, and **a session with no handoff line.**

### The order — its one home

SKILL.md's Pre-Session item 4 keeps the rule and the order's one line; the order itself is here. **Stopping is an
event, not a pause in the conversation.** It fires the moment the user says they are done for now — in any of the session's languages: *stop here · that's it for today · let's wrap up · good night* · **«добраніч» · «на сьогодні досить» · «стоп» · «зупиняємось»** · *gute Nacht · Feierabend · Schluss für heute* · *dobranoc · kończymy na dziś*. Read intent, not a keyword list: this is the list a session has met, and one more phrasing means the same thing.

**This is the one home of the stop's order.** **The record closes first, and one command says what is still open:** `python3 rew_tool/state/process.py <project>/process session-close --check` — it names the open capture round and every step left in progress, exits non-zero while either stands, and writes nothing. It reports; it never closes anything itself, because which evidence ends a step and whether a capture was skipped or is still owed are decisions. Then the record, in this order: **(a)** the round — `capture-skip <title> <reason>` for each one not coming, then `capture-close` (an open round's status lives in REW's measurement list and goes when REW does); **(b)** the step — `done <id> <evidence that RESOLVES>`, or `block <id> <reason>`, or `skip`; **(c)** any ruling the Arbiter made out loud — `decision <question> <answer>`, so a constraint set by voice is not invisible next session; **(d)** anything agreed and not yet banked (🟡) — `apply.propose`; **(e)** the ▶️ CONTINUE line in `tuning-changelog`, the handoff. **Then `session-close`**: with nothing open it RECORDS the stop (`session_closed`), so it is never run to look, and a close recorded by mistake is taken back with `session-reopen <reason>` (S-084). No new file for any of it: these are the carriers that already exist.

**Then the car — EXIT CHECKLIST** (only what THIS session touched): revert test-only values (A/B gains, level-match trims, mutes), remote-knob positions back, back up the DSP config after hardware-state changes.

**Then the GitHub issue, if there is one** — the experience a satisfied user agreed to share, or a defect of the method (`feedback-loop.md`).

**And after that, start nothing new** — even if something looks unfinished. If something genuinely cannot be left overnight, **say so** rather than quietly doing it (why → [`why-these-rules.md`](references/core/why-these-rules.md)).

### Why it is built so

`process.py <project>/process session-close --check` is the one question — what is still open —
and it answers with the commands that close each thing. It deliberately **reports and does not
close**: which evidence ends a step, and whether a capture is skipped or still owed, are judgements
with an argument behind them, and a tool that guessed would write a plausible wrong record.

With nothing open, `session-close` **records** the stop (`session_closed`) — it is the stop, not a
look. A session reconciling state on a Windows VM ran it to look and wrote the close (S-084, hub
#227), so the question has a read-only form: `session-close --check` prints the same report, exits
with the same code, and writes nothing. A close recorded by mistake is taken back with
`session-reopen <reason>`: the close stays in the journal, the reopening follows it, and the session
reads as open again.

**No new carrier was added for this**, deliberately (autosound-hub `HUB-023`, the ask from the hub):
a second record of the same thing drifts from the first. What was missing was an order, not a store.

## The phase boundary — `handoff`

A phase boundary is where a chat gets cleared (SKILL.md's Phase Sliding Window), and clearing is only safe once the
state is on disk: `python3 rew_tool/state/process.py <project>/process handoff` is the check before it. It REFUSES while anything the next session needs is only in this conversation (an open capture round, a step left `todo`, a done step whose evidence resolves to nothing, no ledger snapshot, no ▶️ CONTINUE block) and names each one; it writes nothing, because which evidence closes a step is a decision. When it passes it prints the line to say next and what must stay open — the REW session whose titles are the captures' only identity.

A session can neither restart itself nor `/clear`, so the offer is the Arbiter's to take; what the check removes is the
improvising (S-044).

## The reply after a desk computation

**A reply after a desk computation ends with one of two things**: «введи це» (the sheet), or «виміряй ці N кривих» (N from `state.py … verification-set`, never "re-measure the series"). A defect of the method found mid-session gets one line in the pool, and the tuning goes on.

## The record and the hardware drift apart — verify, don't compute from memory

Three independent occurrences on one build, each caught only by someone reading a screen:

- a rear channel's output gain sat at **−5** while the ledger's attested value was **+3**;
- the ledger recorded a centre gain of **+4.0** that existed in **no preset** — the real baseline was +3.0 in both, so every delta computed from +4.0 was wrong;
- a debrief listed five harvested lessons as "filed in the skill inbox"; the inbox never received them (they sat in the plan document that generated them).

**Rules.** The ledger HEAD says what was banked; the DSP screen says what is set now — read the screen before computing a delta, and record a difference rather than average it. And when a document says work was filed somewhere, check the destination — a harvest queue that is written to but never read from silently becomes a second ledger.

## The system state belongs on the capture round, not in memory

The state outside the DSP (master · sub · effects · fill channel) is recorded with `process.py capture-knobs` for the round — the record the tools read. A copy in the measurement's notes helps a person reading REW; it is not the record. Titles stay protocol-clean — they are the tool-facing identity that name-matching resolves exactly (`naming-and-structure.md`).

⚠️ Writing notes over an API usually **replaces** the field, destroying the capture information the measurement software put there itself. Read → append → write back; never a bare overwrite. (Confirmed by destroying it once.)

## Version identifiers are a namespace — check before you allocate

Banking a change under a version label that already exists silently merges two unrelated states in every later reference. Before writing a new `vN.N` block, grep the ledger for that label. One build hit this when a session's HF work was banked as `v4.5`, a label already held by an earlier entered-and-attested change referenced from eight other places.
