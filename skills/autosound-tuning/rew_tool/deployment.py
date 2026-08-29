#!/usr/bin/env python3
"""deployment -- WHICH copy of the method is this, and does another copy on this machine disagree.

`provenance.py` answers the question an ARTIFACT asks days later: which checkout wrote this file.
This module answers the one a RUN asks while it is happening: which checkout am I, and is the
session that is advising reading the same one. Two halves of one identifier -- autosound-hub
HUB-002 put the sha into the files, HUB-006 is the half that has to reach a screen.

The method is deployed more than once ON PURPOSE, and that is not the fault:

  * a working tree on a moving branch, where the method is edited;
  * an installed checkout at a TAG -- what `install.sh` makes: a `--depth 1 --branch <tag>` clone
    in `~/.claude/skills/.autosound-tuning-src`, with `~/.claude/skills/autosound-tuning` symlinked
    at its `skills/autosound-tuning` (install.sh:61, :774);
  * a per-project pin -- a detached checkout a run holds still so its numbers stay reproducible;
  * a submodule, whose sha the consuming repository records for it (`autosound-tcc`).

The fault is that none of them SAYS which it is. A project's scripts resolve `rew_tool` through
their own `.claude/skills/autosound-tuning`, the session loads `SKILL.md` through the personal one;
when those are different checkouts, the maths a run computes and the method a session advises are
different versions -- both work, and neither is wrong out loud. Measured here on 2026-08-29:
scripts on v3.0.33, session on 3.0.36, working tree on 3.0.37. Three states, no complaint.

**Disagreement is refused; ORDER is not judged.** Which candidate a given loader prefers is not
knowable from inside one of them: a session's skill loader and a script's `sys.path` are two
mechanisms with two rules, and a module that guessed at the ranking would be asserting the one
thing it cannot see. So this reports every candidate that exists and refuses when two of them are
different checkouts -- the fact that stays true no matter which one wins.

**"Cannot be told" is not agreement.** A copy in no repository has no identity. Counting it as
matching would be this module's own failure mode wearing a green tick, so it is a refusal of its
own (exit 4), separate from a real disagreement (exit 3).

    python3 rew_tool/deployment.py               # this copy and the personal one
    python3 rew_tool/deployment.py <project>     # ... plus that project's own pin
    python3 rew_tool/deployment.py --selftest

Exit: 0 one method  |  3 candidates disagree  |  4 a candidate has no identity, or there is none.

stdlib only, py3.9+ -- same as the rest of `rew_tool/`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import provenance

#: Where a consumer points: the skill FOLDER, not the repository around it. Every deployment shape
#: above hands out this path and only this path, which is why the version has to be answerable
#: from inside it rather than from a root the consumer never sees.
SKILL_DIRNAME = "autosound-tuning"

#: Same budget as `provenance._TIMEOUT`, same reason: a wedged git must not hold up the run it is
#: describing.
_TIMEOUT = 3.0


def skill_dir():
    """The `skills/autosound-tuning` this module lives in, symlinks resolved."""
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _git(root, *args):
    """git in `root`, first line, or "" -- never an exception, never git's complaint as data."""
    try:
        done = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                              timeout=_TIMEOUT, check=False)
    except Exception:  # noqa: BLE001 -- no git on the machine is a finding, not a crash
        return ""
    if done.returncode != 0:
        return ""
    lines = (done.stdout or "").strip().splitlines()
    return lines[0].strip() if lines else ""


def version_at(root):
    """`.claude-plugin/plugin.json`'s `version`, or "" -- the string a PERSON quotes.

    Deliberately not derived from the sha and deliberately not trusted as an identifier:
    `provenance`'s docstring already paid for that distinction (`main` carried 3.0.36 while
    `marketplace.json` said 2.8.3). It rides along so a report reads like something a human can
    act on; every comparison this module makes is on the sha.
    """
    if not root:
        return ""
    path = os.path.join(root, ".claude-plugin", "plugin.json")
    try:
        with open(path, encoding="utf-8") as fh:
            got = json.load(fh).get("version", "")
    except Exception:  # noqa: BLE001 -- absent or malformed is "cannot be told", not a crash
        return ""
    return got if isinstance(got, str) else ""


