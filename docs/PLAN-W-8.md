# W-8 · v3.1.2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the October audit's first wave in the skill — a selftest runner that can fail, one module object per
file and contract 1, atomic writes, strict reads, REW in three states with honest exit codes, and the text a session
reads on every tune. Issues #133–#138 on milestone `W-8 · v3.1.2`, all with the Arbiter's `ok` (2026-10-06).

**Architecture:** Two new stdlib modules in `rew_tool/`: `siblings.py` (every by-path sibling load goes through it:
one module object per file) and `project_io.py` (atomic writes, exclusive creates, a torn-line-safe append, a strict
JSON read that raises `Unreadable`). REW's states become exception types inside `rew_api.py`, matched by an
attribute (`rew_state`), never by class. `process.py`'s CLI gets an exit table (0/1/2, 69, 70; 75 reserved), a
catch-all and a per-verb flag table. Every text fix lands with the `docs-check.py` rule that holds it.

**Tech Stack:** Python 3.9+ stdlib (numpy/scipy only where a module already uses them); bash and `perl` (`alarm`) in
the runner; each module's own `_selftest()`; `scripts/run-selftests.sh` as the one entry; ruff 0.12.0.

**Spec:** `docs/PLAN-AUDIT-2026-10.md` §3 (groups S4, J1, J2, J3, J4, S1), §4, §8; the issues #133–#138. The audit
reports: `git show origin/claude/charming-faraday-dcn0ez:docs/AUDIT-TOOLING-2026-10-04.md` (T-*, K-*, §7) and
`git show origin/claude/relaxed-ritchie-pk2nci:docs/AUDIT-INSTRUCTIONS-2026-10-04.md` (I-*, §5.1). TCC's surface:
`~/dev/autosound/tcc/docs/audit/AUDIT-2026-10-SURFACE.md` (B1, B2) and its `docs/PLAN-AUDIT-2026-10.md` §9 (read-only).

## Global Constraints

- Everything tracked, and every commit message, in English (the commit-msg hook refuses Cyrillic). The exception is
  the uk/de/pl language files, and the Ukrainian lines the tools already print.
- Branch `wave-2026-10-06` in the main tree `~/dev/autosound/skill`. No worktree (the hub's board reads the main tree).
- Tests first, red before the code. New tests are separate functions `_check_*()`, called from the module's
  `_selftest()` through a loop that collects every failure — never appended to its one long chain of asserts:
  ```python
  failures = []
  for check in (_check_a, _check_b):
      try:
          check()
      except AssertionError as exc:
          failures.append(f"{check.__name__}: {exc}")
  assert not failures, "\n".join(failures)
  ```
- While working, run only the selftest of the module you changed (`python3 <module> <its argv from
  scripts/selftests.txt>`), plus `python3 scripts/docs-check.py` when a document changes. The full
  `scripts/run-selftests.sh` runs once per group, at the group review, and never while files are being edited
  (the tests read source).
- Python 3.9 compatible (Apple's `python3` runs the method). New modules are stdlib only.
- Contract 1 = the v3.1.x surface (PLAN-AUDIT §8 M5); everything here is additive under it. No `### Breaking`;
  the release is the patch `v3.1.2`.
- Exit codes: **0** yes/done · **1** no/refused · **2** usage · 3 and 4 per tool, as today · **69** REW unavailable,
  nothing written · **70** unexpected error (a bug; the traceback on stderr) · **75** reserved for J2b's lock (W-9; not
  raised here).
- No new sibling import at module level in `rew_api.py` (TCC loads it by path); the REW exception classes live in
  `rew_api.py`.
- Never match an exception by class across module copies: read its attribute (`rew_state`, `is_unreadable`,
  `exit_code`).
- `capture-check`'s existing Ukrainian output lines stay as they are (TCC parses them).
- Flags stay string literals in `process.py` (TCC finds them in the source text, N19).
- uk/de/pl files are translated by the Advisor (`python3 skills/autosound-tuning/scripts/autosound_ai.py ask …`),
  never by a session or a subagent; the session checks the structure.
- A new script with a command line needs a `NOT_ON_BOARD` line in `rew_tool/capabilities.py` (its reverse pass fails
  the suite otherwise) and a line in the runner (Task 1).
- `CHANGELOG.md`: one `## [Unreleased]` section above `## [v3.1.1]`; each task adds its bullets; `### Upgrading`
  collects what a user or TCC must know.
- Models: implementers **opus**; per-task reviewers and group reviewers **sonnet** (read-only); the final review of
  the silent-failures group **Fable**.
- Paths below are relative to the repo root; `RT` = `skills/autosound-tuning/rew_tool`.

## Order, groups, reviews

| # | task | issue | group |
|---|---|---|---|
| 1 | The runner can fail | #133 | S4 |
| 2 | Selftests check values | #133 | S4 |
| — | group review S4: `pr-test-analyzer` on the group's diff, full suite once | | |
| 3 | `siblings.py`; the loaders that broke a by-path load | #137 | J1 |
| 4 | Contract 1: `CONTRACT_VERSION`, `IMPORTABLE`, `CONTRACT.md`, the guard | #137 | J1 |
| — | group review J1: `pr-test-analyzer`, full suite once | | |
| 5 | Atomic writers | #135 | silent failures |
| 6 | Exclusive versions, the torn journal line, unique review names | #135 | silent failures |
| 7 | Strict process state | #136 | silent failures |
| 8 | Strict seals, drafts and gates; the report's last line; newer schemas | #136 | silent failures |
| 9 | `rew_api`: three states, an honest transport, a write that reads back | #134 | silent failures |
| 10 | `verify`: unreachable is its own state | #134 | silent failures |
| 11 | `process.py`: exit table, catch-all, flags, `--help`, superseded rows, no invented captures | #134, #138 (I-15) | silent failures |
| 12 | The live pass at REW (the controller with the Arbiter) | #134 | silent failures |
| — | group review: `silent-failure-hunter` + `pr-test-analyzer` on Tasks 5–12, one fix round; Fable final; full suite | | |
| 13 | Text checks, and the sentences they hold (I-1, I-11, I-20, I-12) | #138 | S1 |
| 14 | Step numbers that point where they say (I-6) | #138 | S1 |
| 15 | One recipe, one answer per rule (I-7, I-16, I-23, I-29, §5.1 rows) | #138 | S1 |
| — | group review S1: one sonnet reader per §5.1 row pair, full suite | | |
| 16 | Close the wave: CHANGELOG, PR, candidate, TCC's run, release | all | — |

**Why J1 before J2:** `project_io.py` is loaded from `rew_tool/`, `rew_tool/state/` and `scripts/`, by path, and
`siblings.py` is that path.

## What needs the Arbiter

- **Task 12:** REW open on this Mac with one swept measurement, about 15 minutes (PLAN-AUDIT §1 question 7).
- **Task 15:** nothing to do, but the resolutions table there changes method text; read it before «го».
- **Task 16:** the release word, after TCC has run its suite on the candidate (PLAN-AUDIT §4 N2).

## Cost

| block | tasks | machine time |
|---|---|---|
| S4 | 1–2 + review | ~2 h |
| J1 | 3–4 + review | ~3 h |
| silent failures | 5–11 + review + Fable | ~7 h |
| live pass | 12 | ~0.5 h, 15 min of the Arbiter |
| S1 | 13–15 + review | ~3 h |
| close | 16 | ~1 h, then TCC's run |
| **total** | 16 | **~16 h**, sequential; two to three days with the stops |

## Where this plan departs from PLAN-AUDIT (found by the code maps, 2026-10-06)

1. J1 is built before J2 (above).
2. #138's I-15 (`--help` per verb) is built in Task 11, inside the same argv pass as N19.
3. J3a also refuses the two writers that stamp a newer file DOWN to v3 (`Project.save`, `dsp_profile.save_profile`):
   the write side of T-21's defect. A v4 `project.json` is today silently rewritten as v3 by any load-modify-save.
4. The atomic-write scan forbids a `".tmp"` literal outside `project_io.py`. `os.replace` is allowed there and in a
   named list of moves that are not temp-to-final (`state.migrate_line`, `intake._set_aside`, `upkeep`'s binary
   install); a blanket ban would trip on all six.
5. The runner's dead port is `http://127.0.0.1:1` (TCC's choice), not `:9`. `path_check._run` takes a fresh
   interpreter only when a call's `REW_API_URL` differs from the process's, or exporting it would slow every call.
6. `contract.py version` runs with the module's own imports, so it is for diagnostics only. TCC reads
   `CONTRACT_VERSION` with `ast` (§8 M7).
7. The by-path probe runs `python3 -c` in an empty temp folder with `PYTHONPATH` unset, not `python3 -P`, which
   needs 3.11.
8. TCC reads about 90 names, not about 40 (SURFACE.md B1).
9. The 1.7 → 1.8 renumber reaches code: `resonalyze_engine.py:1778-1782` and its selftest, `eq_propose.py:345,415`,
   `xover_candidates.py:15`.
10. The double −1.2: the code's step ids stand (`intake.py:881,900`: −1.1 language, −1.2 reviewer).
    `virtual-first.md`'s "new DSP" bullet moves to the free id −1.5.
11. Time Offset (§5.1 row 15): the readers do not take an offset (`resonalyze_ir.py:180-183` refuses a non-zero one),
    so the documents stop telling the tuner to set one.

---

## Task 1: The runner can fail (#133, audit T-28, T-30)

**Files:**
- Modify: `scripts/run-selftests.sh` (rewritten below)
- Create: `scripts/selftests.txt` (the manifest)
- Modify: `.github/workflows/checks.yml:79-106` (ruff installed before the runner; the separate ruff step goes)
- Modify: `RT/path_check.py:128-174` (`_run`: when a fresh interpreter is needed)
- Modify: `RT/state/process.py:3056-3061` (that selftest subprocess names its REW)
- Modify: `RT/verify.py:478-511` (the selftest stubs the impulse read too)
- Modify: `CLAUDE.md` § Tests (the count line)

**Interfaces:**
- Produces: `scripts/selftests.txt`, one line per module: `<path> <argv…>`, or `skip <path> <reason>`; `#` comments.
  Later tasks add their new modules here.
- Produces: the runner's environment knobs `SELFTEST_TIMEOUT` (seconds, default 300), and for its own selftest
  `SELFTEST_TOOL`, `SELFTEST_MANIFEST`, `SELFTEST_ONLY_TOOL`. `REW_API_URL` is exported as `http://127.0.0.1:1`.
- Produces: the verdict is ALWAYS the last stdout line (`all N checks passed…` or `FAILED: …`).

- [ ] **Step 1: Generate the manifest from today's behaviour** (one-off; the file is data from now on)

```bash
cd ~/dev/autosound/skill
TOOL=skills/autosound-tuning/rew_tool
{ echo "# Every rew_tool module's selftest: <path> <argv...>. A module on disk that is neither listed here nor on"
  echo "# a 'skip' line FAILS the run (#133): a new module is listed, never discovered silently."
  find "$TOOL" -name '*.py' | sort | while read -r f; do
    name="${f#"$TOOL"/}"
    if ! grep -q selftest "$f"; then echo "skip $f has no selftest: a plotting helper"; continue; fi
    case "$name" in
      naming.py) echo "$f . selftest" ;;
      *) if grep -q -- '--selftest' "$f"; then echo "$f --selftest"; else echo "$f selftest"; fi ;;
    esac
  done; } > scripts/selftests.txt
grep -c . scripts/selftests.txt   # expect 66: 2 comment lines, 63 modules, 1 skip (make_plot.py)
```

- [ ] **Step 2: Write the runner's own selftest first** — it fails today, because today's runner ignores its arguments.
  It is the `--selftest` branch at the top of the new script (Step 3); before Step 3 exists, check the red by hand:

```bash
scripts/run-selftests.sh --selftest; echo "rc=$?"   # today: runs the whole suite, never prints "runner selftest OK"
```

- [ ] **Step 3: Rewrite `scripts/run-selftests.sh`**

