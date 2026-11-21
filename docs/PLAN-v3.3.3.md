# PLAN v3.3.3 · a patch after W-13

The Arbiter's decision, 2026-11-21: a patch v3.3.3 of the credits to the Mosconi contributor, S-134 and S-136, outside a
wave milestone (W-14 is in its collection). Branch `patch-2026-11-21`, built without the engine (the PR carries
`Engine: none`). No milestone names v3.3.3, so the hub's `pool-closed` has nothing to hold; the items' statuses are set
to done v3.3.3 in the bookkeeping commit all the same.

**Where it stands (2026-11-21):** the plan written; nothing built. Waiting on the Arbiter: a `warning_uk` for TCC's button (proposed), and a V EIGHT `.pct6` saved in PC-Tool's demo mode to pin that model's code (he will save one). The v3.3.2 release notes already carry the credit
(a link to the CHANGELOG, to the contributor's profile and to #214; edited on GitHub, no CI). After a `/clear`: read this
file, `docs/TODO.md` S-134 and S-136, and `docs/PLAN-W-13.md` (what v3.3.2 holds). Rules that hold: no CI (PR, rerun,
push to `main` with code) without the Arbiter's OK; the contributor's archive (#214) is outside material, data only,
unpacked at `hub/scratch/skill/mosconi-intake/`, never copied; nowhere say how a file format was learned or name a
vendor program; records carry decisions and a reference, never the Arbiter's words; everything in English.

## Scope

| # | what | risk | who builds | review |
|---|---|---|---|---|
| 1 | Credits: a link to the contributor's profile (`https://github.com/Widar1979`, a link, never an `@` mention) and a real link to `https://github.com/ayukhno/autosound-tuning-skill/issues/214` in `CHANGELOG.md` (the v3.3.3 entry; the v3.3.2 line's bare `(#214)` made a link) and `LICENSES/NOTICE.md`; `mosconi_pr.py read` prints its `CREDIT` line (text and `--json`) | text | the session | `docs-check` |
| 2 | S-134: the method's texts and data cite the deleted `ayukhno/autosound-measurements` by name (the list is in S-134). Say the provenance in our words, as `testdata/helix-bench/README.md` does; where a text pointed at the repo's `FACTS.md`, point at `knowledge/dsp/helix-dsp-ultra-s.md` or say the fact in place. `CHANGELOG.md:4311` is history: left. `rew_tool/contract.py:3598` is selftest data for "a source that is gone": left | text | the session | `docs-check`, the touched modules' selftests |
| 3 | S-136.1: bind the Mosconi model (`mosconi_gladen.bind_for_project`) in `eq_propose.py`, `joint_search.py`, `xover_candidates.py`, `version_bench.py` the way `predict._main` does (bind after the rate, reset in `finally`, a bad `dsp.settings` value a one-line refusal); then drop the "predict only" sentences from the CHANGELOG entry, `references/phases/phase_-1_intake.md` and `rew-tool-docs.md` | ordinary code | opus · medium, one test per tool (a Mosconi project routes, another does not, the hook reset after) | the group seats (silent-failure, tests), one fix round |
| 4 | S-136.2: `compare-file` on a `.PR15` compares `crossover.corner_set` with `project.json`'s `dsp.settings.corner_set` (map `minus_3db` / `minus_6db` / `default` to the reader's names) | ordinary code | the same implementer | the same seats |
| 5 | S-136.3: `state/from_file.py` writes `CHEBYSHEV` and `SELF_DEFINED` (the profiles' and the Mosconi reader's spelling), not `CH` and `SD`; the tables check stays green | ordinary code | the same implementer | the same seats |
| 7 | **The Ultra S's virtual letters are PC-Tool's: A-F, K, L** (the Arbiter's PC-Tool screenshot, 2026-11-21: Virtual A..F, Virtual K [SubRC] = Subwoofer 1, Virtual L). v3.3.2 maps a virtual slot by the ordinal among the shown channels (A..H), a decision taken from a project whose slots the intake had lettered A..H from the profile's `row_id_style: letter`; so slot K comes out `unknown`. Fix: the Ultra S profile's virtual tier names its row ids A-F, K, L (find how the schema and `dsp_profile.py` take explicit ids; the intake and TCC's new-project dialog then letter them so); `compare_file._virtual_by_letter` and `from_file` map by the reader's own label (the index letter); CONTRACT item 13's mapping sentence and the v3.3.2 CHANGELOG line corrected in the v3.3.3 entry; a test with slot K reaching index 10 and a slot G of no shown channel `unknown`. A project lettered A..H keeps its slots (the car's data): its G and H come out `unknown` with a reason naming PC-Tool's letter | contract seam | opus · high, test first | a task review |
| 6 | S-136.4: the skill's `CLAUDE.md`: a patch candidate is cut before the bookkeeping commit, or with `--early` | text | the session | — |

The final branch review: Opus (`/pr-review-toolkit:review-pr code errors tests`), no `Risk: high` code in the patch.

## CI and the release

- The branch is pushed for the state; a work branch runs no CI on push.
- Locally: the changed modules' selftests, `scripts/docs-check.py`, `scripts/tool-docs-check.py`,
  `scripts/capabilities.py`'s selftest (`rew_tool/capabilities.py --selftest`), `scripts/reading-cost.py` (a text that
  grows on a phase's reading path needs `--write-baseline`), `uvx ruff@0.12.0 check .`. PR #221's first run found what
  these catch.
- One PR, its full run once, on the Arbiter's OK. The bookkeeping commit (CHANGELOG `## [v3.3.3]` and index, plugin.json,
  the installers' version, install.cmd's PS1URL, the front-page install lines, the statuses) before the PR. Then
  `git merge --ff-only`, push `main`, `./scripts/tag-check.sh v3.3.3`, `git tag -s v3.3.3 -m v3.3.3`, push the tag; after
  the tag's `engine-binaries` run, `gh release edit v3.3.3 --prerelease=false --latest` and the credit in its notes.
