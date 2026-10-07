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
loads. A method older than contract 1 has no `version` verb: it exits 2, prints nothing on stdout, and its usage on
stderr begins `usage: contract.py` (v3.0.0, v3.0.40 and v3.1.1 answer so). Read that as contract 0. Python exits 2
too when the path is wrong, with `can't open file` on stderr: the usage line is what tells the two apart.

## 2. `state/process.py <process-dir> <verb>` — guaranteed (W-8, #134)

**The exit table**, for every verb:

| exit | means |
|---|---|
| 0 | done, or yes |
| 1 | refused, or no: the reason on stderr, `error: <reason>`; REW answering something the method cannot read, `error: <REW's words> -- nothing was written`; REW answering with an error, `error: REW answered with an error: <REW's words> -- nothing was written` |
| 2 | usage: an unknown verb (the usage on stderr), a flag the verb does not take, a flag's value missing (one of the verb's flags, `-h` or `--help` in its place, or nothing after it: a value flag left last), `=` on a flag that takes no value, one of the verb's flags with its hyphens autocorrected to a dash, `--help` or `-h` after other arguments, too few arguments |
| 69 | REW did not answer, and nothing was written |
| 70 | an unexpected error, a bug: Python's traceback on stderr, then `error: unexpected <type>: <message>` |
| 75 | the project busy: reserved for the lock (W-9, J2b), not raised yet |

Four verbs answer with their exit code, their report on stdout: `session-close` (1 while a round or a step is open),
`capture-check` (1 while a capture of the open round is unusable), `check` (1 while a done step has no evidence that
resolves) and `handoff` (1 while the next session would miss something), as `state/process-schema.md` says.

**The verbs and their flags** are `VERB_FLAGS` in `process.py`, one string literal per flag:

| verb | flags |
|---|---|
| `add-step` | `--project`, `--covers` |
| `skip` | `--superseded-by` |
| `reviewer` | `--review`, `--mode` |
| `decision` | `--invalidates` |
| `session-close` | `--check` |
| `capture-start` | `--origin`, `--step`, `--under`, `--level`, `--level-read-as`, `--start`, `--phase`, `--optional`, `--plan` |
| `capture-check` | `--session` |
| `capture-import` | `--bind`, `--late`, `--knob` |
| `amp-gain` | `--measured`, `--amends`, `--note` |
| `capture-knobs` | `--amend`, `--reason` |
| `capture-protective` | `--source`, `--amend`, `--reason`, `--hp`, `--lp` |
| `listening-verdict` | `--pair`, `--text`, `--route`, `--ledger-version`, `--note` |
| `listening-verdicts` | `--track`, `--characteristic`, `--ledger-version`, `--bank` |
| `handoff` | `--json` |
| `capture-close` | `--no-rew` |

`show`, `plan`, `enter-phase`, `start`, `done`, `block`, `target`, `session-start`, `session-reopen`,
`capture-taken`, `amp-changes`, `capture-supersede`, `capture-skip` and `check` take none. A flag is `--`, an ASCII
letter and no whitespace -- after an `=`, whitespace is the value's only when the name before it is one of the
verb's flags (`--invalidates=w-L_1 (sw)`); any other token is a word -- a bare `--`, a negative number, and text that
only begins with two dashes (`--бас гуде`, `--bass hums`, `--bass=45 Hz hums?`). A flag the verb does not take is a
usage error, exit 2, and the verb does not run; its words never contain `usage: process.py`. So is, where a flag
stands, one of the verb's flags with its two hyphens autocorrected to a dash: a word that starts with an em or an en
dash and names that flag past its dashes (`—origin`, `–origin=other:49`), said as `<verb>: —origin looks like
--origin with its dashes autocorrected; type two hyphens`. `--flag value` and `--flag=value` are one:
the value is taken as it stands, whatever it looks like (`--text --loud`, `--text=--loud`), with one exception in
both forms -- a value that is one of the verb's own flags, `-h` and `--help` among them (`--note --measured`,
`--note=--measured`, `--text=-h`; the name before any `=` counts), is no value: the value is missing, exit 2. So is
a flag that takes a value and stands last, with nothing after it -- refused before the verb runs -- except
capture-protective's legs `--hp` and `--lp`, which the verb parses: `--hp needs three values` (a flag among them
too), `--hp: 'abc' is not a number`, `--hp: '24.5' is not a whole number`, exit 1; their values are not the verb's
arguments, so legs with no channel are too few. A series `capture-import` cannot read as a number is exit 1 too,
before REW is asked. `--project`,
`--check`, `--plan`, `--session`, `--measured`, `--bank`, `--json` and `--no-rew` take no value and no `=`. A verb needs the arguments its line in the usage names in `<...>` (`_VERB_ARGS` in `process.py`; `skip` needs
its `<id>`, then a reason or `--superseded-by`); fewer is a usage error, exit 2, naming them. `<verb> --help` (or
`-h`), right after the verb, prints that verb's lines and exits 0, reading and writing nothing; after other
arguments either is a usage error, exit 2. `process.py --help` prints the whole usage on stdout. A verb or a flag
added later is an addition (item 12); removing or renaming one is a contract change.

