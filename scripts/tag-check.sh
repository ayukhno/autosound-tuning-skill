#!/usr/bin/env bash
# Everything that must be true BEFORE `git tag vX.Y.Z`. Run it, read it, then tag.
#
#   scripts/tag-check.sh v3.0.30
#
# A patch tag is a PUBLICATION: install.sh, install.ps1 and the TCC updater all install the newest
# tag matching v3.*, so a tag is on somebody's machine the moment it is pushed. Every check below
# is something that has already shipped wrong once, or that cannot be undone once it has.
#
# No `set -e`: every check runs, so one invocation names everything that is not ready and the
# summary is honest instead of stopping at the first complaint.
set -uo pipefail

cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

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
VER="${TAG#v}"; MAJOR="${VER%%.*}"

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

# 4. A published tag is NEVER moved: one version number would then name two builds, and a plain
#    `git fetch` does not move a tag, so every existing clone keeps showing the old commit.
if git tag -l | grep -qxF "$TAG"; then
  bad tag-free-local "$TAG already exists locally -- a published tag is never moved"
else
  ok tag-free-local "no local $TAG"
fi
if remote_tag="$(git ls-remote --tags origin "refs/tags/$TAG" 2>&1)"; then
  if [ -n "$remote_tag" ]; then bad tag-free-origin "$TAG already exists on origin -- never moved, cut the next number"
  else ok tag-free-origin "origin has no $TAG"; fi
else
  # Offline is not a pass: without origin we cannot know whether this tag is already published.
  bad tag-free-origin "cannot reach origin: ${remote_tag//$'\n'/ }"
fi

# 5. CI must be green on the tagged sha, and that requires the sha to EXIST on origin; a dirty tree
#    means the tag would name a commit that is not what you just tested.
if [ -z "$(git status --porcelain)" ]; then ok worktree-clean "nothing uncommitted"
else bad worktree-clean "$(git status --porcelain | wc -l | tr -d ' ') uncommitted path(s) -- commit or clean first"; fi
if git fetch --quiet origin main 2>/dev/null; then     # fetch is read-only, it moves no local ref
  head_sha="$(git rev-parse HEAD 2>/dev/null || true)"
  up_sha="$(git rev-parse origin/main 2>/dev/null || true)"
  if [ -z "$up_sha" ]; then bad head-pushed "cannot resolve origin/main"
  elif [ "$head_sha" = "$up_sha" ]; then ok head-pushed "HEAD = origin/main ${head_sha:0:12}"
  else bad head-pushed "HEAD ${head_sha:0:12} != origin/main ${up_sha:0:12} -- push first, CI runs there"; fi
else
  bad head-pushed "git fetch origin main failed -- cannot confirm HEAD is published"
fi

# 6. The installers take the NEWEST v$MAJOR.* tag, so a lower number publishes nothing and a
#    reused-looking number confuses every machine that already updated.
if origin_tags="$(git ls-remote --tags origin "refs/tags/v${MAJOR}.*" 2>&1)"; then
  newest="$(printf '%s\n' "$origin_tags" | sed 's#.*refs/tags/##' | grep -vF '^{}' \
            | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n1)"
  if [ -z "$newest" ]; then ok version-newer "no existing v${MAJOR}.* tag on origin"
  elif [ "$TAG" = "$newest" ]; then bad version-newer "$TAG is the newest tag already"
  elif [ "$(printf '%s\n%s\n' "$newest" "$TAG" | sort -V | tail -n1)" = "$TAG" ]; then
    ok version-newer "$newest -> $TAG"
  else bad version-newer "$TAG is not newer than $newest -- installers would ignore it"; fi
else
  bad version-newer "cannot list origin tags: ${origin_tags//$'\n'/ }"
fi

# 7. The installer triplet carries the same decisions three times; a claim checked in one file is
#    not checked. Reuse the existing checker rather than restating any part of it here.
if inst_out="$("$PY" scripts/installer-consistency.py 2>&1)"; then
  ok installers "$(printf '%s' "$inst_out" | tail -n1 | cut -c1-60)"
else
  bad installers "scripts/installer-consistency.py failed"
  printf '%s\n' "$inst_out" | tail -n 12 | sed 's/^/         /'
fi

# 8. The selftests are NOT rerun here: CI runs scripts/run-selftests.sh on every push, and the
#    thing that matters is that it was green ON THE SHA THE TAG WILL NAME, not on this checkout.
echo
sha="$(git rev-parse --short HEAD 2>/dev/null || echo HEAD)"
echo "  note: selftests are not rerun here -- CI runs scripts/run-selftests.sh on every push."
echo "        CI must be green on THIS sha before you tag:  gh run list --commit $sha"

echo
if [ "$fail" -ne 0 ]; then
  echo "NOT READY TO TAG $TAG: $fail of $((pass + fail)) checks failed -- ${failed[*]}" >&2
  exit 1
fi
echo "all $pass checks passed -- ready: git tag -a $TAG && git push origin $TAG"
