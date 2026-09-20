# W-1 · v3.0.59 — the plan

> Milestone: <https://github.com/ayukhno/autosound-tuning-skill/milestone/1> · the wave's rules:
> hub `governance/WAVES.md` · the collection it came from: `docs/TODO.md` S-024…S-050.

The Arbiter's decisions at the review, 2026-09-20: this scope, and **a fresh role session per package**
— this conversation makes the milestone and this plan, and does none of the work.

**One sentence of goal, so a session can check itself against it:** a session stops making the person
carry the method's internals — it reports in one line, speaks his language, and writes down where every
fact came from.

## How the work is run

- **One branch for the wave**: `w1-intake-form` already exists and carries the collection plus the
  intake-form prototype. The prototype is NOT in this wave (S-033/S-037 are deferred) — it stays on the
  branch, unreleased, because pulling it out would cost more than leaving it; the CHANGELOG entry says
  what it is. Every package below commits onto that branch.
- **Tests while working**: targeted only — the module's own selftest and the files a change touches.
  The full suite runs ONCE, before the PR, with the Windows VM suspended and `-n 4` (the Mac OOMs on
  `-n auto` next to a VM and a session).
- **CI**: once, on the pull request (`WAVES.md` §2). No `workflow_dispatch` unless a change touches
  Windows or installing — none here does.
- **Models** (the Arbiter asked for the choice): the session itself on **Opus 5** wherever the work is
  judgment — what a rule says, what goes in a provenance field, reviewing a diff. **Sonnet** subagents
  for the mechanical half — sweeping the tree for every text a rule touches, checking cross-references,
  scaffolding tests. At most four at a time, and their output is read, never merged unreviewed.

## Package A — the reporting rule (Opus; Sonnet for the tree sweep)

S-046 · S-038 · S-040 · S-029 · S-031 · S-041 (the umbrella closes with them).

The one change that touches every session on every car, and the cheapest in the wave.

1. **A passed check costs one word.** The reconcile folds into one line («перевірки: зроблено»); only a
   FAILED check gets sentences, and in the useful form — what to do, or the options with the recommended
   one first. Where it lives: `happy-paths.md` §1, SKILL.md's pre-session, and whatever phase text
   repeats the inventory habit (the sweep is a subagent's job).
2. **A verdict is not re-derived in prose** (S-038): after `capture-check`, the session says what the
   check said and stops; arrivals are read in Phase 1, by the tools built for it.
3. **Name the thing, not the metaphor** (S-040): «записую, що зараз у ДСП: конфігурація `v_001`», and the
   one-clause explanation of the ledger once per project. ⚠️ Settle the collision first — «конфігурація»
   is Phase 1's word for a whole candidate set (skill #38); if `v_NNN` takes it, Phase 1 says «варіант».
   The Arbiter's call, and it is one line to ask.
4. **The question mechanism is never retold** (S-029): a question that did not reach him is nothing at
   all — the questions go into the text, with no claim about why.
5. **A plan step names what it covers** (S-031): `process.add_step` gains `covers` (the dotted paths, as
   `open-questions` prints them), the name carries the first two or three and `+N`, and the step's
   printers show it. TCC's rendering half rides as a ticket once the field exists.

**Done when:** the four texts say it, `process.py`'s selftest covers `covers`, and a session reading
only these files would have written the short version of the exhibit in S-046.

## Package B — the language survives a clear (Sonnet writes, Opus reviews)

S-045.

`project.json` carries the language; `intake.save` writes it like any other confirmed answer; the
pre-session reconcile reads it BEFORE the first reply, and a front-end's report still wins when present.
Two fields if the Arbiter's S-037 point 2 stands (the AI's language and the person's can differ) — ask
him in one line before writing the schema, because adding the second field later costs a migration.

**Done when:** a project with `language: "uk"` on disk gets a Ukrainian first reply in a session that
knows nothing else, and the intake's `project.language` stops being «not machine-readable».

## Package C — provenance (Opus; this is the wave's deep end)

S-024 · #48 / S-036 · S-048.

One defect seen three times: a fact whose ORIGIN is not written reads later as everybody's word.

1. **An imported `fs_hz` says it is imported** — the source project and the date it was measured THERE,
   instead of `source: "measured"` with the original timestamp. The Arbiter's rule: his word closes it,
   a second impedance run is not owed, and every report that uses the number names where it came from.
2. **The protective record carries who wrote it** — `user | front_end | default` — and
   `protective.should_de_embed` treats a front-end default as `check`, not as an answer. Plus the
   correction path #48 asks for: a closed round's record can be corrected, the correction visible.
3. **A foreign series number carries its origin** — the project it was taken in and the `_N` it was
   there; a round refuses a series that is not this project's unless that origin is on record; the
   grammar says `_N` is project-scoped in the same breath as it says it is not `v_NNN`.

**Done when:** the three writers refuse to record an origin-less fact, the readers say the origin out
loud, and `car/passat-b8-2026`'s imported `fs_hz` rows read as imported without being re-measured.

## Package D — mechanisms that carry the rule (Opus for D1, Sonnet for D2–D3)

1. **S-047 — the flaw map asks.** A run that produced ASSUMED rows ends with the REQUEST: the channels,
   the titles that would settle them (`<ch> p1…p9_<N> (sw)`), and the offer to open the round. The phase
   does not close while assumed rows exist and no request is on record. Judgment: what counts as «the
   measurement that settles it» for each row kind.
2. **S-034 + #49 / S-035 — the feedback rail.** `post_comment` beside `post_feedback` (same closed
   `CHANNELS`, same `guarded_run`, same URL verification), and a title that comes from the caller with
   `car · dsp` kept as provenance, so the 24-hour duplicate guard stops comparing a constant.
3. **#47 — `naming.py check`** stops reporting `ok` for a title it normalised: say the title on disk
   differs, and what it was read as.

**Done when:** each has a selftest that fails on the old behaviour.

## Release

S-023 / hub `#178` closes with this tag. Order: packages A and B first (they change how every later
session reports), then D, then C (it touches the schema and deserves the most care), then the version
bump, the CHANGELOG entry naming `v3.0.59`, the full suite, the PR, `--ff-only`, the tag.

Exit criteria are the milestone's fifth line, and they are hub `WAVES.md` §3.1 — not repeated here.

## Starting a package

```bash
hub/bin/role skill          # a fresh session; it reads this file and docs/TODO.md, nothing else
```

The first thing such a session does is say which package it is taking, and the last thing is the state
in git. Two questions are open for the Arbiter and both are one line: the «конфігурація» collision
(Package A step 3) and whether the language is one field or two (Package B).
