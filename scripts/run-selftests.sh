#!/usr/bin/env bash
# Run every check of this repo: the scripts' own selftests, every rew_tool module's selftest, ruff.
#
# One runner so CI and a person execute the SAME thing. It must be able to FAIL (#133, audit T-28):
#   * every rew_tool module is in scripts/selftests.txt with the argv its selftest takes, or on a `skip` line with
#     the reason -- a module in neither fails the run (no silent skip); a skip line is printed, and one whose file
#     has a selftest of its own fails;
#   * a selftest passes on exit 0 AND a last output line saying OK: a usage text that exits 0 is not a pass;
#   * each one runs under a timeout (SELFTEST_TIMEOUT seconds, default 300) that stops the check AND everything it
#     started -- perl's alarm over a process group, since macOS has no `timeout`;
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
unset PYTHONOPTIMIZE   # -O strips every assert, and a selftest whose asserts are gone passes: never inherited

# How a check's LAST line is read -- by run_one below, and by the runner's selftest about its own line: one saying
# SKIPPED (as eq_gate/project_repo print it) did not run; one saying OK passed. grep reads to EOF (no -q).
says_not_run() { printf '%s\n' "$1" | grep -w 'SKIPPED' >/dev/null; }
says_ok()      { printf '%s\n' "$1" | grep -w 'OK' >/dev/null; }

