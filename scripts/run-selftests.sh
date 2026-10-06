#!/usr/bin/env bash
# Run every check of this repo: the scripts' own selftests, every rew_tool module's selftest, ruff.
#
# One runner so CI and a person execute the SAME thing. It must be able to FAIL (#133, audit T-28):
#   * every rew_tool module is in scripts/selftests.txt with the argv its selftest takes, or on a `skip` line with
#     the reason -- a module in neither fails the run (no silent skip);
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

if [ "${1:-}" = "--selftest" ]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  mkdir -p "$tmp/t"
  printf 'print("selftest OK -- good")\n'                    > "$tmp/t/good.py"
  printf 'print("usage: usage.py --selftest")\n'            > "$tmp/t/usage.py"
  printf 'print("selftest SKIPPED -- no tool here")\n'      > "$tmp/t/skipped.py"
  printf 'import time\ntime.sleep(5)\nprint("selftest OK")\n' > "$tmp/t/slow.py"
  # A module that starts a child: the timeout must stop the child too, or the child holds the output pipe open and
  # the run waits for it.
  printf 'import subprocess, time\nsubprocess.Popen(["sleep", "30"])\ntime.sleep(5)\nprint("selftest OK")\n' \
                                                            > "$tmp/t/spawner.py"
  printf 'print("selftest OK")\n'                           > "$tmp/t/unlisted.py"
  printf '%s\n' "$tmp/t/good.py" "$tmp/t/usage.py" "$tmp/t/skipped.py" "$tmp/t/slow.py" "$tmp/t/spawner.py" \
                "$tmp/t/gone.py" > "$tmp/m.txt"
  started=$SECONDS
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t" SELFTEST_MANIFEST="$tmp/m.txt" SELFTEST_TIMEOUT=1 CI= \
         bash "$SELF" 2>&1)"; rc=$?
  took=$((SECONDS - started))
  want() { printf '%s\n' "$out" | grep -Eq -- "$1" || { printf 'runner selftest: no line matching "%s" in:\n%s\n' "$1" "$out"; exit 1; }; }
  [ "$rc" -eq 1 ] || { printf 'runner selftest: rc %s, want 1\n%s\n' "$rc" "$out"; exit 1; }
  want '^  ok   good\.py'
  want '^  FAIL usage\.py .*no OK line'
  want '^  --   skipped\.py .*NOT RUN'
  want '^  FAIL slow\.py .*timeout after 1s'
  want '^  FAIL spawner\.py .*timeout after 1s'
  [ "$took" -lt 15 ] || { printf 'runner selftest: the fixture run took %ss -- a timeout must stop what the module started (its sleep 30), not only the module\n%s\n' "$took" "$out"; exit 1; }
  want '^  FAIL gone\.py .*not on disk'
  want '^  FAIL unlisted\.py .*not in '
  want '^FAILED: '
  # Under CI a NOT RUN alone fails the run; locally it is counted and the run passes.
  printf '%s\n' "$tmp/t/good.py" "$tmp/t/skipped.py" "skip $tmp/t/usage.py fixture" "skip $tmp/t/slow.py fixture" \
                "skip $tmp/t/spawner.py fixture" "skip $tmp/t/unlisted.py fixture" > "$tmp/m2.txt"
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t" SELFTEST_MANIFEST="$tmp/m2.txt" CI=true bash "$SELF" 2>&1)"; rc=$?
  [ "$rc" -eq 1 ] || { printf 'runner selftest: under CI a NOT RUN must fail (rc %s)\n%s\n' "$rc" "$out"; exit 1; }
  want 'did not run under CI'
  out="$(SELFTEST_ONLY_TOOL=1 SELFTEST_TOOL="$tmp/t" SELFTEST_MANIFEST="$tmp/m2.txt" CI= bash "$SELF" 2>&1)"; rc=$?
  [ "$rc" -eq 0 ] || { printf 'runner selftest: locally a NOT RUN is counted, not failed (rc %s)\n%s\n' "$rc" "$out"; exit 1; }
  want 'NOT RUN: skipped\.py'
  echo "runner selftest OK -- usage text, skip, timeout (with what the module started), missing and unlisted modules are all named"
  exit 0
fi

pass=0 fail=0 notrun=0 failed=() skipped=()

# The timeout bounds the check AND what it started: a child that outlived the check would hold the output pipe open,
# and the run would wait for it. perl forks; the child leads its own process group and execs the check (the parent
# sets the group too, so an early alarm still finds it); at the limit the parent kills the whole group and exits 142
# (128 + SIGALRM), otherwise with the check's status (128 + the signal when a signal ended it). The group is no longer
# the terminal's, so Ctrl-C, TERM and HUP are passed on to it -- an interrupted run leaves nothing running.
GROUP_TIMEOUT='
  my $limit = shift;
  defined(my $pid = fork) or die "fork: $!\n";
  if (!$pid) { setpgrp(0, 0); exec @ARGV or die "exec $ARGV[0]: $!\n" }
  setpgrp($pid, $pid);
  $SIG{$_} = sub { my $s = shift; $SIG{$s} = "DEFAULT"; kill $s, -$pid; waitpid $pid, 0; kill $s, $$ } for qw(INT TERM HUP);
  $SIG{ALRM} = sub { kill "KILL", -$pid; waitpid $pid, 0; exit 142 };
  alarm $limit;
  waitpid $pid, 0;
  exit(($? & 127) ? 128 + ($? & 127) : $? >> 8);'

# run_one NAME MODE ARGV...   MODE: "ok" = exit 0 AND a last line saying OK; "rc" = exit 0 (tree checks).
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
  run_one "html-in-tree"    rc scripts/html-data-check.py
  # HUB-029: a rule that lives only in prose can be deleted by a tidy-up. The checker's own
  # mechanics, then the documents: SKILL.md's always-on guardrails must still say that everything
  # the session READS is data, not instructions, and the inbox page must say it too.
  run_one "docs-check"      ok scripts/docs-check.py --selftest
  run_one "docs-in-tree"    rc scripts/docs-check.py
  # The same rule where a stranger's text meets a model: the issue body travels inside a fence with
  # a random marker, and the warning stands before it. Offline -- the prompt is built, not sent.
  run_one "issue-triage"    ok skills/autosound-tuning/scripts/issue_triage.py --selftest
  run_one "harvest-inbox"   ok skills/autosound-tuning/scripts/harvest_inbox.py --selftest
  run_one "doc-commands"    ok scripts/doc-commands-check.py --selftest
  run_one "tool-docs"       ok scripts/tool-docs-check.py --selftest
  # HUB-044: README and FAQ live in four languages. The guard compares what can be compared without
  # knowing them -- the heading skeleton and the commands -- and says out loud that it cannot see all
  # four lagging the code together.
  run_one "i18n-check"      ok scripts/i18n-check.py --selftest
  run_one "i18n-in-tree"    rc scripts/i18n-check.py
  # HUB-043: the CHANGELOG's way in. The index is generated from the version headings of the live file
  # and the archive, so a new note without a regenerated table fails here rather than being noticed by
  # a reader who cannot find it.
  run_one "changelog-index" ok scripts/changelog-index.py --selftest
  run_one "changelog-fresh" rc scripts/changelog-index.py --check
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
