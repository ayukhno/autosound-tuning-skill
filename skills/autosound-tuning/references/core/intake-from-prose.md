# Intake from prose — bringing a pre-ledger project into 3.x

> For a project whose state lives in `autosound_context.md`, `audit-trail.md` and a
> `tuning-changelog`, with no `state/<preset>/v_NNN.json` anywhere. `contract.py check` says so
> outright, and `migrate.py` refuses and points here.

## Why this is a reading job and not a script

`migrate.py --into` converts a **ledger** — a machine format into a machine format, mechanically,
with a selftest. There is no ledger here. What there is, is a tune written in sentences by
somebody who did the work: a channel map as a Markdown table, crossovers and delays under a
`[STEP 1]` heading, cabin anomalies as paragraphs with an addendum correcting one of them six
weeks later.

Parsing that is exactly the job a model is good at and a parser is bad at. Every project's prose
is shaped differently, and a parser that gets it 90% right produces a project that is wrong in a
way nobody notices until a delay is typed into the wrong output. So: the model reads, proposes,
and **a person confirms each file before it is written**.

The prose files are never modified. If the result is wrong, delete the new project and start again.

## What must not happen

- **Do not run the ordinary intake interview.** Every answer already exists. Asking again wastes
  the session's context and invites the person to answer differently the second time, which
  silently changes their car's record.
- **Do not write into the old project.** The new machine files go in a NEW directory. The old one
  stays openable by whatever was tuning it.
- **Do not invent.** A fact the prose does not state is an open question, not a default. `null`
  and `_open_questions` exist for this; a plausible guess is worse than a gap, because a gap gets
  asked about.

## Order, and which writer does what

Follow it in this order: each step's output is the next step's input.

**1. Read everything first, write nothing.** `autosound_context.md`, `audit-trail.md`, any
`tuning-changelog`, and any dated ADDENDUM sections. **An addendum overrides the section above
it** — that is what it is for. Note where the prose contradicts itself; that is a question for the
Arbiter, not something to resolve quietly.

**2. `project.json` — the car and its channels.** `python3 rew_tool/project.py <new> …`

| in the prose | becomes |
| :-- | :-- |
| Hardware Configuration | `car`, `dsp`, `amps` |
| Channel Map (wiring & routing) | `channels[]` — `code`, `slot`, `descr`, `role` |
| Measurement Equipment | `mic`, `paths` |
| Naming Convention | `glossary` |
| Known Cabin Anomalies, and every addendum | `acoustics.flaws[]` |

The channel map is the one to get exactly right: `slot` is the processor's own output label — the
letter or number a person types into the DSP — and a table row like `CH3 (C) | w-L (Woofer L)`
means `code: "w-L"`, `slot: "C"`. Rows marked unused are still rows: record them off rather than
omitting them, or the count will not match the profile.

Flaws need `status`: a measured anomaly is `confirmed`, one the prose reasons about is
`hypothesis`. An anomaly a later addendum rewrote takes the addendum's numbers.

**3. `dsp_profile.json` — what the processor can do.** `python3 rew_tool/dsp_profile.py <new> …`
Not what it is currently set to — that is step 4. If the prose does not state a capability, leave
it null and let it become an open question. `dsp_processing_rate_hz` (the DSP's PROCESSING rate; the old name `sample_rate_hz` is still read; a `project.json` written under the old name moves to the new one with `project.py <dir> migrate-fields` — the `mic` / `measurement` rate is the CAPTURE rate and keeps its name) is required before phase 1, so if the
prose never says it, that is the first thing to ask the Arbiter.

**4. The first ledger snapshot — what it is set to now.** The STEP 1/2/3 sections: crossovers,
delays, gains, polarity, per-channel EQ. This is `v_001` of the new project, and its `note` should
say where it came from and as of when — the prose has dates, use them.

Only the CURRENT state. The iteration log is history, and history stays in the prose file, which
remains readable. Carrying it into a ledger would mean inventing which facts were in force when —
the same reason `migrate.py --into` leaves history behind.

**5. Check, then enter the process.** `python3 rew_tool/contract.py check <new>` must come back
clean. Then `enter-phase` at wherever the tune actually is — a finished car is not at phase −1,
and the journal's first entry should say the project was brought over from prose, with the old
path.

## Done when

`contract.py check <new>` is clean, the settings sheet renders with its Slot column filled, and
the Arbiter recognises their own car in it. If any of the three fails, the project is not carried
over — it is half-carried, which is worse than not started.
