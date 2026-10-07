# Contract 1

What a front end (TCC) can rely on in this copy of the method (skill #137). Contract 1 is the v3.1.x surface TCC
listed (its `docs/PLAN-AUDIT-2026-10.md` §9), written down. The number is `CONTRACT_VERSION` in `contract.py`.
`scripts/contract-guard.py` holds this file's title, the constant, the `IMPORTABLE` table (and contract 1's table,
frozen) and the probe of item 9; `scripts/run-selftests.sh` runs it.

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

Before any verb runs, the script exits 2 when a project's `.critic-env` carries a key and git would take it (the file
is tracked, or not ignored). It exits 1 when `--via`, `--model`, `--provider` or `AUTOSOUND_CRITIC_VIA` is not
valid, when no verb is given, or when the verb is unknown. Then each verb answers:

| verb | exit codes |
|---|---|
| `critic`, `advisor`, `ask <package> [<trace>]` | 0 a review came back and was filed, or the clipboard route made the package · 1 an input is missing: the package, or for `critic` and `advisor` the contract or the project context · 3 a model must be picked · 4 the reviewer refused or failed, and no review was filed |
| `doctor` | 0 every check passed · 1 a check failed |
| `key set <provider>` | 0 stored · 2 refused: an unknown provider, wrong arguments, or a value that is not a key |
| `key status [--json]`, `key rm <provider>` | 0 |
| `key move-shell [<provider>] [--drop] [--yes]` | 0 something moved or removed, and nothing refused · 1 nothing to do · 3 something refused or failed · 2 usage |
| `key` with anything else | 2 usage |

On stderr: `>> REVIEW_FILE: <rel>`, `>> REVIEW_ROUTE: omp|api|cli`, `>> PACKAGE_FILE: <path>`. Reviews are written
under `<project>/process/reviews/`.

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
The guard holds every entry to the code: each listed parameter keeps its name, its place, its kind (positional or
keyword) and its default value. These fail the guard: a removal, a rename, a default removed or changed, a
parameter made keyword-only or positional-only. These pass: a new trailing parameter with a default, and a
keyword-only parameter widened to positional-or-keyword. Each name also stays the kind of thing it is: one listed
without parentheses stays a value (an assignment, a class, an attribute `__init__` sets) and never becomes a function;
one listed with them stays a plain function (not async, not a property) or a class.

The table of contract 1 is frozen in the guard: `FROZEN[1]` in `scripts/contract-guard.py`, generated once from
`IMPORTABLE` as committed in dd4312d. While `CONTRACT_VERSION` is 1, every module of that table stays in `IMPORTABLE`,
and every name in it holds against the code by the rules above, whatever `IMPORTABLE` says now. `IMPORTABLE` may grow
(a name, a module, a trailing parameter with a default); a rename or a removal fails the guard even when `IMPORTABLE`
is edited with it.

The guard's probe loads every module below by path, in a fresh python started in an empty folder with `PYTHONPATH`
unset. For two of them it also calls the function that reaches their lazy sibling loads
(`dsp_profile.annotate_modellable`, with one crossover family so that its loop runs, and `rew_api.get_timing`), and
that call must raise no `ImportError`. It also reads the code of the guaranteed modules: no function of theirs imports
a sibling by its bare name, which fails when the module is loaded by path, except the command lines the guard names
(`CLI_IMPORTS`); and no module of the method calls `_siblings()` at import. The column says whether the load also
leaves `sys.path` as it was; the guard holds this column equal to its `CLEAN` set:

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
today, every one the code reads:

- the project: `AUTOSOUND_PROJECT_DIR`, `AUTOSOUND_STATE_ROOT`, `AUTOSOUND_SKILL_ROOT` (the copy a front end
  declares), `AUTOSOUND_NO_GH`;
- REW: `REW_API_URL`;
- the reviewer (`scripts/autosound_ai.py`; `issue_triage.py` for the advisor's model): `AUTOSOUND_DIR`,
  `AUTOSOUND_KEYSTORE`, `AUTOSOUND_CRITIC_MODEL`, `AUTOSOUND_CRITIC_PROVIDER`, `AUTOSOUND_CRITIC_VIA`,
  `AUTOSOUND_CRITIC_BIN`, `AUTOSOUND_CRITIC_CLI_ARGS`, `AUTOSOUND_CRITIC_EFFORT`, `AUTOSOUND_ADVISOR_MODEL`,
  `AUTOSOUND_API_TIMEOUT`, `AUTOSOUND_CLI_TIMEOUT`, `AUTOSOUND_REVIEW_RAW_DIR`, `AUTOSOUND_ALLOW_NESTED_CLI`; it
  also reads the vendors' own (`GEMINI_*`, the providers' API keys);
- the Resonalyze engine: `AUTOSOUND_RESONALYZE_ENGINE`;
- for developers only: `AUTOSOUND_SKIP_TAG_VERIFY` (the installers), `AUTOSOUND_UPSTREAM_CLONE`
  (`scripts/upstream-drift.py`), `AUTOSOUND_PASSAT_IR_SET` and `AUTOSOUND_PASSAT_PROJECT` (the Resonalyze
  engine's acceptance run).

## 11. REW write semantics — planned (W-8, #134)

What `set_filters`, `set_filter` and `rename_measurement` guarantee once they return: REW is read back and the write
is verified (audit K-1). PLAN-W-8 Task 9 flips this item.

## 12. Compatibility — guaranteed

- An addition keeps the number: a new verb, flag, key or exit code, a new exception that subclasses the old type,
  strictness a caller opts into, a new trailing parameter with a default, a usage error for a flag a correct caller
  never sends.
- A breaking change to a guaranteed item moves `CONTRACT_VERSION`. For a listed name that is: removing or renaming
  it, or a parameter TCC passes removed, renamed, made keyword-only or positional-only, or its default removed or
  given another value. It happens only in a minor (a `### Breaking` entry, which the release preflight refuses on a
  patch), and only after a TCC release that accepts the new number is out (§8 M5).
- A bump to N+1 moves `CONTRACT_VERSION` and this file's title, and adds the table of contract N+1 to the guard's
  `FROZEN`, generated from the bump's `IMPORTABLE` in the same commit; the table of contract N stays as it was. The
  guard holds the frozen table of the number the literal names.
- Every change to an item is named in the CHANGELOG's `### Upgrading` note, with a line for TCC.