if [ "${1:-}" = "--selftest" ]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  mkdir -p "$tmp/t" "$tmp/t2"
  printf 'print("selftest OK -- good")\n'                    > "$tmp/t/good.py"
  printf 'print("usage: usage.py --selftest")\n'            > "$tmp/t/usage.py"
  printf 'print("selftest SKIPPED -- no tool here")\n'      > "$tmp/t/skipped.py"
  printf 'import time\nprint("slow: started", flush=True)\ntime.sleep(5)\nprint("selftest OK")\n' > "$tmp/t/slow.py"
  # Modules that start a child: whether the check times out (spawner) or passes and exits (leaver), the child is
  # stopped with it -- otherwise it holds the output pipe open and the run waits for it, past any timeout.
  printf 'import subprocess, time\nsubprocess.Popen(["sleep", "30"])\ntime.sleep(5)\nprint("selftest OK")\n' \
                                                            > "$tmp/t/spawner.py"
  printf 'import subprocess\nsubprocess.Popen(["sleep", "30"])\nprint("selftest OK -- left a child")\n' \
                                                            > "$tmp/t/leaver.py"
  # ...and when the run is interrupted: TERM reaches the wrapper (as when a job is cancelled), the check goes, and its
  # child, which ignores TERM, is killed with the group rather than left holding the pipe.
  printf '%s\n' 'import os, signal, subprocess, time' \
                'signal.signal(signal.SIGTERM, signal.SIG_IGN)' \
                'subprocess.Popen(["sleep", "30"])          # inherits TERM ignored' \
                'signal.signal(signal.SIGTERM, signal.SIG_DFL)' \
                'time.sleep(0.1)' \
                'os.kill(os.getppid(), signal.SIGTERM)' \
                'time.sleep(30)'                            > "$tmp/t/deaf.py"
  printf 'raise SystemExit(3)\n'                            > "$tmp/t/exit3.py"
  # Each half of the pass rule alone: an OK line with a non-zero exit, and an OK line that is not the last.
  printf 'print("selftest OK")\nraise SystemExit(1)\n'       > "$tmp/t/okrc1.py"
  printf 'print("selftest OK")\nprint("then 2 checks FAILED")\n' > "$tmp/t/oknotlast.py"
  # The environment a check runs in (T-30): rew_api, imported from this tree (the runner's cwd), reads the dead port
  # -- the run below hands the runner another REW_API_URL, which must be replaced, not kept -- and asserts are on.
  printf '%s\n' 'import sys' \
                'sys.path.insert(0, "skills/autosound-tuning/rew_tool")' \
                'import rew_api' \
                'if rew_api.BASE_URL != "http://127.0.0.1:1":' \
                '    sys.exit("rew_api.BASE_URL is " + rew_api.BASE_URL + ", not the dead port")' \
                'print("selftest OK -- rew_api reads the dead port")' > "$tmp/t/deadport.py"
  printf '%s\n' 'import sys' \
                'if sys.flags.optimize:' \
                '    sys.exit("asserts are stripped here (PYTHONOPTIMIZE reached the check)")' \
                'print("selftest OK -- asserts run")'      > "$tmp/t/optimize.py"
  printf 'print("selftest OK")\n'                           > "$tmp/t/noreason.py"
  # A skip line cannot hide a module that has a selftest of its own.
  printf 'def _selftest():\n    print("selftest OK")\n\n\nif __name__ == "__main__":\n    _selftest()\n' \
                                                            > "$tmp/t/hidden.py"
  printf 'print("selftest OK")\n'                           > "$tmp/t/unlisted.py"
  # A skip line names a file on disk and gives a reason; the manifest's last line counts without its newline.
  { printf '%s\n' "$tmp/t/good.py" "$tmp/t/usage.py" "$tmp/t/skipped.py" "$tmp/t/slow.py" "$tmp/t/spawner.py" \
                  "$tmp/t/leaver.py" "$tmp/t/deaf.py" "$tmp/t/exit3.py" "$tmp/t/okrc1.py" "$tmp/t/oknotlast.py" \
                  "$tmp/t/deadport.py" "$tmp/t/optimize.py" "skip $tmp/t/vanished.py gone from disk" \
                  "skip $tmp/t/noreason.py" "skip $tmp/t/hidden.py a reason that hides a selftest"
    printf '%s' "$tmp/t/gone.py"; } > "$tmp/m.txt"
  started=$SECONDS
  out="$(REW_API_URL="http://127.0.0.1:9" PYTHONOPTIMIZE=1 SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t" \
         SELFTEST_MANIFEST="$tmp/m.txt" SELFTEST_TIMEOUT=1 CI= bash "$SELF" 2>&1)"; rc=$?
  took=$((SECONDS - started))
  # grep reads to EOF (no -q), so printf never dies of SIGPIPE and pipefail never reads a match as a miss.
  want() { printf '%s\n' "$out" | grep -E -- "$1" >/dev/null || { printf 'runner selftest: no line matching "%s" in:\n%s\n' "$1" "$out"; exit 1; }; }
  # The verdict, exactly, as the LAST line: each failure is COUNTED, not only printed (a kind that stopped counting
  # once left `all 1 checks passed`, rc 0, under its own FAIL line).
  last_is() { [ "$(printf '%s\n' "$out" | tail -n 1)" = "$1" ] || { printf 'runner selftest: the last line is not\n  %s\nin:\n%s\n' "$1" "$out"; exit 1; }; }
  [ "$rc" -eq 1 ] || { printf 'runner selftest: rc %s, want 1\n%s\n' "$rc" "$out"; exit 1; }
  want '^  ok   good\.py'
  want '^  FAIL usage\.py .*no OK line'
  want '^  --   skipped\.py .*NOT RUN'
  want '^  FAIL slow\.py .*timeout after 1s'
  want '^         slow: started$'                     # a timeout shows what the check printed before it hung
  want '^  FAIL spawner\.py .*timeout after 1s'
  want '^  ok   leaver\.py'
  want '^  FAIL deaf\.py +rc=143$'                    # 128 + TERM: the interrupted check, reported as such
  [ "$took" -lt 15 ] || { printf 'runner selftest: the fixture run took %ss -- what a check started must stop when the check ends, times out or is interrupted (spawner.py, leaver.py and deaf.py each leave a sleep 30, and the one deaf.py leaves ignores TERM)\n%s\n' "$took" "$out"; exit 1; }
  want '^  FAIL exit3\.py +rc=3$'
  want '^  FAIL okrc1\.py +rc=1$'
  want '^  FAIL oknotlast\.py .*no OK line'
  want '^  ok   deadport\.py'
  want '^  ok   optimize\.py'
  want '^  FAIL vanished\.py .*skip line names a file not on disk'
  want '^  FAIL noreason\.py .*skip line without a reason'
  want '^  FAIL hidden\.py .*has a selftest: list it, do not skip it'
  want '^  FAIL gone\.py .*listed in .*not on disk'   # the manifest's last line, which has no newline
  want '^  FAIL unlisted\.py .*not in '
  last_is "FAILED: 12 of 17 -- usage.py slow.py spawner.py deaf.py exit3.py okrc1.py oknotlast.py vanished.py noreason.py hidden.py gone.py unlisted.py; NOT RUN: skipped.py"
  # Under CI a NOT RUN alone fails the run; locally it is counted and the run passes. A valid skip line -- a file
  # with no selftest, and the reason -- fails nothing, and is printed.
  cp "$tmp/t/good.py" "$tmp/t/skipped.py" "$tmp/t2/"
  printf '# a plotting helper: no selftest\n'               > "$tmp/t2/plot.py"
  printf '%s\n' "$tmp/t2/good.py" "$tmp/t2/skipped.py" "skip $tmp/t2/plot.py a plotting helper" > "$tmp/m2.txt"
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t2" SELFTEST_MANIFEST="$tmp/m2.txt" CI=true bash "$SELF" 2>&1)"; rc=$?
  [ "$rc" -eq 1 ] || { printf 'runner selftest: under CI a NOT RUN must fail (rc %s)\n%s\n' "$rc" "$out"; exit 1; }
  last_is "FAILED: 1 of 2 did not run under CI -- skipped.py"
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t2" SELFTEST_MANIFEST="$tmp/m2.txt" CI= bash "$SELF" 2>&1)"; rc=$?
  [ "$rc" -eq 0 ] || { printf 'runner selftest: locally a NOT RUN is counted, not failed (rc %s)\n%s\n' "$rc" "$out"; exit 1; }
  want '^  --   plot\.py +skipped: a plotting helper$'
  last_is "all 1 checks passed; NOT RUN: skipped.py"
  ok_line="runner selftest OK -- every failure is named and counted in the verdict: a usage text, rc 1 under an OK line, an OK line not last, rc 3, a module that prints it skipped, a timeout, a missing or unlisted module, a bad skip line or one hiding a selftest; a child left behind, or deaf to TERM, is stopped; checks see REW at the dead port, with asserts on"
  # In a full run this line is the runner's own last line, read by the same rules as every check's: it must read as a
  # pass. One that named the NOT RUN word counted the runner itself as NOT RUN -- and failed CI -- while all passed.
  if says_not_run "$ok_line" || ! says_ok "$ok_line"; then
    printf 'runner selftest: its own OK line would not read as a pass in a run (NOT RUN, or no OK):\n  %s\n' "$ok_line"; exit 1
  fi
  echo "$ok_line"
  exit 0
