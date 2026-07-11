#!/usr/bin/env bash
# skill_metrics.sh — complexity guard for the always-loaded core.
#
# The skill's 2026-07 regression ("slow, timid, micro-stepping sessions") was
# caused by the always-loaded SKILL.md silently growing 1.1k→3.6k words and its
# defensive-tone density doubling. These three numbers catch that BEFORE it's
# felt. Run before a release; non-zero exit = trim (move text into references/),
# don't ship.
#
#   1. SKILL.md words                  ≤ 1500
#   2. defensive markers in SKILL.md   ≤ 15   (never/don't/fail/risk/verify/…)
#   3. external calls per round        ≤ 2    (by design: 1 critique + 1 escalation;
#                                              checked as docs-grep, see below)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

MAX_WORDS=1500
MAX_DEFENSIVE=15

fail=0
words=$(wc -w < SKILL.md)
defensive=$(grep -ciE "never|don't|do not|refuses|ruins|fail|risk|verify|check|re-read|honest" SKILL.md || true)

echo "SKILL.md words:            $words (max $MAX_WORDS)"
echo "SKILL.md defensive markers: $defensive (max $MAX_DEFENSIVE)"
(( words <= MAX_WORDS ))        || { echo "✗ SKILL.md too fat — move text into references/"; fail=1; }
(( defensive <= MAX_DEFENSIVE )) || { echo "✗ tone creep — rewrite warnings as operating defaults"; fail=1; }

# 3. Review-cadence invariants: the docs must keep saying ONE call per round.
grep -q "ONE reviewer call per round" SKILL.md \
  || { echo "✗ SKILL.md lost the one-call-per-round cadence rule"; fail=1; }
grep -q "escalation, not default" references/core/review-loop.md \
  || { echo "✗ review-loop.md lost 'TWO-PASS = escalation, not default'"; fail=1; }
grep -qi "one critic checkpoint" references/phases/phase_2_eq.md \
  || { echo "✗ phase_2_eq.md regressed to multiple mandatory critic checkpoints"; fail=1; }

# 4. Mode separation: anti-confabulation policing must NOT live in SKILL.md
#    (a link/description mentioning it is fine — the RULES themselves are not).
if grep -qiE "narrated compliance|done costs a path|tool-stamped sheet" SKILL.md; then
  echo "✗ driver-discipline text leaked back into the always-loaded core"; fail=1
fi

(( fail == 0 )) && echo "== METRICS OK ✓ ==" || echo "== METRICS FAIL ✗ =="
exit $fail
