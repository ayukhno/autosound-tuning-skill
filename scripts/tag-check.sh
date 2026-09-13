#!/usr/bin/env bash
# Everything that must be true BEFORE `git tag vX.Y.Z`. Run it, read it, then tag.
#
#   scripts/tag-check.sh v3.0.30
#   scripts/tag-check.sh --candidate v3.1.0     a release candidate for v3.1.0; the hub names its rcN
#
# A patch tag is a PUBLICATION: install.sh, install.ps1 and the TCC updater all install the newest
# tag matching v3.*, so a tag is on somebody's machine the moment it is pushed. Every check below
# is something that has already shipped wrong once, or that cannot be undone once it has.
#
# A CANDIDATE (`beta-vX.Y.Z-rcN`, hub RELEASE-CHANNEL.md §11) is checked the same way, with three
# differences: its CHANGELOG entry may still be `## [Unreleased]`, its manifest may still carry the
# previous version, and the channel half asks the hub for the next attempt's name. A release is the
# newest candidate's commit plus only its bookkeeping -- the rename to `## [vX.Y.Z]`, the manifest and
# the install pins (§11.3, hub #141) -- so a candidate is not asked to carry any of them.
#
# THE GIT HALF IS NOT HERE. Everything about the release channel -- clean tree, HEAD published,
# push.followTags, the newest tag on the remote, the tag being free, the tag rule and the hook's
# reading of the exact command lines that will run -- lives in ONE carrier owned by the hub,
# `hub/scripts/release-preflight.py`, and is CALLED from here (hub governance/RELEASE-CHANNEL.md §9,
# ticket HUB-004). Two of those checks never existed in this file: push.followTags was compared by
# hand, and nothing ever asked the hook. What stays here is this repo's inventory -- the manifest,
# the note, the installer triplet -- because no second copy of it exists anywhere
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
MODE="release"
if [ "${1-}" = "--candidate" ]; then MODE="candidate"; shift; fi
TAG="${1-}"
if [ -z "$TAG" ]; then
  echo "usage: scripts/tag-check.sh vX.Y.Z | --candidate vX.Y.Z" >&2
  echo "the tag you intend to cut is required: with no version there is nothing to check against," >&2
  echo "and a check with no input is a failure, not a pass." >&2
  exit 2
fi
if ! printf '%s' "$TAG" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "usage: scripts/tag-check.sh vX.Y.Z | --candidate vX.Y.Z (got '$TAG')" >&2
  exit 2
fi
VER="${TAG#v}"

pass=0 fail=0 failed=()
ok()  { pass=$((pass + 1)); printf '  ok   %-16s %s\n' "$1" "${2-}"; }
bad() { fail=$((fail + 1)); failed+=("$1"); printf '  FAIL %-16s %s\n' "$1" "$2"; }

if [ "$MODE" = "candidate" ]; then echo "pre-tag checks for a candidate for $TAG"
else echo "pre-tag checks for $TAG"; fi

# 2. v3.0.24 shipped with .claude-plugin/plugin.json still saying 3.0.23 -- the manifest bump rode
#    in a separate commit and was forgotten. Parsed as json: grep would match a nested "version".
if mver="$("$PY" -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["version"])' 2>&1)"; then
  if [ "$mver" = "$VER" ]; then ok manifest "plugin.json version = $mver"
  elif [ "$MODE" = "candidate" ]; then
    ok manifest "plugin.json says $mver -- the release commit bumps it to $VER (bookkeeping, hub §11.3)"
  else bad manifest "plugin.json says $mver, tag says $VER (the v3.0.24 mistake)"; fi
else
  bad manifest "cannot read version from .claude-plugin/plugin.json: $mver"
fi

# 3. The Upgrading note is written BEFORE the tag, or it ships as the NEXT patch: the heading must
#    already carry this version, [Unreleased] must be gone, and the body must say something.
if [ ! -f CHANGELOG.md ]; then
  bad changelog "CHANGELOG.md is missing"
elif [ "$MODE" = "candidate" ]; then
  # `## [vX.Y.Z]` when the version is already named, else `## [Unreleased]`. Either must say what is
  # being tried: an empty note is a forgotten note for a candidate too.
  if grep -qF "## [$TAG]" CHANGELOG.md; then head="## [$TAG]"
  else head="$(grep -iE -m1 '^## \[unreleased\]' CHANGELOG.md || true)"; fi
  if [ -z "$head" ]; then
    bad changelog-note "neither '## [$TAG]' nor '## [Unreleased]' in CHANGELOG.md -- nothing says what the candidate carries"
  else
    body="$(awk -v h="$head" 'index($0,h)==1{f=1;next} f&&/^## /{exit} f&&NF{n++} END{print n+0}' CHANGELOG.md)"
    if [ "$body" -lt 1 ]; then
      bad changelog-note "$head has no entry -- an empty note is a forgotten note"
    elif [ "$head" = "## [$TAG]" ]; then
      ok changelog-note "[$TAG] section, $body non-empty lines"
    else
      ok changelog-note "[Unreleased], $body non-empty lines -- renamed to [$TAG] in the release commit"
    fi
  fi
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
if [ "$MODE" = "candidate" ]; then CHAN_ARGS=(--candidate "$TAG"); else CHAN_ARGS=(--tag "$TAG"); fi
echo
if [ ! -f "$PREFLIGHT" ]; then
  bad channel "no carrier at $PREFLIGHT -- the channel checks are the hub's; set PREFLIGHT=<path to hub/scripts/release-preflight.py>"
elif chan_out="$("$PY" "$PREFLIGHT" --root . --role skill "${CHAN_ARGS[@]}" 2>&1)"; then
  ok channel "hub preflight passed -- its own lines below"
  printf '%s\n' "$chan_out" | sed 's/^/         /'
else
  bad channel "hub preflight says NOT READY -- its own lines below"
  printf '%s\n' "$chan_out" | sed 's/^/         /'
fi
echo

# CI green on the sha the tag will name is asked ONCE, by the hub preflight above (`ci-green`,
# HUB-057): this file had its own reader until HUB-059, and the two counted different runs -- this
# one every run on the sha, Pages included; the hub's only this repo's own workflows on push. A red
# Pages build does not hold a tag: installers and TCC's updater fetch the tag from git, not the site.

# The name to cut. For a candidate it is the hub's: the next rcN is counted there, not here.
LABEL="$TAG"
if [ "$MODE" = "candidate" ]; then
  cand="$(printf '%s' "${chan_out-}" | grep -oE 'beta-v[0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+' | head -n 1)"
  LABEL="${cand:-a candidate for $TAG}"
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "NOT READY TO TAG $LABEL: $fail of $((pass + fail)) checks failed -- ${failed[*]}" >&2
  exit 1
fi
echo "all $pass checks passed -- ready: git tag -a $LABEL && git push origin $LABEL"
