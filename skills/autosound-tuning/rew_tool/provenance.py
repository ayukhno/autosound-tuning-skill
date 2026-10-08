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

#: `(skill_sha(), sha_unknown_because())` for the life of the process, once asked. `None` means "not asked yet"; a
#: sha of `""` is an answer. A stamp that changed halfway through a run would put two writers in one file.
_CACHE = None

#: `(case, why)` for each case the selftest could not check on this machine, said one line above its OK line.
_NOT_CHECKED_HERE = []


def repo_root():
    """The checkout this file lives in, or None when it lives in none.

    Resolve the link FIRST, then walk up looking for a marker rather than counting levels: an
    installed method is `~/.claude/skills/autosound-tuning`, a symlink (a junction on Windows) into
    the installer's clone, and two levels up from the LINK is `~/.claude`, which is no checkout at
    all. The companion app bought this: every installed machine reported "not a git checkout" while
    a developer's own tree worked and hid it (`vendor_loader.skill_repo_root`, 2026-08-19). The
    same walk and the same markers here, so the two find the same root by construction rather than
    by coincidence. Their answers part at one root: a copy with no checkout of its own, inside
    another repository, where this says "" (`_answer_at`) and the app asks git without that test.

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


def _same_folder(a, b):
    """True when `a` and `b` name one folder on disk (`os.path.samefile`): a path typed in another letter case where the
    filesystem ignores case (macOS's APFS, NTFS), through a link, an 8.3 name, git's `C:/...` on Windows. Comparing
    the strings named one folder as two on macOS, where `normcase` changes nothing and `realpath` keeps the case as
    typed (part A's re-review, N-2). A path that cannot be read is not the same folder."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _answer_at(root):
    """`(sha, why)` for the checkout at `root`: HEAD's forty characters and "", or "" and why it cannot be told --
    never an exception, never a traceback.

    HEAD, not the state of the working tree: a modified checkout stamps the commit it is based on.
    That is coarse on purpose — the companion app's number means exactly the same thing, and a
    stamp that disagreed with what the screen shows would be worse than one that is honest about
    being a commit and nothing more.

    Only `root`'s own repository answers (the final review's M1): `repo_root` takes a folder holding
    `.claude-plugin/plugin.json` with no `.git`, and git asked there walks up into any repository the copy was unpacked
    inside, whose HEAD is no commit of the method's. So the repository git finds must be `root` itself. `why` names
    the cause -- no git, git not answering, git's own words, a repository around the copy -- where every one of them
    read as "no git".
    """
    try:
        done = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel", "HEAD"],
                              capture_output=True, text=True, timeout=_TIMEOUT, check=False, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return "", "git is not installed here"
    except subprocess.TimeoutExpired:
        return "", f"git did not answer in {_TIMEOUT:g} s"
    except Exception as exc:  # noqa: BLE001 — git that cannot be run is a finding, not a crash
        return "", f"git could not be run ({type(exc).__name__}: {exc})"
    lines = [line.strip() for line in (done.stdout or "").splitlines() if line.strip()]
    if done.returncode != 0 or len(lines) < 2:
        said = [line.strip() for line in (done.stderr or "").splitlines() if line.strip()]
        return "", (f"git: {said[0]}" if said else f"git rev-parse exited {done.returncode}")
    top, first = lines[0], lines[1]
    if not _same_folder(top, root):
        return "", f"{root} is no checkout of its own: git answers for {top}, a repository around it"
    # RECOGNISED, not trusted. git prints its failures as text, and `fatal: not a git repository`
    # standing in the field that identifies the method would be worse than an empty one: it looks
    # like data. Anything that is not forty hex characters is not an answer.
    if not _SHA.match(first):
        return "", f"git answered {first!r}, which is no commit"
    return first, ""


def _sha_at(root):
    """`git rev-parse HEAD` in `root`'s own repository, or "" (`_answer_at`, without the why)."""
    return _answer_at(root)[0]


def _answer():
    """`(sha, why)` for this checkout, asked once per process (`_CACHE`)."""
    global _CACHE
    if _CACHE is None:
        root = repo_root()
        _CACHE = (("", "this copy is in no checkout of the method (no .claude-plugin/plugin.json or .git in the four "
                       "folders above rew_tool/provenance.py)") if root is None else _answer_at(root))
    return _CACHE


def skill_sha():
    """The commit this checkout of the method is at, or "" when it cannot be told.

    `""` is a real answer, not a failure: a skill folder unpacked on its own is in no repository,
    and a machine without git cannot be asked. Writers stamp it as it comes rather than dropping
    the key, so a reader can tell "asked, could not be told" from "written before anything asked" —
    the same distinction `dsp_profile` draws between a null fact and an absent one. Why it could not be told is
    `sha_unknown_because()`.
    """
    return _answer()[0]


def sha_unknown_because():
    """Why `skill_sha()` is "": no checkout around this copy, a repository around the copy that is not its own, no git,
    git not answering, or git's own words -- "" when the sha is told (the final review's M1)."""
    return _answer()[1]


# --------------------------------------------------------------------------- CLI
_USAGE = """usage: provenance.py [--selftest]

  (no arguments)   the stamp this checkout writes, as JSON
  --selftest       this module's own gates, on throwaway repositories
"""


def _check_a_copy_inside_another_repository():
    """A copy of the method unpacked inside another repository -- `.claude-plugin/plugin.json` and no `.git` of its own
    -- has no sha, never that repository's (the final review's M1): `git -C <copy> rev-parse HEAD` walks up past the
    copy, and `contract.py version` and the journal's `written_by` stamped the enclosing repository's HEAD as the
    method's -- a wrong sha that looks exactly like a right one. The answer says why: the repository git found is
    another folder. A copy in no repository at all says git's own words, never "no git" for a git that answered."""
    import tempfile

    def git(cwd, *args):
        subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True,
                       env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull},
                       encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory() as tmp:
        outer = os.path.join(tmp, "another-repo")
        copy = os.path.join(outer, "vendor", "autosound-tuning")
        os.makedirs(os.path.join(copy, ".claude-plugin"))
        with open(os.path.join(copy, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as fh:
            fh.write('{"name": "autosound-tuning", "version": "3.1.2"}\n')
        git(outer, "init", "--quiet")
        git(outer, "config", "user.email", "selftest@example.invalid")
        git(outer, "config", "user.name", "selftest")
        git(outer, "add", ".")
        git(outer, "commit", "--quiet", "-m", "a repository the copy sits in")
        assert _is_root(copy) and not os.path.exists(os.path.join(copy, ".git")), "the fixture is no bare copy"
        assert _sha_at(copy) == "", f"a copy inside another repository answered {_sha_at(copy)!r}, that repository's"
        sha, why = _answer_at(copy)
        assert sha == "" and why.startswith(f"{copy} is no checkout of its own: git answers for ") \
            and "a repository around it" in why, (sha, why)
        # Outside any repository git says so itself; inside one the temp folder sits in, the folder is not that one's.
        alone = os.path.join(tmp, "alone")
        os.makedirs(alone)
        sha, why = _answer_at(alone)
        assert sha == "" and ((why.startswith("git: ") and "not a git repository" in why)
                              or "is no checkout of its own" in why), (sha, why)


def _check_a_checkout_named_in_another_letter_case():
    """A checkout of its own, run by a path typed in another letter case, is that checkout (part A's re-review, N-2):
    macOS's APFS and NTFS ignore case, `realpath` keeps the case the path was typed in and git prints the folder's
    own, so the two strings named one folder as two -- `sha unknown (... is no checkout of its own: git answers for
    ..., a repository around it)`, and the journal stamped "". Where this filesystem tells cases apart, the other
    spelling is no folder: that is said as not checked here."""
    import tempfile

    def git(cwd, *args):
        subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True,
                       env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull},
                       encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "Method-Copy")
        os.makedirs(repo)
        git(repo, "init", "--quiet")
        git(repo, "config", "user.email", "selftest@example.invalid")
        git(repo, "config", "user.name", "selftest")
        git(repo, "commit", "--quiet", "--allow-empty", "-m", "a checkout of its own")
        other = os.path.join(tmp, "Method-Copy".swapcase())
        if not os.path.isdir(other):
            _NOT_CHECKED_HERE.append(("a checkout named in another letter case",
                                      "this filesystem tells letter cases apart"))
            return
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                              encoding="utf-8", errors="replace").stdout.strip()
        assert _answer_at(other) == (head, ""), _answer_at(other)