```bash
#!/usr/bin/env bash
# Run every check of this repo: the scripts' own selftests, every rew_tool module's selftest, ruff.
#
# One runner so CI and a person execute the SAME thing. It must be able to FAIL (#133, audit T-28):
#   * every rew_tool module is in scripts/selftests.txt with the argv its selftest takes, or on a `skip` line with
#     the reason -- a module in neither fails the run (no silent skip);
#   * a selftest passes on exit 0 AND a last output line saying OK: a usage text that exits 0 is not a pass;
#   * each one runs under a timeout (SELFTEST_TIMEOUT seconds, default 300; perl's alarm, since macOS has no
#     `timeout`);
#   * a check that could not run (ruff absent, a module printing SKIPPED) is NOT RUN: counted, printed, and a
#     failure under CI.
# REW is pointed at a dead port (T-30): a selftest must never reach a REW that happens to be open on this machine.
#
#   scripts/run-selftests.sh              # everything; the LAST line is the verdict (`| tail -1`)
#   scripts/run-selftests.sh --selftest   # the runner's own mechanics, on a throwaway tree
#
# Requires numpy and scipy (dsp_math and eq_gate import scipy by name; see the v3.0.12 Upgrading note).
set -uo pipefail

cd "$(dirname "$0")/.."
SELF="scripts/run-selftests.sh"
TOOL="${SELFTEST_TOOL:-skills/autosound-tuning/rew_tool}"
MANIFEST="${SELFTEST_MANIFEST:-scripts/selftests.txt}"
PY="${PYTHON:-python3}"
LIMIT="${SELFTEST_TIMEOUT:-300}"
export REW_API_URL="http://127.0.0.1:1"   # refused at once on every platform (TCC's conftest does the same)
export no_proxy="127.0.0.1,localhost${no_proxy:+,$no_proxy}" NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}"

if [ "${1:-}" = "--selftest" ]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  mkdir -p "$tmp/t"
  printf 'print("selftest OK -- good")\n'                    > "$tmp/t/good.py"
  printf 'print("usage: usage.py --selftest")\n'            > "$tmp/t/usage.py"
  printf 'print("selftest SKIPPED -- no tool here")\n'      > "$tmp/t/skipped.py"
  printf 'import time\ntime.sleep(5)\nprint("selftest OK")\n' > "$tmp/t/slow.py"
  printf 'print("selftest OK")\n'                           > "$tmp/t/unlisted.py"
  printf '%s\n' "$tmp/t/good.py" "$tmp/t/usage.py" "$tmp/t/skipped.py" "$tmp/t/slow.py" "$tmp/t/gone.py" > "$tmp/m.txt"
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t" SELFTEST_MANIFEST="$tmp/m.txt" SELFTEST_TIMEOUT=1 CI= \
         bash "$SELF" 2>&1)"; rc=$?
  want() { printf '%s\n' "$out" | grep -Eq -- "$1" || { printf 'runner selftest: no line matching "%s" in:\n%s\n' "$1" "$out"; exit 1; }; }
  [ "$rc" -eq 1 ] || { printf 'runner selftest: rc %s, want 1\n%s\n' "$rc" "$out"; exit 1; }
  want '^  ok   good\.py'
  want '^  FAIL usage\.py .*no OK line'
  want '^  --   skipped\.py .*NOT RUN'
  want '^  FAIL slow\.py .*timeout after 1s'
  want '^  FAIL gone\.py .*not on disk'
  want '^  FAIL unlisted\.py .*not in '
  want '^FAILED: '
  # Under CI a NOT RUN alone fails the run; locally it is counted and the run passes.
  printf '%s\n' "$tmp/t/good.py" "$tmp/t/skipped.py" "skip $tmp/t/usage.py fixture" "skip $tmp/t/slow.py fixture" \
                "skip $tmp/t/unlisted.py fixture" > "$tmp/m2.txt"
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t" SELFTEST_MANIFEST="$tmp/m2.txt" CI=true bash "$SELF" 2>&1)"; rc=$?
  [ "$rc" -eq 1 ] || { printf 'runner selftest: under CI a NOT RUN must fail (rc %s)\n%s\n' "$rc" "$out"; exit 1; }
  want 'did not run under CI'
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t" SELFTEST_MANIFEST="$tmp/m2.txt" CI= bash "$SELF" 2>&1)"; rc=$?
  [ "$rc" -eq 0 ] || { printf 'runner selftest: locally a NOT RUN is counted, not failed (rc %s)\n%s\n' "$rc" "$out"; exit 1; }
  want 'NOT RUN: skipped\.py'
  echo "runner selftest OK -- usage text, skip, timeout, missing and unlisted modules are all named"
  exit 0
fi

pass=0 fail=0 notrun=0 failed=() skipped=()

# run_one NAME MODE ARGV...   MODE: "ok" = exit 0 AND a last line saying OK; "rc" = exit 0 (tree checks).
run_one() {
  local name="$1" mode="$2"; shift 2
  local out rc last
  if [[ "$1" == *.sh ]]; then
    out="$(perl -e 'alarm shift; exec @ARGV or die "exec: $!\n"' "$LIMIT" bash "$@" 2>&1 </dev/null)"; rc=$?
  else
    out="$(perl -e 'alarm shift; exec @ARGV or die "exec: $!\n"' "$LIMIT" "$PY" "$@" 2>&1 </dev/null)"; rc=$?
  fi
  last="$(printf '%s\n' "$out" | sed '/^[[:space:]]*$/d' | tail -n1)"
  if [ "$rc" -eq 142 ]; then                                   # 128 + SIGALRM
    fail=$((fail + 1)); failed+=("$name"); printf '  FAIL %-24s timeout after %ss\n' "$name" "$LIMIT"
  elif [ "$rc" -eq 0 ] && printf '%s\n' "$last" | grep -qw 'SKIPPED'; then   # the LAST line, as eq_gate/project_repo print it
    notrun=$((notrun + 1)); skipped+=("$name"); printf '  --   %-24s NOT RUN: %s\n' "$name" "$(printf '%s' "$last" | cut -c1-60)"
  elif [ "$rc" -eq 0 ] && { [ "$mode" = rc ] || printf '%s\n' "$last" | grep -qw 'OK'; }; then
    pass=$((pass + 1)); printf '  ok   %-24s %s\n' "$name" "$(printf '%s' "$last" | cut -c1-72)"
  else
    fail=$((fail + 1)); failed+=("$name")
    if [ "$rc" -eq 0 ]; then printf '  FAIL %-24s exit 0 but no OK line -- a usage text is not a pass\n' "$name"
    else                     printf '  FAIL %-24s rc=%s\n' "$name" "$rc"; fi
    printf '%s\n' "$out" | tail -n 12 | sed 's/^/         /'
  fi
}

if [ -z "${SELFTEST_ONLY_TOOL:-}" ]; then
  echo "repo checks"
  run_one "runner"          ok "$SELF" --selftest
  run_one "installers"      rc scripts/installer-consistency.py
  # (keep every other existing fixed line and its comment from the old script, in the same order; give each a
  #  mode: `ok` for a `--selftest`/`selftest` argv, `rc` for a check of the tree. A `--selftest` whose last line
  #  does not say OK is fixed in that script -- its final print -- not by switching it to `rc`.)
fi

echo
echo "rew_tool selftests ($PY)"
listed=()
while read -r first rest; do
  case "$first" in ''|'#'*) continue ;; esac
  if [ "$first" = skip ]; then listed+=("${rest%% *}"); continue; fi
  listed+=("$first")
  name="${first#"$TOOL"/}"
  if [ ! -f "$first" ]; then
    fail=$((fail + 1)); failed+=("$name"); printf '  FAIL %-24s listed in %s, not on disk\n' "$name" "$MANIFEST"; continue
  fi
  # shellcheck disable=SC2086  # the argv is words on purpose
  run_one "$name" ok "$first" $rest
done < "$MANIFEST"
while IFS= read -r f; do
  printf '%s\n' "${listed[@]}" | grep -qxF -- "$f" && continue
  fail=$((fail + 1)); failed+=("${f#"$TOOL"/}")
  printf '  FAIL %-24s not in %s: list its selftest argv, or a skip line with the reason\n' "${f#"$TOOL"/}" "$MANIFEST"
done < <(find "$TOOL" -name '*.py' | sort)

if [ -z "${SELFTEST_ONLY_TOOL:-}" ]; then
  # The LINTER, at the pin CI uses. A check that quietly does not run is worse than one that is absent: no ruff here is
  # NOT RUN, and under CI that fails the run.
  # No arrays here: macOS's bash 3.2 calls an empty array unbound under `set -u`.
  echo
  ruff_cmd="" note=""
  if command -v ruff >/dev/null 2>&1 && [ "$(ruff --version 2>/dev/null)" = "ruff 0.12.0" ]; then ruff_cmd="ruff check"
  elif command -v uvx >/dev/null 2>&1; then ruff_cmd="uvx ruff@0.12.0 check"
  elif command -v ruff >/dev/null 2>&1; then ruff_cmd="ruff check"; note=" (unpinned local ruff)"; fi
  if [ -z "$ruff_cmd" ]; then
    notrun=$((notrun + 1)); skipped+=("ruff"); echo "  --   ruff                     NOT RUN: no uvx and no ruff here"
  elif out="$($ruff_cmd 2>&1)"; then   # word-split on purpose
    pass=$((pass + 1)); echo "  ok   ruff                     $(printf '%s' "$out" | tail -n1)$note"
  else
    fail=$((fail + 1)); failed+=("ruff"); printf '%s\n' "$out" | sed 's/^/       /'
  fi
fi

echo
total=$((pass + fail + notrun))
nr=""; [ "$notrun" -ne 0 ] && nr="; NOT RUN: ${skipped[*]}"
if [ "$fail" -ne 0 ]; then
  echo "FAILED: $fail of $total -- ${failed[*]}$nr"
  exit 1
fi
if [ "$notrun" -ne 0 ] && [ -n "${CI:-}" ]; then
  echo "FAILED: $notrun of $total did not run under CI -- ${skipped[*]}"
  exit 1
fi
echo "all $pass checks passed$nr"
```

- [ ] **Step 4: Run the runner's selftest — expect PASS**

Run: `bash scripts/run-selftests.sh --selftest`
Expected: `runner selftest OK -- usage text, skip, timeout, missing and unlisted modules are all named`, exit 0.

- [ ] **Step 5: CI installs ruff before the runner** — `.github/workflows/checks.yml`: the `install dependencies`
  step becomes `python -m pip install --upgrade pip numpy scipy matplotlib ruff==0.12.0`; the step that runs the
  runner is renamed `selftests, installer consistency and ruff`; the separate `ruff` step is deleted, and its comment
  (why ruff is pinned while numpy is not) moves above `install dependencies`. GitHub sets `CI=true`, so a NOT RUN fails
  there.

- [ ] **Step 6: The REW dead port reaches nothing it should not**
  - `RT/path_check.py` `_run` (~:136): a fresh interpreter only when the call's `REW_API_URL` differs from the
    process's: `if env is not None and env.get("REW_API_URL") != os.environ.get("REW_API_URL"):` (today: whenever
    `env` holds the key, and every call's `env` is built from `os.environ`).
  - `RT/state/process.py:3056-3061`: that `subprocess.run(...)` gets
    `env={**os.environ, "PYTHONIOENCODING": "utf-8", "REW_API_URL": "http://127.0.0.1:1"}`, so the pinned
    "REW down → `capture-close` exits 0, says NO KNOBS RECORDED" no longer depends on what listens on 4735.
  - `RT/verify.py` selftest (~:478-511): beside the `get_measurements`/`get_fr` stubs, stub
    `_api.get_impulse_response = lambda mid, normalised=True: ([0.0, 1 / 48000, 2 / 48000], [0.0, 1.0, 0.0])`
    and restore it in the same `finally`. The counts at `:505-509` stay as they are; if one moves, stop and report.

- [ ] **Step 7: Run the whole suite once with the new rules**

Run: `scripts/run-selftests.sh | tail -1`
Expected: `all N checks passed` (N = 2 + the old fixed lines + 63 + ruff). A module that now FAILs with "no OK line"
gets its final success print moved to be its LAST output line — that and nothing else. Any other red is a finding:
stop and report it, with the module and the output.

- [ ] **Step 8: CLAUDE.md** — § Tests, first bullet: the count is read off `scripts/run-selftests.sh | tail -1`
  (true now: the verdict is the last stdout line), and a new module is added to `scripts/selftests.txt`.

- [ ] **Step 9: Commit**

```bash
git add scripts/run-selftests.sh scripts/selftests.txt .github/workflows/checks.yml CLAUDE.md \
        skills/autosound-tuning/rew_tool/path_check.py skills/autosound-tuning/rew_tool/state/process.py \
        skills/autosound-tuning/rew_tool/verify.py
git commit -m "#133: the selftest runner can fail -- a manifest, an OK line, a timeout, NOT RUN counted, REW at a dead port"
```

---

## Task 2: Selftests check values, not shapes (#133, audit T-25, T-33)

**Files:**
- Modify: `RT/eq_export.py` (selftest), `RT/equal_loudness.py` (selftest), `RT/naming.py` (selftest),
  `RT/state/state.py` (selftest), `RT/contract.py` (selftest)

**Interfaces:** none new; tests only.

- [ ] **Step 1: Write the failing-on-mutation tests** (each passes today; Step 2 proves it can fail)

`RT/eq_export.py` — the ATF rows by their text, through no parser of ours (the row format is `atf_eq.format_atf_eq`,
`atf_eq.py:118-152`: PK `q` two decimals, a shelf `q` one decimal, AP2 an empty gain field and no trailing tab):

```python
def _check_atf_values():
    """The ATF rows by value (audit T-25): today's checks look at types and counts only."""
    rows = [{"type": "PK", "f": 2551, "gain_db": -14.1, "q": 1.5},
            {"type": "LSH", "f": 60, "gain_db": 2.0, "q": 0.7},
            {"type": "APF2", "f": 1200, "q": 1.7}]
    text = export_eq(_profile(), rows, channel="m-L").text      # as the existing selftest does (eq_export.py:439)
    want = ("1\tTrue\tManual\tPK\t2551.0\t-14.1\t1.50\t",
            "2\tTrue\tManual\tLS_Q\t60.0\t2.0\t0.7\t",
            "3\tTrue\tManual\tAP2\t1200.0\t\t1.70")
    lines = text.splitlines()
    for row in want:
        assert any(line.startswith(row) for line in lines), (row, lines[:5])
```

`RT/equal_loudness.py` — published ISO 226:2003 points, not just the 1 kHz anchor:

```python
def _check_iso226_anchors():
    """ISO 226:2003, Table 1 (audit T-33): the contour's SHAPE. Today only 1 kHz is anchored, and moving the 63 Hz
    point by 6 dB stayed green."""
    for phon, f, spl in ((40, 20, 99.85), (40, 63, 73.08), (80, 63, 98.36), (80, 125, 90.09)):
        got = iso226_spl(phon, f)
        assert abs(got - spl) <= 0.05, f"iso226_spl({phon}, {f}) = {got:.2f}; ISO 226:2003 says {spl}"
```

Before committing, check each of the four values against the published ISO 226:2003 table (search the standard's
Table 1 / the 40- and 80-phon contours). If the code's value and the published value differ by more than 0.05 dB,
STOP and report: the anchor is never adjusted to the code. `equal_loudness._selftest` returns a bool and prints
`selftest: OK|FAILED`; run the new check from it and fold its result into `ok`.

`RT/naming.py` — one case per production of the grammar, and the parts nothing asserts today (`p4`…`p9`, `-ctl3`,
`_final`):

```python
def _check_productions():
    cases = {
        "w-L_3 (sw)":       {"code": "w-L", "version_n": 3, "method": "sw", "position": None, "control": None},
        "m-L p9_49 (sw)":   {"code": "m-L", "position": "p9", "version_n": 49},
        "w-L_49 (sw) p5":   {"code": "w-L", "position": "p5", "version_n": 49},
        "m-L-ctl3_49 (sw)": {"code": "m-L", "control": "ctl3", "version_n": 49},
        "sw_final (rta)":   {"code": "sw", "version": "final", "method": "rta"},
        "r-L_17 (sw) noXO": {"code": "r-L", "version_n": 17, "method": "sw"},
        "w-L (imp)":        {"code": "w-L", "method": "imp"},
    }
    for title, want in cases.items():
        got = parse_name(title)
        assert got is not None, f"{title!r} is in the documented grammar and parses to None"
        for key, value in want.items():
            assert got.get(key) == value, (title, key, got.get(key), value)
```

If a case needs the selftest's glossary (`car`, ~:861) to resolve its code, pass it. If a case contradicts the
grammar as documented at the top of `naming.py`, STOP and report — never edit the expectation to what the parser does.

`RT/state/state.py` — one negative case per check `_validate_eq` makes (`state.py:180-206`), so a mutated check goes
red:

```python
def _check_eq_refusals():
    good = {"type": "PK", "f": 1000, "gain_db": -3.0, "q": 1.0, "i": 1}
    _validate_eq("tiers", "w-L", [good])
    bad = {
        "eq not a list": {"PK": 1},
        "band not an object": ["PK"],
        "f missing": [{"type": "PK", "gain_db": -3.0}],
        "f zero": [{"type": "PK", "f": 0}],
        "f a bool": [{"type": "PK", "f": True}],
        "gain_db text": [{"type": "PK", "f": 1000, "gain_db": "-3"}],
        "q text": [{"type": "PK", "f": 1000, "q": "1"}],
        "bypass text": [{"type": "PK", "f": 1000, "bypass": "yes"}],
        "i a bool": [{"type": "PK", "f": 1000, "i": True}],
        "i twice": [dict(good), dict(good)],
    }
    for label, eq in bad.items():
        try:
            _validate_eq("tiers", "w-L", eq)
        except ValueError:
            continue
        raise AssertionError(f"_validate_eq accepted {label}: {eq!r}")
```

`RT/contract.py` — an invalid `project.json` that is present:

```python
def _check_invalid_project_json():
    import tempfile
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 3, "channels": "not-a-list"}, f)
    entry, _data = check_project_json(d)
    assert entry["exists"] and entry["valid"] is False and entry["issues"], entry
```

(If `project.validate` (`project.py:285`) accepts `"channels": "not-a-list"`, use a field it does refuse; read it first.)

- [ ] **Step 2: Prove each check can fail** — break the code under it by hand, run that module's selftest, see red,
  revert: swap `gain=` and `q=` in `eq_export.py:221-223`; add 6.0 to `L_U` of the 63 Hz row of `ISO226`
  (`equal_loudness.py:38`); drop `ctl3` from `CONTROL_CLOSE` (`naming.py:94`); delete the duplicate-`i` check
  (`state.py:203-204`). Write the four reds into the commit message body ("broken by hand, seen red").

- [ ] **Step 3: Run the five selftests — expect PASS** (argv from `scripts/selftests.txt`)

- [ ] **Step 4: Commit**

```bash
git commit -am "#133: selftests check values -- ATF rows by text, ISO 226 points, every naming production, the EQ band refusals, an invalid project.json"
```

### Group review S4

`pr-review-toolkit:pr-test-analyzer` (sonnet) on `git diff main..HEAD`; fixes in one round; then
`scripts/run-selftests.sh | tail -1` → `all N checks passed`.

---

## Task 3: `siblings.py` — one module object per file (#137, audit T-19, T-27; PLAN-AUDIT §3 J1a items 3–4)

**Files:**
- Create: `RT/siblings.py`
- Modify: `RT/dsp_profile.py:318` (`bind_model_rate`), `:384` (`annotate_modellable`), `:341-355` (`_provenance`)
- Modify: `RT/rew_api.py:331` (`get_timing`)
- Modify: `RT/timebase.py:293` (`read_batch`)
- Modify: `RT/state/process.py:416-430` (`_load_sibling`), `:448-462` (`_load_dsp_profile_module`),
  `:516-528` (`_load_rew_tool_module`), `:549-560` (`_load_naming_uncached`), `:2108-2121` (`Process._load_verifier`)
- Modify: `RT/state/state.py:250-260` (`_canonical_code`)
- Modify: `scripts/selftests.txt` (`RT/siblings.py --selftest`); `RT/capabilities.py` `NOT_ON_BOARD` if its reverse
  pass flags `siblings.py`

**Interfaces:**
- Produces: `siblings.load(rel) -> module` (`rel` = `"naming.py"`, `"state/process.py"`); raises `ImportError` for a
  missing file and re-raises whatever the file raises. `siblings.find_loaded(path)`, `siblings.module_name(rel)`,
  `siblings.HERE`, `siblings.COPY`.
- Produces: the `_siblings()` bootstrap below, copied verbatim into every consumer (Task 4's guard holds the copies
  identical); only the `here =` line differs with the file's folder.

- [ ] **Step 1: Write the failing tests**

`RT/dsp_profile.py` selftest — the by-path load TCC does, from an empty folder (red today:
`ModuleNotFoundError: No module named 'dsp_math'`):

```python
def _check_loads_by_path():
    import subprocess, tempfile
    probe = ("import importlib.util, sys\n"
             "spec = importlib.util.spec_from_file_location('probe_dsp_profile', sys.argv[1])\n"
             "m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)\n"
             "m.annotate_modellable({})\n")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    r = subprocess.run([sys.executable, "-c", probe, os.path.abspath(__file__)], cwd=tempfile.mkdtemp(),
                       env=env, capture_output=True, text=True, timeout=120)
    assert "ModuleNotFoundError" not in r.stderr and "ImportError" not in r.stderr, r.stderr[-600:]
```

