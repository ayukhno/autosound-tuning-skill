# Contract 1

What a front end (TCC) can rely on in this copy of the method (skill #137). Contract 1 is the v3.1.x surface TCC
listed (its `docs/PLAN-AUDIT-2026-10.md` §9), written down. The number is `CONTRACT_VERSION` in `contract.py`.
`scripts/contract-guard.py` holds this file's title, the constant, the `IMPORTABLE` table (and contract 1's table,
frozen and pinned by its digest) and the probe of item 9; `scripts/run-selftests.sh` runs it.

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
| 1 | refused, or no: the reason on stderr, `error: <reason>`; REW answering with an error, `error: REW answered with an error: <REW's words> -- nothing was written`; any other state REW's exceptions name but "unavailable" (`protocol`, `write_mismatch`, `not_found`, `ambiguous`, `config`), read off the class, `error: <its words> -- nothing was written`, except that a `write_mismatch` ends `-- REW may hold part of the write: check REW's EQ before going on` and a filter write REW acknowledged and nobody could read back (`rew_unchecked` on its class) is said in its own words alone; `capture-check` when REW's measurement list was not read and REW did not stay silent -- it answered with an error or with something the method cannot read, or it was not asked, its address being none -- `error: REW's measurement list was not read (<why>) -- nothing was recorded`; the project's writer lock that cannot be made, a process folder that is no project's, a round another writer closed or replaced under `capture-close` or `capture-check`, and a phase another writer entered under `enter-phase` (W-9, #141; item 8) |
| 2 | usage: an unknown verb (the usage on stderr), a flag the verb does not take, a flag's value missing (one of the verb's flags, `-h` or `--help` in its place, or nothing after it: a value flag left last), `=` on a flag that takes no value, one of the verb's flags with its hyphens autocorrected to a dash, `--help` or `-h` after other arguments, too few arguments; an `AUTOSOUND_LOCK_TIMEOUT_S` that is no number of seconds (item 8) |
| 69 | REW did not answer, and nothing was written -- but a filter write REW acknowledged before it stopped answering (`rew_unchecked` on its class), said in its own words: sent, acknowledged, not checked |
| 70 | an unexpected error, a bug: Python's traceback on stderr, then `error: unexpected <type>: <message>` |
| 75 | the project busy (W-9, #141): another writer held the project's writer lock past the wait (item 8), and one line on stderr says so, `busy: <the lock file> is held by another writer -- nothing was written, safe to retry` -- but `capture-close` stopped at its second or third hold, after its reconcile landed: its own `busy:` line names what landed and what did not, and that a retry is safe. For that verb past its first hold, the "nothing was written" agreed with TCC (hub #254) does not hold |

Four verbs answer with their exit code, their report on stdout: `session-close` (1 while a round or a step is open),
`capture-check` (1 while a capture of the open round is unusable), `check` (1 while a done step has no evidence that
resolves) and `handoff` (1 while the next session would miss something), as `state/process-schema.md` says.

A state write that owes two journal lines (#141, F M-7) -- `capture-start` over an open round owes the old round's
`capture_round_closed`, then the new round's `capture_task_issued` -- and cannot append the first says both, in order:
`error: <state> is written, but its journal lines are not: <why>. ... append these lines to <journal>, in order:`,
then each line, raw JSON, on a line of its own. That refusal ends in a bare event: a front end that shows only the
last line of stderr shows that line.

`capture-start` says its plan file (S-101): `plan: <the file, its absolute path>` as the last line on stdout once the
file is written, else one line on stderr, `note: the round is open, but its plan <path> could not be written (<why>)
-- process.py <dir> show holds its list`; exit 0 either way, the round open.

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
letter and no whitespace -- after an `=`, whitespace is the value's only when the name before it is one of the verb's
flags (`--invalidates=w-L_1 (sw)`); any other token is a word -- a bare `--`, a negative number, and text that only
begins with two dashes (`--бас гуде`, `--bass hums`, `--bass=45 Hz hums?`). A flag the verb does not take is a usage
error, exit 2, and the verb does not run; its words never contain `usage: process.py`. So is, where a flag stands,
one of the verb's flags with its two hyphens autocorrected to a dash: a word that starts with an em or an en dash and
names that flag past its dashes (`—origin`, `–origin=other:49`), said as `<verb>: —origin looks like --origin with
its dashes autocorrected; type two hyphens`. `--flag value` and `--flag=value` are one: the value is taken as it
stands, whatever it looks like (`--text --loud`, `--text=--loud`), with one exception in both forms -- a value that
is one of the verb's own flags, `-h` and `--help` among them (`--note --measured`, `--note=--measured`, `--text=-h`;
the name before any `=` counts), is no value: the value is missing, exit 2. So is a flag that takes a value and
stands last, with nothing after it -- refused before the verb runs -- except capture-protective's legs `--hp` and
`--lp`, which the verb parses: `--hp needs three values` (a flag among them too), `--hp: 'abc' is not a number`,
`--hp: '24.5' is not a whole number`, a frequency or a slope not above 0, a type other than LR, BW, BE or CH (any
letter case), exit 1; their values are not the verb's arguments, so legs with no channel are too few. A series
`capture-import` cannot read as a number is exit 1 too, before REW is asked; with no titles, REW holding nothing of
the series is exit 1, and every title of it on record already is exit 0, `nothing new`. `--project`, `--check`,
`--plan`, `--session`, `--measured`, `--bank`, `--json` and `--no-rew` take no value and no `=`. A verb needs the
arguments its line in the usage names in `<...>` (`_VERB_ARGS` in `process.py`); fewer is a usage error, exit 2,
naming them -- but `skip <id>` with neither a reason nor `--superseded-by`, which `skip` refuses itself, exit 1
(either one completes its line). `<verb> --help` (or `-h`), right after the verb, prints that verb's lines and exits
0, reading and writing nothing; after other arguments either is a usage error, exit 2. `process.py --help` prints the
whole usage on stdout. A verb or a flag added later is an addition (item 12); removing or renaming one is a contract
change.

**The JSON:** `show` prints `process-state.json` as `state/process-schema.md` describes it (a round's `checks` among
its keys); `plan [phase]` a list of the plan's steps; `handoff --json` `{ok, missing, phase, resume, warnings,
next_message}`, with the same keys when the state cannot be read (`ok` false, the file and its repair in `missing`).
A state a newer method wrote is answered on stderr alone, `error: <file> is schema v4; ...`, exit 1, nothing on
stdout: an empty stdout, which a front end reads as "update the method", which is the answer.

## 3. `contract.py check <dir> [--json] [--no-rew] [--gate | --phase0-gate]` — planned (W-10)

Exit 0/1/2, every top-level key of `--json`, and a REW block that tells *skipped* from *unreachable* (audit T-2).
The keys TCC reads today: `ok`, `project_dir`, `files[]`, `cross_checks{rew, continue_head, glossary_vs_ledgers,
tiers_vs_profile}`, `inherited`, `sources_gone`, `complete`. As built today (#134), the REW block reads the state off
the exception's class into `state`: REW down is `reachable: false`; REW answering its list with an error or with
something that is no measurement list is `reachable: true`, the list not read; an address that is none (`config`),
or a failure that is none of REW's, is `reachable: null`, its note starting `skipped:` as `--no-rew`'s does.
`unreadable` names a `project.json`, a standalone `glossary.json`, `state/slots.json` or an old layout's
`state/<preset>/HEAD` that is there and cannot be read, which both gates' last lines name first (the file's row is
then there and not valid, with its repair), and over which both gates exit 1 (#134: `--phase0-gate` exited 0 under
that line). Over a `project.json` that cannot be read and no
standalone `glossary.json`, the glossary is kept in the file nobody could read: it is not in `missing`, and its row
says it was not read. A `glossary.json` with a UTF-8 BOM is a glossary. `encoding_unread` names the files the encoding
survey could not open; `encoding_cut` (`[{file, repair}]`) the files it found cut inside their last character, each
with its restore -- no code page's, so never in `encoding_damaged`. `lock` (W-9, #141) is one line when the project's
writer lock cannot be taken in its folder -- the OS refuses the lock itself, and the writers write there without it
(item 8) -- else null; the text report says it as `**Writer lock:** <line>.` It is never part of `ok`. It is
`write_lock.probe`'s answer: the lock file tried as a hold tries it and let go at once, nothing made. So `check` says
nothing until a writer has made the lock file there -- a new project on such a folder is named from the first `check`
after its first write. A probe that fails -- the file there and not to be opened, any other error -- is said in that
line, `<project>: whether the project's writer lock can be taken here could not be told (<type>: <why>)`, never a
crash of `check`.

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

