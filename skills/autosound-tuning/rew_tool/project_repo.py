"""project_repo -- a project folder is a git repository, in code (hub #199, TCC-026; the Arbiter, 2026-09-23).

The method said a project's backup is set up at project start (`naming-and-structure.md` §4a), and nothing
carried it: `project_seed.py` wrote a `.gitignore` for a repository that might never exist, and the Arbiter's live
project `EPY-Sep2026` was not a repository at all -- no history, no backup, and nothing said so.

    python3 rew_tool/project_repo.py init <project>      git init, the .gitignore, one first commit
    python3 rew_tool/project_repo.py status <project> [--json]

* **init** makes the folder a repository and commits what is in it. With no git identity set on this machine, it
  sets one for THIS repository only: from the signed-in `gh` (the login and GitHub's no-reply address, so no
  personal address is written), else from the machine's login -- and says which. A git that is missing or fails
  is said in one line, and the project stays usable without history.
* **The GitHub backup is offered, never made** (creating a remote is outward-facing): where `gh` is signed in and
  the repository has no remote, `status` prints the one command for the user's yes. A user who chose no GitHub
  (no `gh`) is not asked again: local history is kept all the same.

Standard library only. Self-test: `python3 project_repo.py --selftest`.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

FIRST_COMMIT = "Project started: the method's files as seeded"


def _git(project_dir, *args, env=None):
    return subprocess.run(["git", "-C", project_dir, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=60)


def _gh(*args):
    gh = shutil.which("gh")
    # AUTOSOUND_NO_GH=1: a self-test (or a machine that wants none of it) never reaches GitHub from here.
    if not gh or os.environ.get("AUTOSOUND_NO_GH") == "1":
        return None
    try:
        return subprocess.run([gh, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None


def gh_state():
    """"signed-in", "signed-out" or "absent"."""
    r = _gh("auth", "status")
    if r is None:
        return "absent"
    return "signed-in" if r.returncode == 0 else "signed-out"


def is_repo(project_dir):
    """True when `project_dir` is itself the top of a git repository (not merely inside someone else's)."""
    if not shutil.which("git") or not os.path.isdir(project_dir):
        return False
    r = _git(project_dir, "rev-parse", "--show-toplevel")
    return r.returncode == 0 and os.path.realpath(r.stdout.strip()) == os.path.realpath(project_dir)


def _identity_for_this_repo(project_dir):
    """`(name, email, from)` for a repository with no identity to commit under, or None when one is set."""
    if _git(project_dir, "config", "user.email").stdout.strip():
        return None
    r = _gh("api", "user", "--jq", ".login + \" \" + (.id|tostring)")
    if r is not None and r.returncode == 0 and len(r.stdout.split()) == 2:
        login, uid = r.stdout.split()
        return login, f"{uid}+{login}@users.noreply.github.com", "the signed-in GitHub account (its no-reply address)"
    user = getpass.getuser()
    host = re.sub(r"[^A-Za-z0-9.-]", "", socket.gethostname()) or "localhost"
    return user, f"{user}@{host}", "this machine's login"


def init(project_dir):
    """`(ok, line)`: make `project_dir` a repository with one first commit. Never raises on a git problem."""
    project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(project_dir):
        return False, f"no folder {project_dir}"
    if not shutil.which("git"):
        return False, "git is not installed: the project has no history until it is (the installer brings it)"
    import project_seed
    project_seed.write_gitignore(project_dir)
    fresh = not is_repo(project_dir)
    if fresh:
        r = _git(project_dir, "init", "-q")
        if r.returncode != 0:
            return False, f"git init failed: {(r.stderr or r.stdout).strip()[-200:]}"
    said = []
    who = _identity_for_this_repo(project_dir)
    if who:
        _git(project_dir, "config", "user.name", who[0])
        _git(project_dir, "config", "user.email", who[1])
        said.append(f"git identity for this project only: {who[0]} <{who[1]}>, from {who[2]}")
    _git(project_dir, "add", "-A")
    if _git(project_dir, "diff", "--cached", "--quiet").returncode == 0:
        state = "a repository already" if not fresh else "a repository now, with nothing to commit yet"
        return True, "; ".join([f"{project_dir} is {state}"] + said)
    r = _git(project_dir, "commit", "-q", "-m", FIRST_COMMIT if fresh else "Project files not yet in history")
    if r.returncode != 0:
        return False, f"git commit failed: {(r.stderr or r.stdout).strip()[-200:]}"
    return True, "; ".join([f"{project_dir} is a git repository{' now' if fresh else ''}, first commit made"] + said)


def status(project_dir):
    """`{"repo", "remote", "gh", "init", "offer"}`: what the project has, and the one command for what it lacks."""
    project_dir = os.path.abspath(project_dir)
    here = os.path.abspath(__file__)
    out = {"repo": is_repo(project_dir), "remote": None, "gh": gh_state(), "init": None, "offer": None}
    if not out["repo"]:
        out["init"] = f'python3 "{here}" init "{project_dir}"'
        return out
    r = _git(project_dir, "remote", "get-url", "origin")
    out["remote"] = r.stdout.strip() or None if r.returncode == 0 else None
    if not out["remote"] and out["gh"] == "signed-in":
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(project_dir)).strip("-") or "autosound-project"
        out["offer"] = f'gh repo create {name} --private --source "{project_dir}" --push'
    return out


