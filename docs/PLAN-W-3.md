# W-3 · v3.0.62 — the plan

Opened 2026-09-23, straight after v3.0.61. **The wave is COLLECTING** (the Arbiter: «головне ми збираємо НЕ РОБИМО»): findings go into the milestone and this table, and nothing is built until he says so. **2026-09-24:** 21 issues on the milestone, every one assessed in its body (class · model · risk · complexity); `ok` on #24 only. **2026-09-26:** 24 issues, #83–#85 from the bus queue (hub #205, #206, #208); hub #203 and #204 were already #67 and #68. The composition was agreed with the Arbiter the same day: everything open
that is not deferred and can be done at the desk. The branch is `wave-2026-09-23`, and the milestone is `W-3 · v3.0.62`.

| item | what | how (decided) |
|---|---|---|
| **#60** | Reviewer CLIs on Windows: Codex and Claude get the whole prompt as an argument through `cmd.exe` (8191-character limit) | The prompt goes on stdin: `codex exec … -` and Claude's `-p` fed from stdin (both checked live). Codex's answer is read from `-o <file>`, and it needs `--skip-git-repo-check` outside a trusted repository (found live). agy's error path is kept. A test sends a package longer than 8191 characters through each route, with fake binaries |
| **#61** | Human deliverables go into `<project>/docs/` | **Folders by kind** (the Arbiter): `docs/sheets/v_NNN-<slot>.md` (what to enter in the DSP software), `docs/plans/_NN-capture.md` (what to measure in a series), `docs/reports/<date>-<what>.md`. The tools that make them write their copy there. `contract.py check` names a deliverable found elsewhere |
| **#64** | The installer prints "about 700 MB" before the running-TCC check | The size line is printed only when the upgrade will run |
| **#24** | The de/pl listening references lag | **Through the Advisor** (the Arbiter): each language as one `autosound_ai.py ask` package, as the intake's translations were made. `c17` in both cheat sheets. `test-tracks.de.md` / `.pl.md` with the 98 cues and the titles. `listening.coverage(lang)` as a report |
| **#70** (S-057) | A verdict block at the top of every tool's output | **The shape** (the Arbiter): at most five lines. The verdict, then 2–3 numbers each with its quantity and its source, then what to do next ("enter this" / "measure these N"). Details follow below, or with `--verbose`. The tools a session calls at a step: `predict`, `analyze-joints`, `eq_propose`, `resonalyze_engine run`, `contract.py check`, `verify_prediction` |
| **#69** (S-056) | The junction level step over the SHARED band | Computed in Python from the same solos and chains as the front's terms, over the band where both members play. No engine change, so no new binaries |
| **#65** | The issue-posting gate is reachable only after the skill loads, and "file an issue" never loads it | Not decided: collected 2026-09-24 |
| **#66** | `L m-tw_52 (rta)` parses silently as side `L` + modifier `m-tw` | His word 2026-09-24: accept. `-` between driver codes inverts the next member, in a chain of any length (`L w-m+tw`); side first (`L m-tw`, never `m-L-tw-L`); the rest of his grammar is quoted in #66 |
| **#67** | Target-curve page: Compare and Analyze give one band two numbers (hub #203 TCC-029) | Not decided: collected 2026-09-24 |
| **#68** | Critic channel: an agy stream cut off mid-answer counts as a refusal (hub #204 TCC-030) | Not decided: collected 2026-09-24 |
| **#71** | README and FAQ name Gemini Pro (High); agy refuses it in some regions (found at #24) | Not decided: collected 2026-09-24 |
| **#72** | One plan step, two labels: the text says 2.8, the panel shows 2d | Not decided: collected 2026-09-24 |
| **#73** | Phase 2's plan is too big; measure, compute, write, no progress — analyse and cut | Not decided: collected 2026-09-24 |
| **#74** | A proposal ended as files on disk: `apply.propose` skipped, no yellow version (same cause as #73, the Arbiter) | Not decided: collected 2026-09-24 |
| **#75** | A capture series announced with no list; made up from the previous one after he asked (same cause as #73, #74) | Not decided: collected 2026-09-24 |
| **#77** | The rule behind #74 and #75: a DSP configuration is born yellow, a measurement is a `cap_NNN` round with a per-driver list, closed against REW whatever captured it; all three modes | Not decided: collected 2026-09-24 |
| **#78** | A round's list ordered by setup: the type the car is set up for first, then one switch (tripod sweep vs seated RTA) | Not decided: collected 2026-09-24 |
| **#79** | A capture round in four columns: Solo (sw), Solo (rta), Group (sw), Group (rta); the panel is TCC's, the split open | Not decided: collected 2026-09-24 |
| **#80** | "If you have time" captures go into the round's list (#77), not only into the message | Not decided: collected 2026-09-24 |
| **#81** | `scene_presets` drops every pair silently: registry keys `m_L`/`w_L`, the tool looks for `m-L` literally | Not decided: collected 2026-09-24 |
| **#82** | `scene_presets`' ladder degenerates on the Passat: every rung the same, presets built by hand | Not decided: collected 2026-09-24 |
| **#83** | An open capture round carries no grouping of its own; the glossary keeps `r-L`/`r-R` active while the registry has them off (hub #205 TCC-031; the rest of that ticket is held by #75, #77–#80) | Not decided: collected 2026-09-26 |
| **#84** | `project_seed.py` records the wrong source project: the controls loop overwrites `name` (hub #206 RES-019) | Not decided: collected 2026-09-26 |
| **#85** | Reviewer channel: the API waits a fixed 120 s, the step down to the CLI carries a model id it does not know, `ask` missing from the usage text (hub #208 RES-021; related #68, #71) | Not decided: collected 2026-09-26 |

**Deferred at the review:** S-055 (needs an ellipsoid round in the car). **Still deferred:** S-001, S-017,
S-021 (after 3.1.x), hub #113 PAS-005, hub #82 HUB-031, #26 (a 3.2 candidate). **Waiting on his run:** S-059.

**Built (with the Arbiter's OK, label `ok`):** #24, 2026-09-23 — through the Advisor (`ask`,
`gemini-3.8-flash-high`; `gemini-3.1-pro-high` is refused in this region). Both cheat sheets are level
with English (`c17`, the two missing sections, the five new route steps); `test-tracks.de.md` and
`.pl.md` carry all 98 cues and the descriptive titles; `listening.py coverage` reports 17/17 · 98/98 ·
10/10 in de, pl and uk. `README.{uk,de,pl}.md` followed the same day at the Arbiter's word, the same way:
level with English, the lag banners gone, `i18n-check` clean. `FAQ` followed in all four languages after a review round with
the Arbiter: `FAQ.md` checked claim by claim against the method, `FAQ.uk.md` through the Advisor and a Gemini
read, `FAQ.de.md` / `.pl.md` through the Advisor; no translation declares a lag any more. TCC's new guides
(English only, hub #202 SKL-053) are linked from the FAQ and the READMEs' language bars.
