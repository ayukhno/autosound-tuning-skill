#!/usr/bin/env bash
# Everything that must be true BEFORE `git tag -s vX.Y.Z`. Run it, read it, then tag (signed: skill #99).
#
#   scripts/tag-check.sh v3.0.30
#   scripts/tag-check.sh --candidate v3.1.0     a release candidate for v3.1.0; the hub names its rcN
#   scripts/tag-check.sh --at <commit> v3.2.0   this repo's half for the release train, at a commit (read-only)
#   scripts/tag-check.sh --selftest             the --at mode and the install-line rule, in a throwaway repo
#
# A patch tag is a PUBLICATION: install.sh, install.ps1 and the TCC updater all install the newest
# tag matching v3.*, so a tag is on somebody's machine the moment it is pushed. Every check below
# is something that has already shipped wrong once, or that cannot be undone once it has.
#
# A CANDIDATE (`beta-vX.Y.Z-rcN`, hub RELEASE-CHANNEL.md §11) is checked the same way, with three
# differences: its CHANGELOG entry may still be `## [Unreleased]`, its manifest may still carry the
# previous version, and the channel half asks the hub for the next attempt's name. An early candidate
# is not asked to carry its release's bookkeeping; the LAST one is, under the release train.
#
# THE RELEASE TRAIN (hub #245, RELEASE-CHANNEL.md §11.6): a minor, a major or a skipped version goes out
# through `release` as the group, and its tag lands on the last candidate's commit -- nothing is committed
# on release day. So that candidate carries `## [vX.Y.Z]`, plugin.json at X.Y.Z, every file shipped inside
# the tag that names the tag (install.cmd's PS1URL), and the wave's pool closed. The lines users copy from
# main's front page (README*, FAQ*, ADVANCED.md) still name the release before: the train rewrites them,
# with the catalog, in one commit after the tag, so they never point at a tag that does not exist yet.
# `--at <commit> vX.Y.Z` is the content half the train runs (`release-groups.json` `check`): it exports the
# commit's tree to a temporary folder and checks it there, so neither the working tree nor HEAD matters.
# The channel half -- CI on that commit, the tag rule, signing, the pool -- is the train's own preflight.
# An ordinary patch is the session's own, as before: its bookkeeping commit moves the front-page lines
# too, and the plain `vX.Y.Z` mode holds them to the tag.
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

USAGE="usage: scripts/tag-check.sh vX.Y.Z | --candidate vX.Y.Z | --at <commit> vX.Y.Z | --selftest"

