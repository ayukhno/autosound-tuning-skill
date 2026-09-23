# W-3 · v3.0.62 — the plan

Opened 2026-09-23, straight after v3.0.61. **The wave is COLLECTING** (the Arbiter: «головне ми збираємо НЕ РОБИМО»): findings go into the milestone and this table, and nothing is built until he says so. The composition was agreed with the Arbiter the same day: everything open
that is not deferred and can be done at the desk. The branch is `wave-2026-09-23`, and the milestone is `W-3 · v3.0.62`.

| item | what | how (decided) |
|---|---|---|
| **#60** | Reviewer CLIs on Windows: Codex and Claude get the whole prompt as an argument through `cmd.exe` (8191-character limit) | The prompt goes on stdin: `codex exec … -` and Claude's `-p` fed from stdin (both checked live). Codex's answer is read from `-o <file>`, and it needs `--skip-git-repo-check` outside a trusted repository (found live). agy's error path is kept. A test sends a package longer than 8191 characters through each route, with fake binaries |
| **#61** | Human deliverables go into `<project>/docs/` | **Folders by kind** (the Arbiter): `docs/sheets/v_NNN-<slot>.md` (what to enter in the DSP software), `docs/plans/_NN-capture.md` (what to measure in a series), `docs/reports/<date>-<what>.md`. The tools that make them write their copy there. `contract.py check` names a deliverable found elsewhere |
| **#64** | The installer prints "about 700 MB" before the running-TCC check | The size line is printed only when the upgrade will run |
| **#24** | The de/pl listening references lag | **Through the Advisor** (the Arbiter): each language as one `autosound_ai.py ask` package, as the intake's translations were made. `c17` in both cheat sheets. `test-tracks.de.md` / `.pl.md` with the 98 cues and the titles. `listening.coverage(lang)` as a report |
| **S-057** | A verdict block at the top of every tool's output | **The shape** (the Arbiter): at most five lines. The verdict, then 2–3 numbers each with its quantity and its source, then what to do next ("enter this" / "measure these N"). Details follow below, or with `--verbose`. The tools a session calls at a step: `predict`, `analyze-joints`, `eq_propose`, `resonalyze_engine run`, `contract.py check`, `verify_prediction` |
| **S-056** | The junction level step over the SHARED band | Computed in Python from the same solos and chains as the front's terms, over the band where both members play. No engine change, so no new binaries |

**Deferred at the review:** S-055 (needs an ellipsoid round in the car). **Still deferred:** S-001, S-017,
S-021 (after 3.1.x), hub #113 PAS-005, hub #82 HUB-031, #26 (a 3.2 candidate). **Waiting on his run:** S-059.
