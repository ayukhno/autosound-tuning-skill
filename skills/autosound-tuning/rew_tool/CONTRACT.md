# Contract 1

What a front end (TCC) can rely on in this copy of the method (skill #137). Contract 1 is the v3.1.x surface TCC
listed (its `docs/PLAN-AUDIT-2026-10.md` §9), written down. The number is `CONTRACT_VERSION` in `contract.py`.
`scripts/contract-guard.py` holds this file's title, the constant, the `IMPORTABLE` table and the probe of item 9;
`scripts/run-selftests.sh` runs it.

Each item says where it stands:

- **guaranteed**: true in this copy; changing it is a contract change (item 12);
- **planned (W-N, #issue)**: the wave and the issue that make it true; until then it is as today;
- **not promised** / **not built**: left out on purpose (`docs/PLAN-AUDIT-2026-10.md` §8 M6).

## 1. Identity — guaranteed

`CONTRACT_VERSION = 1` in `rew_tool/contract.py`, an int literal. Read it from any tag with `ast`
(`git show <tag>:skills/autosound-tuning/rew_tool/contract.py`), without running the file.

For diagnostics, `python3 rew_tool/contract.py version --json` prints
`{"contract_version": 1, "format_version": 3, "skill_version": "<plugin.json version>" | null, "sha": "<git sha>" | null}`
(without `--json`, the same on one line). It runs with the module's own imports, so it answers only where the method
loads. A method older than contract 1 has no `version` verb: it prints its usage and exits 2. Read that as contract 0.

## 2. `state/process.py <process-dir> <verb>` — planned (W-8, #134)

The verbs and their flags, the exit table (0 done or yes · 1 refused or no, the reason on stderr · 2 usage · 69 REW
unavailable, nothing written · 70 an unexpected error; 75 reserved for the lock), and the JSON of `show`, `plan` and
`handoff --json`. PLAN-W-8 Task 11 writes the table and flips this item.

## 3. `contract.py check <dir> [--json] [--no-rew] [--gate | --phase0-gate]` — planned (W-10)

Exit 0/1/2, every top-level key of `--json`, and a REW block that tells *skipped* from *unreachable* (audit T-2).
The keys TCC reads today: `ok`, `project_dir`, `files[]`, `cross_checks{rew, continue_head, glossary_vs_ledgers,
tiers_vs_profile}`, `inherited`, `sources_gone`, `complete`.

## 4. `deployment.py [<project>] [--json]` — not promised

TCC does not need it (§8 M6). It answers as `SKILL.md` documents, outside this contract.

## 5. `scripts/autosound_ai.py critic|advisor|ask|doctor|key` — guaranteed, as today

Exit 0 done · 1 error · 2 refused: a key file that git would take, or a key that was not stored · 3 a model must be
picked · 4 the reviewer refused or failed, and no review was filed. On stderr: `>> REVIEW_FILE: <rel>`,
`>> REVIEW_ROUTE: omp|api|cli`, `>> PACKAGE_FILE: <path>`. Reviews are written under `<project>/process/reviews/`.

## 6. `"contract": N` in every JSON output — not built

One handshake per copy is enough (item 1); TCC asked for no number per output (§8 M6).

## 7. Files, their versions, and the read rule — planned (W-8, #136)

Today `project.json`, `process/process-state.json`, the ledger's `v_NNN.json` and `dsp_profile.json` carry
`schema_version` 3 (`FORMAT_VERSION`); `glossary.json` carries 1; `process/journal.jsonl`, `state/slots.json` and
`state/seals.json` carry none. A ledger version, once written, is not rewritten.

The rule: a file newer than this copy reads is refused, and an older one gets the migration hint. PLAN-W-8 Task 8
flips this item.

## 8. How to write them — atomic writes planned (W-8, #135); the lock planned (W-9, J2b)

Atomic writes: every writer writes a temporary file with a name of its own, flushes and fsyncs it, then moves it over
the old one with `os.replace`. PLAN-W-8 Task 5 flips this half. The lock comes with J2b in W-9: which file, how long
a writer waits, and the busy exit 75.

## 9. The modules TCC imports — guaranteed (names); `sys.path` partly planned (W-10, J1b)

The names TCC reads from each module, with the parameters it passes, are the `IMPORTABLE` table in `contract.py`.
The guard holds every entry to the code. A removal or a rename fails it; a new trailing parameter with a default
does not.

Every module below loads by path from an empty folder with `PYTHONPATH` unset, and its lazy sibling loads raise no
`ImportError`: the guard's probe checks all of them. The column says whether that load also leaves `sys.path` as it
was:

| module | loads by path without touching `sys.path` |
|---|---|
| `rew_api.py` | guaranteed |
| `state/state.py` | guaranteed |
| `state/process.py` | guaranteed |
| `naming.py` | guaranteed |
| `dsp_profile.py` | guaranteed |
| `dsp_math.py` | guaranteed |
| `listening.py` | guaranteed |
| `gates/side_effect.py` | guaranteed |
| `car_profile.py` | guaranteed |
| `project.py` | W-10 (J1b) |
| `resonalyze_vc.py` | W-10 (J1b) |
| `project_seed.py` | W-10 (J1b) |
| `eq_export.py` | W-10 (J1b) |
| `protective.py` | W-10 (J1b) |
| `verify.py` | W-10 (J1b) |

The guaranteed rows are the guard's `CLEAN` set. The other six put `rew_tool/` on `sys.path` when they load. A call
can still load a sibling that edits `sys.path`: `Process.enter_phase` loads `contract.py`, and `rew_api.get_timing`
loads `timebase.py`. From J1b (W-10), no module TCC imports, and no module those load, edits `sys.path` at import or
at call time.

TCC also compares values that no name pins: naming's method tags `"sw"` and `"rta"`, rew_api's measurement kinds
`"sweep"`, `"rta"` and `"impedance"`, and the journal's event names and fields. The shapes of returned values (the
keys of `verify.verdict`, the result of `resonalyze_vc.convert` or `eq_export.export_eq`) are written down in J1b
(W-10).

## 10. Environment variables — planned (W-10)

Each variable listed, with its precedence over an explicit argument written down and left as it is (J1b). Known
today: `AUTOSOUND_PROJECT_DIR`, `AUTOSOUND_STATE_ROOT`, `AUTOSOUND_SKILL_ROOT`, `REW_API_URL`, `AUTOSOUND_NO_GH`,
`AUTOSOUND_KEYSTORE`, `AUTOSOUND_CRITIC_*`, and `AUTOSOUND_SKIP_TAG_VERIFY` (for developers only).

## 11. REW write semantics — planned (W-8, #134)

What `set_filters`, `set_filter` and `rename_measurement` guarantee once they return: REW is read back and the write
is verified (audit K-1). PLAN-W-8 Task 9 flips this item.

## 12. Compatibility — guaranteed

- An addition keeps the number: a new verb, flag, key or exit code, a new exception that subclasses the old type,
  strictness a caller opts into, a new trailing parameter with a default, a usage error for a flag a correct caller
  never sends.
- A breaking change to a guaranteed item moves `CONTRACT_VERSION`. It happens only in a minor (a `### Breaking`
  entry, which the release preflight refuses on a patch), and only after a TCC release that accepts the new number
  is out (§8 M5).
- Every change to an item is named in the CHANGELOG's `### Upgrading` note, with a line for TCC.