`project.json`, `process/process-state.json`, the ledger's `v_NNN.json` and `dsp_profile.json` carry `schema_version` 3
(`FORMAT_VERSION`); `glossary.json` carries 1; `process/journal.jsonl`, `state/slots.json` and `state/seals.json` carry
none. A ledger version, once written, is not rewritten: `state/migrate.py --into` refuses a folder that holds a
project's ledger (`state/` with a version, `slots.json`) or `dsp_profile.json`, naming each, before anything is written
(`IntoRefused`, `is_into_refused` on its class; #134), and claims the `v_001.json` it imports by creating it (item 8).
Every refusal of the import is made before it takes the new project's writer lock, so it makes nothing in the folder
it names -- not the lock's `.autosound/` either (W-9, #141): that folder may be no project at all. Then, under the lock,
it reads that folder's `project.json` again and merges into it as it stands.

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

**The read rule: a file that is there and cannot be read is refused, never read as absent.** Empty, cut off (inside
a character too), not UTF-8, not JSON, the wrong top-level type, a folder in its place or a file that cannot be opened
raises an exception with `is_unreadable` (`project_io.Unreadable`, with `.path`, `.reason`, `.repair`; neither an
`OSError` nor a `ValueError`, so match the attribute, never the class), naming the file and its repair, and nothing is
written. The repair for a file that cannot be opened is its cause's: for a permission refusal on Windows, close what
holds it; on POSIX, where nothing holds a file against a reader, a permission (to read, or to write) or a file standing
where a folder of the path belongs is said as such; anything else -- a full disk, an I/O error -- is the disk's, on
both. No file at all is the one quiet case: a fresh project. It holds for:

- `process/process-state.json`: every `process.py` verb but `plan`, `amp-changes` and `listening-verdicts`, every
  writer method, `handoff()` and `contract.py check` (`state/process-schema.md` has it in full);
- `process/journal.jsonl` (#134): the method's own readers read it strictly and refuse one that cannot be opened,
  and a line in another code page (naming the line and `contract.py repair-encoding`, or, for a line no code page
  makes JSON of, `contract.py repair-encoding --set-aside`): every `process.py` verb that reads or writes it,
  `session_closed()`, the flaw-map gate, every writer method, and the command lines that read it through `Process`
  (`predict.py` -- its read of a series' knobs included --, `flaw_map.py`, `rew_tool.py analyze-joints`,
  `resonalyze_ir.py`, `eq_propose.py`, `ear_suspects.py`, `naming.py next-series`), each in one line, `error: <file>
  <reason> -- <repair>`, exit 1. One that reads and refuses the append is `cannot be appended to (...)`.
  `Process.events()`, the reader for a screen, stays lenient, as `Process.load()` does: no journal and one that cannot
  be opened are `[]` there, and a line in another code page is skipped and counted in `journal_skipped` (`{"torn":
  [...], "not_utf8": [...]}`, line numbers from 1). A line torn by a cut write, inside its last character too, is
  skipped by every reader. `contract.py check` reads it strictly too, and reports as not valid a journal that cannot
  be opened, that holds a line in another code page, or that has lines and no event or as many lines that are no event
  as events or more; it counts the skipped lines (`skipped`), and fewer torn lines than events are only said;
- `state/seals.json`: `state.py verify` and `seal` (exit 1), a bank (`PresetHistory.snapshot`: nothing banked) and
  `repair-version`. A version banked after its ledger line's first seal and never sealed (its seal write failed) is
  reported by `verify` (exit 3) and `contract.py check`; one older than the line's first seal -- banked before seals
  existed, or imported by `migrate.py --into` -- is not;
- `project.json`, where a bank stamps its `project_rev` and where the phase-1 gate reads the flaw map; `Project.load()`,
  and `contract.py check` through it, read a UTF-8 BOM in it, as `read_json` does (#134);
- `glossary.json`, and the glossary `project.json` keeps (#134): `contract.py check` and the phase gates (below), and
  the method's own readers through `naming.Glossary.for_project(project_dir, strict=True)` -- `capture-start`, with
  `--plan` or not, `capture-close`'s read against REW, `capture-import`, `naming.py codes|parse|expect|check` and
  `flaw_map.py --rew` -- each in one line, `error: <file> <reason> -- <repair>`, exit 1, nothing written.
  `Glossary.for_project(project_dir)`, the screen's read (TCC's, contract 1), stays lenient: a file it cannot read is no
  glossary. Both read a UTF-8 BOM. A `glossary.json` that is a link to nothing is refused by the strict read and by
  `contract.py check` (`<file> is a link to <target>, which is not there -- ...`), and read past by the lenient one, to
  `project.json`'s glossary;
- `dsp_profile.json` and `dsp_profile.draft.json`: `load_profile`, `load_draft` and every writer that reads through
  them (`set-field`, `reset-field`, `start`, `finalize`, `set-setting`, `refresh`), and the phase-1 and phase-2
  profile gate. The intake's processor change, which replaces the profile, sets such a file aside unread and byte for
  byte, with one line on stderr saying where; the intake form's page shows it with its repair.

Each phase gate refuses what it cannot check. Leaving phase −1: an intake check that raises or cannot be loaded, and a
`project.json` or a standalone `glossary.json` that cannot be read, named with its repair (#134) -- the glossary inside
the one read as not produced, and the other as no glossary. Leaving phase 0: a `project.json` that cannot be read, where
the flaw-map gate reads the map, and a standalone `glossary.json` that cannot be read -- the intake check runs on every
move forward, so `enter-phase 1` names either, and `contract.py check --phase0-gate` exits 1 under the last line that
names it (#134; it exited 0 there). Into phases 1 and 2: a `dsp_profile.json` that cannot be read or that a newer method
wrote, and a profile check that cannot be loaded. Leaving −1 still gates on missing files and those two only, so
`enter-phase 0` passes over a `dsp_profile.json` that is there and cannot be read, or a newer one, where `contract.py
check --gate` says NOT READY; gating it on the profile's readability, with that parity, waits for J3b (W-11).
`contract.py check` reports such a file (`exists: true`, `valid: false`, the refusal in `issues`) instead of failing.

## 8. How to write them — atomic writes guaranteed (W-8, #135); the lock guaranteed (W-9, #141)

Atomic writes: a writer that replaces one of the files below writes a temporary file beside it under a name of its
own (`<file>.<pid>-<8 hex>.tmp`, created exclusively), flushes and fsyncs it, then moves it over the file with one
`os.replace`, and on POSIX fsyncs the folder, so the move survives a power loss (#134; Windows has no folder fsync).
That writer is `rew_tool/project_io.py` (`atomic_write_text`, `atomic_write_json`, `atomic_write_bytes`). A reader
sees the old file or the new one, never part of either, and two writers never share a temp file. On POSIX a private
file (the reviewer's machine file, 0600) is private from its first byte: its temp is created with that mode (Windows
ignores the mode). The files, each with the bytes its old writer wrote:

- `project.json`, `process/process-state.json`, `state/slots.json`, `state/seals.json`;
- `dsp_profile.json` and `dsp_profile.draft.json`;
- the old (per-preset) layout's `registry.json` and `HEAD` (a bank's, and the one `state/migrate.py --into` writes);
- a ledger version `state.py repair-version` or `repair-encoding` rewrites, and the `<file>.<codec>.orig` backup
  `repair-encoding` keeps (any project text file it repairs, the same way); the journal `repair-encoding
  --set-aside` rewrites, and the `<journal>.set-aside` it writes first (#134, R56);
- the Resonalyze impulse-response files (`resonalyze_ir.write_v7`);
- the reviewer's machine file and key store, and a shell profile `autosound_ai.py key move-shell` rewrites, with its
  `.autosound-bak`.

On Windows a move refused because a process holds the file open is retried for under a second (0.75 s), then raised,
with the old file whole; `process.py` says it as a refusal, exit 1 (`<file> could not be written (...) -- close what
holds it ...; it is as it was`) -- of the journal too since W-9, a round's close included: the close goes to the
journal after its state write (below). A `*.tmp` beside a file is a crash's leftover, never a file to read; a new
project's `.gitignore` ignores it. `scripts/atomic-write-check.py` holds this: outside `project_io.py`, no `.tmp`
literal but two it names (neither is a temp name), and no `os.replace`, `os.rename` or `os.renames` but three named
moves of whole files.

Three of these files, by five writers, were written in place before W-8 and are replaced now: `dsp_profile.json`
(`save_profile`, `set_setting`) and the old layout's `registry.json` and `HEAD` (a bank's, and `state/migrate.py
--into`'s since #134). So a symbolic or hard link at such a name becomes a regular file, the file's mode becomes the
umask's default, a watcher sees the file replaced rather than changed, and on Windows a reader holding the file open
makes the write fail after the retries, where the in-place write went through.

Two more writes go through `project_io.py`; neither replaces a file:

- A new ledger version (`state.py`, `PresetHistory.snapshot`, and the `v_001.json` `state/migrate.py --into` imports,
  #134) is created, never written over (`create_exclusive`), with the bytes its old writer wrote. Its text goes into a
  temp of its own as above, which is then linked to the version's name; the link fails when the name is there. The temp
  is removed afterwards, best effort: one a remove could not take (a Windows scanner holding it) stays as a `*.tmp`
  beside the version, a second link to it (a copy where hard links are refused) that no lister reads. Two writers that
  pick one number cannot overwrite each other: the second is told and takes the next number, and after 100 numbers taken
  under it gives up with `SnapshotError`, naming the numbers it tried; the import takes no other number, and a
  `v_001.json` there by then is its refusal (item 7), naming what it had written. A watcher of the versions folder sees
  the temp come and go and the version appear whole. On a filesystem that refuses hard links (FAT, some network shares)
  the name is created exclusively and written in place, so there a reader can meet a version mid-write for an instant.
  On POSIX the folder is fsynced after the link (#134).
- A line appended to `process/journal.jsonl` (`append_line`) has the old append's bytes, with one line ending before
  it when the file's last write was cut before its newline: the torn line stays one line a reader skips, and the
  event after it is read. That holds for a write cut inside a multi-byte character too: the method's readers decode
  the journal line by line, split on `\n` alone, and skip a line that stops inside its last character like one that
  is not JSON; a line that is not UTF-8 before its end is another code page, which the method's readers refuse (item
  7). The survey of `repair-encoding` reads a `.jsonl` line by line, does not count a line that stops inside its last
  character as a wrong code page, and repairs it line by line: only the lines that are not UTF-8 are rewritten. A
  line no code page makes JSON of (a write cut off in it: a write cut inside a character with the next event glued
  on, before T-14, or a lone line cut in a legacy page) is left by every page's rewrite; on the person's
  `--set-aside` it moves, bytes kept, into `<journal>.set-aside` as `line N: <bytes>`, every other line
  byte-identical (R56). Nothing is rewritten or set aside while a file could not be read, and a write the disk
  refuses there is one line, exit 1, with what landed. The append itself is a plain one: text mode, the platform's
  line ending, no lock of its own -- the writer that appends holds the project's (below); it is fsynced, and so is
  the folder when the append made the file (#134). A journal that cannot be opened is refused by the append too
  (`Unreadable`), and one that reads and refuses the append is `cannot be appended to (...)`. `process.py` reads the
  journal, and opens it for appending, before it writes the state that an event goes with; an append refused after
  that write is said as what landed -- the state holds the change, the journal has no line for it -- with the line to
  append, exit 1 (with the lines, when the write owes two: item 2).

Every other write is still a plain one, in place. Among them: `state/apply.py`'s proposal deltas and sheets; the capture
plans in `docs/plans/`; the review files in `process/reviews/` (each created under a name of its own since #135, `-2`,
`-3`, ... when its second already holds one, so never over another file, but written in place); what `state.py
migrate-line` rebuilds; a fresh project's `CLAUDE.md` and `.gitignore`; and what the command lines export (`eq_export`,
`sums_export`, the Resonalyze conversion's `manifest.json`, ...). `scripts/atomic-write-check.py` does not see these: it
checks temp names and moves, not every write.

**One writer at a time: the project's writer lock** (W-9, #141; audit K-3, T-12, T-18). A writer holds it across its
read, its change, its write and its event, so another writer -- TCC, a second command line, another thread -- can
neither land between them and be written over, nor be written over by it. Before it, two processes each writing 40
channels into one `project.json` lost 40 of the 80 (`project.py`'s selftest, run on the code without the lock).

- **The file:** `<project>/.autosound/write.lock`. A hold in a project folder that is there makes `.autosound/` when it
  is not there yet, and in it a `.gitignore` holding `*`: `git add -A` in the project stages nothing from the folder.
  It is never TCC's `process/.process-write.lock`: TCC holds that one around the child it runs, and a child taking it
  would wait on its own parent.
- **The lock never makes the project folder** (R23). A hold on a folder that is not there -- a mistyped path, one
  gone -- is this process's thread lock alone, under the same wait, and makes nothing: no folder, no `.autosound/`, no
  OS lock. So a verb run on a project folder that is not there makes nothing: it refuses, or answers as over an empty
  project, as before the lock, which made `<typo>/.autosound/` under verbs that went on to say "nothing was written".
  The writer's own first write makes the folder, and the next hold makes `.autosound/` and takes the lock. What that
  costs: a hold that found no folder stays the thread lock alone until it ends, so what it writes once the folder is
  there -- `intake.py set-car`'s `project.json`, `state/migrate.py --into`'s `project.json` and then its ledger and
  profile -- is not ordered against another process's writer of that project. Two processes creating one new project
  at the same moment are not ordered by the OS lock.
- **The sign:** a line `PROTOCOL = 1`, on a line of its own, in `rew_tool/write_lock.py`. Read the file as text, never
  import it: TCC's `core/project_lock.py` `locks_itself` matches `^PROTOCOL\s*=\s*1[ \t]*(?:#.*)?$`, multiline. No copy
  up to v3.1.2 has the file, and such a copy takes no lock of its own.
- **The lock:** `fcntl.flock` on the file on POSIX, `LockFileEx` on its first byte on Windows (through ctypes), both
  tried without blocking and polled, under one deadline over this process's other threads and the other processes.
  Only another writer's lock is "held": on Windows, `LockFileEx`'s ERROR_LOCK_VIOLATION alone -- a share that refuses
  the lock any other way (access denied, not supported) is a folder that cannot be locked, below. Re-entrant within a
  thread: a writer that calls another (`capture-import` its rounds, a bank its snapshot) takes it once.
- **Who holds it:** every public writer of `Process` (`state/process.py`), and `Project.record_change`, which appends
  to the process journal; `Project.save` and `Project.update`; the ledger's writers in `state/state.py` --
  `PresetHistory.snapshot` and its HEAD on `PresetHistory.project_dir` (the project the caller names, else the ledger
  root's parent); `save_config`, `seal_all`, `repair_version`, the registry's writes and `migrate_line` with `apply`
  on the root's parent; `repair_encoding` and `set_aside` on the `project_dir` every caller names (a required
  keyword; both command lines name it). The root's parent is the project in the usual `<project>/state/`; a ledger
  `AUTOSOUND_STATE_ROOT` keeps outside its project is locked on the project only where a caller names it, and on the
  root's parent otherwise, as from `state.py`'s command line. Then `state/apply.py`'s `propose` (one hold over the read
  of HEAD, the snapshot, its delta and its sheet) and `attest` (over the read of HEAD and the snapshot);
  `dsp_profile.py`'s writers, on the folder that holds `dsp_profile.json`; and the command lines of the table below.
  Not under it, among them: the Resonalyze impulse-response files, the review files, the exports, the reviewer's
  machine files, and what `project_seed.seed` writes after its `project.json` -- the `.gitignore`, the
  `dsp_profile.json` it copies, the prose files, and the repository `project_repo.init` makes with its `CLAUDE.md`.
- **Never across REW, git, `gh` or any other subprocess.** What is slow runs first, with the lock free -- the reads
  of REW in `capture-check` and `capture-close`, `enter-phase`'s intake gate (git, `gh`), the git sha a journal's
  header or a profile's stamp carries -- then the hold, a fresh strict read, the change, the write and the event.
  `capture-check` merges its verdicts by title into the state as it is then, and refuses a round closed or replaced
  while REW was read; `enter-phase` refuses a phase another writer made active while its gates ran: exit 1, nothing
  written.
- **The wait:** `AUTOSOUND_LOCK_TIMEOUT_S` seconds, read at each call; 10 when unset; 0 tries once. A value that is no
  number of seconds, 0 or more (`soon`, `-1`, `nan`, `inf`, an empty one), is a usage error, exit 2, said before
  anything is taken or made: `error: AUTOSOUND_LOCK_TIMEOUT_S=<value> is not a number of seconds (0 or more) -- unset
  it for the default 10`. Set it per call, never in an environment every child inherits: TCC's `child_env()` is what an
  agent's session runs in too. No `--lock-timeout` flag.
- **Busy:** the lock still held at the deadline is exit 75, one line on stderr, `busy: <the lock file> is held by
  another writer -- nothing was written, safe to retry`, with nothing taken by that hold. The wait is per hold. A
  writer that writes more than once with nothing slow between takes one hold over all of it (R20), so a held lock is
  met before its first write and "nothing was written" is true: `project.py catch-up`'s three fills, the intake's knobs
  and a new processor's base (its set-aside of another processor's draft or profile included), each answer of the
  intake form, as `flaw_map.py --write`, `setup_import.py --write` and `state/migrate.py --into` already did. One
  command line takes several holds in a row, because it reads REW between them: `process.py capture-close` -- its
  reconcile against REW, its checks, its close (the close alone when REW was not read). Past its first hold its own
  `busy:` line names what landed -- the reconcile of the round, and its checks when they ran -- and what did not, and
  says a retry is safe, as `busy: <the lock file> is held by another writer -- the reconcile of cap_002 landed; the
  checks and the close did not; run capture-close again (the reconcile is safe to repeat)`. Exit 75; for this verb the
  "nothing was written" agreed with TCC (hub #254) holds at its first hold alone.
- **A folder that cannot be locked** -- the OS refuses the lock itself, as some network, cloud and VM shared folders
  do; on Windows, any refusal of `LockFileEx` but ERROR_LOCK_VIOLATION -- is written WITHOUT the lock, and the writer
  says so on stderr, once per process for each folder (R22): `note: <project> cannot be locked (<why>) -- writing
  without the project lock; two writers at once can lose a change here`. A `note:` line on stderr with exit 0 means
  the write landed WITHOUT the lock -- show it. TCC's own lock refused such a folder (its flock, on POSIX; on Windows
  it takes none across processes). `contract.py check` names such a folder in one line of its report (`lock`, item
  3) once a writer has made the lock file there. Refused, the method would stop every write in such a folder. Not
  promised: a lock between two machines on one shared folder -- a Mac and its Windows VM -- where each side's lock may
  be its own, unseen by the other, and then nothing is said.
- **A lock that cannot be made** -- `.autosound/`, its `.gitignore` or `write.lock`: a project folder this user may
  not write, a read-only disk, a file where the folder belongs -- is refused before anything is taken:
  `write_lock.Unwritable`, `is_unreadable` on its class, `.path`, `.reason` and `.repair`, said as
  `project_io.Unreadable` says itself. A command line prints it in one line, `error: <path> cannot be made for the
  project's writer lock (<why>), so nothing was written -- <repair>`, exit 1 -- every command line of the table but
  two: `intake.py` keeps its traceback (exit 1; the sentence in its last line, where TCC's `car_library` reads it),
  and `setup_import.py` says it as its other refusals, `REFUSED -- ...`, exit 3.
- **In process** the three raise as they are: `write_lock.Busy` (`is_busy`, `exit_code` 75, `.path` the lock file,
  `.waited_s`), `BadTimeout` (`exit_code` 2) and `Unwritable`. Match the attribute, never the class: a copy of the
  module loaded under another name has classes of its own.

The command lines that write under it. Each answers a held lock with 75 and its `busy:` line, and a bad wait with 2
and one `error:` line:

| command line | writes under the lock | a lock that cannot be made |
|---|---|---|
| `state/process.py` | every verb that writes the state or the journal (`session-close --check` only reads) | 1, one line |
| `project.py` | every verb that writes, `record-change` included (a dry run -- `--dry-run`, `fix-ids` without `--apply` -- only reads, and takes no lock) | 1, one line |
| `intake.py` | `set`, `set-car`, `set-channel`, `set-amp` | 1, its traceback |
| `state/state.py` | every verb that writes the ledger: `revert`, `variant new` and `switch`, `registry set-active` and `describe`, `config save`, `seal`, `repair-version`, `repair-encoding --from`, `migrate-line --apply` | 1, one line |
| `dsp_profile.py` | `start`, `set-field`, `reset-field`, `set-setting`, `finalize`, `refresh --write` | 1, one line |
| `state/apply.py` | `propose`, `attest` | 1, one line |
| `contract.py` | `repair-encoding --from`, `repair-encoding --set-aside` | 1, one line |
| `flaw_map.py` | `--write` | 1, one line |
| `setup_import.py` | `--write` | 3, `REFUSED -- ...` |
| `state/migrate.py` | `--into` | 1, one line |

Two front ends that are not command lines say it too. The intake form's server (`intake_form.py`) writes each answer
under one hold, and answers a save the lock refused, or a bad wait, with HTTP 400 and `{"error": "<its line>"}`. In a
batch it is 200, with that line as the answer's error; the answers after a busy one get the same line untried -- each
would wait as long again -- while an answer refused for any other reason leaves the others to go on.
`project_seed.seed`, behind TCC's new-project dialog, returns `ok` false and `problem` the busy line itself, no class
name before it, and a bad wait's line the same way; its command line exits 1 for the busy lock, and 2 for a bad wait,
said before the source is read.

**`Project.save` and `Project.update`.** `save(data)` holds the lock and writes `project_rev` as the revision on disk
plus one -- no file counts as 0 -- whatever `data` carries: facts loaded at 3 and saved over a file at 7 are written
as 8, where they were written as 4, a number the file had passed. A `project.json` that is there and cannot be read is
refused (`ProjectError`), never counted from 0 and written over. The lock orders the writes and no more: facts loaded,
held and saved later still write over a change made meanwhile. A load-and-save goes through `update(fn)` (in
`IMPORTABLE`, item 9), which loads, calls `fn(data)` and saves under one hold; every `project.py` verb that writes
`project.json` goes so. `fn` returns one of four: None (it changed `data` in place, and `data` is written), `data`
itself, a whole document -- a dict carrying the loaded facts' own `schema_version`, as `dict(data, ...)` gives one --
or `UNCHANGED`, which writes nothing and moves no `project_rev`. Anything else raises `TypeError` and writes nothing:
a block returned by mistake, `d.setdefault("car", {})`, would otherwise be written as the whole file. A refusal raised
in `fn` writes nothing. `fn` runs with the lock held, so nothing slow goes in it; and a writer of the same project
called inside `fn` re-enters the lock, lands first, and is written over by `update`'s save. `update` returns what was
saved, or, unchanged, the facts as they stand.

**What `process.py` writes first, and where it starts nothing:**

- **A close lands in the state, then in the journal.** `capture-close`, and `capture-start` closing the round it
  supersedes, write the state first and append `capture_round_closed` after it. A state write refused (`... it is as
  it was`) leaves no close in the journal either, and the retry closes the round once. The event went first: the
  journal said closed over a state that did not, and the retry closed the round a second time.
- **A process folder that does not exist is refused unless it is a project's** (W-8's R46). Every verb that writes is
  refused there, exit 1, before anything is made -- no folder, no `.autosound/`:
  - not called `process`: `error: <folder> does not exist, and the method's process folder is called process -- a
    mistyped path? nothing was written`;
  - called `process`, with no `project.json` beside it: `error: <project> holds no project.json: not a project yet --
    the intake starts one with enter-phase -1; nothing was written` -- but for `enter-phase -1`, which starts one, and
    `session-start` where the project folder itself is there (R19), which starts one too.

  A `process` folder beside a `project.json` is the project's first process write, and goes through: a project TCC's
  new-project dialog seeds holds `project.json` before any verb. TCC's project gate also takes an empty folder, and at
  a session's start runs `session-start`, then `enter-phase -1`, in one `try`: both go through there, where
  `session-start` was refused and the second never ran. A mistyped `process-typo`, and `session-start` on a project
  folder that is not there, stay refused. `project.py record-change` refuses the same way, exit 1, one line, and
  `capture-import` says this before it asks REW for a series' titles.
- **`capture-close` closes the round it read.** It reads the open round once, before REW, and holds each of its
  three stages to it. A round another writer closed or replaced in between is refused, exit 1, the brackets saying
  `<id> is the open round now` or `no round is open now`: before anything landed, `error: round <id> was closed or
  replaced after it was read (...) -- nothing was written`; after the reconcile landed, `error: round <id> was closed
  or replaced by another writer while capture-close ran (...) -- <what> landed; <what> did not`. It closed the round
  open by then, unchecked. It reads `AUTOSOUND_LOCK_TIMEOUT_S` before it asks REW, so a bad one is exit 2 with nothing
  printed before it.

## 9. The modules TCC imports — guaranteed (names); `sys.path` partly planned (W-10, J1b)

The names TCC reads from each module, with the parameters it passes, are the `IMPORTABLE` table in `contract.py`.
The guard holds every entry to the code: each listed parameter keeps its name, its place, its kind (positional or
keyword) and its default value. These fail the guard: a removal, a rename, a default removed or changed, a
parameter made keyword-only or positional-only. These pass: a new trailing parameter with a default, and a
keyword-only parameter widened to positional-or-keyword. Each name also stays the kind of thing it is: one listed
without parentheses stays a value (an assignment, a class, an attribute `__init__` sets) and never becomes a function;
one listed with them stays a plain function (not async, not a property) or a class.

The table of contract 1 is frozen in the guard: `FROZEN[1]` in `scripts/contract-guard.py`, generated once from
`IMPORTABLE` as committed in dd4312d, and pinned beside it by its digest (`FROZEN_SHA256[1]`, the sha256 of its
canonical JSON). While `CONTRACT_VERSION` is 1, every module of that table stays in `IMPORTABLE`, and every name in it
holds against the code by the rules above, whatever `IMPORTABLE` says now. `IMPORTABLE` may grow (a name, a module, a
trailing parameter with a default); a rename or a removal in the code fails the guard even when `IMPORTABLE` is edited
with it, and an edit of the frozen table fails it until the digest is edited too. That is where the guard stops: the
table and its digest edited in one commit pass it (item 12).

`IMPORTABLE` has grown under contract 1 by two names of `project.py` (W-9, #141): `Project.update(fn)` and
`UNCHANGED`, what its change returns to write nothing (item 8). They are additions (item 12). The guard holds them to
the code as it holds every entry of `IMPORTABLE`; the frozen table predates them, so `IMPORTABLE` alone holds them:
one removed from the code and from `IMPORTABLE` in one commit passes the guard.

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

A sibling the method loads lazily, or through a loader of its own, comes from `rew_tool/siblings.py`: one module
object per file under one lock (`siblings.load` adopts a copy already loaded, or waits for a load in progress); the
module-level sibling imports of the modules that put `rew_tool/` on `sys.path` (the W-10 rows above, `contract.py`)
are not converted yet. TCC's `reload_loaded()` drops `_autosound_<copy>_siblings` with that lock and its table, so
drop it only when no method call is in flight, or a thread inside a load can run a file twice.

TCC also compares values that no name pins: naming's method tags `"sw"` and `"rta"`, rew_api's measurement kinds
`"sweep"`, `"rta"` and `"impedance"`, and the journal's event names and fields. The shapes of returned values (the
keys of `verify.verdict`, the result of `resonalyze_vc.convert` or `eq_export.export_eq`) are written down in J1b
(W-10).

**A protective leg the method cannot model is refused, never taken out as another family** (#134, R49, R52; the
Arbiter's word). `protective.de_embed` and `protective.matters_at` (and `protective.response`, which both read the
chain through) raise `Unmodelled` for a live leg whose type is outside `dsp_math.MODELLABLE_FAMILIES` -- a Chebyshev,
`CH`, which the record keeps as typed (item 2) -- naming the leg and the way on; match `is_unmodelled` on the
exception's class (`protective.Unmodelled` is `dsp_math.Unmodelled`; neither an `OSError` nor a `ValueError`). The
signatures are as the table holds them. Why: the method has no Chebyshev verified on a DSP -- its ripple is not
identified, so the filter is not determined -- and it never puts another family in its place; there is no override.
The person's way on is on the DSP: set a filter the method models (LR, BW or BE) as the protective and sweep again,
or sweep with the protective filter OFF where the driver is safe without it. A Chebyshev model comes only from
research that teaches the method: a user who researches the Chebyshev mathematics and verifies it against their own
DSP in their project sends it as an issue in the skill's repo. LR, BW and BE are taken out as before, bit for bit; a
type is read in any letter case.

## 10. Environment variables — planned (W-10)

Each variable listed, with its precedence over an explicit argument written down and left as it is (J1b). Known
today, every one the code reads:

- the project: `AUTOSOUND_PROJECT_DIR`, `AUTOSOUND_STATE_ROOT`, `AUTOSOUND_SKILL_ROOT` (the copy a front end
  declares), `AUTOSOUND_NO_GH`;
- the project's writer lock (W-9, #141; item 8): `AUTOSOUND_LOCK_TIMEOUT_S`, the seconds a writer waits for a held
  lock, read at each call -- 10 when unset; a value that is no number of seconds is exit 2, naming it. Set per call,
  never in an environment every child inherits;
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
passes, a value REW clamped to the equaliser's range does not. A read-back that fails once REW has acknowledged the
write -- REW stops answering, answers the read with an error, or with something that is no list of slots -- raises
in the state it met, with `rew_unchecked = True` on its class and words that say the write was sent and acknowledged
but not checked, ending `check REW's EQ before going on`: `RewReadBackUnavailable` (a `RewUnavailable`),
`RewReadBackRefused` (an `HTTPError`, no `rew_state`), `RewReadBackUnreadable` (a `RewProtocolError`).

`rename_measurement` is not read back: it returns REW's answer, as before.

The exceptions `rew_api` raises for REW carry `rew_state`, and these six values are what a front end may match:
`"unavailable"` (REW did not answer, or dropped its answer midway: `RewUnavailable`, a `URLError`; a host that does
not resolve is this too, its words naming the host), `"protocol"` (REW answered something that cannot be read:
`RewProtocolError`, a `ValueError`), `"write_mismatch"` (above), `"not_found"` and `"ambiguous"`
(`find_measurement_id` found no measurement, or two, under a title: `MeasurementNotFound` and `AmbiguousTitle`,
`KeyError`s with the words they always had), and `"config"` (REW's address is no address -- no `http://` or
`https://`, another scheme, no host, a port that is not a whole number from 0 to 65535, a space or a control character
-- refused before anything is sent: `RewAddressError`, a `ValueError`; its words name `REW_API_URL` only when the
address came from it). REW answering with an error is an `HTTPError`, with no `rew_state`. Match the value
(`rew_api.rew_state(exc)`, or the attribute on the exception's class), never the class: the copy a front end loads by
path and the method's own raise different classes.

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
  `FROZEN`, generated from the bump's `IMPORTABLE` in the same commit, with its digest in `FROZEN_SHA256`; the table
  of contract N stays as it was, and so does its digest. The guard holds the frozen table of the number the literal
  names, and fails while that number has none, or while a frozen table is not the one its digest pins.
- What the guard holds is the code against the frozen table, whatever `IMPORTABLE` says: a name of it renamed or
  removed in the code fails it, and so does a module of it dropped from `IMPORTABLE`. An edit of a frozen table
  together with its digest, in one commit, passes it: review alone catches that today. A test on TCC's side that
  keeps contract 1's table as TCC reads it would hold it, and TCC keeps none yet.
- Every change to an item is named in the CHANGELOG's `### Upgrading` note, with a line for TCC.
