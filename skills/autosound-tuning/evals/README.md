# Trigger eval set

`trigger-eval-set.json` — 62 queries (since 2026-10-14; 51 from 2026-10-13, 34 before), each with a `"context"`:
`"neutral"` (an empty folder) or `"project"` (a seeded tuning project, below). The 2026-10-14 eleven: a TCC feature
request, feedback to the maintainers, bare "continue" / «продовжуємо» / "where were we" and a bare "file an issue" in a
project, which should fire; a feature request for another app, a GitHub task in a repo named `hub`, an issue for the
autosound-hub governance docs, and bare "continue" and "file an issue" in an empty folder, which should not. The 51: 25 that should trigger — a tune from scratch,
casual English, imaging, an EMMA round, an MMM sweep, a house curve, uk/de/pl asks, resuming a tune (by name, inside a
project folder, and TCC's two openers), a bug report or feedback on the skill or TCC in en/uk/de/pl — and 26
near-misses that should not: home audio and studio monitors, a speaker, box, impedance or crossover question with no
tune in it (a sub or a DSP to buy, a door rattle included), a code project's "where did we leave off", a bug report
for another project. It validates the SKILL.md `description` triggering; skill-creator's loop was the first harness:

```
python3 -m scripts.run_loop --eval-set <this>/trigger-eval-set.json \
  --skill-path <skill-dir> --model <session-model> --max-iterations 5 --verbose
```

⚠️ Known env caveat (2026-06-22 run): the skill-creator `claude -p` eval subprocess reported
0% recall on EVERYTHING — incl. slam-dunk existing triggers (EMMA, imaging, MMM sweep) — which
is not real (the live skill triggers on those). The skill was not being registered/detected in
the `claude -p` subprocess; the improve step then hit a token limit. So the impedance/T-S/box
trigger phrases in `description` were added MANUALLY (additive — cannot reduce existing recall).
Re-run this set on a machine where the eval harness actually registers the skill to get a valid
before/after.

## `run_trigger_eval.py` — valid runner (repairs the caveat above)

The 0%-recall artifact was diagnosed (2026-07-01): skill-creator's `run_eval` injects the
candidate description as a temp **slash-command** and only matches that uuid in the tool input —
so it never matches a real `Skill(autosound-tuning)` invocation and reports false 0 even for
slam-dunk triggers (confirmed: an EMMA/crossover query really does fire `Skill(autosound-tuning)`).

`run_trigger_eval.py` tests the **actually-loaded** skill instead: it runs `claude -p <query>` and
detects a real `Skill(<skill-name>)` tool_use in the stream, killing the subprocess the moment a
trigger is seen (so you don't pay for the whole skill run). Requires the skill to be discoverable
by `claude -p` (a `~/.claude/skills/<name>` symlink or an installed plugin), and tests the LIVE
description. Pass `--model` explicitly (the default-model bug is what produced the old 0% — a
disabled session model made every `claude -p` fail).

```
python3.12 evals/run_trigger_eval.py --eval-set evals/trigger-eval-set.json \
  --skill-name autosound-tuning --model claude-sonnet-4-6 --workers 5
```

**What every run checks (#145, 2026-10-09).** Each `claude -p` prints an init event listing the skills it sees. The
runner reads it before anything else: `--skill-name` must be in it (a run that cannot see the skill measures nothing —
the old false 0%), and every `--absent` skill must not be (another skill on the same subject competes for the same
queries); a run that ends in an error result — a model that is not available, no access — is no "not triggered"
either, nor is one that ends after its init without a result, or that `--timeout` cuts off: that problem carries the
last lines `claude -p` wrote to stderr. Any of these voids the run, and so does a query that could not start (no
`claude` on PATH): the query is named with what was wrong, the queries not started are cancelled, the runner prints no
score (`no score: the run is void`; in the JSON `"void": true, "passed": null`) and exits 1 — what ran before the void
is not a sample. With nothing wrong it prints `init skill list: <skill> in all N runs, <absent> in none`, the score and
the duration; the JSON on stdout carries the `claude` command line, the duration and, per query, what its init list
held.

- `--settings <json-or-file>` and `--no-session-persistence` are handed to every `claude -p` as they are.
- `--absent <skill>` (repeatable): a skill that must not be in a run's list (a plugin's or a synced copy's
  `<prefix>:<skill>` counts).
- `--cwd DIR`: the folder the neutral queries run in. By default a fresh `trigger_eval_*` folder under the system temp
  folder, removed after the run. A folder inside a git repository, or whose path names `autosound`, `hub` or `skill`,
  is refused in one line (exit 2): the model reads the path, and from a folder named for the hub it took the TCC bug
  reports for a GitHub task there (#170). The folders are printed on stderr and in the JSON (`cwd`, `project_cwd`).
- `--project-fixture`: the queries whose `"context"` is `"project"` run in a fresh `trigger_eval_project_*` folder
  seeded as a tuning project: the `CLAUDE.md` that `rew_tool/project_seed.py` `write_claude_md` writes (its first line
  loads the skill), stubs of `autosound_context.md`, `process/process-state.json` and `state/dsp-state.md`. Without
  the flag those queries are not run; stderr says how many, the JSON has `skipped_project`, and the score is over the
  queries that ran.
- `--keep-folders`: keep the folders the runner made, to look into them after.
- `--selftest`: the runner's own mechanics against a stand-in `claude` on PATH, offline (it is in
  `scripts/run-selftests.sh`).

Validated 2026-07-01 on the v2.0.1 description (added casual-EN + create-a-curve triggers):
**9/9** on a focused set — all casual-EN / create-curve queries fire; near-misses
(home-theater, studio monitors, sub-buying, door-rattle) correctly do not.

v2.0.2 added **UK/DE/PL native-language triggers** (Gemini native-QA: use technical markers —
процесор/затримки, Car-HiFi einmessen/Laufzeitkorrektur, strojenie DSP/opóźnienia — which are
both idiomatic and exclude home-hifi/PC-speaker false-positives). Validated **7/7**: all
UK/DE/PL enthusiast queries fire; native-language near-misses (home theater, living-room hi-fi,
PC speakers) correctly do not.

v2.0.4 added **resume / continuation triggers** (so a returning user's message fires the skill's
Resume protocol on ANY project, not only ones with rich auto-memory — a gap found by the
anti-drift dry-run). Validated: **imperative** resume phrasings ("resume my car-audio tune",
«продовжуємо тюн авто», «на чому зупинились у тюні авто») fire; generic-project near-misses
("resume my code project", «продовжуємо роботу над проєктом», bare "what's my current state")
correctly do not. **Known limitation (documented, not a defect):** a *pure status question*
("coming back — what's my current DSP state?") consistently does NOT trigger (0/4) — the model
routes "what is X?" as a lookup, not a skill-load. Low impact: the anti-drift dry-run showed such
a question still **self-answers correctly from disk** (reads dsp-state/changelog/audit-trail), and
forcing a lookup to load a full tuning skill isn't clearly desirable. Imperative resume is the
common case and it works.

## Run on the 3.x description — 2026-08-26 (v3.0.31 + the DVC wording)

`python3 evals/run_trigger_eval.py --eval-set evals/trigger-eval-set.json --skill-name autosound-tuning --model sonnet --workers 4`
against the LIVE skill (a `~/.claude/skills/autosound-tuning` symlink to the working checkout — the
same shape `install.sh --terminal` makes).

**36 / 37 — no false positives.** Everything the set says should fire, fires: the from-scratch and
casual-EN asks, imaging/staging, an EMMA round, an MMM sweep reading, house-curve creation, the
impedance / T-S / sealed-box family, the UK/DE/PL native-language asks, and all three resume
phrasings. Every near-miss stays silent: home theatre, bookshelf-speaker impedance, PC speakers,
a 3D-printer enclosure, a Fusion 360 box, a code project's "where did we leave off", and a bare
"what's my current state?".

**The one miss is marginal, not a hole:** *"how should i wire my dual 4-ohm voice coil subwoofer,
and does series-vs-parallel change what box volume i should build?"* — 0/4 on the v3.0.31 wording
("DVC coil wiring"), then, with the description sharpened to the user's own words ("dual-voice-coil
(DVC) wiring — series vs parallel, the load it makes and whether the box volume changes"), 0/3 on
single re-runs and 1/1 inside the second full run (**37/37**). So it sits on the model's routing
edge — a question that reads as one electrical fact is sometimes answered as a lookup rather than
by loading a tuning method (the same shape as the documented status-question limit). Low impact:
the sibling queries of the same family (a DVC sub in Ukrainian, T-S from a datasheet, box
verification by impedance sweep, L/R matching) fire every time. The sharpened wording is kept —
accurate, additive, and recall elsewhere did not move.

## What the set deliberately does NOT ask for (2026-09-09)

Seven bench queries — Thiele-Small by the added-mass method, sealed-box volume for a Qtc, checking a
built box for leaks, DVC wiring, L/R driver matching by impedance — were removed from the set, and
the matching sentence was removed from `description`.

**Why, measured rather than assumed.** They were in the description for months, worded with every
keyword the queries use, and they fired **0 out of 7** — in the long description and in two rewrites
of it. The diagnosis is not the wording: a model can answer a Thiele-Small or box-volume question
out of its own knowledge, so it never reaches for a skill. Adding keywords does not change that;
only a promise the model cannot keep alone would — "measure it with the project's jig workflow and
record the result in the project" rather than "explain T-S".

The capability did not go anywhere: it is on the board (`references/core/capabilities.md`, four
rows) and in `references/core/impedance-ts.md`, so a session already working on a car finds it. What
changed is that the skill no longer *promises* to wake up for a bench question — and the description
stopped being 200 characters too long to be shown in full, which was costing the DE and PL triggers.

Baselines on the 2026-09-09 set (`--model claude-sonnet-4-6`): the long description scored 15/22
with 3 false positives; a full rewrite 12/22; a minimal reorder 13/22 with 1. The rewrites were
discarded — no measured gain, and a run-to-run spread of 2-3 on 22 queries is not a result.

## The baseline before the SKILL.md cut — 2026-10-13 (#145, I-4's "before")

Three runs on the description as `8ab9133` left it (its last change; the tree at `2e46e12`), the 34-query set,
Claude Code 2.1.296, each from an empty folder outside any repository — no project `CLAUDE.md`, no project settings,
no copy of the skill but the `~/.claude/skills/autosound-tuning` link:

```
python3 evals/run_trigger_eval.py --eval-set evals/trigger-eval-set.json --model claude-sonnet-4-6 --workers 4 \
  --settings '{"skillOverrides":{"rew-car-audio-tuning":"off"},"disableAllHooks":true}' \
  --absent rew-car-audio-tuning --no-session-persistence
```

`skillOverrides` hides the other car-audio skill, which answers the same queries: `rew-car-audio-tuning`, synced from
claude.ai, listed as `anthropic-skills:rew-car-audio-tuning`. `disableAllHooks` keeps the account's session hooks from
running 34 times a run. Every run printed `init skill list: autosound-tuning in all 34 runs, rew-car-audio-tuning in
none`.

| run (UTC) | score | should fire, fired | should not, fired |
|---|---|---|---|
| 1 · 13:27 | **29/34** | 13/15 | 3/19 |
| 2 · 13:30 | **29/34** | 12/15 | 2/19 |
| 3 · 13:33 | **29/34** | 12/15 | 2/19 |

In all three: a miss on «на чому ми зупинились у тюні авто минулого разу? який зараз стан DSP?» (the pure status
question, the limit documented above) and a false positive on "a flat reference target curve for my studio nearfield
monitors". In two: a miss on «продовжуємо тюн авто, нагадай на чому зупинились — …» and a false positive on „mein
Wohnzimmer-Heimkino und die HiFi-Anlage einzustellen". Once each: the EMMA, MMM-sweep and resume-my-helix misses, and
the living-room subwoofer and Dolby Atmos false positives. The runs after the cut use the same command, settings and
kind of folder, so the two compare like with like.

## The runs after the SKILL.md cut — 2026-10-13 (#145, I-4's "after")

First the set grew from 34 to 51 queries (I-24). Ten should fire: a bug report on TCC in en/uk/de/pl and a feedback
package for the skill (the tooling block: "something in TCC is broken", "file an issue", "feedback package"); "continue
my car-audio tune … crossover, time-alignment and gain state"; resuming inside a project folder, in English and
Ukrainian; TCC's two openers, as `core/openers.py` writes them. Seven should not: an issue for a React repo, a bug for
the Python maintainers, DIY bookshelf crossovers, REW and an AV receiver in a living room, studio-monitor imaging, "what
is a Linkwitz-Riley crossover", a DSP to buy. The runner starts every query in one folder, so "inside a project
folder" is said in the query. In a real project a bare "continue" names nothing, and what loads the skill there is the
first line of the project `CLAUDE.md` that `rew_tool/project_seed.py` writes — "Load the `autosound-tuning` skill for
every request in this folder." This set cannot measure that line.

Six runs on the 51, with the command, settings and kind of folder of the baseline above (the other car-audio skill
hidden, the account's hooks off), Claude Code 2.1.296, `claude-sonnet-4-6`. Every run printed `init skill list:
autosound-tuning in all 51 runs, rew-car-audio-tuning in none`. Three on the description as `a04396e` cut it (1,017
characters); three on the old one: the frontmatter of `ed95425` (as `8ab9133` left it) put over the cut body in the
working tree's SKILL.md, the copy the `~/.claude/skills/autosound-tuning` link reads, and taken back after.

| run (UTC) | description | score | should fire, fired | should not, fired | the baseline's 34 |
|---|---|---|---|---|---|
| 1 · 14:46 | cut, `a04396e` | **41/51** | 17/25 | 2/26 | 30/34 |
| 2 · 14:51 | cut | **37/51** | 15/25 | 4/26 | 28/34 |
| 3 · 14:57 | cut | **40/51** | 18/25 | 4/26 | 29/34 |
| 4 · 15:02 | old, `ed95425` | **40/51** | 17/25 | 3/26 | 28/34 |
| 5 · 15:06 | old | **37/51** | 14/25 | 3/26 | 27/34 |
| 6 · 15:13 | old | **37/51** | 13/25 | 2/26 | 27/34 |

**No recall drop.** The cut description scores 37–41 (39.3 on average), the old one 37–40 (38.0): inside the spread of
2–3 recorded above. Moved by two of three or more: the Passat imaging ask (old 0/3 fired, cut 2/3), the custom house
curve (1 → 3), "resume my car-audio tune — … crossover and delay settings" (1 → 3), and the Ukrainian home-cinema
near-miss (0 → 2: a false positive gained). Moved by one: «продовжуємо тюн авто, нагадай …» and the Dolby Atmos
near-miss (1 → 2), the German Heimkino near-miss and the feedback package (3 → 2).

**What fires on neither.** The four bug reports on TCC fire 0/3 on both descriptions; the audit's probes (one run each,
2026-10-04, another machine) had 4/4. Probed here, the model takes the request for a GitHub task and goes looking for a
repository — and the run folder's own path, a session scratchpad, carries the hub's name, so it looks there. That is
so for every run here and for the baseline, which keeps the comparison like with like; a folder whose path names
nothing would say more. Inside a project the `CLAUDE.md` names the gate. Resuming inside a project folder fires 1/3 in
English and 0/3 in Ukrainian, "continue my car-audio tune" 1/3, the pure status question 0/3 (the limit above). TCC's
two openers fire 3/3 on both.

## Runs of 2026-10-14 (#170)

The 62-query set, each neutral query in a fresh folder under the system temp folder, each project query in the seeded
project:

```
python3 evals/run_trigger_eval.py --eval-set evals/trigger-eval-set.json --model claude-sonnet-4-6 --workers 4 \
  --settings '{"skillOverrides":{"rew-car-audio-tuning":"off"},"disableAllHooks":true}' \
  --absent rew-car-audio-tuning --no-session-persistence --project-fixture
```

| run (UTC) | score | should fire, fired | should not, fired | neutral | project | the TCC bug reports (4) |
|---|---|---|---|---|---|---|
| 1 · | | | | | | |
| 2 · | | | | | | |
| 3 · | | | | | | |
