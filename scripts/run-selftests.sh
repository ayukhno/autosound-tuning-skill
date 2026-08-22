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
  out="$("$PY" "$@" 2>&1)"; rc=$?
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

echo
echo "rew_tool selftests ($PY)"
for f in "$TOOL"/*.py; do
  grep -q selftest "$f" || continue
  name="$(basename "$f")"
  case "$name" in
    # takes a project argument first; it is ignored by the selftest, but argv must carry it
    naming.py)                 run_one "$name" "$f" . selftest ;;
    *)
      if grep -q -- '--selftest' "$f"; then run_one "$name" "$f" --selftest
      else                                  run_one "$name" "$f" selftest
      fi ;;
  esac
done

echo
if [ "$fail" -ne 0 ]; then
  echo "FAILED: $fail of $((pass + fail)) -- ${failed[*]}" >&2
  exit 1
fi
echo "all $pass checks passed"