(`annotate_modellable({})` may raise for an empty profile — anything but an import error is the call's business; if
it needs a minimal profile to reach `import dsp_math`, give it one.) The same shape in `RT/rew_api.py`'s selftest for
`get_timing("1")` (REW is not there; an import error is the only failure).

`RT/siblings.py` selftest — in a throwaway tree holding a copy of `siblings.py` and small modules:

```python
def _selftest():
    import shutil, tempfile, textwrap
    root = tempfile.mkdtemp()
    shutil.copy(os.path.realpath(__file__), os.path.join(root, "siblings.py"))
    def put(name, body):
        with open(os.path.join(root, name), "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(body))
    put("a.py", "X = object()\n")
    put("boom.py", "raise RuntimeError('boom at import')\n")
    put("cyc1.py", "import siblings_probe\nB = siblings_probe.load('cyc2.py')\n")
    put("cyc2.py", "import siblings_probe\nA = siblings_probe.load('cyc1.py')\n")
    put("slow.py", "import time, os\ntime.sleep(0.2)\nopen(os.path.join(os.path.dirname(__file__), 'ran.txt'), 'a').write('x')\n")
    spec = importlib.util.spec_from_file_location("siblings_probe", os.path.join(root, "siblings.py"))
    sib = importlib.util.module_from_spec(spec); sys.modules["siblings_probe"] = sib; spec.loader.exec_module(sib)
    failures = []
    def check(label, fn):
        try:
            fn()
        except AssertionError as exc:
            failures.append(f"{label}: {exc}")
    def one_object():
        a1, a2 = sib.load("a.py"), sib.load("a.py")
        assert a1 is a2 and sys.modules[sib.module_name("a.py")] is a1
    def adopts():
        path = os.path.join(root, "a.py")
        other_spec = importlib.util.spec_from_file_location("someone_elses_name", path)
        # a copy registered under another name first is ADOPTED, not executed again
        sys.modules.pop(sib.module_name("a.py"), None); sib._BY_PATH.clear()
        other = importlib.util.module_from_spec(other_spec); sys.modules["someone_elses_name"] = other
        other_spec.loader.exec_module(other)
        assert sib.load("a.py") is other
    def fails_clean():
        try:
            sib.load("boom.py")
        except RuntimeError:
            assert sib.module_name("boom.py") not in sys.modules
        else:
            raise AssertionError("a module that raises at import was returned")
        try:
            sib.load("missing.py")
        except ImportError:
            pass
        else:
            raise AssertionError("a missing file did not raise")
    def cycle():
        c1 = sib.load("cyc1.py")
        assert c1.B.A is c1
    def threads():
        import threading
        ts = [threading.Thread(target=sib.load, args=("slow.py",)) for _ in range(8)]
        for t in ts: t.start()
        for t in ts: t.join()
        with open(os.path.join(root, "ran.txt")) as f:
            assert f.read() == "x", "slow.py ran more than once"
    for label, fn in (("one object", one_object), ("adopts a loaded copy", adopts), ("fails clean", fails_clean),
                      ("cycle", cycle), ("threads", threads)):
        check(label, fn)
    assert not failures, "\n".join(failures)
    print("siblings selftest OK -- one object per file, adoption, clean failure, cycles, threads")
```

`RT/state/process.py` selftest — the loaders now hand out ONE object:

```python
def _check_one_naming():
    sib = _siblings()
    assert _load_naming() is sib.load("naming.py")
    assert _load_sibling("contract.py") is _load_sibling("contract.py")
```

- [ ] **Step 2: Run them — expect FAIL** (`siblings.py` does not exist; dsp_profile and rew_api import by bare name)

- [ ] **Step 3: Create `RT/siblings.py`**

```python
"""One module object per file of the method, loaded by its path (skill #137; audit T-19, T-27).

The front ends load the method's modules by FILE PATH (TCC's `vendor_loader`), and until W-8 the modules loaded each
other three ways: a bare `import` that needs `rew_tool/` on `sys.path`, private loaders that ran a FRESH copy on every
call, and `sys.path` edits at import. One file then lived as several module objects -- two `NamingError` classes,
several `rew_api` modules each with its own `BASE_URL`.

`load(rel)` is the one way in:
  * a module already in `sys.modules` whose file is this one (by real path) is ADOPTED, whatever its name -- a bare
    `import naming`, TCC's `autosound_tcc._vendor.naming`, an earlier `load`;
  * otherwise the file runs once, under a name tied to this copy of the method, registered in `sys.modules` BEFORE it
    runs (a cycle finds it) and removed again if it fails;
  * one re-entrant lock around both, so two threads never run one file twice.

A missing file, or one that fails, RAISES. A caller that reads "cannot load" as "cannot tell" says so at its own call
site, where the choice can be seen. Consumers reach this file through `_siblings()`, a fixed bootstrap copied into each
of them (scripts/contract-guard.py holds the copies identical): it cannot be imported, since importing is the problem.
"""
import hashlib
import importlib.util
import os
import sys
import threading

#: `rew_tool/` of THIS copy of the method, real path.
HERE = os.path.dirname(os.path.realpath(__file__))
#: Ties module names to this copy: two copies of the method in one process never share a name.
COPY = hashlib.sha1(HERE.encode("utf-8")).hexdigest()[:8]
_LOCK = threading.RLock()
_BY_PATH = {}


def _real(path):
    return os.path.normcase(os.path.realpath(path))


def path_of(rel):
    """`rew_tool/<rel>` of this copy; `rel` is written with `/` ("state/process.py")."""
    return os.path.join(HERE, *rel.split("/"))


def module_name(rel):
    """The name `load(rel)` registers: `_autosound_<copy>_<rel without .py, "__" for "/">`."""
    stem = rel[:-3] if rel.endswith(".py") else rel
    return f"_autosound_{COPY}_" + stem.replace("/", "__").replace("-", "_")


def find_loaded(path):
    """The module already in `sys.modules` for `path` (by real path), or None."""
    want = _real(path)
    module = _BY_PATH.get(want)
    if module is not None and sys.modules.get(module.__name__) is module:
        return module
    for module in list(sys.modules.values()):
        file = getattr(module, "__file__", None)
        if file and _real(file) == want:
            _BY_PATH[want] = module
            return module
    return None


def load(rel):
    """`rew_tool/<rel>` as ONE module object per process. Raises if the file is missing or fails."""
    path = path_of(rel)
    with _LOCK:
        module = find_loaded(path)
        if module is not None:
            return module
        if not os.path.isfile(path):
            raise ImportError(f"siblings: {rel} is not in {HERE}")
        name = module_name(rel)
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"siblings: {path} cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        _BY_PATH[_real(path)] = module
        return module


# def _selftest(): -- the function from Step 1, verbatim, here at module level


if __name__ == "__main__":
    _selftest()
```

  (Its manifest line is `skills/autosound-tuning/rew_tool/siblings.py --selftest`; `__main__` ignores the argv.)

- [ ] **Step 4: The bootstrap, verbatim, into each consumer** (put it after the module's imports; `os` and `sys` are
  imported at the top of every consumer)

```python
def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.realpath(__file__))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    return module
```

  The `here` line per folder: `rew_tool/*.py` as above; `rew_tool/state/*.py`:
  `here = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))`; `scripts/*.py` (Task 5):
  `here = os.path.realpath(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "rew_tool"))`.
  The name equals `siblings.module_name("siblings.py")`, so the bootstrap and `siblings.load` agree on it.

- [ ] **Step 5: Convert the sites**
  - `dsp_profile.py:318` and `:384`: `import dsp_math` → `dsp_math = _siblings().load("dsp_math.py")`.
  - `dsp_profile.py:341-355` `_provenance()`: the body becomes
    `try: return _siblings().load("provenance.py")` / `except Exception: return None  # noqa: BLE001 -- a
    provenance stamp that cannot be made leaves the file unstamped, as before`.
  - `rew_api.py:331`: `import timebase` → `timebase = _siblings().load("timebase.py")`.
  - `timebase.py:293`: `import rew_api` → `rew_api = _siblings().load("rew_api.py")`.
  - `process.py`: `_load_sibling(name)` keeps its contract (None when it cannot load):
    ```python
    def _load_sibling(name):
        """A `rew_tool/` module through `siblings` -- one object per file. None when it cannot be loaded: the
        callers here read that as "cannot tell", and say so at their call site."""
        try:
            return _siblings().load(name)
        except Exception:  # noqa: BLE001
            return None
    ```
    `_load_dsp_profile_module()` → `return _load_sibling("dsp_profile.py")`;
    `_load_rew_tool_module(name)` → `return _load_sibling(name + ".py")`;
    `_load_naming_uncached()` → `return _load_sibling("naming.py")`;
    `Process._load_verifier()` → `return _load_sibling("verify.py")`. Keep each function's docstring reason.
  - `state.py:250-260` `_canonical_code`: the module comes from `_siblings().load("naming.py")` (it raises today and
    keeps raising).

- [ ] **Step 6: Run the selftests of `siblings`, `dsp_profile`, `rew_api`, `timebase`, `state/process`, `state/state` —
  expect PASS.** A selftest that relied on a FRESH copy per call (it patched a module object it got from a loader)
  now sees the shared one: fix the test to restore what it patches, never the loader.

- [ ] **Step 7: Commit**

```bash
git commit -am "#137: one module object per file -- siblings.py, and the loaders that broke a by-path load"
```

---

## Task 4: Contract 1 (#137; PLAN-AUDIT §3 J1a items 1–2; audit K-6, §7)

**Files:**
- Modify: `RT/contract.py` (`CONTRACT_VERSION`, `IMPORTABLE`, the `version` verb, `_USAGE`)
- Create: `RT/CONTRACT.md`
- Create: `scripts/contract-guard.py`
- Modify: `scripts/run-selftests.sh` (two fixed lines: `contract-guard ok scripts/contract-guard.py --selftest`,
  `contract-in-tree rc scripts/contract-guard.py`), `RT/capabilities.py` (`NOT_ON_BOARD["contract-guard.py"]`)

**Interfaces:**
- Produces: `contract.CONTRACT_VERSION = 1` — a top-level int literal, read by TCC with `ast`.
- Produces: `contract.IMPORTABLE` — a top-level dict literal `{module_rel: (entry, ...)}`; an entry is a name
  (`"BASE_URL"`), a function with its parameters (`"find_measurement_id(name, measurements=None, exact=True)"`) or a
  method (`"Process.load()"`). Later tasks that add a trailing parameter with a default update the entry (the guard
  allows that; it refuses a removal or a rename).
- Produces: `python3 RT/contract.py version [--json]` →
  `{"contract_version": 1, "format_version": 3, "skill_version": "<plugin.json version>" | null, "sha": "<git sha>" | null}`.
- Produces: `scripts/contract-guard.py [--selftest]`.

- [ ] **Step 1: Write the failing tests**

`RT/contract.py` selftest:

```python
def _check_version_verb():
    import ast, contextlib, io
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    lit = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "CONTRACT_VERSION"
                                                                         for t in n.targets)]
    assert lit and isinstance(lit[0].value, ast.Constant) and lit[0].value.value == 1, "CONTRACT_VERSION literal"
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert _main(["contract.py", "version", "--json"]) == 0
    v = json.loads(out.getvalue())
    assert v["contract_version"] == CONTRACT_VERSION == 1 and v["format_version"] == FORMAT_VERSION, v
    # an older method has no `version`: it answers usage and exit 2 -- that is how a caller reads "contract 0"
    with contextlib.redirect_stderr(io.StringIO()):
        assert _main(["contract.py", "no-such-verb"]) == 2
```

`scripts/contract-guard.py --selftest` (Step 3) breaks each rule in a throwaway tree and needs the rule to name it.

- [ ] **Step 2: Run — expect FAIL** (`CONTRACT_VERSION` and `version` do not exist)