# The --at mode and the install-line rule, run against a throwaway repository built from this working tree: a
# release-train candidate passes, and each thing it must carry is taken away once and named by the refusal.
selftest() {
  local repo base newest next a out rc
  ST_TMP="$(mktemp -d)"; repo="$ST_TMP/skill"; mkdir -p "$repo"
  trap 'rm -rf "$ST_TMP"' EXIT
  git ls-files -z | tar --null -T - -cf - 2>/dev/null | tar -xf - -C "$repo"
  G() { git -C "$repo" -c user.name=selftest -c user.email=selftest@invalid -c commit.gpgsign=false "$@"; }
  newest="$(grep -m1 -oE '^## \[v[0-9]+\.[0-9]+\.[0-9]+\]' "$repo/CHANGELOG.md" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')"
  IFS=. read -r ma mi _ <<<"${newest#v}"; next="v$ma.$((mi + 1)).0"
  # The base is a released state whatever this tree is (a train candidate's front page is one release behind):
  # every front-page line and install.cmd at the CHANGELOG's newest heading.
  "$PY" - "$repo" "$newest" <<'PYEOF' || return 1
import pathlib, re, sys
root, tag = pathlib.Path(sys.argv[1]), sys.argv[2]
pin = re.compile(rb"(autosound-tuning-skill/)v\d+\.\d+\.\d+/")
for f in [*root.glob("README*.md"), *root.glob("FAQ*.md"), root / "ADVANCED.md", root / "install.cmd"]:
    f.write_bytes(pin.sub(rb"\g<1>" + tag.encode() + b"/", f.read_bytes()))
PYEOF
  G init -q && G add -A && G commit -qm base || { echo "selftest: cannot build the throwaway repo" >&2; return 1; }
  base="$(G rev-parse HEAD)"
  # The last candidate of $next: the heading, the manifest, install.cmd's PS1URL -- and the front page left alone.
  "$PY" - "$repo" "$newest" "$next" <<'PYEOF' || return 1
import json, pathlib, re, sys
root, old, new = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
ch = root / "CHANGELOG.md"
s = ch.read_text(encoding="utf-8")
note = f"## [{new}] — selftest\n\nA candidate that is the release.\n\n### Upgrading\n\n- Nothing to do.\n\n"
# Between tags the tree carries `## [Unreleased]` (a wave's work in progress), and the release commit renames it: a
# last candidate has none. Anchored to a line start -- the CHANGELOG's prose quotes the heading in backticks.
m = re.search(r"(?m)^## \[[Uu]nreleased\][^\n]*\n", s)
if m:
    s = s[:m.start()] + note + s[m.end():]
else:
    i = s.index(f"## [{old}]")
    s = s[:i] + note + s[i:]
ch.write_text(s, encoding="utf-8")
pj = root / ".claude-plugin" / "plugin.json"
d = json.loads(pj.read_text(encoding="utf-8")); d["version"] = new[1:]
pj.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
cmd = root / "install.cmd"
cmd.write_bytes(cmd.read_bytes().replace(f"/{old}/".encode(), f"/{new}/".encode()))
PYEOF
  G commit -qam candidate; a="$(G rev-parse HEAD)"
  expect() {  # expect <rc> <word in the output> <what> -- <args...>
    local want="$1" word="$2" what="$3"; shift 4
    out="$("$repo/scripts/tag-check.sh" "$@" 2>&1)"; rc=$?
    if [ "$rc" != "$want" ] || ! printf '%s' "$out" | grep -qF -- "$word"; then
      echo "selftest[tag-check] FAIL: $what (rc=$rc, wanted $want and «${word}»)" >&2
      printf '%s\n' "$out" | tail -n 15 >&2; return 1
    fi
  }
  # Each break starts from the candidate and is checked while HEAD sits elsewhere: --at reads the commit.
  brk() {  # brk <name> <python that edits the tree at $1>
    G checkout -q "$a" && "$PY" -c "$2" "$repo" "$newest" "$next" && G commit -qam "$1" && G rev-parse HEAD
  }
  local b c d
  b="$(brk front 'import sys,pathlib
r,o,n=pathlib.Path(sys.argv[1]),sys.argv[2],sys.argv[3]
for f in [*r.glob("README*.md"),*r.glob("FAQ*.md"),r/"ADVANCED.md"]: f.write_text(f.read_text(encoding="utf-8").replace("/"+o+"/","/"+n+"/"),encoding="utf-8")')" || return 1
  c="$(brk manifest 'import sys,json,pathlib
p=pathlib.Path(sys.argv[1])/".claude-plugin"/"plugin.json"; d=json.loads(p.read_text()); d["version"]=sys.argv[2][1:]; p.write_text(json.dumps(d,indent=2)+"\n")')" || return 1
  d="$(brk cmd 'import sys,pathlib
p=pathlib.Path(sys.argv[1])/"install.cmd"; p.write_bytes(p.read_bytes().replace(("/"+sys.argv[3]+"/").encode(),("/"+sys.argv[2]+"/").encode()))')" || return 1
  G checkout -q "$base"
  expect 0 "ready at ${a:0:12}" "the last candidate carries the release" -- --at "$a" "$next" || return 1
  expect 1 "FAIL install-lines" "front-page lines naming the coming tag" -- --at "$b" "$next" || return 1
  expect 1 "FAIL manifest" "a manifest still at the previous version" -- --at "$c" "$next" || return 1
  expect 1 "FAIL shipped-pins" "install.cmd still fetching the previous tag" -- --at "$d" "$next" || return 1
  expect 2 "not in this repository" "a commit that is not here" -- --at 0123456789abcdef0123456789abcdef01234567 "$next" || return 1
  expect 2 "usage" "--at with no tag" -- --at "$a" || return 1
  # A patch (the plain mode, at HEAD) holds the front page to its own tag; the channel half fails here, no hub.
  expect 1 "ok   install-lines" "a patch's front page at its tag" -- "$newest" || return 1
  expect 1 "FAIL install-lines" "a patch whose front page is behind" -- "$next" || return 1
  echo "selftest[tag-check] OK -- --at reads the named commit, not HEAD: a last candidate carrying its heading, manifest and" \
       "install.cmd pin passes with the front page one release behind; front-page lines naming the coming tag, a manifest" \
       "or an install.cmd pin left behind are each refused by name; a commit not here and a missing tag are usage errors;" \
       "a patch's front page is held to its own tag"
}