def status_lines(project_dir):
    """What `contract.py check` shows: nothing when there is nothing to do."""
    st = status(project_dir)
    if st["init"]:
        return [f"no git history in this project: `{st['init']}` (a first commit; no remote is made)"]
    if st["offer"]:
        return [f"no backup of this project on GitHub (gh is signed in): `{st['offer']}` -- only with the user's yes"]
    if not st["remote"] and st["gh"] == "signed-out":
        return ["no backup of this project on GitHub: gh is installed but not signed in (`gh auth login --web`)"]
    return []


def _selftest():
    if not shutil.which("git"):
        print("selftest[project_repo] SKIPPED -- no git on this machine")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "EPY Sep2026")
        os.makedirs(proj)
        with open(os.path.join(proj, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"project_rev": 0}, fh)
        with open(os.path.join(proj, ".critic-env"), "w", encoding="utf-8") as fh:
            fh.write("GEMINI_API_KEY=AQ." + "x" * 50 + "\n")
        env_home = os.path.join(tmp, "home")                    # no global identity: the fallback must work
        os.makedirs(env_home)
        saved = {k: os.environ.get(k) for k in ("HOME", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")}
        os.environ.update(HOME=env_home, GIT_CONFIG_GLOBAL=os.path.join(env_home, ".gitconfig"), GIT_CONFIG_NOSYSTEM="1")
        # no gh either (it may share a folder with git on PATH, so it is stubbed, not hidden): the identity falls
        # back to the machine's login, and no GitHub offer is made
        real_gh = globals()["_gh"]
        globals()["_gh"] = lambda *a: None
        try:
            st = status(proj)
            assert not st["repo"] and "init" in st["init"] and status_lines(proj)[0].startswith("no git history"), st
            ok, line = init(proj)
            assert ok and "first commit made" in line and "this machine's login" in line, line
            assert is_repo(proj) and _git(proj, "log", "--oneline").stdout.count("\n") == 1
            tracked = _git(proj, "ls-files").stdout.split()
            assert "project.json" in tracked and ".gitignore" in tracked and ".critic-env" not in tracked, tracked
            ok2, line2 = init(proj)
            assert ok2 and "a repository already" in line2, line2          # a second run changes nothing
            st2 = status(proj)
            assert st2["repo"] and st2["gh"] == "absent" and st2["offer"] is None and status_lines(proj) == [], st2
            # a folder inside another repository is not a repository of its own
            inner = os.path.join(proj, "sub")
            os.makedirs(inner)
            assert not is_repo(inner)
        finally:
            globals()["_gh"] = real_gh
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    print("selftest[project_repo] OK -- a project becomes a repository with one first commit, the key file kept out "
          "by the seeded .gitignore; with no identity, one for this repository only; a second run is a no-op; no gh, "
          "no GitHub offer; a folder inside another repository is not taken for one")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] in (["--selftest"], ["selftest"]):
        return _selftest()
    if len(argv) < 2 or argv[0] not in ("init", "status"):
        print(__doc__)
        return 2
    if argv[0] == "init":
        ok, line = init(argv[1])
        print(("✓ " if ok else "✗ ") + line)
        return 0 if ok else 1
    st = status(argv[1])
    if "--json" in argv:
        print(json.dumps(st))
    else:
        print("\n".join(status_lines(argv[1])) or "✓ a repository" + (f", backed up to {st['remote']}" if st["remote"] else ""))
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    raise SystemExit(main())
