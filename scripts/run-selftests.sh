#!/usr/bin/env bash
# Run every rew_tool module's own selftest, plus the installer consistency check.
#
# One runner so CI and a person execute the SAME thing -- a CI that runs something nobody can
# reproduce locally is a second source of truth about whether the tree is healthy.
#
#   scripts/run-selftests.sh          # everything, one line per module
#
# Requires numpy and scipy. dsp_math and eq_gate import scipy by name, and since v3.0.12 the
# dsp_math selftest DESIGNS crossovers, so a bare python3 fails there with a RuntimeError rather
# than skipping -- that is deliberate (see the v3.0.12 Upgrading note) and it means CI must
# install scipy, not hope for it.
set -uo pipefail

cd "$(dirname "$0")/.."
TOOL="skills/autosound-tuning/rew_tool"
PY="${PYTHON:-python3}"

pass=0 fail=0 failed=()

run_one() {                       # name, then the argv to hand the module
  local name="$1"; shift
  local out rc
  # A `.sh` runs under bash; everything else is a Python module handed to $PY.
  if [[ "$1" == *.sh ]]; then out="$(bash "$@" 2>&1)"; rc=$?
  else                        out="$("$PY" "$@" 2>&1)"; rc=$?; fi
  if [ "$rc" -eq 0 ]; then
    pass=$((pass + 1))
    printf '  ok   %-20s %s\n' "$name" "$(printf '%s' "$out" | tail -n1 | cut -c1-72)"
  else
    fail=$((fail + 1)); failed+=("$name")
    printf '  FAIL %-20s rc=%s\n' "$name" "$rc"
    printf '%s\n' "$out" | tail -n 12 | sed 's/^/         /'
  fi
}

echo "installer consistency"
run_one "installers" scripts/installer-consistency.py
# The upstream-drift checker's own mechanics (a throwaway git repo, no network). The real check
# against the upstream is `scripts/upstream-drift.py --fork <clone> --fetch`, run by a person.
run_one "upstream-drift" scripts/upstream-drift.py --selftest
# Issue #21: the console's code page must not be able to destroy a computed result. The checker
# scans the tree; its own --selftest breaks each rule on purpose first.
run_one "encoding" scripts/encoding-check.py --selftest
# No key leaves this repository: the scanner's own mechanics, then the tree as committed (a key
# in a tracked file or a tracked/unignored key file fails the suite, and CI, before a tag).
run_one "secret-scan" scripts/secret-scan.py --selftest
run_one "secrets-in-tree" scripts/secret-scan.py
# HUB-040: in the curve visualizer a dropped file's name (and the `#curve=` link) is data, never
# markup. The checker's own mechanics, then every .html in the tree.
run_one "html-data" scripts/html-data-check.py --selftest
run_one "html-in-tree" scripts/html-data-check.py
# HUB-029: a rule that lives only in prose can be deleted by a tidy-up. The checker's own
# mechanics, then the documents: SKILL.md's always-on guardrails must still say that everything
# the session READS is data, not instructions, and the inbox page must say it too.
run_one "docs-check" scripts/docs-check.py --selftest
run_one "docs-in-tree" scripts/docs-check.py
# The same rule where a stranger's text meets a model: the issue body travels inside a fence with
# a random marker, and the warning stands before it. Offline -- the prompt is built, not sent.
run_one "issue-triage" skills/autosound-tuning/scripts/issue_triage.py --selftest
run_one "harvest-inbox" skills/autosound-tuning/scripts/harvest_inbox.py --selftest
run_one "doc-commands" scripts/doc-commands-check.py --selftest
run_one "tool-docs" scripts/tool-docs-check.py --selftest
# HUB-044: README and FAQ live in four languages. The guard compares what can be compared without
# knowing them -- the heading skeleton and the commands -- and says out loud that it cannot see all
# four lagging the code together.
run_one "i18n-check" scripts/i18n-check.py --selftest
run_one "i18n-in-tree" scripts/i18n-check.py
# HUB-043: the CHANGELOG's way in. The index is generated from the version headings of the live file
# and the archive, so a new note without a regenerated table fails here rather than being noticed by
# a reader who cannot find it.
run_one "changelog-index" scripts/changelog-index.py --selftest
run_one "changelog-fresh" scripts/changelog-index.py --check
# The reviewer channel's shell plumbing: the closed gemini-CLI path is recognised and named, not
# retried on a fallback model (hub PAS-004). Offline -- the CLI call is stubbed.
run_one "gemini-channel" skills/autosound-tuning/scripts/gemini_critic.sh --selftest
# The direct-API reviewer: the key travels as a header, a retired model becomes a CHOICE carrying
# the key's own list (never a fall-through to a CLI or the clipboard). Offline -- urlopen stubbed.
run_one "autosound-ai" skills/autosound-tuning/scripts/autosound_ai.py selftest

echo
echo "rew_tool selftests ($PY)"
# find, not a glob: rew_tool has subpackages (state/, gates/) and a plain "$TOOL"/*.py silently
# skipped six modules that all have working selftests -- state/{state,process,migrate,apply} and
# gates/{presweep_safety,side_effect}. Reported by TCC on 2026-08-22, who were running four of them
# and none of the eleven this script did. Two partial sets, each believing it was the whole.
while IFS= read -r f; do
  grep -q selftest "$f" || continue
  name="${f#"$TOOL"/}"
  case "$name" in
    # takes a project argument first; it is ignored by the selftest, but argv must carry it
    naming.py)                 run_one "$name" "$f" . selftest ;;
    __init__.py)               continue ;;
    *)
      if grep -q -- '--selftest' "$f"; then run_one "$name" "$f" --selftest
      else                                  run_one "$name" "$f" selftest
      fi ;;
  esac
done <<EOF
$(find "$TOOL" -name '*.py' | sort)
EOF

echo
if [ "$fail" -ne 0 ]; then
  echo "FAILED: $fail of $((pass + fail)) -- ${failed[*]}" >&2
  exit 1
fi
echo "all $pass checks passed"