def describe(path):
    """Identify the deployment whose skill folder is `path`.

    `sha` is the answer that gets COMPARED; `version`, `ref` and `branch` are for the screen. `ref`
    comes from `describe --tags`, so a pinned checkout says `v3.0.33` and a moving one says
    `v3.0.37-1-g458eb45` -- the difference between held still and drifting, in the string itself.
    """
    real = os.path.realpath(path)
    if not os.path.isdir(real):
        return {"path": real, "exists": False, "sha": "", "version": "", "ref": "", "branch": ""}
    # The same walk `provenance.repo_root()` makes, from the folder instead of from this file: a
    # candidate is somebody ELSE's checkout, and asking our own root about it would answer for us.
    root, here = None, real
    for _ in range(4):
        if (os.path.isfile(os.path.join(here, ".claude-plugin", "plugin.json"))
                or os.path.exists(os.path.join(here, ".git"))):
            root = here
            break
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    sha = _git(root, "rev-parse", "HEAD") if root else ""
    return {
        "path": real,
        "exists": True,
        "root": root or "",
        "sha": sha if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha) else "",
        "version": version_at(root),
        "ref": _git(root, "describe", "--tags", "--always") if root else "",
        # "" means detached -- which is what a pin looks like, so it is reported, not hidden.
        "branch": _git(root, "symbolic-ref", "--quiet", "--short", "HEAD") if root else "",
    }


def candidates(project_dir=None, home=None):
    """Every deployment a run on this machine can reach, in the order a project's scripts try them.

    `here` is first because it is the copy doing the talking -- a report that left itself out would
    be the "two partial sets, each believing it was the whole" that `run-selftests.sh` already has
    a paragraph about.
    """
    home = home or os.path.expanduser("~")
    out = [dict(describe(skill_dir()), origin="here", link=skill_dir())]
    if project_dir:
        link = os.path.join(project_dir, ".claude", "skills", SKILL_DIRNAME)
        out.append(dict(describe(link), origin="project", link=link))
    link = os.path.join(home, ".claude", "skills", SKILL_DIRNAME)
    out.append(dict(describe(link), origin="personal", link=link))
    return out


def verdict(cands):
    """(exit code, one line). Distinct CHECKOUTS is the question -- distinct paths is not.

    A clone and a worktree standing at the same commit are one method deployed twice, which is the
    normal, healthy case; grouping by path would call that a fault and train everybody to ignore
    the check. So the grouping key is the sha, and two paths agree when their shas do.
    """
    live = [c for c in cands if c["exists"]]
    if not live:
        return 4, "no deployment of the method found — nothing to compare, and nothing to run"
    nameless = [c for c in live if not c["sha"]]
    if nameless:
        where = ", ".join(c["link"] for c in nameless)
        return 4, f"a deployment cannot say which checkout it is: {where} — unknown is not agreement"
    shas = sorted({c["sha"] for c in live})
    if len(shas) > 1:
        names = " vs ".join(sorted({f"{c['ref'] or c['sha'][:12]}" for c in live}))
        return 3, f"{len(shas)} different checkouts of the method are reachable here: {names}"
    return 0, f"one method: {live[0]['version'] or '?'} ({live[0]['ref'] or live[0]['sha'][:12]})"


def report(cands):
    """The table, widest field first so the shas line up under each other."""
    rows = []
    for c in cands:
        if not c["exists"]:
            rows.append(f"  {c['origin']:<9} {'—':<12} {'(no such path)':<26} {c['link']}")
            continue
        state = c["branch"] or "DETACHED"
        rows.append(f"  {c['origin']:<9} {c['version'] or '?':<12} "
                    f"{(c['ref'] or 'no repository')[:26]:<26} {state:<10} {c['path']}")
    return "\n".join(rows)


# --------------------------------------------------------------------------- CLI
_USAGE = """usage: deployment.py [<project-dir>] [--json] [--selftest]

  (no arguments)   this copy and the personal ~/.claude one
  <project-dir>    also that project's own .claude/skills/autosound-tuning
  --json           the same facts as a machine object
  --selftest       this module's own gates, on throwaway repositories

exit  0 one method   3 checkouts disagree   4 a deployment has no identity, or there is none
"""


