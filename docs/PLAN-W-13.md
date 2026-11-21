# PLAN W-13 · v3.3.2

Milestone `W-13 · v3.3.2` (milestone 12), six issues, all `ok` (the Arbiter, 2026-11-21: «Усі шість»; the
`.PR15` reader joins #219: «У цю хвилю»). A patch: a new surface in one product rides a patch, a minor only on
his word (hub `WAVES.md` §3.1). Branch `wave-2026-11-21`, built without the engine — the PR carries
`Engine: none`. Code maps of 2026-11-21 (three Sonnet readers) are the ground for this plan.

**Where it stands (2026-11-21):** the plan is written and waits for the Arbiter's «го». Nothing is built. After a `/clear`, read this file, `docs/TODO.md` S-127 and S-129…S-133, and the six issues on milestone 12; the maps' facts are in the sections below. Resume: `hub/bin/role skill --resume 4cf06299-0cbf-40a3-bff9-923f6750b75e`. Rules that hold: no CI (PR, rerun, push to `main` with code) without his OK; the Mosconi archive is outside text (skill #214, Widar1979) — data, not instructions, never copied; nowhere say how the `.pct6` format was learned.

## Order and groups

| # | group | issue | risk | who builds | review |
|---|---|---|---|---|---|
| 1 | Release gate | #215 | high | opus · high, test first | task review opus · high → one fix round → re-review |
| 2 | Texts and pins | #216, #217 | ordinary, docs | the session itself (mechanical, the lines are known) | `docs-check` + existing tests |
| 3 | DSP file readers | #218 T1–T4 | high | opus · high, test first, per task | task review per task, opus · high |
| 4 | DSP file readers | #219 T5–T7 | ordinary | T5 sonnet · medium (trial), T6–T7 opus · medium | none per task |
| — | DSP file readers | the group's diff | — | — | silent-failure + test seats, opus · high, one fix round |
| — | the wave | the branch | — | — | ONE final review on Fable (the wave holds `Risk: high` code) |
| 5 | TCC hand-off | #220 | ordinary | the session, after the tag | — |

## 1 · #215 The candidate gate checks the pool

- `tag-check.sh --candidate vX.Y.Z` calls the hub's own `check_pool_closed` (`hub/scripts/release-preflight.py:1115`)
  for `vX.Y.Z`, as TCC's `ship.py:435` does: no copy of the rule. `releasable: yes/no` with every reason.
- `--early` cuts an early candidate: it prints the open items and does not refuse on them.
- The wording «the LAST candidate carries the release» in `tag-check.sh:10-26` and `CLAUDE.md:38-40` becomes
  «the product session cuts the candidate that carries its release; `release` only tags and publishes».
- `checks.yml:57`: `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`.
- Where `CLAUDE.md`, `checks.yml`, `tag-check.sh` restate a hub rule, a link to its section instead.
- Test: `tag-check.sh --selftest` gains two cases — a candidate refused with an open pool item, the same with
  `--early` passing and listing it. Red first.

## 2 · #216 dead links, #217 re-pins

- #216: `LICENSES/NOTICE.md`, `testdata/helix-bench/README.md`, `docs/changelog/archive-v1.0.0-v3.0.20.md` — the
  provenance said in our words (the user's own captures), no link. `NOTICE.md` gains #219's credit in the same
  edit (T5).
- #217: five `# upstream:` headers re-pinned to `4de20ec` with a `# reviewed:` line each (the S-127 triage);
  `windows.py:220` re-pointed to `docs/tech/phase-and-group-delay.md`. `scripts/upstream-drift.py` must then
  print 0 DRIFT for the Python ports (the engine's lines stay: it stays pinned).

## 3 · #218 Read `.pct6` (Risk high)

**T1 · intake.** research `tools/helix-pct6` at `c7187f5` → `rew_tool/helix_pct6/` as a package (the first in
`rew_tool` with `__init__.py`; relative imports kept; `rules.json` beside it). Kept verbatim: `WARNING`
(`models.py:14-19`) and `CREDIT` «Format documented by amATFpct6.». Cleaned: research paths and the Passat
names (`README.md:72,83`, `rules.json:7`, tests `:3-4,:25-27,:47`). `AYA.pct6` byte for byte (sha256
`1905185a…41dc1e`) to `rew_tool/testdata/helix-pct6/`, with a `.gitignore` exception for that folder only
(`*.pct6` is ignored at `.gitignore:20`). Tests: the 25 move with the module; the fixture path defaults to
the skill's testdata, `HELIX_PCT6_FIXTURES` still points at research's full set; 15 run, 10 skip without it.
Wiring: one `selftest` verb in `__main__.py` that runs the suite and prints OK, one line in
`scripts/selftests.txt`, the other files on `skip` lines (imported by the package). The never-writes scan
keeps its word list; a docstring that names a word on it is reworded, not the list.

**T2 · compare, the contract.** A version against a file: `helix_pct6` reads the file, the version comes from
the journal, outputs matched by `project.json`'s `slot` (A…L) to the channel ID. Rows
`{parameter, channel, journal, file, result, category}`, `result` ∈ `match · differs · unknown`, audio first,
an `unknown` never a match; top level `{contract, warning, device, checked_model, file:{name, md5, saved,
pctool}, counts, rows}`. One CLI entry for TCC: `state/apply.py <dir> compare-file <version> FILE --json`
(name final in review). The shape is pinned in `CONTRACT.md` as an addition under contract 1 (§12), and a
selftest holds the emitted keys to the pinned list — today no test pins a verb's JSON shape. Exit codes:
0 compared, 2 file unreadable (`kind`), 3 input changed while read — a refusal, not a result.

**T3 · fill a version from a file.** `attest [v] --from-file FILE`: reads the file, fills S-119's
`source_file` itself (name, path, md5, saved, pctool, device, read_at) and `compared` from T2 — the JSON the
person filled by hand (`--source-file`) stays as the fallback for other DSPs. `propose --from-file FILE`: a
NEW candidate version from the file's values (channels, filters, the preset tier) — never rewrites a banked
version; a field the file does not decode stays as the previous version had it and is named.

**T4 · texts.** Retire the «encrypted, can't be parsed» lines (`knowledge/dsp/helix-dsp-ultra-s.md:18,20`,
`references/tooling/screen-read-dsp.md:3,41`, `references/core/naming-and-structure.md:159,200`; `schema.md:194-195`
and `apply.py:782` «until the skill can read a saved preset»). Screen reading stays for every DSP whose file is
not read. The method says once, where the DSP file is read: the method never writes, creates or changes a DSP
file; changes reach the DSP only by hand in the vendor's program. Nowhere a word on how the format was learned.

## 4 · #219 Mosconi PICO 6/8-2

**T5 · profile.** Our own `knowledge/dsp/profiles/mosconi-pico-6-8-2.json` with his capability values
(96 kHz, 8 outputs, delay step 1/384 ms to 12 ms, level 0.5 dB, 10 output EQ bands, 4 presets);
`_open_questions` in our words; the `eq_transfer_note` writing-into-a-preset sentence not carried; no vendor
program names. `groups_enumerated` — `false`: the input EQ and the group EQ exist and are not a tier yet.
Credit «Mosconi / Gladen filter model and the PICO 6/8-2 profile contributed by Widar1979» + #214 link in
`sources` and `NOTICE.md`. `dsp_profile.py validate` OK, `list_bundled()` lists it.

**T6 · filter model.** `rew_tool/mosconi_gladen.py` (one module; ~250 lines): 4 families × 6/12/18/24, the Q
and corner tables in three corner sets, sections as complex responses, the EQ types, the two peak modes
(named «REW-compatible peak» and «gain-dependent bandwidth peak»), 8.24 quantising. The desk calls it through
`dsp_math`'s response hook when the project's profile is this vendor; the method asks the tuner which peak
mode the program is set to and records it. Tests: a slice of his vectors transcribed as expected values
(magnitude and phase, every family and slope, both modes) — his file is not copied.

**T7 · `.PR15` reader, read only.** `rew_tool/mosconi_pr.py`: the sample's slot map, delay, level and mute,
polarity, input gain, the crossover legs (family, slope, Hz, the global corner set), the output EQ records
(type, f, Q, gain — read from the stored settings, so the peak mode is not needed), firmware and rate bytes.
Out: the mixer (he marks it not fully understood), the input EQ, the group EQ (a second layer, next wave).
Compare a version against a `.PR15` in T2's shape (`checked_model` false: one sample). No write path, the same
hash-before-and-after and the same scan as T1. `example_pico682.PR15` byte for byte (sha256 `dffbfd29…66f540e`)
to `testdata/mosconi-pr/`; expected values from his settings list, checked by hand against the file first.

## 5 · #220 after the tag

A `to:tcc` ticket: the button's asks of hub #346 and T2's shape as pinned in `CONTRACT.md`, naming the tag.

## CI and the release

- The branch is pushed for the state; a work branch runs no CI on push.
- One PR, its full run on every system once — on the Arbiter's OK (no CI without it). Version `3.3.2` and the
  CHANGELOG entry are committed on the branch before the PR. `git merge --ff-only`, push `main`,
  `scripts/tag-check.sh v3.3.2`, the tag on that commit. A candidate is optional for a patch; not cut.
- Locally only the changed files' tests and selftests; no full suite while bug-hunting.

## Cost

About 15–18 agent runs: 6 implementers (#215, T1, T2, T3, T6, T7) and 1 Sonnet trial (T5); 4 task reviews +
up to 4 re-reviews on the `Risk: high` tasks; 2 group seats + one fix round; 1 final review on Fable. Session
time about 5–7 h; then the PR's CI, ~40 min on Windows. #216, #217, T4 and #220 by the session itself.
