# Trigger eval set

`trigger-eval-set.json` — 20 queries (10 should-trigger incl. the impedance/T-S/box-design
capability + recall guards for existing triggers, 10 should-NOT near-misses) for validating
the SKILL.md `description` triggering via skill-creator:

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