**The JSON:** `show` prints `process-state.json` as `state/process-schema.md` describes it (a round's `checks` among
its keys); `plan [phase]` a list of the plan's steps; `handoff --json` `{ok, missing, phase, resume, warnings,
next_message}`, with the same keys when the state cannot be read (`ok` false, the file and its repair in `missing`).

## 3. `contract.py check <dir> [--json] [--no-rew] [--gate | --phase0-gate]` — planned (W-10)

Exit 0/1/2, every top-level key of `--json`, and a REW block that tells *skipped* from *unreachable* (audit T-2).
The keys TCC reads today: `ok`, `project_dir`, `files[]`, `cross_checks{rew, continue_head, glossary_vs_ledgers,
tiers_vs_profile}`, `inherited`, `sources_gone`, `complete`.

## 4. `deployment.py [<project>] [--json]` — not promised

TCC does not need it (§8 M6). It answers as `SKILL.md` documents, outside this contract.

## 5. `scripts/autosound_ai.py critic|advisor|ask|doctor|key` — guaranteed, as today

Before any verb runs, the script exits 2 when a project's `.critic-env` carries a key and git would take it (the file
is tracked, or not ignored). It exits 1 when `--via`, `--model` or `--provider` is not valid, when
`AUTOSOUND_CRITIC_VIA` is not valid and the run names no route of its own (`--via` or `--mode`), when no verb is
given, or when the verb is unknown. Any verb also exits 1 on an exception the script does not catch, with Python's
traceback on stderr. Then each verb answers:

| verb | exit codes |
|---|---|
| `critic`, `advisor`, `ask <package> [<trace>]` | 0 a review came back, or the clipboard route made the package · 1 an input is missing: the package, or for `critic` and `advisor` the contract or the project context · 3 a model must be picked · 4 the reviewer refused or failed, and no review was filed |
| `doctor` | 0 every check passed · 1 a check failed |
| `key set <provider>` | 0 stored · 2 refused: an unknown provider, wrong arguments, or a value that is not a key |
| `key status [--json]`, `key rm <provider>` | 0 |
| `key move-shell [<provider>] [--drop] [--yes]` | 0 something moved or removed, and nothing refused · 1 nothing to do: no export found, or every export found kept at the prompt (declined; a closed stdin ends in an uncaught `EOFError`, exit 1 as well) · 3 something refused or failed · 2 usage |
| `key` with anything else | 2 usage |

A 0 from `critic`, `advisor` or `ask` does not say the review was filed: `>> REVIEW_FILE: <rel>` on stderr does.
Outside a project, or when the file cannot be written, the review is printed and not filed, and the exit is still 0.
On stderr: `>> REVIEW_FILE: <rel>`, `>> REVIEW_ROUTE: omp|api|cli`, `>> PACKAGE_FILE: <path>`. Reviews are written
under `<project>/process/reviews/`.

`key move-shell`'s "no export found" is a stdout line that ends `у профілях оболонки не знайдено`:
`· <VAR> у профілях оболонки не знайдено` with a provider, `· ключів у профілях оболонки не знайдено` without one
(`autosound_ai.py`, `move_shell_run`). TCC tells "nothing to remove" from the other exits 1 by that sentence (tcc
`core/reviewer_key.py`, `_NOTHING_FOUND`), so it stays as it is, like `capture-check`'s Ukrainian lines.

## 6. `"contract": N` in every JSON output — not built

One handshake per copy is enough (item 1); TCC asked for no number per output (§8 M6).

## 7. Files, their versions, and the read rule — guaranteed (W-8, #136)

`project.json`, `process/process-state.json`, the ledger's `v_NNN.json` and `dsp_profile.json` carry
`schema_version` 3 (`FORMAT_VERSION`); `glossary.json` carries 1; `process/journal.jsonl`, `state/slots.json` and
`state/seals.json` carry none. A ledger version, once written, is not rewritten.

**A file a newer method wrote** (an int `schema_version` above 3) is refused, naming the file, both numbers and the
way out: `<file> is schema v4; this method reads v3 -- update the method: /autosound-tuning:setup, the installer, or
TCC's «Оновити Скіл»`. Nothing is written.