- [ ] **Step 3: Write the code**
  - `contract.py`, beside `FORMAT_VERSION` (`:48`):
    ```python
    #: The contract the front ends program against (skill #137; rew_tool/CONTRACT.md). An int LITERAL: TCC reads it
    #: from any tag with `ast`, without running this file. It moves only on a breaking change to a listed item, only
    #: in a minor, and only after a TCC release that accepts the new number is out (PLAN-AUDIT-2026-10 §8 M5).
    CONTRACT_VERSION = 1
    ```
  - `IMPORTABLE` beside `CONTRACT` (a separate table — `intake.py:1339` unpacks `CONTRACT` rows as 4-tuples): the 15
    modules of TCC's `vendor_loader._VENDORED` and every name of SURFACE.md B1, plus `dsp_profile.bundled_dir`,
    `dsp_profile.list_bundled` (TCC plan §9). Write each function with the parameters TCC uses, from the code at
    HEAD; where B1 says `FORM_*`, list the constants by name. Check each entry exists before adding it; one that does
    not is a finding — report it, do not invent it.
  - The verb, before `if argv[1] != "check"` in `_main`:
    ```python
    if argv[1] == "version":
        info = {"contract_version": CONTRACT_VERSION, "format_version": FORMAT_VERSION,
                "skill_version": _skill_version(), "sha": _skill_sha()}
        if "--json" in argv:
            print(json.dumps(info))
        else:
            print(f"contract {info['contract_version']} · format {info['format_version']} · "
                  f"skill {info['skill_version'] or 'unknown'} · {info['sha'] or 'no git'}")
        return 0
    ```
    with `_skill_version()` walking up from `_HERE` (at most five folders) to `.claude-plugin/plugin.json` and
    returning its `version` (None if absent or unreadable), and `_skill_sha()` returning
    `provenance.skill_sha()` (a lazy `import provenance`; None on any failure). `_USAGE` gains the line
    `contract.py version [--json]   the contract this copy keeps (CONTRACT_VERSION), for diagnostics`.
  - `RT/CONTRACT.md`: title `# Contract 1`; the twelve items of the tooling report's §7, each marked
    **guaranteed** or **planned (W-N, #issue)**: 1 identity — guaranteed; 2 `process.py` verbs and exit codes —
    planned (W-8, #134; Task 11 flips it); 3 `contract.py check` keys — planned (W-10); 4 `deployment.py` — not
    promised (§8 M6); 5 `autosound_ai.py` exit codes — as today, listed; 6 `"contract": N` in outputs — not built
    (§8 M6); 7 the read rule — planned (W-8, #136; Task 8 flips it); 8 atomic writes — planned (W-8, #135; Task 5);
    the lock — planned (W-9, J2b); 9 the importable modules — the table from `IMPORTABLE`, each module marked
    "loads by path without touching sys.path: guaranteed" for the CLEAN set of the guard, "W-10 (J1b)" for the rest;
    10 environment variables — listed, precedence written, not flipped (W-10); 11 REW write semantics — planned
    (W-8, #134; Task 9); 12 the compatibility policy (the bump rule above).
  - `scripts/contract-guard.py`:

```python
#!/usr/bin/env python3
"""Hold the method to its contract (skill #137; PLAN-AUDIT-2026-10 §3 J1).

    scripts/contract-guard.py             # the tree: exit 0, or each break named and exit 1
    scripts/contract-guard.py --selftest  # every rule broken on purpose in a throwaway tree

  1. CONTRACT_VERSION in rew_tool/contract.py is a top-level int literal, and CONTRACT.md's title names it.
  2. IMPORTABLE is a top-level dict literal; every module exists; every entry is defined at that module's top level
     (`Class.method` inside the class); listed parameters are a PREFIX of the real ones and every real one past them
     has a default -- an addition passes, a removal or a rename does not.
  3. Every `_siblings()` bootstrap is the canonical text; only its `here =` line may differ.
  4. The probe (audit T-27): each IMPORTABLE module loads by path in a fresh python started in an empty folder with
     PYTHONPATH unset; a lazy-import call raises no ImportError; for CLEAN modules sys.path is untouched by the load.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "skills", "autosound-tuning", "rew_tool")
SCRIPTS = os.path.join(ROOT, "skills", "autosound-tuning", "scripts")

#: Modules that load by path without touching sys.path -- CONTRACT.md item 9 says "guaranteed" for exactly these.
#: The rest are J1b's (W-10). Filled in Step 4 from what the probe reports, not from a guess.
CLEAN = ()
#: The call that reaches a module's lazy sibling imports, and its arguments as a Python literal.
CALLS = {"dsp_profile.py": ("annotate_modellable", "({},)"), "rew_api.py": ("get_timing", "('1',)")}

BOOTSTRAP_HERE = "    here = "
PROBE = r'''
import importlib.util, json, sys
path, call, args = sys.argv[1], sys.argv[2], sys.argv[3]
before = list(sys.path)
spec = importlib.util.spec_from_file_location("contract_probe_target", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
after = list(sys.path)
error = None
if call:
    try:
        getattr(module, call)(*eval(args))
    except ImportError as exc:
        error = f"{type(exc).__name__}: {exc}"
    except Exception:
        pass
print(json.dumps({"path_changed": after != before, "import_error": error}))
'''


def _module_ast(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return node.value
    return None


def _params(args):
    names = [a.arg for a in args.posonlyargs + args.args] + [a.arg for a in args.kwonlyargs]
    n_pos = len(args.posonlyargs) + len(args.args)
    defaults = [None] * (n_pos - len(args.defaults)) + list(args.defaults) + list(args.kw_defaults)
    return names, defaults


def _defined(tree, entry):
    """(ok, why) for one IMPORTABLE entry against a module's ast."""
    name, _, sig = entry.partition("(")
    owner, _, attr = name.partition(".")
    scope = tree.body
    if attr:
        cls = next((n for n in scope if isinstance(n, ast.ClassDef) and n.name == owner), None)
        if cls is None:
            return False, f"class {owner} is not defined"
        scope, name = cls.body, attr
    node = None
    for n in scope:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name:
            node = n
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(getattr(t, "id", None) == name for t in targets):
                node = n
    if node is None:
        return False, f"{entry.partition('(')[0]} is not defined"
    if not sig:
        return True, ""
    if isinstance(node, ast.ClassDef):
        node = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
        if node is None:
            return True, ""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False, f"{name} is listed with parameters and is not a function"
    listed, _ = _params(ast.parse(f"def _x({sig.rstrip(')')}): pass").body[0].args)
    real, real_defaults = _params(node.args)
    if attr and real[:1] in (["self"], ["cls"]):
        real, real_defaults = real[1:], real_defaults[1:]
    if real[:len(listed)] != listed:
        return False, f"{name}({', '.join(real)}) does not begin with ({', '.join(listed)})"
    extra = [p for p, d in zip(real[len(listed):], real_defaults[len(listed):]) if d is None]
    if extra:
        return False, f"{name} has new required parameters {extra} -- a contract break"
    return True, ""


def _bootstraps(dirs):
    """{path: source of its `_siblings` with the `here =` line blanked}."""
    out = {}
    for d in dirs:
        for base, _dirs, files in os.walk(d):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(base, fn)
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                tree = ast.parse(text)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == "_siblings":
                        src = ast.get_source_segment(text, node)
                        out[path] = "\n".join(line if not line.startswith(BOOTSTRAP_HERE) else BOOTSTRAP_HERE
                                              for line in src.splitlines())
    return out


def check(tool, scripts, clean=CLEAN, calls=CALLS):
    problems = []
    contract_path = os.path.join(tool, "contract.py")
    tree = _module_ast(contract_path)
    cv = _literal(tree, "CONTRACT_VERSION")
    if not (isinstance(cv, ast.Constant) and type(cv.value) is int):
        problems.append("contract.py: CONTRACT_VERSION is not a top-level int literal (TCC reads it with ast)")
    else:
        md = os.path.join(tool, "CONTRACT.md")
        title = open(md, encoding="utf-8").readline().strip() if os.path.isfile(md) else ""
        if title != f"# Contract {cv.value}":
            problems.append(f"CONTRACT.md's title is {title!r}, not '# Contract {cv.value}'")
    imp = _literal(tree, "IMPORTABLE")
    try:
        importable = ast.literal_eval(imp) if imp is not None else None
    except ValueError:
        importable = None
    if not isinstance(importable, dict):
        problems.append("contract.py: IMPORTABLE is not a top-level dict literal")
        importable = {}
    for rel, entries in importable.items():
        path = os.path.join(tool, *rel.split("/"))
        if not os.path.isfile(path):
            problems.append(f"IMPORTABLE lists {rel}, which is not in rew_tool/")
            continue
        mod_tree = _module_ast(path)
        for entry in entries:
            ok, why = _defined(mod_tree, entry)
            if not ok:
                problems.append(f"{rel}: {why}")
    boot = _bootstraps([tool, scripts])
    if len(set(boot.values())) > 1:
        first = sorted(boot)[0]
        for path, src in sorted(boot.items()):
            if src != boot[first]:
                problems.append(f"{os.path.relpath(path, tool)}: _siblings() differs from {os.path.relpath(first, tool)}")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    for rel in importable:
        path = os.path.join(tool, *rel.split("/"))
        if not os.path.isfile(path):
            continue
        call, args = calls.get(rel, ("", "()"))
        r = subprocess.run([sys.executable, "-c", PROBE, path, call, args], cwd=tempfile.mkdtemp(), env=env,
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            problems.append(f"{rel}: does not load by path from an empty folder -- {r.stderr.strip().splitlines()[-1:]}")
            continue
        seen = json.loads(r.stdout.strip().splitlines()[-1])
        if seen["import_error"]:
            problems.append(f"{rel}: {call}() fails a sibling import when loaded by path -- {seen['import_error']}")
        if rel in clean and seen["path_changed"]:
            problems.append(f"{rel}: listed CLEAN, and loading it changed sys.path")
    return problems


def _selftest():
    <builds a throwaway tree under tempfile.mkdtemp(): rew_tool/{contract.py, CONTRACT.md, siblings.py (copy),
     m.py, n.py} and scripts/; asserts check() == [] on the good tree, then names each break in turn:
     CONTRACT_VERSION = 1 + 0; CONTRACT.md titled "# Contract 2"; IMPORTABLE naming an absent function; a listed
     parameter renamed; a new required parameter; a module listed that is not there; a `_siblings` copy with one
     changed line; a CLEAN module whose import does `sys.path.insert(0, ".")`; a CALLS function doing a bare
     `import nowhere_module`. Prints "contract-guard selftest OK -- ..." last.>


def main(argv):
    if argv[1:] == ["--selftest"]:
        _selftest()
        return 0
    problems = check(TOOL, SCRIPTS)
    for p in problems:
        print(f"[contract] {p}")
    print(f"contract-guard: {len(problems)} problem(s)" if problems else "contract-guard OK -- contract 1 holds")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Fill `CLEAN`** — run `python3 -c` the probe over every IMPORTABLE module (a throwaway loop over
  `check(…, clean=tuple(importable))`), put in `CLEAN` exactly the modules whose load leaves `sys.path` untouched, and
  mark the same set "guaranteed" in CONTRACT.md item 9. PLAN-AUDIT expected six; the code map counts seven (or six
  without `state/process.py`, which loads `contract.py`). Record what the probe says.

- [ ] **Step 5: Run** `python3 scripts/contract-guard.py --selftest` and `python3 scripts/contract-guard.py`, and
  `contract.py`'s selftest — expect PASS. Add the two runner lines and the `NOT_ON_BOARD` line
  (`"contract-guard.py": "the guard that holds contract 1 (skill #137): a maintainer's check, not a tuner's step"`).

- [ ] **Step 6: Commit**

```bash
git add -A skills/autosound-tuning/rew_tool/contract.py skills/autosound-tuning/rew_tool/CONTRACT.md \
           scripts/contract-guard.py scripts/run-selftests.sh skills/autosound-tuning/rew_tool/capabilities.py
git commit -m "#137: contract 1 -- CONTRACT_VERSION, the IMPORTABLE list TCC reads, CONTRACT.md and its guard"
```

### Group review J1

`pr-review-toolkit:pr-test-analyzer` (sonnet) on the J1 diff; one fix round; the full suite once.

---

## Task 5: Atomic writers (#135; audit T-8, T-17; PLAN-AUDIT §3 J2a items 1–2)

**Files:**
- Create: `RT/project_io.py`
- Modify (writers): `RT/state/process.py:2529-2539`, `RT/project.py:839-842`, `RT/state/state.py:574-582, 725-729,
  866-869, 1677-1690, 1137, 1484`, `RT/dsp_profile.py:465, 708-711, 785-786`, `RT/state/migrate.py:237-240`,
  `RT/resonalyze_ir.py:345-348`, `skills/autosound-tuning/scripts/autosound_ai.py:476-482, 2294-2301`
- Modify: `RT/project_seed.py:267-277` (`GITIGNORE_LINES` gains `*.tmp`)
- Create: `scripts/atomic-write-check.py`
- Modify: `scripts/selftests.txt` (`RT/project_io.py --selftest`), `scripts/run-selftests.sh`
  (`atomic-write ok scripts/atomic-write-check.py --selftest`, `atomic-in-tree rc scripts/atomic-write-check.py`),
  `RT/capabilities.py` (`NOT_ON_BOARD` for `atomic-write-check.py` and, if flagged, `project_io.py`)
- Modify: `CHANGELOG.md` (`## [Unreleased]` created here)

**Interfaces:**
- Consumes: `_siblings()` (Task 3).
- Produces: `project_io.atomic_write_text(path, text, *, newline=None, mode=None, makedirs=False)` and
  `project_io.atomic_write_json(path, data, *, indent=2, sort_keys=False, ensure_ascii=False, trailing_newline=False,
  newline=None, mode=None, makedirs=False)`. Each consumer gets the module as `_siblings().load("project_io.py")`.

- [ ] **Step 1: Write the failing tests**

`RT/state/process.py` selftest:

```python
def _check_foreign_tmp_untouched():
    """Two writers never share a temp file (audit T-8): a `process-state.json.tmp` that is not ours stays as it is."""
    import tempfile
    d = os.path.join(tempfile.mkdtemp(), "process")
    os.makedirs(d)
    foreign = os.path.join(d, "process-state.json.tmp")
    with open(foreign, "wb") as f:
        f.write(b"someone else's half-written file")
    assert _main(["process.py", d, "enter-phase", "-1"]) == 0
    with open(foreign, "rb") as f:
        assert f.read() == b"someone else's half-written file", "the writer used a temp name another writer uses"


def _check_state_bytes():
    """The same bytes as before the change: json.dumps(indent=2, ensure_ascii=False) and a final newline."""
    import tempfile
    d = os.path.join(tempfile.mkdtemp(), "process")
    p = Process(d)
    p.enter_phase("-1")
    with open(p.state_path, encoding="utf-8") as f:
        text = f.read()
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"
```

`RT/project_io.py` selftest (the module's own; it lands with the module in Step 3, run it red first by writing the
functions as `raise NotImplementedError`):

```python
def _check_text_and_json(): <write text and json to a temp dir; read back; bytes equal json.dumps(...) (+ "\n")>

def _check_foreign_tmp(): <a file "<path>.tmp" beside the target survives a write byte for byte>

def _check_replace_fails_clean():
    """A crash between the temp and the move leaves the old file whole and no temp behind."""
    import tempfile
    d = tempfile.mkdtemp(); path = os.path.join(d, "x.json")
    atomic_write_json(path, {"v": 1})
    before = open(path, "rb").read()
    real = os.replace
    def broken(src, dst):
        raise OSError("disk pulled")
    os.replace = broken                      # the writer's own move fails: a fault injected through the writer
    try:
        try:
            atomic_write_json(path, {"v": 2})
        except OSError:
            pass
        else:
            raise AssertionError("a failed move was reported as written")
    finally:
        os.replace = real
    assert open(path, "rb").read() == before
    assert [f for f in os.listdir(d) if f.endswith(".tmp")] == [], os.listdir(d)

def _check_private_mode(): <on POSIX, mode=0o600 → stat mode & 0o777 == 0o600>

def _check_two_writers_one_reader():
    """Audit T-8's test: two processes write one file 100 times each while a third reads it: every read parses."""
    <multiprocessing.get_context("spawn"); two writers calling atomic_write_json(path, {"n": i, "pad": "x" * 4000});
     the reader loops json.load until both writers finish and counts failures; assert failures == 0>
```

`scripts/atomic-write-check.py --selftest` (Step 4) names a `".tmp"` literal and an unlisted `os.replace` in a
throwaway tree.

- [ ] **Step 2: Run — expect FAIL** (the foreign `.tmp` is overwritten and renamed away today; `project_io` raises)

- [ ] **Step 3: Create `RT/project_io.py`**

```python
"""How the method writes, and reads, the files it owns (skill #135, #136; audit T-8, T-17, K-2).

WRITES go through `atomic_write_text` / `atomic_write_json`: a temp file with a name no other writer uses, opened
exclusively, written, flushed and fsynced, then moved over the target in one `os.replace`. A reader sees the old file
or the new one, never half of either; two writers never share a temp file. A Windows `PermissionError` on the move (an
editor, an antivirus scan or TCC holding the target open) is retried for under a second.

Stdlib only. Loaded by path like every sibling: `_siblings().load("project_io.py")`.
"""
import io
import json
import os
import secrets
import time

#: Waits before the next `os.replace` attempt on Windows. A holder that outlives them is a real conflict.
_REPLACE_RETRIES_S = (0.05, 0.1, 0.2, 0.4)


def _temp_name(path):
    # Ends in `.tmp`, never `.json`/`.jsonl`: `contract.project_text_files` lists those, and a leftover must not be
    # read as a project file. The pid and the token make it unique per writer.
    return f"{path}.{os.getpid()}-{secrets.token_hex(4)}.tmp"


def _replace(src, dst):
    for delay in _REPLACE_RETRIES_S + (None,):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if delay is None or os.name != "nt":
                raise
            time.sleep(delay)


def atomic_write_text(path, text, *, newline=None, mode=None, makedirs=False):
    """Write `text` to `path` so that no reader ever sees a half-written file.

    `newline` is `open()`'s: None writes the platform's line ending -- what `open(path, "w")` did at every site this
    replaces -- while "" and "\\n" keep the text's own. `mode` (POSIX only) is set on the temp BEFORE the move, so the
    target never exists with looser permissions.
    """
    if makedirs:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = _temp_name(path)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with io.open(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None and os.name != "nt":
            os.chmod(tmp, mode)
        _replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, data, *, indent=2, sort_keys=False, ensure_ascii=False, trailing_newline=False,
                      newline=None, mode=None, makedirs=False):
    """`json.dumps(data, ...)` through `atomic_write_text` -- the same text `json.dump` wrote at each old site."""
    text = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    if trailing_newline:
        text += "\n"
    atomic_write_text(path, text, newline=newline, mode=mode, makedirs=makedirs)
```

- [ ] **Step 4: Convert every writer** — keep each site's `validate` and `makedirs` before the write; the arguments
  reproduce today's bytes (the code map's dump classes):

| site | becomes |
|---|---|
| `process.py` `Process._write` | `_project_io().atomic_write_json(self.state_path, state, indent=2, ensure_ascii=False, trailing_newline=True)` |
| `project.py` `Project.save` | `atomic_write_json(path, data, indent=2, sort_keys=True, ensure_ascii=False)` |
| `state.py` `_write_slots`, `repair_version`, `Registry._write` (`makedirs=True`), `dsp_profile.py` `save_draft`, `save_profile`, `migrate.py` `_write_json` | `atomic_write_json(path, data, indent=2, sort_keys=True, ensure_ascii=False)` |
| `state.py` `_write_seals` | `atomic_write_json(path, seals, indent=1, sort_keys=True, ensure_ascii=True)` |
| `dsp_profile.py` `set_setting` | `atomic_write_json(target, data, indent=2, ensure_ascii=False)` (no `sort_keys`, as today) |
| `state.py` `_set_head` | `atomic_write_text(self._head_path(), version + "\n")` |
| `state.py` `repair_encoding` | the original's bytes go to `<file>.<codec>.orig` by `shutil.copy2` (today a move, which left the target absent until the end, T-17), then `atomic_write_text(path, text, newline="")` |
| `resonalyze_ir.py` `write_v7` | `atomic_write_text(path, dumps_v7(doc), newline="\n")` |
| `autosound_ai.py` `_dpapi_write` | `atomic_write_json(path, store, indent=None, ensure_ascii=True, makedirs=True)` |
| `autosound_ai.py` `_write_private` | `atomic_write_text(path, "\n".join(lines) + "\n", mode=0o600, makedirs=True)` |

  `autosound_ai.py` takes the `scripts/` form of the `_siblings()` bootstrap (Task 3, Step 4). CI's Windows job runs
  `_dpapi_put/_get/_delete`, which is this writer on Windows — leave that step as it is.

- [ ] **Step 5: `scripts/atomic-write-check.py`** — an AST scan of every `.py` under `skills/autosound-tuning/` and
  `scripts/`: (a) a string constant ending in `.tmp` outside `rew_tool/project_io.py` is a complaint; (b) a call to
  `os.replace` or `os.rename` outside `project_io.py` is a complaint unless its (file, enclosing function) is in
  `MOVES = {("rew_tool/state/state.py", "migrate_line"), ("rew_tool/intake.py", "_set_aside"),
  ("scripts/upkeep.py", "<the function holding upkeep.py:616>")}` — moves of whole files that are not temp-to-final,
  each listed with a one-line reason. `--selftest` writes a throwaway tree with one violation of each kind and one
  allowed move, and needs the two violations named and the move passed; it prints
  `atomic-write-check selftest OK -- ...` last. Tree mode prints each complaint and exits 1, or prints
  `atomic-write-check OK -- every write goes through project_io`.

- [ ] **Step 6: `*.tmp` in `GITIGNORE_LINES`** (`project_seed.py:267-277`), with a comment: a temp left by a crash is
  never committed by `project_repo.init`'s `git add -A`. New projects only; say so in the CHANGELOG.

- [ ] **Step 7: Run** the selftests of `project_io`, `state/process`, `state/state`, `project`, `dsp_profile`,
  `state/migrate`, `resonalyze_ir`, `autosound_ai`, and both modes of `atomic-write-check.py` — expect PASS.

- [ ] **Step 8: CHANGELOG** — create `## [Unreleased]` above `## [v3.1.1]` with: "Every file the method owns is now
  written atomically: a unique temp file, fsync, one move (#135, audit T-8). A crash or a second writer can no longer
  leave `project.json` or `process-state.json` half-written. New projects ignore `*.tmp`."

- [ ] **Step 9: Commit**

```bash
git commit -am "#135: every file the method owns is written atomically -- project_io, and a scan that keeps it so"
```

---

## Task 6: Exclusive versions, the torn journal line, unique review names (#135; audit T-9, T-14, T-17)

**Files:**
- Modify: `RT/project_io.py` (+ `create_exclusive`, `append_line`)
- Modify: `RT/state/state.py:1170-1208` (`PresetHistory.snapshot`)
- Modify: `RT/state/process.py:2573-2581` (`Process._append`)
- Modify: `skills/autosound-tuning/scripts/autosound_ai.py:707-710` (`keep_raw`), `:2870-2902` (`_persist_review`),
  `:2905-2930` (`_write_package`)

**Interfaces:**
- Produces: `project_io.create_exclusive(path, text, *, newline=None)` — creates `path` with `text`, or raises
  `FileExistsError` and leaves the existing file alone; `project_io.append_line(path, line)` — appends `line` and a
  newline, starting on a fresh line if the file's last write was torn.

- [ ] **Step 1: Write the failing tests**

`RT/state/state.py` selftest:

```python
def _check_version_never_overwritten():
    """Two writers that pick one number: the second takes the next, and the first's file is untouched (audit T-9)."""
    <a project with v_001 (the selftest's own fixtures); a foreign `versions/v_002.json` written by hand with known
     bytes; PresetHistory._next_version patched to return "v_002" on its first call only; snapshot(...) returns
     "v_003", and v_002's bytes are unchanged>   # red today: v_002 is truncated and rewritten
```

`RT/state/process.py` selftest:

```python
def _check_torn_journal_line():
    """A journal whose last line was cut keeps the NEXT event readable (audit T-14)."""
    import tempfile
    d = os.path.join(tempfile.mkdtemp(), "process")
    os.makedirs(d)
    with open(os.path.join(d, "journal.jsonl"), "w", encoding="utf-8") as f:
        f.write('{"at": "2026-10-06T00:00:00Z", "type": "decision", "question": "q1"')   # no newline: torn
    assert _main(["process.py", d, "decision", "q2", "yes", "-1.1"]) == 0
    assert any(e.get("type") == "decision" and e.get("question") == "q2" for e in Process(d).events()), \
        "the event after a torn line was glued to it and lost"
```

(Read `record_decision`'s event fields first; use the field that holds the question.)

`autosound_ai.py` selftest:

```python
def _check_review_names_unique():
    """Two reviews in one second are two files; a package and its answer keep one base name."""
    <in a temp project, call _persist_review twice with the same frozen stamp; two files, neither overwritten;
     _write_package twice: "<stamp>-<role>-package.md" and "<stamp>-<role>-2-package.md", and the answer name derived
     by replace("-package.md", ".md") of each is free>
```

`project_io` selftest: `create_exclusive` creates; a second call raises `FileExistsError` with the first file
unchanged; with `os.link` patched to raise `OSError(errno.EPERM)`, it still creates exclusively (the fallback).

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Write the code**

```python
def create_exclusive(path, text, *, newline=None):
    """Create `path` holding `text`, or raise `FileExistsError` -- never overwrite (audit T-9).

    For files whose NAME is the claim (a ledger version `v_NNN.json`): of two writers that picked one number, one
    wins and the other is told. The text is written to a temp first and LINKED into place, so the name never appears
    empty or half-written. Where the filesystem cannot hard-link (FAT, some network shares), the name is created
    exclusively and written in place -- a reader can then meet it mid-write for an instant; said, not hidden.
    """
    tmp = _temp_name(path)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with io.open(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise
        except OSError:
            fd2 = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            with io.open(fd2, "w", encoding="utf-8", newline=newline) as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def append_line(path, line):
    """Append `line` and a newline. If the file's last write was cut before its newline, start on a fresh line, so
    the torn line stays one skipped line and the new one is read (audit T-14)."""
    torn = False
    try:
        with open(path, "rb") as f:
            if f.seek(0, os.SEEK_END):
                f.seek(-1, os.SEEK_END)
                torn = f.read(1) != b"\n"
    except FileNotFoundError:
        pass
    with open(path, "a", encoding="utf-8") as f:
        f.write(("\n" if torn else "") + line + "\n")
```

  - `snapshot`: pick the version and build the snapshot's text INSIDE a loop; `create_exclusive(self._path(version),
    text)`; on `FileExistsError` pick again; after 100 tries raise `SnapshotError("no free version number after 100
    tries -- another writer is claiming them as fast as this one")`. The seals and slots read-modify-write after it
    stays as it is: the lock is J2b's (W-9).
  - `_append`: `_project_io().append_line(self.journal_path, json.dumps(event, ensure_ascii=False))` (the line keeps
    today's text; text mode keeps today's line ending).
  - `autosound_ai.py`: one helper `_free_base(folder, stamp, role)` returns the first of `<stamp>-<role>`,
    `<stamp>-<role>-2`, `-3`, … for which neither `<base>.md` nor `<base>-package.md` exists; `_persist_review` and
    `_write_package` open their file with mode `"x"` and move to the next base on `FileExistsError`; `keep_raw`'s
    two files get the same suffix rule.

- [ ] **Step 4: Run** the selftests of `project_io`, `state/state`, `state/process`, `autosound_ai` — expect PASS.

- [ ] **Step 5: CHANGELOG** bullet; **commit**

```bash
git commit -am "#135: a version number is claimed, never overwritten; a torn journal line keeps the next event; review files never collide"
```

---

## Task 7: Strict process state — unreadable is not empty (#136; audit K-2, I-28 part; PLAN-AUDIT §3 J3a items 1–2)

**Files:**
- Modify: `RT/project_io.py` (+ `Unreadable`, `read_json`)
- Modify: `RT/state/process.py` (`Process.load` :974-986, `Process._write`, verbs `show` :3573, `session-close`
  :3653-3699, `_main`'s `except`)
- Modify: `RT/contract.py:185-197` (`check_process`), `RT/contract.py` `IMPORTABLE` (`Process.load(strict=False)`)
- Modify: `RT/state/process-schema.md` (the read rule)

**Interfaces:**
- Produces: `project_io.Unreadable(path, reason, repair=None)` — `.path`, `.reason`, `.repair`,
  `is_unreadable = True`; NOT a `ValueError` and NOT an `OSError`.
- Produces: `project_io.read_json(path, default=None, *, want=dict, repair=None)` — `default` if absent;
  `Unreadable` if present and empty, truncated, not UTF-8, not JSON, of the wrong top-level type, or a directory; a
  UTF-8 BOM is read.
- Produces: `Process.load(strict=False)`.

- [ ] **Step 1: Write the failing tests** (`RT/state/process.py` selftest)

```python
_UNREADABLE = {
    "empty": b"",
    "truncated": b'{"schema_version": 3, "pla',
    "cp1251": '{"schema_version": 3, "note": "тест"}'.encode("cp1251"),
    "a list": b"[1, 2]",
    "null": b"null",
}


def _state_dir_with(content):
    import tempfile
    d = os.path.join(tempfile.mkdtemp(), "process")
    os.makedirs(d)
    with open(os.path.join(d, "process-state.json"), "wb") as f:
        f.write(content)
    return d


def _check_unreadable_state():
    import contextlib, io as _io
    for label, content in _UNREADABLE.items():
        d = _state_dir_with(content)
        p = Process(d)
        assert p.load()["plan"] == [], f"{label}: the lenient read is an empty process"      # [1,2]/null crash today
        try:
            p.load(strict=True)
        except Exception as exc:
            assert getattr(exc, "is_unreadable", False), (label, exc)
        else:
            raise AssertionError(f"{label}: strict load read it")
        for argv in (["enter-phase", "-1"], ["show"], ["session-close"]):
            err = _io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(_io.StringIO()):
                rc = _main(["process.py", d, *argv])
            assert rc == 1 and "process-state.json" in err.getvalue(), (label, argv, rc, err.getvalue())
            with open(p.state_path, "rb") as f:
                assert f.read() == content, f"{label}: {argv[0]} rewrote the unreadable file"
        assert not any(e.get("type") == "session_closed" for e in p.events()), f"{label}: session-close wrote a close"
    # a fresh project has no file, and that is not a fault
    import tempfile
    fresh = os.path.join(tempfile.mkdtemp(), "process")
    assert _main(["process.py", fresh, "enter-phase", "-1"]) == 0
    # a BOM is an editor's marker, not damage
    d = _state_dir_with(b'\xef\xbb\xbf' + json.dumps(_empty_state()).encode())
    assert Process(d).load(strict=True)["schema_version"] == SCHEMA_VERSION
```

`RT/project_io.py` selftest: `read_json` over the whole matrix — absent → the default; empty, truncated, a cp1251
byte, `[1, 2]` (with `want=dict`), a directory → `Unreadable` naming the path; a UTF-8 BOM → read.

`RT/contract.py` selftest: a project whose `process/process-state.json` is `{"schema_version": 3, "pla` →
`check_process(d)` gives `exists: True`, `valid: False`, and an issue naming the file (today `valid: True`).

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: `Unreadable` and `read_json`** (append to `project_io.py`; extend its module docstring with the
  READS paragraph)

```python
class Unreadable(Exception):
    """A file that is THERE and cannot be read (K-2). Deliberately neither a `ValueError` nor an `OSError`: the method
    has dozens of `except (OSError, ValueError)` blocks that would turn it back into "empty". Matched by the attribute
    `is_unreadable` -- module copies make `except Unreadable` unreliable."""
    is_unreadable = True

    def __init__(self, path, reason, repair=None):
        self.path, self.reason, self.repair = path, reason, repair
        super().__init__(f"{path} {reason}" + (f" -- {repair}" if repair else ""))


def read_json(path, default=None, *, want=dict, repair=None):
    """The JSON in `path`; `default` if there is no such file; `Unreadable` for anything else that cannot be read.

    Absent is the one quiet case: a fresh project has no state yet. Empty, truncated, not UTF-8, not JSON, the wrong
    top-level type, a directory -- each raises `Unreadable` naming the file and, where one is known, the repair.
    A UTF-8 BOM is read: it is an editor's marker, not damage.
    """
    if os.path.isdir(path):
        raise Unreadable(path, "is a directory, not a file", repair)
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return default
    except OSError as exc:
        raise Unreadable(path, f"cannot be opened ({exc})", repair) from exc
    if not raw.strip():
        raise Unreadable(path, "is empty -- a write was cut off", repair)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Unreadable(path, f"is not UTF-8 (byte {exc.start})", repair) from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise Unreadable(path, f"is not valid JSON ({exc})", repair) from exc
    if want is not None and not isinstance(data, want):
        raise Unreadable(path, f"holds a JSON {type(data).__name__} where an object belongs", repair)
    return data
```

- [ ] **Step 4: `process.py`**
  - `Process._repair()` returns the repair line for the state file: for a non-UTF-8 file
    `rewrite it as UTF-8: python3 <rew_tool>/contract.py repair-encoding <project-dir>`; otherwise
    `restore the last committed copy: git -C <process-dir> checkout HEAD -- process-state.json (the journal keeps
    every event)`. (Pass it as `repair=`; for the UTF-8 case build it where `UnicodeDecodeError` is caught — give
    `read_json` a `repair_encoding=` keyword if that reads cleaner.)
  - `load(strict=False)`: read through `read_json(self.state_path, default=None, repair=self._repair())`. Lenient: an
    `Unreadable` becomes the empty process (this also ends today's `TypeError` on `[1, 2]` and `null`). Strict: it
    propagates. Then the existing merge with `_empty_state()` and the titles. Document both modes in the docstring.
  - `_write`: after `validate(state)`, if the file exists, `read_json(self.state_path, repair=self._repair())` first —
    a file that is there and cannot be read is never replaced by what a lenient read made of it. Then
    `atomic_write_json` (Task 5).
  - `show`: `p.load(strict=True)`. `session-close`: `p.open_work(state=p.load(strict=True))` before anything is written.
  - `_main`: after `except (ProcessError, IndexError)` add
    ```python
    except Exception as exc:  # noqa: BLE001 -- Task 11 makes this the catch-all
        if getattr(exc, "is_unreadable", False):
            print(f"error: {exc}", file=sys.stderr)
            return 1
        raise
    ```
- [ ] **Step 5: `contract.check_process`** — `proc.load(strict=True)` inside `try`; an exception with
  `is_unreadable`, or a `ProcessError`, gives `_entry("process/process-state.json", True, None, False, [str(exc)])`.
- [ ] **Step 6: Run** the selftests of `project_io`, `state/process`, `contract` — expect PASS. Update `IMPORTABLE`'s
  `Process.load()` entry to `Process.load(strict=False)` and run `scripts/contract-guard.py`.
- [ ] **Step 7: Docs and CHANGELOG** — `process-schema.md`: the read rule (lenient for readers, strict for writers,
  `show`, `session-close` and `contract.py check`). CHANGELOG `### Upgrading`: "A `process-state.json` that cannot be
  read is no longer overwritten with an empty process: every write verb refuses, names the file and the repair
  (#136, audit K-2). For TCC: `Process.load()` keeps its default; `load(strict=True)` raises an exception with
  `is_unreadable`."
- [ ] **Step 8: Commit**

```bash
git commit -am "#136: an unreadable process state is refused, never read as empty and overwritten"
```

---

## Task 8: Strict seals, drafts and gates; the report's last line; newer schemas (#136; audit T-10, T-11, T-13, T-21, I-28)

**Files:**
- Modify: `RT/state/state.py` (`_read_seals` :717-722, `seal_all` :744-755, `verify_seals`, `snapshot`'s
  `_project_rev` :342-350, `_read_snapshot_json` :465, the CLI's error handling)
- Modify: `RT/dsp_profile.py` (`load_profile` :336-338, `load_draft` :670-683, `save_profile` :459, the CLI's error
  handling)
- Modify: `RT/state/process.py` (`_require_intake` :383-413, `_flaw_map_entries` :203-216, `_require_profile_facts`
  :483-490)
- Modify: `RT/contract.py` (`render_report` :1016-1234, `_main` :1316-1334)
- Modify: `RT/project.py` (`Project.save` :825-843)

**Interfaces:**
- Consumes: `project_io.read_json`, `Unreadable` (Task 7).
- Produces: `render_report(report, gate=None)` — `gate` is `None`, `"intake"` (`--gate`) or `"phase0"`
  (`--phase0-gate`); every existing one-argument call keeps its output.

- [ ] **Step 1: Write the failing tests**
  - `state.py`: seal; truncate `seals.json`; `verify_seals(root)` raises (`is_unreadable`); `snapshot(...)` raises and
    `seals.json`'s bytes are unchanged; `python3 state.py <root> verify` exits 1 and names the file (today: `{}` —
    "nothing to verify"). Truncate `project.json`; `snapshot(...)` raises (today: rev 0 stamped into an immutable
    snapshot).
  - `dsp_profile.py`: a good `dsp_profile.json` and a corrupt draft; `set_field(...)` raises; the draft's bytes are
    unchanged (today: a blank draft is saved over it).
  - `process.py`:
    ```python
    def _check_gates_refuse_unreadable():
        <(a) contract.check_project patched to raise RuntimeError → enter-phase 0 exits 1, stderr says the intake check
         raised, nothing written; (b) the flaw map file holds `[1, 2]` → enter-phase 1 exits 1 (today a TypeError);
         (c) dsp_profile.json truncated → enter-phase 1 exits 1 (today it passes silently)>
    ```
  - `contract.py`:
    ```python
    def _check_gate_last_line():
        import tempfile
        report = check_project(tempfile.mkdtemp(), skip_rew=True)
        assert render_report(report, gate="intake").splitlines()[-1].startswith("**NOT READY"), "I-28"
        assert render_report(report).splitlines()[-1] in ("**OK — nothing to fix.**", "**Issues found — see above.**")
        assert "every row stands on a measurement" not in render_report(report, gate="phase0")
    ```
  - T-21, one test per reader and writer: `process-state.json` at schema 4 → `load(strict=True)` raises `ProcessError`
    naming 4 and 3; a ledger snapshot at schema 4 → `PresetHistory(...).load(v)` raises `SnapshotError`;
    `dsp_profile.json` at schema 4 → `load_profile` raises (`is_unreadable`, reason "is schema v4; this method reads
    v3"); `Project.save({"schema_version": 4, ...})` raises `ProjectError` with `project.json` unchanged;
    `save_profile` with schema 4 raises.
- [ ] **Step 2: Run — expect FAIL**
- [ ] **Step 3: Write the code**
  - `_read_seals`: `read_json(path, default={}, repair="restore it: git -C <root> checkout HEAD -- seals.json, or move
    it aside and run `state.py <root> seal` to rebuild it from the versions")`. `seal_all`, `verify_seals`,
    `repair_version` and `snapshot` let it propagate.
  - `_project_rev`: when `project.json` exists, read it with `read_json` (strict); `_project_json` itself stays lenient
    for `project_channels` (the sheet's join, where "not captured" is the right answer).
  - `_read_snapshot_json`: a `schema_version` that is an int above `SCHEMA_VERSION` raises `SnapshotError("<file> is
    schema v4; this method reads v3 -- update the method")`.
  - `load_profile(path)`: an absent file raises `FileNotFoundError` as today; otherwise `read_json(path, repair=…)`;
    a newer schema raises `Unreadable(path, f"is schema v{n}; this method reads v{SCHEMA_VERSION}", "update the method:
    /autosound-tuning:setup, the installer, or TCC's «Оновити Скіл»")`.
  - `load_draft`: the loop returns `load_profile(path)` for the first file that exists — no `try`, no `break`.
  - `save_profile` and `Project.save`: before stamping `schema_version`, refuse an incoming int above the module's
    `SCHEMA_VERSION` (`ValueError` / `ProjectError`), so a newer file is never written down to v3.
  - `_require_intake`: load `contract.py` with `_siblings().load("contract.py")`; a failure raises
    `ProcessError(f"phase {phase} is not entered: the intake check could not be loaded ({type(exc).__name__}: {exc})
    -- the install is broken, not the project")`. `check_project` raising raises `ProcessError(f"phase {phase} is not
    entered: the intake check raised {type(exc).__name__}: {exc}")` — an exception with `is_unreadable` propagates as
    itself. Replace the comment "a checker that raises must not become a wall" with the reason for the reversal
    (#136, audit T-10: a gate that cannot check let the phase in).
  - `_flaw_map_entries`: `read_json(path, default=None)`; `_require_profile_facts`: a profile that exists and cannot be
    read propagates.
  - `render_report(report, gate=None)`: the last line by the gate — `"phase0"`: `**READY for phase 0.**` if
    `report["map_ready"]` else `**NOT READY for phase 0 — flaw rows without evidence.**`; `"intake"`:
    `**READY: everything phase 0 needs is here.**` if `report["complete"]` else
    `f"**NOT READY for phase 0 — {len(report.get('missing') or [])} item(s) missing.**"`; `None`: today's line. The
    vacuous flaw-map line is printed only when the map has at least one row; with none it says
    `- flaw map: no rows yet.` (find the row count the report already carries).
  - `contract._main`: `render_report(report, gate="phase0" if "--phase0-gate" in argv else "intake" if gate else None)`.
  - `state.py`'s and `dsp_profile.py`'s CLIs: an exception with `is_unreadable` prints `error: <message>` to stderr and
    exits 1.
- [ ] **Step 4: Run** the selftests of `state/state`, `dsp_profile`, `state/process`, `contract`, `project` — expect
  PASS. `scripts/contract-guard.py` (signatures unchanged except additions).
- [ ] **Step 5: Docs** — CONTRACT.md item 7 → guaranteed (W-8); `process-schema.md:203` region: the read rule.
  CHANGELOG `### Upgrading`: seals, drafts, the gates, the last line of `contract.py check --gate`, newer schemas
  refused on read and never written down. For TCC: `load_profile` raises an exception with `is_unreadable` for a
  profile that exists and cannot be read, or is newer than this method.
- [ ] **Step 6: Commit**

```bash
git commit -am "#136: seals, drafts and the phase gates refuse what they cannot read; the gate report ends with its verdict; newer schemas are refused"
```

---

## Task 9: `rew_api` — three states, an honest transport, a write that reads back (#134; audit T-2, T-3, K-1; TCC's R3)

**Files:**
- Modify: `RT/rew_api.py` (`_open` :30-50, `_get`/`_body_request`/`_post`/`_put`/`_delete` :53-81,
  `get_measurements` :112, `find_measurement_id` :265-290, `set_filters` :473-493, `set_filter` :496-502)
- Modify: `skills/autosound-tuning/references/tooling/rew-api-quirks.md` (:26 describes `set_filter`, not
  `set_filters`; a "REW's three states" paragraph)

**Interfaces:**
- Produces, in `rew_api`:
  ```python
  class RewUnavailable(urllib.error.URLError):  rew_state = "unavailable"     # still a URLError / OSError
  class RewProtocolError(ValueError):           rew_state = "protocol"
  class RewWriteMismatch(RewProtocolError):     rew_state = "write_mismatch"
  class MeasurementNotFound(KeyError):          rew_state = "not_found"       # same words as today
  class AmbiguousTitle(KeyError):               rew_state = "ambiguous"       # message starts "Ambiguous"
  def rew_state(exc) -> "str | None"
  def _fetch(method, path, data=None)
  ```
  `_get(path)`, `_post(path, data)`, `_put(path, data)`, `_delete(path)` keep their signatures and call
  `urllib.request.urlopen(req, timeout=_TIMEOUT_S)` exactly once each, as `with … as r: r.read()` (TCC's
  `test_vendor_loader.py:50-65` pins that); a GET is still sent as a bare URL string (TCC's `fake_urlopen` tells a GET
  that way).

- [ ] **Step 1: Write the failing tests** (`rew_api` selftest; a small fake REW on `http.server`, port 0)

```python
class _FakeRew:
    """A local HTTP server answering what a test tells it to, counting requests (stdlib, port 0)."""
    def __init__(self, routes):
        import http.server, threading
        self.routes, self.count, self.filters = routes, 0, {}
        fake = self
        class H(http.server.BaseHTTPRequestHandler):
            def _answer(self, method):
                fake.count += 1
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                status, payload = fake.routes(method, self.path, body, fake)
                self.send_response(status)
                self.end_headers()
                self.wfile.write(payload)
            def do_GET(self): self._answer("GET")
            def do_POST(self): self._answer("POST")
            def do_PUT(self): self._answer("PUT")
            def log_message(self, *a): pass
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _with_base(url, fn):
    global BASE_URL
    saved = BASE_URL
    BASE_URL = url
    try:
        return fn()
    finally:
        BASE_URL = saved


def _check_words_pinned():
    """Today's words, pinned BEFORE the change: TCC reads them (curve_dialog, measurement_view)."""
    ms = {"1": {"title": "a (sw)"}, "2": {"title": "b (sw)"}, "3": {"title": "b (sw)"}}
    try:
        find_measurement_id("c (sw)", ms)
    except KeyError as e:
        assert e.args[0].startswith("No measurement titled 'c (sw)' (REW holds 3"), e.args[0]
    try:
        find_measurement_id("b (sw)", ms)
    except KeyError as e:
        assert e.args[0].startswith("Ambiguous: 2 measurements titled 'b (sw)'"), e.args[0]


def _check_closed_port():
    try:
        _with_base("http://127.0.0.1:1", get_measurements)
    except urllib.error.URLError as e:
        assert rew_state(e) == "unavailable", e
    else:
        raise AssertionError("a closed port answered")


def _check_fake_rew_answers():
    answers = {"/a": (500, b'{"message": "boom"}'), "/b": (500, b"[]"), "/c": (200, b"<html>no</html>"),
               "/measurements": (200, b"[]")}
    fake = _FakeRew(lambda m, p, b, f: answers[p])
    try:
        for path, want in (("/a", "REW said: boom"), ("/b", "HTTP Error 500")):
            try:
                _with_base(fake.url, lambda: _get(path))
            except urllib.error.HTTPError as e:
                assert want in str(e), (path, str(e))
        for fn in (lambda: _get("/c"), get_measurements):
            try:
                _with_base(fake.url, fn)
            except ValueError as e:
                assert rew_state(e) == "protocol", e
            else:
                raise AssertionError("a non-JSON or wrong-shape answer was returned as data")
    finally:
        fake.close()


def _check_filter_keys_refused():
    fake = _FakeRew(lambda m, p, b, f: (200, b'{"message": "Filters set"}'))
    try:
        _with_base(fake.url, lambda: set_filters("1", [{"index": 1, "type": "PK", "frequency": 100.0,
                                                          "gain": -3.0, "q": 1.0}]))
    except ValueError as e:
        assert "gain" in str(e) and fake.count == 0, (str(e), fake.count)
    else:
        raise AssertionError("a filter with REW-foreign key `gain` was sent")
    finally:
        fake.close()


def _check_read_back():
    def honest(method, path, body, f):
        if method == "POST":
            f.filters = json.loads(body)["filters"]
            return 200, b'{"message": "Filters set"}'
        return 200, json.dumps(f.filters).encode()
    def drops_gain(method, path, body, f):
        status, payload = honest(method, path, body, f)
        if method == "GET":
            return 200, json.dumps([dict(x, gaindB=0.0) for x in f.filters]).encode()
        return status, payload
    def truncates(method, path, body, f):
        status, payload = honest(method, path, body, f)
        if method == "GET":
            return 200, json.dumps(f.filters[:1]).encode()
        return status, payload
    bands = [{"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 1.41},
             {"index": 2, "type": "PK", "enabled": True, "frequency": 2000.0, "gaindB": -2.0, "q": 2.0}]
    for routes, want in ((honest, None), (drops_gain, "gaindB"), (truncates, "slot 2")):
        fake = _FakeRew(routes)
        try:
            _with_base(fake.url, lambda: set_filters("1", bands))
            assert want is None, f"a write REW did not take was reported done ({want})"
        except ValueError as e:
            assert want is not None and rew_state(e) == "write_mismatch" and want in str(e), (want, str(e))
        finally:
            fake.close()
```

- [ ] **Step 2: Run — expect FAIL** (no exception types; `[]` body → `AttributeError`; no key check; no read-back)

- [ ] **Step 3: Write the code** — the five classes and `rew_state()` with docstrings saying why each subclasses what
  it does (callers that caught `URLError`, `ValueError`, `KeyError` keep catching). Then:

```python
def _open(req_or_url):
    <unchanged, except the body parse:>
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = None
            said = (parsed.get("message") if isinstance(parsed, dict) else None) or body


def _fetch(method, path, data=None):
    """One request to REW, read whole -- the one place REW's states are told apart (#134, audit T-2).

    No answer (refused, timed out, reset) -> `RewUnavailable`; an HTTP error -> `HTTPError` carrying REW's words (it
    answered); an answer that is not JSON -> `RewProtocolError`. An empty body is `{}` for a write and a protocol error
    for a read.
    """
    url = BASE_URL + path
    if method == "GET":
        req = url
    else:
        body = None if data is None else json.dumps(data).encode()
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _open(req) as r:
            raw = r.read()
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError as exc:
        raise RewUnavailable(exc.reason, url) from exc
    except (TimeoutError, ConnectionError, socket.timeout) as exc:   # socket.timeout: Python 3.9
        raise RewUnavailable(exc, url) from exc
    if not raw:
        if method == "GET":
            raise RewProtocolError(f"REW answered GET {path} with nothing")
        return {}
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise RewProtocolError(f"REW answered {method} {path} with something that is not JSON: {raw[:80]!r}") from exc


def _get(path):
    return _fetch("GET", path)


def _body_request(path, data, method):
    return _fetch(method, path, data)


def _post(path, data):
    return _fetch("POST", path, data)


def _put(path, data):
    return _fetch("PUT", path, data)


def _delete(path):
    return _fetch("DELETE", path)
```

  - `RewUnavailable.__init__(self, reason, url=None)` keeps `reason`; `__str__` →
    `f"REW is not answering at {self.url or BASE_URL}: {self.reason}"`.
  - `get_measurements()`: the answer must be a dict whose values are dicts, else
    `RewProtocolError("REW's measurement list is not a map of measurements: <type>")`.
  - `find_measurement_id`: raise `MeasurementNotFound(<today's message>)` and `AmbiguousTitle(<today's message>)`.
  - `set_filters` / `set_filter`: `_refuse_foreign_keys(filters)` before anything is sent; the write; then
    `_read_back(mid, written)` — the GET answer may be a list of slot dicts or `{"filters": [...]}` (anything else is a
    `RewProtocolError` "cannot read the filters back"); each written slot (by `index`, else position + 1) must be
    there (`RewWriteMismatch("slot N is not there after the write -- REW keeps K filter slots and drops the rest")`),
    with the same `type` and `enabled`, and `frequency`, `gaindB`, `q` within `_READBACK_TOL`; a `type` of `"None"`
    checks the type only. Keep `set_filters`'s docstring text (TCC pins `gaindB`, `0 dB`, `POST` in it) and add the
    read-back paragraph.
    ```python
    #: REW's keys are index, type, enabled, frequency, gaindB, q. The method's own dialects use these instead, and REW
    #: drops an unknown key without a word -- a `gain` lands as a flat filter (K-1). A denylist until the live pass
    #: (Task 12) shows REW's full key set.
    _FOREIGN_FILTER_KEYS = ("gain", "gain_db", "freq", "f", "Q")
    #: (absolute, relative) tolerance per field when a write is read back. PROVISIONAL: Task 12 replaces these with
    #: the rounding REW is seen to apply.
    _READBACK_TOL = {"frequency": (0.1, 0.005), "gaindB": (0.05, 0.0), "q": (0.005, 0.01)}
    ```
  - `import socket` at the top (stdlib).

- [ ] **Step 4: Run** `python3 RT/rew_api.py --selftest`, and the selftests that use `rew_api`: `rew_stub`, `verify`,
  `flaw_map`, `path_check` — expect PASS.

- [ ] **Step 5: Docs, CHANGELOG** — `rew-api-quirks.md`: `:26` corrected (one filter per call is `set_filter`, PUT;
  `set_filters` sends the list, POST); a short "REW's three states" section. CHANGELOG `### Upgrading`, for TCC:
  the exception types and `rew_state`; `set_filters`/`set_filter` read back and raise `RewWriteMismatch`, so a test
  fake must answer `GET …/filters` with what was written (`tests/test_rew_api_shapes.py`, R3 — blocking for TCC's
  re-pin); a non-dict listing is a `RewProtocolError`.

- [ ] **Step 6: Commit**

```bash
git commit -am "#134: rew_api tells REW down from REW answering from a bad answer; a filter write is read back"
```

---

## Task 10: `verify` — unreachable is its own state (#134; audit T-2, T-4)

**Files:**
- Modify: `RT/verify.py` (`verdict` :59-166, `verify` :169-178, `summary` :395-409, `_USAGE`, `_main` :421-462)

**Interfaces:**
- Consumes: `rew_state` attributes from Task 9 (read with `getattr`, never by class).
- Produces: every verdict carries `"reachable"`: `True`, or `False` with `"exists": None` when REW did not answer;
  `"exists": None` with `"reachable": True` when REW answered an error. `summary()` gains `"unreachable"`;
  `"missing"` counts `exists is False` only. `verify.py` exits **69** when any verdict is unreachable.

- [ ] **Step 1: Write the failing tests** (`verify` selftest)

```python
def _check_unreachable_state():
    class Down(OSError):
        rew_state = "unavailable"
    saved = _api.get_measurements
    _api.get_measurements = lambda: (_ for _ in ()).throw(Down("refused"))
    try:
        vs = verify(["a (sw)"])
        assert vs[0]["reachable"] is False and vs[0]["exists"] is None, vs
        s = summary(vs)
        assert s["missing"] == 0 and s["unreachable"] == 1, s
        assert _main(["verify.py", "a (sw)"]) == 69
    finally:
        _api.get_measurements = saved


def _check_protocol_error_state():
    <get_measurements raising an error with rew_state "protocol" → reachable True, exists None, an issue
     starting "REW answered an error", summary["invalid"] == 1, exit 1>


def _check_ir_failure_on_a_sweep():
    """Audit T-4: an impulse read that fails on a swept capture is an issue, not silence. REW's own 404 is the one
    answer let through (a capture REW keeps no impulse for)."""
    <with the selftest's listing/get_fr stubs: get_impulse_response raising RuntimeError → the sweep's verdict has
     valid False and an issue "impulse response unreadable"; raising urllib.error.HTTPError(url, 404, ...) →
     valid True; raising an error with rew_state "unavailable" → reachable False>
```

- [ ] **Step 2: Run — expect FAIL**
- [ ] **Step 3: Write the code**
  - `_rew_down(exc)`: `getattr(exc, "rew_state", None) == "unavailable"`.
  - `_unreached(name, exc)`: the full verdict dict (`name`, `exists: None`, `applicable: True`, `kind: UNKNOWN`,
    `valid: False`, `stats: {}`) with `reachable: False` and `"REW unavailable: …"` when `_rew_down(exc)`, else
    `reachable: True` and `"REW answered an error: …"`.
  - `verdict`: `out` starts with `"reachable": True`; the listing failure returns `_unreached(name, exc)`; a `get_fr`
    failure that is `_rew_down` sets `reachable` False with "REW unavailable while reading the frequency response";
    the impulse read: `_rew_down` → `reachable` False and an issue; `getattr(exc, "code", None) == 404` → nothing
    (REW's answer); anything else → `"impulse response unreadable: {exc}"`.
  - `verify`: the listing failure returns `[_unreached(n, exc) for n in names]`; `_flag_outlier_sweeps` skips verdicts
    whose `exists` is not True (check it does).
  - `summary`: `missing = exists is False`; `unreachable = reachable is False`; `invalid` counts
    `exists is not False and reachable is not False and not valid`, minus the not-applicable ones.
  - `_main`: the marks gain `NO REW ` (unreachable) and `ERROR  ` (exists None, reachable True); the count line adds
    `, N unreachable` when there are any; exit `69` if any verdict is unreachable, else today's rule. `_USAGE`: "Exit
    0 when every title is valid, 1 otherwise, 69 when REW did not answer."
- [ ] **Step 4: Run** the `verify` selftest; `path_check`'s (it asserts the summary line's prefix) — expect PASS. The
  `_DECIDED_ASKS` key `("verify.py", "verdict", "get_fr")` stays valid (the read stays in `verdict`).
- [ ] **Step 5: CHANGELOG** (`verify.py` exits 69 with REW down; `reachable`, `exists: None`); **commit**

```bash
git commit -am "#134: verify reports REW down as its own state and exits 69; a failed impulse read on a sweep is an issue"
```

---

## Task 11: `process.py` — the exit table, a catch-all, the flags, `--help`, superseded rows, no invented captures (#134: T-1, T-23, N17, N19; #138: I-15)

**Files:**
- Modify: `RT/state/process.py` (constants near `ProcessError` :157; `check_captures` :2123-2192; `unusable_captures`
  :2212-2231; `_close_capture` :2263-2276; `_USAGE` :2588-2692; `_main` :3564-4067; the `capture-check` print loop
  :3745-3773)
- Modify: `RT/state/process-schema.md` (exit table; `round.checks`), `RT/CONTRACT.md` (item 2 → guaranteed)

**Interfaces:**
- Produces: `EXIT_OK = 0`, `EXIT_NO = 1`, `EXIT_USAGE = 2`, `EXIT_REW_UNAVAILABLE = 69`, `EXIT_UNEXPECTED = 70`,
  `EXIT_BUSY = 75` (reserved); `class UsageError(ProcessError)` (`exit_code = 2`);
  `class RewUnavailableError(ProcessError)` (`exit_code = 69`, `rew_state = "unavailable"`); `VERB_FLAGS`
  (verb → tuple of flag literals); a round's `checks` map (`{title: verified}`).

- [ ] **Step 1: Write the failing tests** (`process` selftest; `_cli` is the existing subprocess helper at ~:2957)

```python
def _check_exit_table():
    import tempfile
    d = os.path.join(tempfile.mkdtemp(), "process")
    Process(d).enter_phase("0")
    r = _cli_env(d, ["capture-protective", "w-L", "--hp", "abc", "LR", "24"])
    assert r.returncode == 70 and "unexpected ValueError" in r.stderr and "Traceback" in r.stderr, (r.returncode, r.stderr)
    Process(d).start_capture("1", expected=["a (sw)"])
    before = {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d)}
    r = _cli_env(d, ["capture-check"], REW_API_URL="http://127.0.0.1:1")
    assert r.returncode == 69, (r.returncode, r.stderr)
    assert {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d)} == before, "REW down wrote something"
    r = _cli_env(d, ["capture-close"], REW_API_URL="http://127.0.0.1:1")
    assert r.returncode == 0, "capture-close closes on the record alone with REW down, as before"


def _check_unknown_flags():
    import tempfile
    d = os.path.join(tempfile.mkdtemp(), "process")
    Process(d).enter_phase("0")
    r = _cli_env(d, ["capture-start", "1", "a (sw)", "--origni", "x"])
    assert r.returncode == 2 and "--origni" in r.stderr and "usage: process.py" not in r.stderr, r.stderr
    assert Process(d).load().get("capture") is None, "an unknown flag opened a round"
    Process(d).add_step("1.1", "a"); Process(d).add_step("2.1", "b")
    assert _cli_env(d, ["skip", "1.1", "--superseded-by=2.1"]).returncode == 0
    step = next(s for s in Process(d).load()["plan"] if s["id"] == "1.1")
    assert step.get("superseded_by") == "2.1", step
    # every flag literal the dispatcher reads is in VERB_FLAGS (TCC finds them in this file's text)
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    main = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_main")
    literals = {n.value for n in ast.walk(main) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value.startswith("--") and len(n.value) > 2 and n.value[2].isalpha()}
    known = {f for flags in VERB_FLAGS.values() for f in flags} | {"--help"}
    assert literals <= known, sorted(literals - known)


def _check_help_writes_nothing():
    """#138 I-15: `<verb> --help` prints that verb's lines and writes nothing -- for every verb."""
    import tempfile, ast
    d = os.path.join(tempfile.mkdtemp(), "process")
    Process(d).enter_phase("0")
    Process(d).start_capture("1", expected=["a (sw)"])
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    main = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_main")
    verbs = sorted({c.comparators[0].value for c in ast.walk(main)
                    if isinstance(c, ast.Compare) and isinstance(c.left, ast.Name) and c.left.id == "cmd"
                    and isinstance(c.comparators[0], ast.Constant)})
    snapshot = lambda: {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d)}
    before = snapshot()
    for verb in verbs:
        r = _cli_env(d, [verb, "--help"])
        assert r.returncode == 0 and verb in r.stdout, (verb, r.returncode, r.stdout[:200], r.stderr[-200:])
    assert snapshot() == before, "a --help wrote to the project"


def _check_superseded_not_taken():
    """N17: a superseded row is a typo's trace, not a measurement -- in every reader of `taken`."""
    <round expecting "a (sw)"; record_capture("a (sw)") then supersede_capture("a (sw)", "a2 (sw)"); assert
     "a (sw)" in unusable_captures(); the capture_closed event's `taken` lacks "a (sw)"; the capture-check print
     loop's line for it is "UNUSABLE a (sw) — superseded by a2 (sw)">


def _check_check_never_invents_taken():
    """T-1: a check records a verdict for every title, and creates a `taken` row only for a title REW holds (#77)."""
    class Verifier:
        def verify(self, titles):
            return [{"name": "a (sw)", "exists": True, "reachable": True, "valid": True, "issues": [], "stats": {}},
                    {"name": "b (sw)", "exists": False, "reachable": True, "valid": False,
                     "issues": ["No measurement titled 'b (sw)' (REW holds 1)"], "stats": {}}]
    <round expecting both; check_captures(verifier=Verifier()); assert "a (sw)" in taken and "b (sw)" not in taken;
     round["checks"]["b (sw)"]["exists"] is False; "b (sw)" in capture_outstanding(); the CLI print loop's line for b
     is "UNUSABLE b (sw) — No measurement titled 'b (sw)' (REW holds 1)">
```

  `_cli_env(d, argv, **env)` is `_cli` with extra environment: write it beside `_cli` if it does not exist.

- [ ] **Step 2: Run — expect FAIL**
- [ ] **Step 3: Write the code**
  - The constants and the two error classes, with the comment block: 0/1/2 keep their meaning; 69, 70 and 75 are
    sysexits' (`EX_UNAVAILABLE`, `EX_SOFTWARE`, `EX_TEMPFAIL`), and no tool of the method returned them before
    (PLAN-AUDIT §8 M1).
  - `VERB_FLAGS`: built by reading every branch of `_main` — each `"--…"` literal it compares against, per verb (the
    code map's list: `add-step` --project --covers · `skip` --superseded-by · `reviewer` --review --mode ·
    `decision` --invalidates · `session-close` --check · `capture-start` --origin --step --under --level
    --level-read-as --start --phase --optional --plan · `capture-check` --session · `capture-import` --bind --late
    --knob · `amp-gain` --measured --amends --note · `capture-knobs` --amend --reason · `capture-protective` --source
    --amend --reason --hp --lp · `listening-verdict` --pair --text --route --ledger-version --note ·
    `listening-verdicts` --track --characteristic --ledger-version --bank · `handoff` --json · `capture-close`
    --no-rew · and `check`/`show` if they read `--json`). Then compare with every flag TCC sends
    (`~/dev/autosound/tcc/src/autosound_tcc/core/process_writer.py`, read-only): each must be listed; list the TCC
    flags in a selftest tuple `_TCC_FLAGS` (with the TCC commit you read) and assert they are all known.
  - `_args_checked(cmd, args)`: a token is flag-shaped when it starts with `--` and its third character is a letter;
    `--flag=value` becomes `--flag`, `value` when `--flag` is the verb's; any other flag-shaped token raises
    `UsageError(f"{cmd} does not take {flag}" + (f" -- it takes {', '.join(known)}" if known else " -- it takes no
    flags"))`. The message never contains `usage: process.py` (TCC's `_refuse_if_too_old` reads that as "the method
    is too old"). A bare `--` and non-flag words pass. Branches that matched a flag by `startswith` (`reviewer`,
    `decision`) now receive the split form: check each still reads `--flag value`.
  - `--help`: `process.py --help` and `process.py <dir> --help` print `_USAGE` to stdout and exit 0;
    `<dir> <verb> --help` (or `-h`) prints `_verb_usage(verb)` — every line of `_USAGE` that belongs to the verb
    (its own lines, which can be split across the text, and their indented continuations) — and exits 0, before
    `Process(root)` is touched; an unknown verb prints `_USAGE` to stderr and exits 2, as today.
  - `_main`'s handlers:
    ```python
    except ProcessError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", EXIT_NO)
    except IndexError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NO
    except Exception as exc:  # noqa: BLE001 -- the catch-all (#134, audit T-23): a bug exits 70, not 1
        if getattr(exc, "is_unreadable", False):
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_NO
        if getattr(exc, "rew_state", None) == "unavailable":
            print(f"error: {exc} -- nothing was written", file=sys.stderr)
            return EXIT_REW_UNAVAILABLE
        traceback.print_exc()
        print(f"error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_UNEXPECTED
    ```
  - `check_captures`: after `verifier.verify(wanted)`, any verdict with `reachable is False` raises
    `RewUnavailableError("REW did not answer (<its first issue>) -- nothing was recorded; start REW and run
    capture-check again")` before anything is written. For each verdict: `round_.setdefault("checks", {})[title] =
    dict(verified, exists=verdict.get("exists"))`; the `taken` row is created only when `verdict.get("exists") is True`
    (the rule of #77), and updated when the title is already there. Rewrite the docstring's paragraph accordingly.
  - The `capture-check` print loop: a title whose `taken` row is superseded prints `UNUSABLE <title> — superseded by
    <new title>`; otherwise the verdict comes from `taken[title]["verified"]`, else `checks[title]`. The Ukrainian
    lines stay as they are.
  - `unusable_captures`: `entry = taken.get(title) if _is_taken(round_, title) else None`.
  - `_close_capture`'s event: `taken=sorted(t for t in round_.get("taken", {}) if _is_taken(round_, t))`.
- [ ] **Step 4: Run** the `process` selftest; then `contract`, `path_check` (they drive `process.py`) — expect PASS.
- [ ] **Step 5: Docs** — `_USAGE` gains the exit table: `exit  0 done · 1 refused · 2 usage · 69 REW did not answer,
  nothing written · 70 unexpected error (a bug: the traceback is above it) · 75 project busy (reserved)`.
  `process-schema.md`: the same table and `round.checks`. CONTRACT.md item 2 → guaranteed (W-8). CHANGELOG
  `### Upgrading`: the exit codes; an unknown flag is exit 2 (it used to become a title or reason text); `--flag=value`
  is read; `<verb> --help` writes nothing; `capture-check` exits 69 with REW down and records nothing; a check never
  creates a `taken` row for a title REW does not hold (`round.checks` holds its verdict); superseded rows count
  nowhere as taken. Tell the issue #138 thread that I-15 is built here.
- [ ] **Step 6: Commit**

```bash
git commit -am "#134: process.py's exit table and catch-all; unknown flags refused; --help writes nothing; a check never invents a capture (I-15 of #138)"
```

---

## Task 12: The live pass at REW (#134; PLAN-AUDIT §1 question 7) — the controller with the Arbiter

Not a subagent task: it needs REW and the Arbiter, about 15 minutes.

- [ ] **Step 1:** ask the Arbiter to open REW on this Mac with one swept measurement, any title.
- [ ] **Step 2:** in a throwaway script, against the real REW:
  1. `get_measurements()`; save the raw answer as `RT/testdata/rew/measurements.json` (titles anonymised to `m1…`).
  2. `set_filters(mid, [{"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 1.41}])`;
     save `get_filters(mid)`'s raw answer as `RT/testdata/rew/filters-after-pk.json`. Read the stored values: replace
     `_READBACK_TOL` with REW's observed rounding (with a comment naming the file it came from), and the read-back
     shape handling with the one REW sends.
  3. The gain trap: the same filter with `gain` instead of `gaindB` is refused before any request.
  4. Clear the slot: `set_filters(mid, [{"index": 1, "type": "None", "enabled": True}])`; check it reads back.
  5. Save one `GET /measurements/<an RTA or a non-IR id>/impulse-response` error answer, if REW has one, as
     `RT/testdata/rew/impulse-404.json` (status and body).
  6. The Arbiter quits REW; `process.py <throwaway project>/process capture-check` exits 69 and the files are unchanged.
- [ ] **Step 3:** a `rew_api` selftest `_check_recorded_answers()` replays the three files through `_FakeRew`: the
  listing parses, the PK read-back passes, the 404 is recognised by `verify` as "no impulse".
- [ ] **Step 4: Commit**

```bash
git commit -am "#134: the live pass at REW -- the filters' read-back shape and rounding recorded as goldens"
```

### Group review — silent failures (Tasks 5–12)

- `pr-review-toolkit:silent-failure-hunter` and `pr-review-toolkit:pr-test-analyzer` (sonnet), both on
  `git diff <the commit before Task 5>..HEAD`. Their findings: one fix round, each fix with its test.
- Fable: the final review of the same diff — `project_io`, `Process.load`/`_write`, the gates, the catch-all,
  `rew_api`'s transport and read-back.
- `scripts/run-selftests.sh | tail -1` → `all N checks passed`.

---

## Task 13: Text checks, and the sentences they hold (#138: I-1, I-11, I-20, I-12 interim)

**Files:**
- Modify: `scripts/docs-check.py` (four rules, their selftest cases; `RULES` at :386-393)
- Modify: `skills/autosound-tuning/SKILL.md:82, :152`; `references/tooling/installation.md:7-46`;
  `RT/project.py:942-944, :1438-1440`; `references/phases/phase_1_foundation.md:27, :48-53`;
  `references/tooling/rew-api-quirks.md:44-56`; `references/core/diagnostic-techniques.md:61-66`;
  `references/phases/phase_{0_baseline,1_foundation,2_eq,3_control}.md:5`

**Interfaces:** each rule is `rule_x(root) -> list[str]`, appended to `RULES`, with a selftest case that names the
regression and one that passes the fix (`docs-check.py`'s own pattern). `_selftest` ends `assert run(ROOT) == 0`, so
each rule and its text fix land in ONE commit.

- [ ] **Step 1 (I-1): rule `plugin-route`** — no file in `_md_files` says `pinned at 2.8.3` while
  `.claude-plugin/marketplace.json`'s plugin `ref` starts with `v3.` (read it like `rule_install_ref` reads the
  front page). Text: `SKILL.md:152` → "Install and update (the installer, or the plugin from the catalog plus
  `/autosound-tuning:setup`), which copy is running, troubleshooting." `installation.md` §1–§3: two supported routes —
  §1 the installer (unchanged), §2 the plugin: `/plugin install autosound-tuning`, then `/autosound-tuning:setup`
  once in the first session (it installs the libraries and the tools and checks the copy against the signed tag);
  the bullet at `:42-45` (plugin = 2.8.3, offer to uninstall) is replaced by "As a Claude Code plugin: supported —
  run `/autosound-tuning:setup` once if the session says it is not set up"; `:46` (a hand copy drifts) stays.
  Run red (rule, old text), then green (new text); commit.
- [ ] **Step 2 (I-11): rule `owner-sentence`** — none of "sentence is still owed", "still wants the owner's own
  sentence", "would close the gate on nobody's words" in `_md_files` and in `rew_tool/project.py`'s text. Text:
  `SKILL.md:82` → "It invents no fact. The owner's symptom line is optional — a communication line for the finished
  tune; nothing about it gates phase 0 (the Arbiter's ruling, 2026-09-08)." The same meaning in `project.py`'s
  `catch-up` usage (`:1438-1440`) and `catch_up`'s docstring (`:942-944`). Red, green, commit.
- [ ] **Step 3 (I-20): rule `arrivals`** — none of "MUST inspect", "MANUALLY INSPECT IMPULSE GRAPHS",
  "manually-inspected IR onsets" in `phase_1_foundation.md`, `rew-api-quirks.md`, `diagnostic-techniques.md`; and
  "The tools read arrivals" present in `phase_1_foundation.md` and `rew-api-quirks.md`. Text, one sentence in each of
  the three files: "The tools read arrivals (`predict --align`, `windows.py`, `analyze-joints`; `arrival_triangulate`
  is the function behind `predict --align`, not a command); the REW GUI is the cross-check when a tool says
  ILL-POSED or UNVERIFIED." The gate (`phase_1_foundation.md:27`) → "arrival TA set from the tools' reading,
  cross-checked in the GUI where a tool says ILL-POSED or UNVERIFIED". `:48-53`'s "MUST inspect … manually" paragraph
  and `diagnostic-techniques.md:61-65`'s copy are replaced by the sentence; `rew-api-quirks.md:47`'s heading goes,
  `:53` ("take the API TA into work by default") stays. (FAQ:130 is S5's, W-10.) Red, green, commit.
- [ ] **Step 4 (I-12 interim): rule `one-path-banner`** — the four phase files' line 5 is the same text and none of
  them says "If Phase −1 chose". Text, each file's line 5: "**One path.** The order of work is
  [`virtual-first.md`](references/phases/virtual-first.md)'s; the sections of this file marked *iterative* apply only
  when its Degradation section routes here. This file stays the authority on every gate." Red, green, commit.

Commit messages: `#138: <rule> -- <what it holds>` (four commits).

---

## Task 14: Step numbers that point where they say (#138: I-6, P6)

**Files:**
- Modify: `references/phases/virtual-first.md` (`:272` the second 1.7 → **1.8**; pointers `:48, :93, :146, :198,
  :204`), `phase_1_foundation.md:7`, `phase_2_eq.md:115`, `phase_4_listening.md:47`, `SKILL.md:141`,
  `references/core/analysis-playbook.md:22`, `references/core/estimator-scope.md:115`,
  `references/core/capabilities.md:67, :136`, `references/tooling/rew-tool-docs.md:87, :93`,
  `references/patterns/listening-cheat-sheet.md` (legend `:47`, rows `:52-68`) and its `.uk/.de/.pl`
- Modify (code): `RT/resonalyze_engine.py:1778-1782` and its selftest `:2771, :2777`; `RT/eq_propose.py:345, :415`;
  `RT/xover_candidates.py:15`
- Modify: `scripts/docs-check.py` (rule `step-ids`)

**The mapping, by meaning:** the joints 1.3 → **1.5**; the levels 1.4 → **1.6**; the coarse EQ 2.1 → **1.4**; the
variants' choice (the second 1.7) → **1.8**; the crossovers stay **1.3**; the fine EQ over MMM stays **3.3**; c16's
"protection filters (1.2)" → **−1.3 protective filters**. Read each sentence before changing its number: the number
follows what the sentence is about, not a search-and-replace.

- [ ] **Step 1: rule `step-ids`** (red on today's text): (a) no duplicate step id in `virtual-first.md` (bullets
  `- **<id>**`, U+2212 read as `-`); (b) a pointer written `<id> <word>` in `SKILL.md`, `references/phases/`,
  `references/core/` and the English cheat sheet resolves: the id exists and the word is in that step's bullet text;
  (c) every route cell of the English cheat sheet is `<id> <word>` (e.g. `1.5 joints`), never a bare number; (d) the
  ids in each translated cheat sheet's route cells equal the English ones, row by row.
- [ ] **Step 2: the text** — every pointer in the file list as `<id> <name>` in the mapping above (e.g. `SKILL.md:141`
  → "`predict --align` (1.5 joints) · `eq_propose` (1.4 coarse EQ / 3.3 fine EQ over MMM)"); the English cheat
  sheet's legend and rows c01–c17 (c01 → "desk 1.5 joints / 1.6 levels"; c02 → "1.6 levels / 1.3 crossovers"; c03 →
  "1.5 joints; 1.6 levels"; c05, c11 → "1.5 joints"; c06 → "1.3 crossovers / 1.6 levels"; c07, c09, c10, c15 → their
  joint as "1.5 joints", the rest unchanged; c14 → "1.5 joints / 1.6 levels; 3.3 fine EQ"; c16 → "−1.3 protective
  filters").
- [ ] **Step 3: the translations** — the uk/de/pl cheat sheets' legend and route cells, by the Advisor:
  `python3 skills/autosound-tuning/scripts/autosound_ai.py ask` with the English diff of the cheat sheet and the
  translated file, asking for those cells only, in the words each file's legend already uses («стики», «рівні», …).
  The session checks: rule (d) passes, nothing else in the file moved (`git diff --stat`).
- [ ] **Step 4: the code** — `resonalyze_engine.py` prints "(1.8, predict)" (and its selftest asserts it);
  `eq_propose.py:415` prints "(1.5 joints)"; `eq_propose.py:345`'s comment "(1.6 levels)"; `xover_candidates.py:15`
  "(1.5 joints)". Run those three selftests.
- [ ] **Step 5:** `python3 scripts/docs-check.py --selftest` and the tree — PASS; **commit**

```bash
git commit -am "#138: step pointers name their step -- 1.5 joints, 1.6 levels, 1.8 the choice; a rule holds them"
```

---

## Task 15: One recipe, one answer per rule (#138: I-7, I-16, I-23, I-29; the instructions report's §5.1 rows)

**Files:** the documents named per row below; `scripts/docs-check.py` (rule `no-capture-start-literal`);
`skills/autosound-tuning/scripts/autosound_ai.py:2815-2820` (the doctor's engine line).

Resolutions — the source of truth is named in each row; where it is the code, the text follows the code:

| row | resolution | edit |
|---|---|---|
| I-7 one recipe | `capture-session-sheet.md`'s Block 0 is the home: `process.py <project>/process enter-phase 0` → `naming.py <project> next-series` → N → `process.py <project>/process capture-start <N> --plan [--level "<dB rel. max>"]` | Block 0 (`:44-49`) becomes that; `SKILL.md:103`, `phase_0_baseline.md:70-79`, `virtual-first.md:113-117`, `phase_-1_intake.md:165` each become a one-line pointer that keeps the literal `capture-start` (`rule_capture_round_opened` needs it). Series are `_N`, never zero-padded: `virtual-first.md:129,130,137,138,366,370`, `capture-session-sheet.md:58,59,86-89`, `naming-and-structure.md:86`. The Phase-2 row of `naming-and-structure.md:96` says "iterative fallback only — virtual-first captures nothing in Phase 2" (`virtual-first.md:353-354`). Rule `no-capture-start-literal`: no `capture-start\s+1\b` in `references/phases/*.md`. |
| I-16 the doctor | the step closes on the doctor's exit code | `project-intake.md:43-46`: `doctor > <project>/rew_analitic/reviewer-check.md; rc=$?`; on 0 the `reviewer … -1.2 --review …` and `done -1.2 …` lines as today; otherwise `block -1.2 "<the first ✗ line of reviewer-check.md>"`. `:53-54`'s `tee` sentence follows. `autosound_ai.py:2817`: the engine line stops claiming Phase 1.3 needs it ("Він не обовʼязковий: Фаза 1.3 обходиться без нього (virtual-first.md)") — Ukrainian, like every doctor line |
| I-23 the interview | the form is the interview in a terminal | `project-intake.md:29-30` → "With no front-end, hand the person the form's URL (`intake_form.py serve`); ask in chat only what the form marks *not machine-readable*." |
| I-29 output style | scope each rule | `SKILL.md:221` → "A reply **after a desk computation** ends with one of two things (#58 P12): …"; `:220` → "no emoji in a table of values he types; no praise; one screen, then «деталі?»" |
| 7 boost | the tool's rule (`eq_propose.py:38`): ≤ +6 dB per band, no boost unless `--allow-boost` AND the excess-phase gate | `SKILL.md:118`, `phase_2_eq.md:28`, `happy-paths.md:39`, `virtual-first.md:353` say exactly that; `phase_1_foundation.md:105`, `virtual-first.md:208, :328` ("zero boosts") name the step they are about (read `eq_propose.py`'s `--part` handling: if the coarse EQ refuses boosts outright, they say "1.4 coarse EQ: cuts only") |
| 13 current DSP value | both, in order | `SKILL.md:97` and `process-control.md:107`, one sentence: "The ledger HEAD says what was banked; the DSP screen says what is set now — read the screen before computing a delta, and record a difference rather than average it." |
| 14 knob state | `capture-knobs` is the record (the tools and TCC read it) | `process-control.md:109-113` → "The state outside the DSP (master · sub · effects · fill channel) is recorded with `process.py capture-knobs` for the round — the record the tools read. A copy in the measurement's notes helps a person reading REW; it is not the record." |
| 15 Time Offset | the readers do not take one (`resonalyze_ir.py:180-183` refuses a non-zero `timingOffset`; captures are loopback at offset 0, `capture-session-sheet.md:19`) | `phase_1_foundation.md:43-44, :115`, `diagnostic-techniques.md:69`, `rew-api-quirks.md:52` → "Do not set a Time Offset on a measurement: the tools read arrivals with loopback timing at offset 0, and `resonalyze_ir` refuses a measurement whose offset is not 0." |
| 19 taste | `intake.py:1220-1249`'s `when` per field | `phase_-1_intake.md:15` → "`preference-profile.md` may start as a stub: Phase 0 asks the music and what is loved most, Phase 4 the reference tracks, Phase 5 the taste axes — each field's `when` in `intake.py` names its step." |
| 20 language, −1.2 | the code's ids (`intake.py:881,900`): −1.1 the language (`project.json` + a decision), −1.2 the reviewer | `project-intake.md:38-40`: the step closes on `project.json`; `SKILL.md:72` adds the `decision "dialogue language" "<code>" -1.1` line; `virtual-first.md:96-98`: −1.1 names the language among the intake's outputs, a new **−1.2** bullet is the reviewer channel (one live `doctor` run, recorded), the "new DSP" bullet becomes **−1.5**; `process-schema.md:190`'s example uses an id that means what its text says |
| 21 stop order | one home, `SKILL.md:86-90` | the order there: `session-close --check` (what is open) → record (captures, steps, decisions, `apply.propose`, the ▶️ CONTINUE line) → `session-close` → the car's exit checklist (DSP config backup) → the GitHub issue if any → start nothing new. `phase_4_listening.md:75` and `process-control.md:63-97` point to it |
| 22 the generated sheet | `dsp-state-current` is generated | `phase_3_control.md:17`'s gate → "changelog and audit-trail updated; `dsp-state-current` re-rendered (generated, never edited)" |
| 23 Phase-3 titles | the grammar (`naming-and-structure.md:97`) | `phase_3_control.md:29-33` → `sw_final (rta)`, `w-L_final (rta)`, `Ws_final (rta)`, `sw+Ws_final (rta)`, `ALL_final (rta)` |
| delays vs all-pass | the newer, tool-backed order (`virtual-first.md:210-213`, `predict --align`) | `phase_2_eq.md:74` → "Joints: delay × polarity first (`predict --align`, on the DSP's delay grid), an all-pass only where a null remains"; `:20` → "re-shifting a channel's delay in Phase 2 to chase phase (it breaks the TA set in 1.5 joints)" |
| review before/after banking | `state/apply.py`'s `propose(…, reviewed=)` and `attest` | read which states a version passes through and where `reviewed=` is required; `happy-paths.md:40` and `virtual-first.md:357-359` say that order |
| RTA FFT | the sheet is the home | `analysis-playbook.md:51`'s example names its sample rate ("64k at 48 kHz, 128k at 96 kHz") and points to the sheet; the overlap numbers stay (an acoustic choice, PLAN-AUDIT §6) |
| hand-copy install | `installation.md` | `feedback-loop.md:50` → "Installing for new hands: the installer or the plugin (`references/tooling/installation.md`); a hand copy drifts." |
| sweep level | two quantities, named | `project-intake.md:104` → "the generator's OUTPUT level (e.g. −20 dBFS in REW's generator)"; `capture-session-sheet.md:52`, `virtual-first.md:125` → "the INPUT peak −5…−10 dBFS (REW's input meter); the output level is a separate number" |
| TCC's facts | TCC's plan (B9, B10) | `SKILL.md:98`'s tool map: add `session_close`, `set_target`, `capture_knobs`; `capture-protective` and `listening-verdict` are the GUI's; `reviewer` is written by `call_critic`. `project-intake.md:16-17`, `phase_-1_intake.md:41`: "`reviewer.reachable` is null when no reviewer is configured; then `model` and `ready` are absent" |

- [ ] **Step 1:** rule `no-capture-start-literal`, red; the I-7 row; green; commit.
- [ ] **Step 2:** the rest of the table, one commit per row or per pair of rows, `python3 scripts/docs-check.py`
  green after each. `autosound_ai.py`'s selftest after the doctor line.
- [ ] **Step 3:** CHANGELOG bullets for the method's text.

### Group review S1

One sonnet reader per §5.1 row pair: "do the two copies now say the same thing, and does it match the source of
truth named in Task 15's table?" Then `scripts/run-selftests.sh | tail -1`.

---

## Task 16: Close the wave

- [ ] **Step 1:** `scripts/run-selftests.sh | tail -1` → `all N checks passed`.
- [ ] **Step 2:** CHANGELOG `## [Unreleased]` reads as the release note (not a one-liner); `### Upgrading` complete.
- [ ] **Step 3:** push `wave-2026-10-06`; one PR to `main` with the wave's description; the full CI on it; and
  `gh workflow run checks --ref wave-2026-10-06` (the Windows job: `project_io`'s retry and the DPAPI writer on
  Windows).
- [ ] **Step 4:** merge `--ff-only`, push `main`.
- [ ] **Step 5: the candidate** — `scripts/tag-check.sh --candidate v3.1.2`, then the signed tag `beta-v3.1.2-rc1` on
  `main`'s HEAD (the release guard's refusals name the path; follow them).
- [ ] **Step 6: TCC** — a bus ticket to `tcc`: run your suite with `AUTOSOUND_SKILL_DIR` at `beta-v3.1.2-rc1`
  (PLAN-AUDIT §4 N2). What changes for TCC: the exit codes (69, 70; unknown flags → 2), `rew_api`'s exception types
  and `rew_state`, `set_filters`/`set_filter` read back (your `test_rew_api_shapes.py` fake must answer `GET …/filters`
  with what was written — R3), `get_measurements` refuses a non-dict listing, `load_profile` raises `is_unreadable`,
  `Process.load(strict=)`, `round.checks`, `CONTRACT_VERSION = 1`, `contract.py version`.
- [ ] **Step 7: the release, on the Arbiter's word after TCC's answer** — the bookkeeping commit (`## [v3.1.2]`,
  `plugin.json` 3.1.2, the front-page install lines), `scripts/tag-check.sh v3.1.2`, the signed tag, the milestone and
  #133–#138 closed with `git tag --contains <commit>`; `docs/TODO.md` S-101 → `done` with the tag's command line.