fi

pass=0 fail=0 notrun=0 failed=() skipped=()

# The timeout bounds the check AND what it started: a child that outlived the check would hold the output pipe open,
# and the run would wait for it, past any timeout. perl forks; the child leads its own process group and execs the
# check (the parent sets the group too, so an early alarm still finds it). At the limit the parent kills the whole
# group and exits 142 (128 + SIGALRM). When the check ends first, whatever it left in its group is killed too, and the
# exit is the check's own status (128 + the signal when a signal ended it). The group is no longer the terminal's, so
# Ctrl-C, TERM and HUP are passed on to it, and once the check has gone, what is left in its group is killed as on the
# normal path, a member that ignored the signal included -- an interrupted run leaves nothing running -- except a
# signal the run was started with ignored (a background job, nohup): that one stays ignored.
GROUP_TIMEOUT='
  my $limit = shift;
  defined(my $pid = fork) or die "fork: $!\n";
  if (!$pid) { setpgrp(0, 0); exec @ARGV or die "exec $ARGV[0]: $!\n" }
  setpgrp($pid, $pid);
  for my $s (qw(INT TERM HUP)) {
    next if ($SIG{$s} // "") eq "IGNORE";
    $SIG{$s} = sub { $SIG{$s} = "DEFAULT"; kill $s, -$pid; waitpid $pid, 0; kill "KILL", -$pid; kill $s, $$ };
  }
  $SIG{ALRM} = sub { kill "KILL", -$pid; waitpid $pid, 0; exit 142 };
  alarm $limit;
  waitpid $pid, 0;
  alarm 0;
  my $st = $?;
  kill "KILL", -$pid;
  exit(($st & 127) ? 128 + ($st & 127) : $st >> 8);'

# run_one NAME MODE ARGV...   MODE: "ok" = exit 0 AND a last line saying OK; "rc" = exit 0, for a tree check whose
# success line says no OK (secret-scan's "clean"). Every check that does end its success with an OK line is `ok`.
run_one() {
  local name="$1" mode="$2"; shift 2
  local out rc last
  if [[ "$1" == *.sh ]]; then
    out="$(perl -e "$GROUP_TIMEOUT" "$LIMIT" bash "$@" 2>&1 </dev/null)"; rc=$?
  else
    out="$(perl -e "$GROUP_TIMEOUT" "$LIMIT" "$PY" "$@" 2>&1 </dev/null)"; rc=$?
  fi
  last="$(printf '%s\n' "$out" | sed '/^[[:space:]]*$/d' | tail -n1)"
  if [ "$rc" -eq 142 ]; then                                   # 128 + SIGALRM
    fail=$((fail + 1)); failed+=("$name"); printf '  FAIL %-24s timeout after %ss\n' "$name" "$LIMIT"
    [ -z "$out" ] || printf '%s\n' "$out" | tail -n 12 | sed 's/^/         /'
  elif [ "$rc" -eq 0 ] && says_not_run "$last"; then
    notrun=$((notrun + 1)); skipped+=("$name"); printf '  --   %-24s NOT RUN: %s\n' "$name" "$(printf '%s' "$last" | cut -c1-60)"
  elif [ "$rc" -eq 0 ] && { [ "$mode" = rc ] || says_ok "$last"; }; then
    pass=$((pass + 1)); printf '  ok   %-24s %s\n' "$name" "$(printf '%s' "$last" | cut -c1-72)"
  else
    fail=$((fail + 1)); failed+=("$name")
    if [ "$rc" -eq 0 ]; then printf '  FAIL %-24s exit 0 but no OK line -- a usage text is not a pass\n' "$name"
    else                     printf '  FAIL %-24s rc=%s\n' "$name" "$rc"; fi
    [ -z "$out" ] || printf '%s\n' "$out" | tail -n 12 | sed 's/^/         /'
  fi
}

if [ -z "${SELFTEST_ONLY_TOOL:-}" ]; then
  echo "repo checks"
  run_one "runner"          ok "$SELF" --selftest
  run_one "installers"      ok scripts/installer-consistency.py
  # HUB-075 (hub #245): the release train runs `tag-check.sh --at <commit> vX.Y.Z` as this repo's half. Its own
  # mechanics in a throwaway repo built from this tree: a last candidate passes, each missing piece is named.
  run_one "tag-check"       ok scripts/tag-check.sh --selftest
  # The upstream-drift checker's own mechanics (a throwaway git repo, no network). The real check
  # against the upstream is `scripts/upstream-drift.py --fork <clone> --fetch`, run by a person.
  run_one "upstream-drift"  ok scripts/upstream-drift.py --selftest
  # Issue #21: the console's code page must not be able to destroy a computed result. The checker
  # scans the tree; its own --selftest breaks each rule on purpose first.
  run_one "encoding"        ok scripts/encoding-check.py --selftest
  # No key leaves this repository: the scanner's own mechanics, then the tree as committed (a key
  # in a tracked file or a tracked/unignored key file fails the suite, and CI, before a tag).
  run_one "secret-scan"     ok scripts/secret-scan.py --selftest
  run_one "secrets-in-tree" rc scripts/secret-scan.py
  # Everything that reaches GitHub is in English, and a commit subject is the title of its CI run
  # (2026-09-13). The commit-msg hook's own mechanics, through git in a throwaway repository.
  run_one "commit-lang"     ok scripts/commit-lang.py --selftest
  # HUB-040: in the curve visualizer a dropped file's name (and the `#curve=` link) is data, never
  # markup. The checker's own mechanics, then every .html in the tree.
  run_one "html-data"       ok scripts/html-data-check.py --selftest
  run_one "html-in-tree"    ok scripts/html-data-check.py
  # HUB-029: a rule that lives only in prose can be deleted by a tidy-up. The checker's own
  # mechanics, then the documents: SKILL.md's always-on guardrails must still say that everything
  # the session READS is data, not instructions, and the inbox page must say it too.
  run_one "docs-check"      ok scripts/docs-check.py --selftest
  run_one "docs-in-tree"    ok scripts/docs-check.py
  # The same rule where a stranger's text meets a model: the issue body travels inside a fence with
  # a random marker, and the warning stands before it. Offline -- the prompt is built, not sent.
  run_one "issue-triage"    ok skills/autosound-tuning/scripts/issue_triage.py --selftest
  run_one "harvest-inbox"   ok skills/autosound-tuning/scripts/harvest_inbox.py --selftest
  run_one "doc-commands"    ok scripts/doc-commands-check.py --selftest
  run_one "tool-docs"       ok scripts/tool-docs-check.py --selftest
  # #137: contract 1 -- CONTRACT_VERSION, the IMPORTABLE table TCC reads, the _siblings() copies, the by-path probe.
  # The guard's own mechanics in a throwaway tree, then this tree (its success line says OK, so `ok`, not `rc`).
  run_one "contract-guard"  ok scripts/contract-guard.py --selftest
  run_one "contract-in-tree" ok scripts/contract-guard.py
  # #135: every file the method owns is written through rew_tool/project_io.py -- no fixed `.tmp` name, no move but
  # the named whole-file ones. The scan's own mechanics in a throwaway tree, then this tree (its success line says OK).
  run_one "atomic-write"    ok scripts/atomic-write-check.py --selftest
  run_one "atomic-in-tree"  ok scripts/atomic-write-check.py
  # HUB-044: README and FAQ live in four languages. The guard compares what can be compared without
  # knowing them -- the heading skeleton and the commands -- and says out loud that it cannot see all
  # four lagging the code together.
  run_one "i18n-check"      ok scripts/i18n-check.py --selftest
  run_one "i18n-in-tree"    ok scripts/i18n-check.py
  # HUB-043: the CHANGELOG's way in. The index is generated from the version headings of the live file
  # and the archive, so a new note without a regenerated table fails here rather than being noticed by
  # a reader who cannot find it.
  run_one "changelog-index" ok scripts/changelog-index.py --selftest
  run_one "changelog-fresh" ok scripts/changelog-index.py --check
  # The reviewer channel's shell plumbing: the closed gemini-CLI path is recognised and named, not
  # retried on a fallback model (hub PAS-004). Offline -- the CLI call is stubbed.
  # The direct-API reviewer: the key travels as a header, a retired model becomes a CHOICE carrying
  # the key's own list (never a fall-through to a CLI or the clipboard). Offline -- urlopen stubbed.
  run_one "autosound-ai"    ok skills/autosound-tuning/scripts/autosound_ai.py selftest
  # The one update path (W-4: #91 #92 #97 #98 #99): signed / unsigned / foreign-signed tags in a temp repo, local
  # changes kept as a patch before the reset, each tool updated the way it was installed. Offline.
  run_one "upkeep"          ok skills/autosound-tuning/scripts/upkeep.py selftest
fi

echo
echo "rew_tool selftests ($PY)"
listed=()
while read -r first rest || [ -n "$first" ]; do     # `||`: a last line without its newline still counts
  case "$first" in ''|'#'*) continue ;; esac
  # skip <path> <reason>: the file is on disk, the reason is given, and the file has no selftest of its own -- a skip
  # line must not be able to silence a module. A valid one is printed, so what the run left out is seen.
  if [ "$first" = skip ]; then
    path="${rest%%[[:space:]]*}"; reason="${rest#"$path"}"; reason="${reason#"${reason%%[![:space:]]*}"}"
    name="${path#"$TOOL"/}"; listed+=("$path")
    if [ ! -f "$path" ]; then
      fail=$((fail + 1)); failed+=("${name:-skip}")
      printf '  FAIL %-24s skip line names a file not on disk (%s)\n' "${name:-skip}" "$MANIFEST"
    elif [ -z "$reason" ]; then
      fail=$((fail + 1)); failed+=("$name"); printf '  FAIL %-24s skip line without a reason (%s)\n' "$name" "$MANIFEST"
    elif grep -E '^[[:space:]]*def _?selftest\(' "$path" >/dev/null; then
      fail=$((fail + 1)); failed+=("$name")
      printf '  FAIL %-24s has a selftest: list it, do not skip it (%s)\n' "$name" "$MANIFEST"
    else
      printf '  --   %-24s skipped: %s\n' "$name" "$reason"
    fi
    continue
  fi
  listed+=("$first")
  name="${first#"$TOOL"/}"
  if [ ! -f "$first" ]; then
    fail=$((fail + 1)); failed+=("$name"); printf '  FAIL %-24s listed in %s, not on disk\n' "$name" "$MANIFEST"; continue
  fi
  # shellcheck disable=SC2086  # the argv is words on purpose
  run_one "$name" ok "$first" $rest
done < "$MANIFEST"
# find, not a glob: rew_tool has subpackages (state/, gates/), and a glob that did not recurse once left six of their
# modules out of the run. A heredoc, not `< <(...)`: `sh scripts/run-selftests.sh` must parse too.
# grep reads to EOF (no -q): an early exit would kill printf with SIGPIPE, and pipefail would read a match as a miss.
while IFS= read -r f; do
  [ -n "$f" ] || continue
  printf '%s\n' "${listed[@]}" | grep -xF -- "$f" >/dev/null && continue
  fail=$((fail + 1)); failed+=("${f#"$TOOL"/}")
  printf '  FAIL %-24s not in %s: list its selftest argv, or a skip line with the reason\n' "${f#"$TOOL"/}" "$MANIFEST"
done <<EOF
$(find "$TOOL" -name '*.py' | sort)
EOF

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