# 1. The intended tag is REQUIRED -- a check whose input is missing must FAIL, not report
#    "no objection" about a version it was never told (references/core/estimator-scope.md).
MODE="release" AT=""
case "${1-}" in
  --selftest) selftest; exit $? ;;
  --candidate) MODE="candidate"; shift ;;
  --at) MODE="at"; AT="${2-}"; shift; [ $# -gt 0 ] && shift ;;
esac
TAG="${1-}"
if [ -z "$TAG" ]; then
  echo "$USAGE" >&2
  echo "the tag you intend to cut is required: with no version there is nothing to check against," >&2
  echo "and a check with no input is a failure, not a pass." >&2
  exit 2
fi
if ! printf '%s' "$TAG" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "$USAGE (got '$TAG')" >&2
  exit 2
fi
VER="${TAG#v}"

# --at: the commit's own tree, exported to a temporary folder -- read-only for this repo, and the checks below
# (installer-consistency.py included) are the commit's versions, run on the commit's files.
if [ "$MODE" = "at" ]; then
  SHA="$(git rev-parse --verify --quiet "${AT}^{commit}" 2>/dev/null || true)"
  if [ -z "$AT" ] || [ -z "$SHA" ]; then
    echo "$USAGE" >&2
    echo "commit '${AT}' is not in this repository -- fetch it first (git fetch origin --tags)" >&2
    exit 2
  fi
  AT_DIR="$(mktemp -d)"
  trap 'rm -rf "$AT_DIR"' EXIT
  if ! git archive "$SHA" | tar -xf - -C "$AT_DIR"; then
    echo "cannot export ${SHA:0:12} to check it" >&2
    exit 2
  fi
  cd "$AT_DIR"
fi

pass=0 fail=0 failed=()
ok()  { pass=$((pass + 1)); printf '  ok   %-16s %s\n' "$1" "${2-}"; }
bad() { fail=$((fail + 1)); failed+=("$1"); printf '  FAIL %-16s %s\n' "$1" "$2"; }

if [ "$MODE" = "candidate" ]; then echo "pre-tag checks for a candidate for $TAG"
elif [ "$MODE" = "at" ]; then echo "pre-tag checks for $TAG at ${SHA:0:12} -- this repo's half for the release train"
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

# 4c. A file shipped INSIDE the tag that names the tag carries it already: install.cmd fetches install.ps1 by tag
#     (it stayed on v3.0.46 for three releases, 2026-09-13). installer-consistency.py compares it with the
#     CHANGELOG's newest heading; this names it against the tag itself. A candidate may still be behind.
if [ "$MODE" != "candidate" ]; then
  ps1url="$(sed -n 's/^set "PS1URL=\([^"]*\)".*/\1/p' install.cmd 2>/dev/null | tr -d '\r' | head -n 1)"
  case "$ps1url" in
    */"$TAG"/install.ps1) ok shipped-pins "install.cmd fetches install.ps1 at $TAG" ;;
    "") bad shipped-pins "install.cmd has no PS1URL line" ;;
    *) bad shipped-pins "install.cmd fetches ${ps1url} -- the tag ships it, so it must name $TAG" ;;
  esac
fi

# 4d. The install lines people copy from main's front page (README*, FAQ*, ADVANCED.md). A patch moves them in its
#     own bookkeeping, so they name its tag. A release-train candidate leaves them on the release before -- they
#     must never name a tag that does not exist yet -- and the train moves them right after the tag (hub #245).
if [ "$MODE" != "candidate" ]; then
  if lines_out="$("$PY" - "$TAG" "$MODE" 2>&1 <<'PYEOF'
import glob, re, sys
tag, mode = sys.argv[1], sys.argv[2]
key = lambda v: tuple(int(x) for x in v[1:].split("."))
found = {}
for name in sorted(glob.glob("README*.md") + glob.glob("FAQ*.md") + glob.glob("ADVANCED.md")):
    text = open(name, encoding="utf-8").read()
    for m in re.finditer(r"raw\.githubusercontent\.com/ayukhno/autosound-tuning-skill/(v\d+\.\d+\.\d+)/", text):
        found.setdefault(m.group(1), set()).add(name)
