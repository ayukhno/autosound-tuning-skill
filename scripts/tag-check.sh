#!/usr/bin/env bash
# Everything that must be true BEFORE `git tag vX.Y.Z`. Run it, read it, then tag.
#
#   scripts/tag-check.sh v3.0.30
#
# A patch tag is a PUBLICATION: install.sh, install.ps1 and the TCC updater all install the newest
# tag matching v3.*, so a tag is on somebody's machine the moment it is pushed. Every check below
# is something that has already shipped wrong once, or that cannot be undone once it has.
#
# THE GIT HALF IS NOT HERE. Everything about the release channel -- clean tree, HEAD published,
# push.followTags, the newest tag on the remote, the tag being free, the tag rule and the hook's
# reading of the exact command lines that will run -- lives in ONE carrier owned by the hub,
# `hub/scripts/release-preflight.py`, and is CALLED from here (hub governance/RELEASE-CHANNEL.md §9,
# ticket HUB-004). Two of those checks never existed in this file: push.followTags was compared by
# hand, and nothing ever asked the hook. What stays here is this repo's inventory -- the manifest,
# the note, the installer triplet, this repo's CI -- because no second copy of it exists anywhere
# to drift against. The carrier only reports; the tag is still cut by a human afterwards.
#
# No `set -e`: every check runs, so one invocation names everything that is not ready and the
# summary is honest instead of stopping at the first complaint. The carrier was built to the same
# rule, so the two halves read as one list.
set -uo pipefail

cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

# The hub is checked out beside this repo. PREFLIGHT overrides that for a hub living elsewhere;
# it is a path to the carrier, not a switch that can turn the channel checks off.
PREFLIGHT="${PREFLIGHT:-$(cd .. && pwd)/hub/scripts/release-preflight.py}"

# 1. The intended tag is REQUIRED -- a check whose input is missing must FAIL, not report
#    "no objection" about a version it was never told (references/core/estimator-scope.md).
TAG="${1-}"
if [ -z "$TAG" ]; then
  echo "usage: scripts/tag-check.sh vX.Y.Z" >&2
  echo "the tag you intend to cut is required: with no version there is nothing to check against," >&2
  echo "and a check with no input is a failure, not a pass." >&2
  exit 2
fi
if ! printf '%s' "$TAG" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "usage: scripts/tag-check.sh vX.Y.Z (got '$TAG')" >&2
  exit 2
fi
VER="${TAG#v}"

pass=0 fail=0 failed=()
ok()  { pass=$((pass + 1)); printf '  ok   %-16s %s\n' "$1" "${2-}"; }
bad() { fail=$((fail + 1)); failed+=("$1"); printf '  FAIL %-16s %s\n' "$1" "$2"; }

echo "pre-tag checks for $TAG"

# 2. v3.0.24 shipped with .claude-plugin/plugin.json still saying 3.0.23 -- the manifest bump rode
#    in a separate commit and was forgotten. Parsed as json: grep would match a nested "version".
if mver="$("$PY" -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["version"])' 2>&1)"; then
  if [ "$mver" = "$VER" ]; then ok manifest "plugin.json version = $mver"
  else bad manifest "plugin.json says $mver, tag says $VER (the v3.0.24 mistake)"; fi
else
  bad manifest "cannot read version from .claude-plugin/plugin.json: $mver"
fi

# 3. The Upgrading note is written BEFORE the tag, or it ships as the NEXT patch: the heading must
#    already carry this version, [Unreleased] must be gone, and the body must say something.
if [ ! -f CHANGELOG.md ]; then
  bad changelog "CHANGELOG.md is missing"
else
  if grep -qE '^## \[[Uu]nreleased\]' CHANGELOG.md; then
    bad changelog-note "a '## [Unreleased]' heading is still there -- rename it to [$TAG] first"
  elif ! grep -qF "## [$TAG]" CHANGELOG.md; then
    bad changelog-note "no '## [$TAG]' heading in CHANGELOG.md -- write the note before tagging"
  else
    body="$(awk -v h="## [$TAG]" 'index($0,h)==1{f=1;next} f&&/^## /{exit} f&&NF{n++} END{print n+0}' CHANGELOG.md)"
    if [ "$body" -ge 3 ]; then ok changelog-note "[$TAG] section, $body non-empty lines"
    else bad changelog-note "[$TAG] section has $body non-empty lines -- an empty note is a forgotten note"; fi
  fi
