"""Which checkout of the method wrote a file — asked here and only here (autosound-hub HUB-002).

An artifact leaves the machine that made it. A journal and a `dsp_profile.json` brought back from a
competition weekend are read days later on a different laptop, next to another project's pair — and
neither of them said which method wrote them. Two runs made by two versions of the method looked
alike, so comparing them was an act of trust rather than a check.

**The sha is the identifier; `plugin.json`'s `version` is a signature for a person.** The two are
not interchangeable, and this repository is the proof: `main` carries 3.0.36 while
`marketplace.json` still says 2.8.3 (measured 2026-08-27). A version string is maintained by hand
and drifts; a sha cannot. So the version goes on screen, where a person quotes it, and the sha goes
into the files, where things are compared. Putting both in the artifacts would be one key kept in
two places, watching them come apart.

**One spelling, not two.** What this module hands out is the whole forty characters — the number a
person can paste back into git, and the same number the companion app shows for the same checkout
(`autosound-tcc`, `core/install_report.skill_sha`). No short form is written anywhere; if a display
ever needs one it takes a PREFIX of this, with the length in that one place, and does not ask git a
second time. Two spellings of an identifier are two identifiers.

**Read here rather than accepted from a caller.** A number handed down by a front-end says what the
front-end believes, not which code wrote the file. The writer signs for itself, so a mismatch
between the screen and the artifact is visible instead of impossible.

stdlib only, py3.9+ — same as the rest of `rew_tool/`.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

#: What a commit looks like, so that a git error message cannot be mistaken for one.
_SHA = re.compile(r"^[0-9a-f]{40}$")

#: How long git may take before the answer is written off. This is a local `rev-parse`; three
#: seconds is already generous, and a wedged git must not hold up the write it is stamping —
#: provenance is worth less than the artifact it rides on.
_TIMEOUT = 3.0

#: `skill_sha()` for the life of the process, once asked. `None` means "not asked yet"; `""` is an
#: answer. A stamp that changed halfway through a run would put two writers in one file.
_CACHE = None


def repo_root():
    """The checkout this file lives in, or None when it lives in none.

    Resolve the link FIRST, then walk up looking for a marker rather than counting levels: an
    installed method is `~/.claude/skills/autosound-tuning`, a symlink (a junction on Windows) into
    the installer's clone, and two levels up from the LINK is `~/.claude`, which is no checkout at
    all. The companion app bought this: every installed machine reported "not a git checkout" while
    a developer's own tree worked and hid it (`vendor_loader.skill_repo_root`, 2026-08-19). The
    same walk and the same markers here, so the two answers agree by construction rather than by
    coincidence.

    Four candidates and no further: this module sits three levels under the repository root
    (`rew_tool/` → `skills/autosound-tuning/` → `skills/` → root), and a walk that kept going would
    happily adopt an unrelated repository that a skill folder was unpacked inside — a wrong sha
    that looks exactly like a right one.
    """
    here = os.path.dirname(os.path.realpath(__file__))
    for _ in range(4):
        if _is_root(here):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return None


def _is_root(path):
    """The two markers of the method's own repository. `.git` is tested with `exists`, not `isdir`:
    in a submodule checkout — which is how the companion app carries this skill — it is a FILE."""
    return (os.path.isfile(os.path.join(path, ".claude-plugin", "plugin.json"))
            or os.path.exists(os.path.join(path, ".git")))


def _sha_at(root):
    """`git rev-parse HEAD` in `root`, or "" — never an exception, never a traceback.

    HEAD, not the state of the working tree: a modified checkout stamps the commit it is based on.
    That is coarse on purpose — the companion app's number means exactly the same thing, and a
    stamp that disagreed with what the screen shows would be worse than one that is honest about
    being a commit and nothing more.
    """
    try:
        done = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=_TIMEOUT, check=False)
    except Exception:  # noqa: BLE001 — no git on the machine is a finding, not a crash
        return ""
    lines = (done.stdout or "").strip().splitlines()
    first = lines[0].strip() if lines else ""
    # RECOGNISED, not trusted. git prints its failures as text, and `fatal: not a git repository`
    # standing in the field that identifies the method would be worse than an empty one: it looks
    # like data. Anything that is not forty hex characters is not an answer.
    return first if _SHA.match(first) else ""


def skill_sha():
    """The commit this checkout of the method is at, or "" when it cannot be told.

    `""` is a real answer, not a failure: a skill folder unpacked on its own is in no repository,
    and a machine without git cannot be asked. Writers stamp it as it comes rather than dropping
    the key, so a reader can tell "asked, could not be told" from "written before anything asked" —
    the same distinction `dsp_profile` draws between a null fact and an absent one.
    """
    global _CACHE
    if _CACHE is None:
        root = repo_root()
        _CACHE = "" if root is None else _sha_at(root)
    return _CACHE


# --------------------------------------------------------------------------- CLI
_USAGE = """usage: provenance.py [--selftest]

  (no arguments)   the stamp this checkout writes, as JSON
  --selftest       this module's own gates, on throwaway repositories
"""


def _selftest():
    """Both directions on real repositories, because both have been wrong in the neighbouring tree.

    A checkout must give ITS commit (not a parent's, not a tag object's), and a directory that is
    no repository must give "" rather than git's complaint about it. The second half is the one
    worth having: it is the case that produced `fatal: …` in an identifier field.
    """
    import tempfile

    def git(cwd, *args):
        subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True,
                       env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                            "GIT_CONFIG_SYSTEM": os.devnull})

    with tempfile.TemporaryDirectory() as tmp:
        # -- a real checkout answers with its own HEAD --
        repo = os.path.join(tmp, "repo")
        os.makedirs(repo)
        git(repo, "init", "--quiet")
        git(repo, "config", "user.email", "selftest@example.invalid")
        git(repo, "config", "user.name", "selftest")
        open(os.path.join(repo, "f"), "w").close()
        git(repo, "add", "f")
        git(repo, "commit", "--quiet", "-m", "one")
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        got = _sha_at(repo)
        assert got == head, f"checkout: {got!r} != {head!r}"
        assert _SHA.match(got), f"not a sha: {got!r}"

        # -- a directory that is no repository answers "", not git's complaint about it --
        bare = os.path.join(tmp, "not-a-repo")
        os.makedirs(bare)
        got = _sha_at(bare)
        assert got == "", f"non-repository answered {got!r}"

        # The check the check needs: git DID speak there, and what it said was rejected rather
        # than absent. Without this the line above passes just as well on a git that never ran.
        spoke = subprocess.run(["git", "-C", bare, "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=False)
        assert spoke.returncode != 0 and spoke.stderr.strip(), "git said nothing — case is hollow"

        # -- the marker walk stops at a marker, and does not climb past one --
        inner = os.path.join(repo, "skills", "autosound-tuning", "rew_tool")
        os.makedirs(inner)
        assert _is_root(repo), "a checkout is a root"
        assert not _is_root(inner), "a directory with no marker is not a root"

    # -- this checkout, whatever it is, answers in ONE shape: forty hex characters or nothing --
    mine = skill_sha()
    assert mine == "" or _SHA.match(mine), f"own checkout answered {mine!r}"
    assert skill_sha() is mine, "cached: a second call must not ask git again"
    root = repo_root()
    print(f"selftest OK — checkout and non-repository both answered; here: "
          f"{mine or 'no repository'} ({root or 'not in one'})")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    if argv and argv[0] == "--selftest":
        return _selftest()
    if argv:
        print(_USAGE, file=sys.stderr)
        return 2
    print(json.dumps({"skill_sha": skill_sha()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