if not found:
    sys.exit("no install line in README*, FAQ*, ADVANCED.md -- they are the lines people paste")
where = lambda v: ", ".join(sorted(found[v]))
if mode == "at":
    early = [v for v in found if key(v) >= key(tag)]
    if early:
        sys.exit(" ".join(f"{v} in {where(v)}" for v in sorted(early, key=key)) + f" -- not tagged yet; the front page "
                 f"stays on the release before, and the release train moves it after the tag")
    print(f"the front page names {', '.join(sorted(found, key=key))} -- the train moves it to {tag} after the tag")
else:
    off = [v for v in found if v != tag]
    if off:
        sys.exit(" ".join(f"{v} in {where(v)}" for v in sorted(off, key=key)) + f" -- a patch moves them to {tag} "
                 f"in its bookkeeping")
    print(f"every front-page install line names {tag}")
PYEOF
)"; then ok install-lines "$lines_out"
  else bad install-lines "$lines_out"; fi
fi

# 4b. The tag is SIGNED (skill #99, hub #82 HUB-031). From v3.0.64 the installers and TCC's update path refuse a
#     release tag that does not verify against the author's key, so an unsigned tag cut here would stop every new
#     install. Checked before the tag: git's signing config has to name the key in `allowed_signers`, which
#     installer-consistency.py holds equal to the installers' own constant.
if [ "$MODE" = "at" ]; then
  echo "  --   signing          the train's: release-preflight checks the key that will sign"
else
sig_fmt="$(git config --get gpg.format || true)"
sig_key="$(git config --get user.signingkey || true)"
case "$sig_key" in key::*) sig_key="${sig_key#key::}" ;; "~/"*) sig_key="$HOME/${sig_key#\~/}" ;; esac
[ -f "$sig_key" ] && sig_key="$(awk '{print $1, $2; exit}' "$sig_key")"
sig_want="$(grep -v '^#' allowed_signers 2>/dev/null | awk 'NF {print $3, $4; exit}')"
if [ -z "$sig_want" ]; then
  bad signing "no key in allowed_signers -- the installers would have nothing to check the tag against"
elif [ "$sig_fmt" != "ssh" ] || [ "$sig_key" != "$sig_want" ]; then
  bad signing "git would not sign with the author's key (gpg.format=${sig_fmt:-unset}, user.signingkey $([ -n "$sig_key" ] && echo "names another key" || echo unset)) -- git config --global gpg.format ssh; git config --global user.signingkey ~/.ssh/id_ed25519.pub"
else
  ok signing "git signs with the key in allowed_signers (${sig_want:12:20}…)"
fi
fi

# 5. The channel half, asked of the carrier with the tag named explicitly. Its lines are printed
#    verbatim underneath, in the hub's language: a verdict restated in other words is a second
#    copy of it, and this whole ticket exists because two copies drifted. A missing carrier is a
#    FAILURE, not a skip -- without it the git side is unchecked, and unchecked is not "fine".
if [ "$MODE" = "candidate" ]; then CHAN_ARGS=(--candidate "$TAG"); else CHAN_ARGS=(--tag "$TAG"); fi
echo
if [ "$MODE" = "at" ]; then
  echo "  --   channel          the train's: release-preflight --at runs CI, the rule, the pool and the hook on this commit"
elif [ ! -f "$PREFLIGHT" ]; then
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
# --at speaks to the train, which reads the LAST line: both verdicts go to stdout and name the commit.
if [ "$MODE" = "at" ]; then
  if [ "$fail" -ne 0 ]; then
    echo "NOT READY at ${SHA:0:12} for $TAG: $fail of $((pass + fail)) checks failed -- ${failed[*]}"
    exit 1
  fi
  echo "ready at ${SHA:0:12}: all $pass checks of this repo's half passed for $TAG"
  exit 0
fi
if [ "$fail" -ne 0 ]; then
  echo "NOT READY TO TAG $LABEL: $fail of $((pass + fail)) checks failed -- ${failed[*]}" >&2
  exit 1
fi
echo "all $pass checks passed -- ready: git tag -s $LABEL -m $LABEL && git push origin $LABEL"