def _selftest():
    """Both verdicts on real repositories, and the two that a green tick would hide.

    Made to fail on purpose before it was kept: with the sha comparison replaced by a path
    comparison, `two checkouts at the SAME commit` below reports a disagreement — which is how the
    grouping key was chosen rather than assumed.
    """
    import tempfile

    def git(cwd, *args):
        subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True,
                       env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                            "GIT_CONFIG_SYSTEM": os.devnull})

    def make_repo(root, version, body):
        skills = os.path.join(root, "skills", SKILL_DIRNAME)
        os.makedirs(os.path.join(root, ".claude-plugin"))
        os.makedirs(skills)
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": SKILL_DIRNAME, "version": version}, fh)
        with open(os.path.join(skills, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(body)
        git(root, "init", "--quiet")
        git(root, "config", "user.email", "selftest@example.invalid")
        git(root, "config", "user.name", "selftest")
        git(root, "add", "-A")
        git(root, "commit", "--quiet", "-m", version)
        return skills

    with tempfile.TemporaryDirectory() as tmp:
        a = make_repo(os.path.join(tmp, "a"), "3.0.33", "one")
        b = make_repo(os.path.join(tmp, "b"), "3.0.37", "two")

        # -- a checkout identifies itself: version off plugin.json, sha off git, both present --
        d = describe(a)
        assert d["version"] == "3.0.33", d
        assert len(d["sha"]) == 40, d
        assert d["branch"], "a repository on a branch must say which"

        # -- two checkouts at DIFFERENT commits is the fault this module exists for --
        code, line = verdict([dict(describe(a), origin="project", link=a),
                              dict(describe(b), origin="personal", link=b)])
        assert code == 3, f"two checkouts read as {code}: {line}"
        assert "3.0.33" in line or "different" in line, line

        # -- two PATHS at the same commit is not a fault; a clone beside a worktree is normal --
        clone = os.path.join(tmp, "clone")
        subprocess.run(["git", "clone", "--quiet", os.path.join(tmp, "a"), clone],
                       capture_output=True, text=True, check=True)
        code, line = verdict([dict(describe(a), origin="here", link=a),
                              dict(describe(os.path.join(clone, "skills", SKILL_DIRNAME)),
                                   origin="personal", link=clone)])
        assert code == 0, f"same commit twice read as a disagreement: {line}"

        # -- a copy in NO repository is refused, and refused differently from a disagreement --
        loose = os.path.join(tmp, "loose", "skills", SKILL_DIRNAME)
        os.makedirs(loose)
        d = describe(loose)
        assert d["exists"] and d["sha"] == "", f"a loose folder claimed an identity: {d}"
        code, line = verdict([dict(describe(a), origin="here", link=a),
                              dict(d, origin="personal", link=loose)])
        assert code == 4, f"unknown identity read as {code}: {line}"
        assert code != 3, "unknown must not be filed as disagreement — different repairs"

        # -- nothing at all FAILS; it does not report "no objection" (repo rule, CLAUDE.md) --
        code, line = verdict([dict(describe(os.path.join(tmp, "gone")), origin="here", link="gone")])
        assert code == 4, f"an empty machine reported {code}: {line}"

        # -- the walk stops at a marker: a skill folder unpacked INSIDE another repository must
        #    not adopt it. Four levels is provenance's limit; this is the case it protects. --
        deep = os.path.join(tmp, "a", "nested", "here", "skills", SKILL_DIRNAME)
        os.makedirs(deep)
        assert describe(deep)["sha"] == "", "a nested folder adopted a repository above it"

    # -- and on this machine, whatever it is, the answer has ONE shape --
    code, line = verdict(candidates())
    assert code in (0, 3, 4), f"unknown verdict {code}"
    print(f"selftest OK — disagreement, agreement, no-identity and nothing-at-all all named; "
          f"here: {line}")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    if argv and argv[0] == "--selftest":
        return _selftest()
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if len(argv) > 1:
        print(_USAGE, file=sys.stderr)
        return 2
    cands = candidates(argv[0] if argv else None)
    code, line = verdict(cands)
    if as_json:
        print(json.dumps({"verdict": code, "summary": line, "deployments": cands},
                         ensure_ascii=False, indent=2))
        return code
    print(report(cands))
    print()
    print(("OK: " if code == 0 else "REFUSED: ") + line)
    return code


if __name__ == "__main__":
    sys.exit(main())