def _selftest():
    """Both directions on real repositories, because both have been wrong in the neighbouring tree.

    A checkout must give ITS commit (not a parent's, not a tag object's), and a directory that is
    no repository must give "" rather than git's complaint about it. The second half is the one
    worth having: it is the case that produced `fatal: …` in an identifier field.
    """
    import tempfile
    failures = []
    for check in (_check_a_copy_inside_another_repository, _check_a_checkout_named_in_another_letter_case):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

    def git(cwd, *args):
        subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True,
                       env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                            "GIT_CONFIG_SYSTEM": os.devnull}, encoding="utf-8", errors="replace")

    with tempfile.TemporaryDirectory() as tmp:
        # -- a real checkout answers with its own HEAD --
        repo = os.path.join(tmp, "repo")
        os.makedirs(repo)
        git(repo, "init", "--quiet")
        git(repo, "config", "user.email", "selftest@example.invalid")
        git(repo, "config", "user.name", "selftest")
        open(os.path.join(repo, "f"), "w", encoding="utf-8").close()
        git(repo, "add", "f")
        git(repo, "commit", "--quiet", "-m", "one")
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True, encoding="utf-8", errors="replace").stdout.strip()
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
                               capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
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
    for case, why in _NOT_CHECKED_HERE:                  # one line above the OK line, as siblings.py says its own
        print(f"provenance: {case} was not checked here -- {why}")
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
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(main())