- On read: `Process.load(strict=True)` raises `ProcessError`, so every `process.py` verb but the three display-only
  ones refuses such a state. A ledger version raises `SnapshotError` wherever it is read (`PresetHistory.load`,
  `verify`, ...). `dsp_profile.load_profile` raises an exception with `is_unreadable` (below), and through it the
  draft, `set-setting`, `refresh` and the phase-1 and phase-2 profile gate refuse too. Leaving phase −1 does not
  refuse such a profile yet (below).
- On write: `Project.save` (`ProjectError`) and `dsp_profile.save_profile` (`ValueError`) refuse data a newer method
  wrote before they stamp v3 over it, and so does `state/migrate.py`'s import into a folder whose `project.json` a
  newer method wrote (`ProjectError`, in `Project.save`'s words); `process.py`'s `_write` and `_append` refuse beside
  a state a newer method wrote since the writer read it.
- Left as they were: `Process.load()` (lenient) and `Project.load()` return such a file as it is (`project.py`'s
  `validate` calls it unsupported, and `contract.py check` reports every one of the four as not valid).

An older file gets the migration hint where it got one before (`project.json`'s and `process-state.json`'s
`validate`, a ledger row carrying identity fields); a check per file for older versions, the glossary's included, is
planned (W-11, J3b).

**The read rule: a file that is there and cannot be read is refused, never read as absent.** Empty, cut off, not
UTF-8, not JSON, the wrong top-level type, a folder in its place or a file that cannot be opened raises an exception
with `is_unreadable` (`project_io.Unreadable`, with `.path`, `.reason`, `.repair`; neither an `OSError` nor a
`ValueError`, so match the attribute, never the class), naming the file and its repair, and nothing is written. No
file at all is the one quiet case: a fresh project. It holds for:

- `process/process-state.json`: every `process.py` verb but `plan`, `amp-changes` and `listening-verdicts`, every
  writer method, `handoff()` and `contract.py check` (`state/process-schema.md` has it in full);
- `state/seals.json`: `state.py verify` and `seal` (exit 1), a bank (`PresetHistory.snapshot`: nothing banked) and
  `repair-version`;
- `project.json`, where a bank stamps its `project_rev` and where the phase-1 gate reads the flaw map;
- `dsp_profile.json` and `dsp_profile.draft.json`: `load_profile`, `load_draft` and every writer that reads through
  them (`set-field`, `reset-field`, `start`, `finalize`, `set-setting`, `refresh`), and the phase-1 and phase-2
  profile gate. The intake's processor change, which replaces the profile, sets such a file aside unread and byte for
  byte, with one line on stderr saying where; the intake form's page shows it with its repair.

Each phase gate refuses what it cannot check. Leaving phase −1: an intake check that raises or cannot be loaded.
Leaving phase 0: a `project.json` that cannot be read, where the flaw-map gate reads the map. Into phases 1 and 2: a
`dsp_profile.json` that cannot be read or that a newer method wrote, and a profile check that cannot be loaded.
Leaving −1 still gates on missing files only, so `enter-phase 0` passes over a `dsp_profile.json` that is there and
cannot be read, or a newer one, where `contract.py check --gate` says NOT READY; gating it on the profile's
readability, with that parity, waits for J3b (W-11). `contract.py check` reports such a file (`exists: true`,
`valid: false`, the refusal in `issues`) instead of failing.

## 8. How to write them — atomic writes guaranteed (W-8, #135); the lock planned (W-9, J2b)

Atomic writes: a writer that replaces one of the files below writes a temporary file beside it under a name of its
own (`<file>.<pid>-<8 hex>.tmp`, created exclusively), flushes and fsyncs it, then moves it over the file with one
`os.replace`. That writer is `rew_tool/project_io.py` (`atomic_write_text`, `atomic_write_json`,
`atomic_write_bytes`). A reader sees the old file or the new one, never part of either, and two writers never share a
temp file. On POSIX a private file (the reviewer's machine file, 0600) is private from its first byte: its temp is
created with that mode (Windows ignores the mode). The files, each with the bytes its old writer wrote:

- `project.json`, `process/process-state.json`, `state/slots.json`, `state/seals.json`;
- `dsp_profile.json` and `dsp_profile.draft.json`;
- the old (per-preset) layout's `registry.json` and `HEAD`;
- a ledger version `state.py repair-version` or `repair-encoding` rewrites, and the `<file>.<codec>.orig` backup
  `repair-encoding` keeps (any project text file it repairs, the same way);
- the ledger version `state/migrate.py --into` imports;
- the Resonalyze impulse-response files (`resonalyze_ir.write_v7`);
- the reviewer's machine file and key store, and a shell profile `autosound_ai.py key move-shell` rewrites, with its
  `.autosound-bak`.

On Windows a move refused because a process holds the file open is retried for under a second (0.75 s), then raised,
with the old file whole. A `*.tmp` beside a file is a crash's leftover, never a file to read; a new project's
`.gitignore` ignores it. `scripts/atomic-write-check.py` holds this: outside `project_io.py`, no `.tmp` literal but
two it names (neither is a temp name), and no `os.replace`, `os.rename` or `os.renames` but three named moves of whole
files.

Three of these files, by four writers, were written in place before W-8 and are replaced now: `dsp_profile.json`
(`save_profile`, `set_setting`) and the old layout's `registry.json` and `HEAD`. So a symbolic or hard link at such a
name becomes a regular file, the file's mode becomes the umask's default, a watcher sees the file replaced rather than
changed, and on Windows a reader holding the file open makes the write fail after the retries, where the in-place
write went through.

Two more writes go through `project_io.py`; neither replaces a file:

- A new ledger version (`state.py`, `PresetHistory.snapshot`) is created, never written over (`create_exclusive`),
  with the bytes its old writer wrote. Its text goes into a temp of its own as above, which is then linked to the
  version's name; the link fails when the name is there. The temp is removed afterwards, best effort: one a remove
  could not take (a Windows scanner holding it) stays as a `*.tmp` beside the version, a second link to it (a copy
  where hard links are refused) that no lister reads. Two writers that pick one number cannot overwrite each other:
  the second is told and takes the next number, and after 100 numbers taken under it gives up with `SnapshotError`,
  naming the numbers it tried. A watcher of the versions folder sees the temp come and go and the version appear
  whole. On a filesystem that refuses hard links (FAT, some network shares) the name is created exclusively and
  written in place, so there a reader can meet a version mid-write for an instant.
- A line appended to `process/journal.jsonl` (`append_line`) has the old append's bytes, with one line ending before
  it when the file's last write was cut before its newline: the torn line stays one line a reader skips, and the
  event after it is read. That holds for a write cut inside a multi-byte character too: the method's readers decode
  the journal line by line, so a line that is not UTF-8 is skipped like one that is not JSON, and the survey of
  `repair-encoding` reads a `.jsonl` line by line and does not count a line that stops inside its last character as
  a wrong code page. The append itself is a plain one: text mode, the platform's line ending, no lock.

Every other write is still a plain one, in place. Among them: `state/apply.py`'s proposal deltas and sheets; the
capture plans in `docs/plans/`; the review files in `process/reviews/` (each created under a name of its own since
#135, `-2`, `-3`, ... when its second already holds one, so never over another file, but written in place); what
`state.py migrate-line` rebuilds, and the `HEAD` that `migrate.py --into` writes; a fresh project's `CLAUDE.md` and
`.gitignore`; and what the command lines export (`eq_export`, `sums_export`, the Resonalyze conversion's
`manifest.json`, ...). `scripts/atomic-write-check.py` does not see these: it checks temp names and moves, not every
write. The lock comes with J2b in W-9: which file, how long a writer waits, and the busy exit 75.

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
  `AUTOSOUND_API_TIMEOUT`, `AUTOSOUND_CLI_TIMEOUT`, `AUTOSOUND_REVIEW_RAW_DIR`, `AUTOSOUND_ALLOW_NESTED_CLI`, and two
  without the prefix: `PROJECT_MIRROR` (the folder the reviewer looks in first for the project's contract, context
  and `.critic-env`; `rew_analitic/` in the current folder by default) and `ADVISOR_MEMORY` (the reviewer's memory
  file; `depth-advisor-memory.md` in that folder by default). It also reads the vendors' own: `GEMINI_*`, the
  providers' API keys, agy's `AGY_ADC_AUTH` with Google's `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`
  and `GOOGLE_CLOUD_QUOTA_PROJECT`, and the markers of an agent session it runs in (`CLAUDECODE`,
  `CLAUDE_CODE_ENTRYPOINT`, `ANTIGRAVITY`, `AGY_*`, `GEMINI_SESSION`);
- the Resonalyze engine: `AUTOSOUND_RESONALYZE_ENGINE`;
- for developers only: `AUTOSOUND_SKIP_TAG_VERIFY` (the installers), `AUTOSOUND_UPSTREAM_CLONE`
  (`scripts/upstream-drift.py`), `AUTOSOUND_PASSAT_IR_SET` and `AUTOSOUND_PASSAT_PROJECT` (the Resonalyze
  engine's acceptance run), `SMOKE_VERBOSE` (`scripts/smoke_test.py`), the selftest runner's `SELFTEST_TIMEOUT`,
  `SELFTEST_TOOL`, `SELFTEST_MANIFEST` and `SELFTEST_ONLY_TOOL`, `PYTHON` (the interpreter `scripts/run-selftests.sh`
  and `scripts/tag-check.sh` run), `PREFLIGHT` (`scripts/tag-check.sh`'s path to the hub's release preflight) and
  `CHROME` (the browser `scripts/xss-proof-visualizer.mjs` drives).

Beyond these, the code reads only the system's and Python's own (`PATH`, `HOME`, `SHELL`, `APPDATA`,
`LOCALAPPDATA`, `ProgramFiles`, `XDG_*`, `EDITOR`, `VISUAL`, `no_proxy`, `PYTHONPATH`, ...), a CI's `CI`
(`scripts/run-selftests.sh`), uv's `UV_TOOL_BIN_DIR` (where `install.sh` also looks for TCC), and Claude Code's
`CLAUDE_PLUGIN_ROOT` (the plugin's session hook).

## 11. REW write semantics — the filter writes guaranteed (W-8, #134); a rename's read-back not built

`set_filters` and `set_filter` refuse with a `ValueError`, before any request, a filter that is not a dict, a filter
carrying any key but the ones REW takes (`index`, `type`, `enabled`, `isAuto`, `frequency`, `gaindB`, `q`, `shape`,
`slopedBPerOctave`), and a write that names one slot twice. REW drops a key it does not know without a word: it
answers 200 and stores a `gain` filter flat, at 0 dB (audit K-1). The refusal names the key and, where one is known,
REW's spelling of it. Once they return, the filters have been read back from REW: every written slot is there, with
its `type` and `enabled` (and a crossover's `shape` and `slopedBPerOctave`), and its `frequency`, `gaindB` and `q`
within `rew_api._READBACK_TOL`; a slot written `"None"` is checked for its type only. A difference raises
`RewWriteMismatch` (`rew_state` `"write_mismatch"`, a `ValueError`), and a read-back in another shape than REW's
raises `RewProtocolError` (`"protocol"`). Both were measured at the live pass at REW (PLAN-W-8 Task 12, 2026-10-07;
REW's answers in `rew_tool/testdata/rew/`): REW answers the read with a list of every slot, each carrying its
`index` (`filters-after-pk.json`), and the tolerance comes from REW's grid (`grid.json`) -- a value REW snapped
passes, a value REW clamped to the equaliser's range does not.

`rename_measurement` is not read back: it returns REW's answer, as before.

The exceptions `rew_api` raises for REW carry `rew_state`, and these five values are what a front end may match:
`"unavailable"` (REW did not answer, or dropped its answer midway: `RewUnavailable`, a `URLError`), `"protocol"` (REW
answered something that cannot be read: `RewProtocolError`, a `ValueError`), `"write_mismatch"` (above),
`"not_found"` and `"ambiguous"` (`find_measurement_id` found no measurement, or two, under a title:
`MeasurementNotFound` and `AmbiguousTitle`, `KeyError`s with the words they always had). REW answering with an error
is an `HTTPError`, with no `rew_state`. Match the value (`rew_api.rew_state(exc)`, or the attribute on the exception's
class), never the class: the copy a front end loads by path and the method's own raise different classes.

## 12. Compatibility — guaranteed

- An addition keeps the number: a new verb, flag, key or exit code, a new exception that subclasses the old type,
  strictness a caller opts into, a new trailing parameter with a default, a usage error for a flag a correct caller
  never sends.
- A breaking change to a guaranteed item moves `CONTRACT_VERSION`. For a listed name that is: removing or renaming
  it; making it another kind of thing (a value made a function, a function made async or a property); or a
  parameter TCC passes removed, renamed, made keyword-only or positional-only, or its default removed or given
  another value. It happens only in a minor (a `### Breaking` entry, which the release preflight refuses on a
  patch), and only after a TCC release that accepts the new number is out (§8 M5).
- A bump to N+1 moves `CONTRACT_VERSION` and this file's title, and adds the table of contract N+1 to the guard's
  `FROZEN`, generated from the bump's `IMPORTABLE` in the same commit; the table of contract N stays as it was. The
  guard holds the frozen table of the number the literal names, and fails while that number has none.
- Every change to an item is named in the CHANGELOG's `### Upgrading` note, with a line for TCC.
