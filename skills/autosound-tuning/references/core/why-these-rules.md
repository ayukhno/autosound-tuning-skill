# Why these rules exist — what each one cost

`SKILL.md` carries the rules a session must follow, and it is loaded in **every** phase. The stories
behind them — what went wrong once, on a real project, that made a rule necessary — are worth
keeping and are not worth paying for on every load. They live here, and this file is read when
someone asks *why*, or when a rule looks like ceremony and the temptation is to skip it.

Moved out of `SKILL.md` on 2026-09-09 (release review). **Nothing here is an instruction** — every
rule itself stayed where it was.

## Opening the phase before the interview

`enter-phase <N>` is an entry condition, not a checklist item. An interview that runs long is
exactly how a phase came to be narrated for a whole session and never opened: the model asked its
questions first, intending to log afterwards, and afterwards never arrived. Nothing in the record
said the session had begun.

## Evidence that resolves

"Baseline measurements analysed" is prose. It reads like a closed step and points at nothing, so the
next session cannot tell whether the work happened. A measurement name in the grammar, a ledger
version that exists, a project file that exists — each can be checked by a reader who was not there.
Write the artefact first, then close the step against it (SCR-035).

## The critique's text is a file

A record saying that a critique happened, without what it argued, loses the half worth reading back
a week later — and the half an audit needs. `scripts/autosound_ai.py` writes the text to
`process/reviews/<ts>-<role>.md` and prints the path; clipboard mode writes the package to the same
place, so a review answered by hand does not look like no review at all (SCR-027).

## The Arbiter's rulings

Their half of the conversation was in no machine file at all. A constraint the user set out loud was
invisible to the next session unless somebody happened to re-read it out of prose — and the prose
files may repeat it, or may not be the only copy. `decision` puts the ruling itself on the record,
before it is acted on (SCR-030).

## The capture round

Without an open round, a measurement's status lives only in REW's open-measurement list, and closing
REW loses it. A skip with no reason is indistinguishable from a step forgotten, so it gets proposed
again next session — nine times out of nine on the live journal, which is why the reason is now
required rather than encouraged.

## Narrating instead of recording

Writing the phase or the plan into chat, or into `tuning-changelog`, without also writing the
matching event is exactly the gap that leaves resume with nothing real to reconcile against. The
prose reads as though the work is captured; the machine record is empty.

## Bringing a project current (`catch-up`)

`CAR-007`: a schema field existed for two days and had reached one flaw map out of four — and all
four were one machine. A schema change reaches the model at once and the projects on disk never,
unless something asks. That is why `catch-up` is run there and then rather than carried as a to-do.

## Stopping as an event

`HUB-023`: the next session resumes from what is on disk, so work done after the record was closed
is work it will reconcile against nothing. Test states left in hardware are the top source of
ledger/hardware forks, which is why the exit checklist covers what THIS session touched rather than
the whole car.

## A passed check costs one word

The Arbiter handed over a whole session reply — the first message after a clean start — as «ось
приклад зайвої інформації». What he owed the reader was three lines: he is at step 0.6, it is desk
work, it needs no new measurements. What arrived was the version match, the clean project file, the
only saved DSP state, REW being open with all eight solos, the four still-open steps, why Phase 1
would not open, 44 proposed flaw rows with per-channel counts and three caveats about them, a prose
reading of the midbass arrivals, a four-row table of protective minima for a sweep that was blocked
anyway, two «small things in the files» — and then the question. His correction is the rule: a check
that PASSED costs one word, because a session that says nothing about its checks is
indistinguishable from one that skipped them, and a session that spends a paragraph on each buries
the one line that was for him (S-046, 2026-09-19).

## A verdict re-derived in prose

`capture-check --session` answered: 8 sweeps usable, 8 RTA unchecked, levels, arrivals, and no
`ctl1`/`ctl3` so the drift is unknown. The session then read the arrivals on top of that — right-side
mids ~1.2 ms later, converted to ~41 cm, called plausible for a left-hand-drive seat, with a
confidence disclaimer about the broad impulse peak and a note that it was «a candidate for
cross-check in Phase 1». That last line is the tell: it is a candidate for Phase 1 because Phase 1
is where the reading belongs, where `predict --align` and `arrival_triangulate` do it through a
window with the trust gate, the alias rules and the ILL-POSED verdict said out loud. The same
reading came back in a FRESH session after the chat was cleared, which is what makes it structural
rather than one session's whim (S-038).

## Absolute values, never relative

"Remove the +3" once landed 3 dB off intent: the Arbiter and the model disagreed about what the
current value was, and a relative instruction hides that disagreement instead of surfacing it.