fi

# 4. The installer triplet carries the same decisions three times; a claim checked in one file is
#    not checked. Reuse the existing checker rather than restating any part of it here.
if inst_out="$("$PY" scripts/installer-consistency.py 2>&1)"; then
  ok installers "$(printf '%s' "$inst_out" | tail -n1 | cut -c1-60)"
else
  bad installers "scripts/installer-consistency.py failed"
  printf '%s\n' "$inst_out" | tail -n 12 | sed 's/^/         /'
fi

# 5. The channel half, asked of the carrier with the tag named explicitly. Its lines are printed
#    verbatim underneath, in the hub's language: a verdict restated in other words is a second
#    copy of it, and this whole ticket exists because two copies drifted. A missing carrier is a
#    FAILURE, not a skip -- without it the git side is unchecked, and unchecked is not "fine".
echo
if [ ! -f "$PREFLIGHT" ]; then
  bad channel "no carrier at $PREFLIGHT -- the channel checks are the hub's; set PREFLIGHT=<path to hub/scripts/release-preflight.py>"
elif chan_out="$("$PY" "$PREFLIGHT" --root . --role skill --tag "$TAG" 2>&1)"; then
  ok channel "hub preflight passed -- its own lines below"
  printf '%s\n' "$chan_out" | sed 's/^/         /'
else
  bad channel "hub preflight says NOT READY -- its own lines below"
  printf '%s\n' "$chan_out" | sed 's/^/         /'
fi
echo

# 6. CI green ON THE SHA THE TAG WILL NAME. Until HUB-004 this was a printed reminder and the one
#    thing in the list held by attention instead of by a gate -- the same shape as the
#    push.followTags gap that ticket closed. It is a gate now: the selftests are still not rerun
#    here (CI runs scripts/run-selftests.sh on every push, and what matters is that it was green on
#    the sha, not on this checkout), but whether it WAS green is now asked rather than assumed.
#    Not knowing is not a pass: no gh, no answer from it, no run on this sha, or a run still going
#    are each "not ready", and each says which.
sha="$(git rev-parse HEAD 2>/dev/null || true)"
if [ -z "$sha" ]; then
  bad ci-green "cannot resolve HEAD -- there is no sha to ask about"
elif ! command -v gh >/dev/null 2>&1; then
  bad ci-green "gh is not on PATH: CI on ${sha:0:12} is unverified, and unverified is not green"
elif ! runs="$(gh run list --commit "$sha" --limit 50 --json status,conclusion,workflowName 2>&1)"; then
  bad ci-green "gh run list failed: $(printf '%s' "$runs" | tr '\n' ' ' | cut -c1-140)"
elif ! ci_msg="$("$PY" -c '
import json, sys
runs = json.loads(sys.argv[1])
if not runs:
    print("FAIL no run on this sha -- CI has not seen the commit the tag would name")
    raise SystemExit
pending = sorted({r["workflowName"] for r in runs if r["status"] != "completed"})
broken = sorted({r["workflowName"] + ":" + str(r["conclusion"]) for r in runs
                 if r["status"] == "completed"
                 and r["conclusion"] not in ("success", "skipped", "neutral")})
green = sorted({r["workflowName"] for r in runs if r["conclusion"] == "success"})
if pending:
    print("FAIL still running: " + ", ".join(pending) + " -- a run in flight is not a green run")
elif broken:
    print("FAIL " + ", ".join(broken) + " -- red on the sha the tag would name")
elif not green:
    print("FAIL nothing succeeded on this sha: "
          + ", ".join(sorted({str(r["conclusion"]) for r in runs})))
else:
    print("OK " + ", ".join(green) + " green on " + sys.argv[2][:12])
' "$runs" "$sha" 2>&1)"; then
  bad ci-green "cannot read gh output: $(printf '%s' "$ci_msg" | tr '\n' ' ' | cut -c1-140)"
else
  case "$ci_msg" in
    OK*) ok ci-green "${ci_msg#OK }" ;;
    *)   bad ci-green "${ci_msg#FAIL }" ;;
  esac
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "NOT READY TO TAG $TAG: $fail of $((pass + fail)) checks failed -- ${failed[*]}" >&2
  exit 1
fi
echo "all $pass checks passed -- ready: git tag -a $TAG && git push origin $TAG"
