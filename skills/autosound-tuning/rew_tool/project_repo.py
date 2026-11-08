"""project_repo -- a project folder is a git repository, in code (hub #199, TCC-026; the Arbiter, 2026-09-23).

The method said a project's backup is set up at project start (`naming-and-structure.md` §4a), and nothing
carried it: `project_seed.py` wrote a `.gitignore` for a repository that might never exist, and the Arbiter's live
project `EPY-Sep2026` was not a repository at all -- no history, no backup, and nothing said so.

    python3 rew_tool/project_repo.py init <project>      git init, the .gitignore, one first commit
    python3 rew_tool/project_repo.py status <project> [--json] [--fetch]
    python3 rew_tool/project_repo.py save <project> [--dry-run]

* **init** makes the folder a repository and commits what is in it. With no git identity set on this machine, it
  sets one for THIS repository only: from the signed-in `gh` (the login and GitHub's no-reply address, so no
  personal address is written), else from the machine's login -- and says which. A git that is missing or fails
  is said in one line, and the project stays usable without history.
* **The GitHub backup is offered, never made** (creating a remote is outward-facing): where `gh` is signed in and
  the repository has no remote, `status` prints the one command for the user's yes. A user who chose no GitHub
  (no `gh`) is not asked again: local history is kept all the same.
* **save** (#204) commits the tuning files with the method's message and pushes. It stages only those, never
  `git add -A`: the housekeeping (`project_seed.HOUSEKEEPING`: `.sessions.log`, `.tcc/`, `*.tmp`, the key's files, the
  skill's link, ...) stays out even where an older `.gitignore` does not name it, and a link already tracked stops being
  tracked with the next commit. The order: no remote -> fetch -> the remote ahead -> commit -> push, every refusal
  before the commit, so a refusal and `--dry-run` leave the history, the index and the files as they were (a fetch moves
  only the last-known remote ref). A refusal is exit 1 with its line, a held git lock among them. Nothing to commit but
  commits not pushed is a push. A push that fails after the commit names the commit, and the next `save` sends it.
* **status --json** adds, beside `repo, remote, gh, init, offer`, `changes: {tuning, housekeeping}`,
  `ahead: [{hash, time, subject}]`, `remote_head: {hash, time}`, `fetched`, `fetch_error` and `sends` ("session" when
  the project's `CLAUDE.md` or `AGENTS.md` carries the rule, else "person"). The network stays out of it, as it runs at
  every `contract.py check` and TCC's window waits on it: it reads the last-known remote ref and says when that was
  fetched (`fetched`, null for never). `--fetch` asks the remote first; a fetch that failed is `fetch_error`.

Standard library only. Self-test: `python3 project_repo.py --selftest`.
"""

from __future__ import annotations

import contextlib
import datetime
import fnmatch
import getpass
import io
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
#: The commit `save` makes.
SAVE_COMMIT = "Tuning saved: {n} file(s)"
#: A first push carries the project's captures (TCC's own bound on it, Ruling 48).
PUSH_SECONDS = 600
FETCH_SECONDS = 60


def _git(project_dir, *args, env=None):
    return subprocess.run(["git", "-C", project_dir, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=60)


def _network(project_dir, seconds, *args):
    """git that goes to the remote: its whole tree ended at the deadline (#167: a helper or ssh holds the pipes), and
    no prompt for a password nobody is there to type. Raises `subprocess.TimeoutExpired` past it."""
    import bounded_run
    return bounded_run.run(["git", "-C", project_dir, *args], seconds, encoding="utf-8", errors="replace",
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))


def _git_paths(project_dir, paths, *args):
    """`git <args>` on exactly `paths`: on stdin, as hundreds of captures do not fit a Windows command line, and taken
    literally, as a `[` in a capture's title is no glob."""
    import bounded_run
    return bounded_run.run(["git", "--literal-pathspecs", "-C", project_dir, *args, "--pathspec-from-file=-",
                            "--pathspec-file-nul"], PUSH_SECONDS, input="\0".join(paths), encoding="utf-8",
                           errors="replace")


#: What `_gh` answers for a gh that did not answer in its deadline (#167): not "absent" -- gh is there.
NO_ANSWER = subprocess.CompletedProcess(["gh"], None, "", "no answer in 30 s")


def _gh(*args):
    """gh's `CompletedProcess`; None where there is no gh (or `AUTOSOUND_NO_GH=1`) or it cannot start; `NO_ANSWER`
    for one past its 30 s, its tree killed (#167)."""
    gh = shutil.which("gh")
    # AUTOSOUND_NO_GH=1: a self-test (or a machine that wants none of it) never reaches GitHub from here.
    if not gh or os.environ.get("AUTOSOUND_NO_GH") == "1":
        return None
    import bounded_run                       # #167: a deadline that ends the call on Windows too
    try:
        return bounded_run.run([gh, *args], 30, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return NO_ANSWER
    except OSError:
        return None


def gh_state():
    """"signed-in", "signed-out", "absent" -- or "no-answer" (#167): a gh that did not answer `auth status` in its
    30 s is there, and was read as absent, which stopped offering the backup without a word."""
    r = _gh("auth", "status")
    if r is None:
        return "absent"
    if r is NO_ANSWER:
        return "no-answer"
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
    project_seed.write_claude_md(project_dir)     # skill #65: the gate named where a session greps first
    project_seed.write_agents_md(project_dir)     # #149: the same two rules where Codex reads, which is not CLAUDE.md
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
    # #204: the skill's link is the installer's, and an existing .gitignore need not name it.
    _git(project_dir, "add", "-A", "--", ".", f":(exclude){project_seed.SKILL_LINK}")
    if _git(project_dir, "diff", "--cached", "--quiet").returncode == 0:
        state = "a repository already" if not fresh else "a repository now, with nothing to commit yet"
        return True, "; ".join([f"{project_dir} is {state}"] + said)
    r = _git(project_dir, "commit", "-q", "-m", FIRST_COMMIT if fresh else "Project files not yet in history")
    if r.returncode != 0:
        return False, f"git commit failed: {(r.stderr or r.stdout).strip()[-200:]}"
    return True, "; ".join([f"{project_dir} is a git repository{' now' if fresh else ''}, first commit made"] + said)


def _repo_state(project_dir):
    """`{"repo", "remote", "gh", "init", "offer"}`: what the project has, and the one command for what it lacks. `gh` is
    `gh_state()`'s: "signed-in", "signed-out", "absent" or "no-answer" (#167)."""
    project_dir = os.path.abspath(project_dir)
    here = os.path.abspath(__file__)
    out = {"repo": is_repo(project_dir), "remote": None, "gh": gh_state(), "init": None, "offer": None}
    if not out["repo"]:
        out["init"] = f'python3 "{here}" init "{project_dir}"'
        return out
    out["remote"] = _origin(project_dir)
    if not out["remote"] and out["gh"] == "signed-in":
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(project_dir)).strip("-") or "autosound-project"
        out["offer"] = f'gh repo create {name} --private --source "{project_dir}" --push'
    return out


def _origin(project_dir):
    r = _git(project_dir, "remote", "get-url", "origin")
    return r.stdout.strip() or None if r.returncode == 0 else None


def _branch(project_dir):
    """The branch HEAD is on, born or not; None for a detached HEAD."""
    r = _git(project_dir, "symbolic-ref", "-q", "--short", "HEAD")
    return r.stdout.strip() or None if r.returncode == 0 else None


def _tracking(project_dir, branch):
    """The last-known remote ref of `branch`, or None where the remote has not been seen to have it."""
    ref = f"refs/remotes/origin/{branch}"
    return ref if branch and _git(project_dir, "rev-parse", "-q", "--verify", ref).returncode == 0 else None


def _git_path(project_dir, name):
    return os.path.join(project_dir, _git(project_dir, "rev-parse", "--git-path", name).stdout.strip())


def _is_housekeeping(path):
    """`path`, as git names it: does it match `project_seed.HOUSEKEEPING`, read as `.gitignore` reads its lines? A name
    ending in `/` is a folder that git shows whole: another repository inside this one, which is not `save`'s to take."""
    import project_seed
    if path.endswith("/"):
        return True
    parts = path.split("/")
    for pattern in project_seed.HOUSEKEEPING:
        if pattern.endswith("/"):
            if pattern[:-1] in parts[:-1]:
                return True
        elif "/" in pattern:
            if path == pattern or path.startswith(pattern + "/"):
                return True
        elif any(fnmatch.fnmatchcase(part, pattern) for part in parts):
            return True
    return False


def _changes(project_dir):
    """What is not committed: `tuning` and `housekeeping` (each path once), `staged_housekeeping`, `unmerged`; None when
    git cannot say. Takes no lock of git's: this runs from a window while a commit may be under way."""
    r = _git(project_dir, "--no-optional-locks", "status", "--porcelain=v1", "-z", "--untracked-files=all",
             "--no-renames")
    if r.returncode != 0:
        return None
    out = {"tuning": [], "housekeeping": [], "staged_housekeeping": [], "unmerged": []}
    for entry in r.stdout.split("\0"):
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if xy in ("DD", "AU", "UD", "UA", "DU", "AA", "UU"):
            out["unmerged"].append(path)
        if _is_housekeeping(path):
            out["housekeeping"].append(path)
            if xy[0] not in " ?":
                out["staged_housekeeping"].append(path)
        else:
            out["tuning"].append(path)
    return out


def _commits(project_dir, *revs):
    """`[{hash, time, subject}]`, newest first; empty for a range git cannot read (a branch with no commit yet)."""
    r = _git(project_dir, "log", "--no-show-signature", "--format=%H%x00%cI%x00%s", *revs)
    if r.returncode != 0:
        return []
    return [dict(zip(("hash", "time", "subject"), line.split("\0", 2))) for line in r.stdout.splitlines() if line]


def _ahead(project_dir, branch):
    """The commits on `branch` the remote is not known to have. A branch the remote has never seen: all that no branch
    of the remote holds."""
    if not branch:
        return []
    ref = _tracking(project_dir, branch)
    return _commits(project_dir, f"{ref}..HEAD") if ref else _commits(project_dir, "HEAD", "--not", "--remotes=origin")


def _who_sends(project_dir):
    """"session" where `CLAUDE.md` or `AGENTS.md` carries the rule, "person" otherwise (a project from before it)."""
    import project_seed
    for name in ("CLAUDE.md", "AGENTS.md"):
        try:
            with open(os.path.join(project_dir, name), encoding="utf-8", errors="replace") as fh:
                if project_seed.SEND_RULE_MARK in fh.read():
                    return "session"
        except OSError:
            continue
    return "person"


def _fetch(project_dir):
    """Ask the remote. The reason it did not answer, or None."""
    try:
        r = _network(project_dir, FETCH_SECONDS, "fetch", "-q", "origin")
    except subprocess.TimeoutExpired:
        return f"the remote did not answer in {FETCH_SECONDS} s"
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-200:] or f"git fetch exited {r.returncode}"


def status(project_dir, fetch=False):
    """`_repo_state`'s five keys, which TCC requires, and what is not on the remote (#204: the module's docstring). Local
    only, unless `fetch`."""
    project_dir = os.path.abspath(project_dir)
    out = _repo_state(project_dir)
    out.update(changes={"tuning": [], "housekeeping": []}, ahead=[], remote_head=None, fetched=None, fetch_error=None,
               sends=_who_sends(project_dir))
    if not out["repo"]:
        return out
    changes = _changes(project_dir)
    if changes:
        out["changes"] = {"tuning": changes["tuning"], "housekeeping": changes["housekeeping"]}
    if not out["remote"]:
        return out
    if fetch:
        out["fetch_error"] = _fetch(project_dir)
    branch = _branch(project_dir)
    out["ahead"] = _ahead(project_dir, branch)
    ref = _tracking(project_dir, branch)
    if ref:
        head = _commits(project_dir, "-1", ref)
        out["remote_head"] = {"hash": head[0]["hash"], "time": head[0]["time"]} if head else None
    try:
        when = os.path.getmtime(_git_path(project_dir, "FETCH_HEAD"))
        out["fetched"] = datetime.datetime.fromtimestamp(when).astimezone().isoformat(timespec="seconds")
    except OSError:
        pass                                     # never fetched here: null says so
    return out


def save(project_dir, dry_run=False):
    """`(ok, line)`: commit the tuning files with the method's message and push them. `ok` False is a refusal, exit 1.
    Never raises on a git problem. (#204: the module's docstring.)"""
    project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(project_dir):
        return False, f"no folder {project_dir}"
    if not shutil.which("git"):
        return False, "git is not installed: nothing to send with (the installer brings it)"
    if not is_repo(project_dir):
        return False, f'{project_dir} is not a git repository: `python3 "{os.path.abspath(__file__)}" init "{project_dir}"`'
    try:
        return _save(project_dir, dry_run)
    except subprocess.TimeoutExpired as exc:
        return False, f"git did not finish in {exc.timeout} s: nothing was pushed"


def _count(n, what):
    return f"{n} {what}" + ("" if n == 1 else "s")


def _save(project_dir, dry_run):
    import project_seed
    if not _origin(project_dir):
        return False, "no remote: this project has nowhere to send to (`status` offers the GitHub backup)"
    branch = _branch(project_dir)
    if not branch:
        return False, "HEAD is not on a branch: finish what git is in the middle of, then save"
    lock = _git_path(project_dir, "index.lock")
    if os.path.exists(lock):
        return False, f"git's lock is held ({lock}): another git is at work, or one crashed and its lock needs removing"
    reason = _fetch(project_dir)
    if reason:
        return False, f"could not reach the remote: {reason}. Nothing changed"
    changes = _changes(project_dir)
    if changes is None:
        return False, "git could not read this project's changes. Nothing changed"
    if changes["unmerged"] or _git(project_dir, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0:
        return False, "a merge is not finished here: finish it, then save. Nothing changed"
    ref = _tracking(project_dir, branch)
    if ref:
        r = _git(project_dir, "rev-list", "--count", f"HEAD..{ref}" if _git(project_dir, "rev-parse", "-q", "--verify",
                                                                             "HEAD").returncode == 0 else ref)
        if r.returncode != 0:
            return False, f"could not compare with the remote: {r.stderr.strip()[-200:]}. Nothing changed"
        if int(r.stdout.strip() or 0):
            return False, (f"pull first: the remote has {_count(int(r.stdout), 'commit')} this copy does not. "
                           "Nothing changed")
    tuning, ahead = changes["tuning"], _ahead(project_dir, branch)
    kept_out = len(changes["housekeeping"])
    left = f"; {_count(kept_out, 'housekeeping file')} {'stays' if kept_out == 1 else 'stay'} out" if kept_out else ""
    if not tuning and not ahead:
        return False, f"nothing to send: no tuning file changed and no commit is waiting{left}"
    link_tracked = bool(_git(project_dir, "ls-files", "--", project_seed.SKILL_LINK).stdout.strip())

    if dry_run:
        parts = ([f"a new commit of {_count(len(tuning), 'file')}"] if tuning else []) + \
                ([f"{_count(len(ahead), 'commit')} already waiting"] if ahead else [])
        lines = [f"would send to origin: {' and '.join(parts)}{left}"]
        lines += [f"  {path}" for path in tuning]
        lines += [f"  commit {c['hash'][:9]} {c['subject']}" for c in ahead]
        if tuning and link_tracked:
            lines.append(f"  and stop tracking {project_seed.SKILL_LINK}")
        return True, "\n".join(lines)

    made = None
    if tuning:
        who = _identity_for_this_repo(project_dir)
        if who:
            _git(project_dir, "config", "user.name", who[0])
            _git(project_dir, "config", "user.email", who[1])
        steps = []
        if changes["staged_housekeeping"]:       # staged by hand: a commit takes the whole index
            steps.append(_git_paths(project_dir, changes["staged_housekeeping"], "reset", "-q"))
        steps.append(_git_paths(project_dir, tuning, "add"))
        if link_tracked:
            steps.append(_git(project_dir, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--",
                              project_seed.SKILL_LINK))
        steps.append(_git(project_dir, "commit", "-q", "-m", SAVE_COMMIT.format(n=len(tuning))))
        for step in steps:
            if step.returncode != 0:
                return False, f"could not commit: {(step.stderr or step.stdout).strip()[-200:]}. Nothing was pushed"
        made = _git(project_dir, "rev-parse", "--short", "HEAD").stdout.strip()

    try:
        r = _network(project_dir, PUSH_SECONDS, "push", "-q", "-u", "origin", branch)
        reason = None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-200:] or f"git push exited {r.returncode}"
    except subprocess.TimeoutExpired:
        reason = f"the push did not finish in {PUSH_SECONDS // 60} minutes"
    if reason:
        kept = f"commit {made} is made here and NOT sent" if made else f"{_count(len(ahead), 'commit')} here, NOT sent"
        return False, f"{kept}: {reason}. The next save sends it"
    sent = (f"commit {made} ({_count(len(tuning), 'file')})" if made else "") + \
           (" and " if made and ahead else "") + (_count(len(ahead), "waiting commit") if ahead else "")
    return True, f"sent to origin: {sent}{left}"


def status_lines(project_dir):
    """What `contract.py check` shows: nothing when there is nothing to do."""
    st = _repo_state(project_dir)
    if st["init"]:
        return [f"no git history in this project: `{st['init']}` (a first commit; no remote is made)"]
    if st["offer"]:
        return [f"no backup of this project on GitHub (gh is signed in): `{st['offer']}` -- only with the user's yes"]
    if not st["remote"] and st["gh"] == "signed-out":
        return ["no backup of this project on GitHub: gh is installed but not signed in (`gh auth login --web`)"]
    if not st["remote"] and st["gh"] == "no-answer":
        return ["no backup of this project on GitHub, and gh did not answer `gh auth status` in 30 s (a network that "
                "answers nothing?): run `gh auth status` once it can"]
    return []


# ── #204: `save` and the fuller `status` ─ every check on a temporary project and a bare remote beside it, with no
# identity, no system config and no gh: nothing below can reach a real remote or a real project.

@contextlib.contextmanager
def _sandbox():
    """`(project, bare remote, temp folder)`: a project with a first commit, the remote empty and not yet connected."""
    keys = ("HOME", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "AUTOSOUND_NO_GH")
    saved = {k: os.environ.get(k) for k in keys}
    with tempfile.TemporaryDirectory() as tmp:
        home = os.path.join(tmp, "home")
        os.makedirs(home)
        os.environ.update(HOME=home, GIT_CONFIG_GLOBAL=os.path.join(home, ".gitconfig"), GIT_CONFIG_NOSYSTEM="1",
                          AUTOSOUND_NO_GH="1")
        try:
            proj = os.path.join(tmp, "project")
            _write(proj, "project.json", "{}\n")
            bare = os.path.join(tmp, "remote.git")
            subprocess.run(["git", "init", "-q", "--bare", bare], check=True, capture_output=True)
            ok, line = init(proj)
            assert ok, line
            yield proj, bare, tmp
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _write(proj, rel, text="x\n"):
    path = os.path.join(proj, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _connect(proj, bare):
    assert _git(proj, "remote", "add", "origin", bare).returncode == 0
    r = _git(proj, "push", "-q", "-u", "origin", "HEAD")
    assert r.returncode == 0, r.stderr


def _link(proj):
    """The skill's link in the project; a real folder where this machine may not make one (Windows without the right)."""
    path = os.path.join(proj, ".claude", "skills", "autosound-tuning")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        os.symlink(_HERE, path, target_is_directory=True)
    except (OSError, NotImplementedError):
        _write(proj, ".claude/skills/autosound-tuning/SKILL.md")


def _said(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = main(list(argv))
    return rc, out.getvalue()


def _head(repo):
    return _git(repo, "rev-parse", "-q", "--verify", "HEAD").stdout.strip()


def _on_remote(bare):
    return _git(bare, "for-each-ref", "--format=%(objectname)", "refs/heads").stdout.strip()


def _tree(repo, rev):
    return _git(repo, "ls-tree", "-r", "--name-only", "-z", rev).stdout.split("\0")


def _porcelain(proj):
    return _git(proj, "status", "--porcelain").stdout


def _second_copy_pushes(bare, tmp):
    """Someone else's commit lands on the remote."""
    other = os.path.join(tmp, "other")
    r = subprocess.run(["git", "clone", "-q", bare, other], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    _git(other, "config", "user.name", "other")
    _git(other, "config", "user.email", "other@example.invalid")
    _write(other, "from-elsewhere.txt")
    _git(other, "add", "from-elsewhere.txt")
    _git(other, "commit", "-q", "-m", "from elsewhere")
    r = _git(other, "push", "-q", "origin", "HEAD")
    assert r.returncode == 0, r.stderr


def _refuse_pushes(bare):
    hook = os.path.join(bare, "hooks", "pre-receive")
    os.makedirs(os.path.dirname(hook), exist_ok=True)
    with open(hook, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("#!/bin/sh\necho refused by the test remote >&2\nexit 1\n")
    os.chmod(hook, 0o755)
    return hook


def _check_save_sends_the_tuning_files_and_only_those():
    with _sandbox() as (proj, bare, _tmp):
        _connect(proj, bare)
        before = _head(proj)
        for rel in ("process/journal.jsonl", "state/versions/v_002.json", "m-L_4 (sw) [захват].txt"):
            _write(proj, rel)
        _write(proj, ".sessions.log", "a session's log\n")
        _link(proj)
        rc, said = _said("save", proj)
        assert rc == 0 and _on_remote(bare) == _head(proj) != before, (rc, said)
        sent = _tree(bare, _on_remote(bare))
        for rel in ("process/journal.jsonl", "state/versions/v_002.json", "m-L_4 (sw) [захват].txt"):
            assert rel in sent, (rel, sent)
        assert ".sessions.log" not in sent, sent
        assert not [p for p in sent if p.startswith(".claude/")], sent
        assert _git(proj, "rev-parse", "HEAD~1").stdout.strip() == before, "more than one commit"
        assert _git(proj, "log", "-1", "--format=%s").stdout.startswith("Tuning saved"), "not the method's message"
        assert os.path.isfile(os.path.join(proj, ".sessions.log")), "the log was taken from the folder"
        assert ".sessions.log" in _porcelain(proj), "the log should stay as it was: not committed"


def _check_save_deletes_what_was_deleted():
    with _sandbox() as (proj, bare, _tmp):
        _write(proj, "old-sheet.md")
        init(proj)
        _connect(proj, bare)
        os.remove(os.path.join(proj, "old-sheet.md"))
        rc, said = _said("save", proj)
        assert rc == 0 and "old-sheet.md" not in _tree(bare, _on_remote(bare)), (rc, said)


def _check_a_refusal_changes_nothing():
    with _sandbox() as (proj, bare, tmp):
        # no remote
        _write(proj, "tuning.txt")
        before, dirty = _head(proj), _porcelain(proj)
        rc, said = _said("save", proj)
        assert rc == 1 and "no remote" in said, (rc, said)
        assert (_head(proj), _porcelain(proj)) == (before, dirty), "a refusal with no remote changed the repository"
        _connect(proj, bare)
        # the remote ahead
        _second_copy_pushes(bare, tmp)
        remote_was = _on_remote(bare)
        rc, said = _said("save", proj)
        assert rc == 1 and "pull first" in said, (rc, said)
        assert (_head(proj), _porcelain(proj), _on_remote(bare)) == (before, dirty, remote_was), said


def _check_nothing_to_send_is_refused():
    with _sandbox() as (proj, bare, _tmp):
        _connect(proj, bare)
        rc, said = _said("save", proj)
        assert rc == 1 and "nothing to send" in said, (rc, said)
        _write(proj, ".sessions.log")                 # housekeeping alone is nothing to send either
        rc, said = _said("save", proj)
        assert rc == 1 and "nothing to send" in said, (rc, said)


def _check_commits_not_pushed_are_a_push():
    with _sandbox() as (proj, bare, _tmp):
        _connect(proj, bare)
        _write(proj, "by-hand.txt")
        _git(proj, "add", "by-hand.txt")
        _git(proj, "commit", "-q", "-m", "a commit the session made")
        rc, said = _said("save", proj)
        assert rc == 0 and _on_remote(bare) == _head(proj), (rc, said)
        assert _git(proj, "log", "-1", "--format=%s").stdout.strip() == "a commit the session made", "a new commit"


def _check_dry_run_says_and_changes_nothing():
    with _sandbox() as (proj, bare, _tmp):
        _connect(proj, bare)
        _write(proj, "tuning.txt")
        _git(proj, "config", "--unset", "user.email")
        was = (_head(proj), _porcelain(proj), _on_remote(bare))
        rc, said = _said("save", proj, "--dry-run")
        assert rc == 0 and "tuning.txt" in said, (rc, said)
        assert (_head(proj), _porcelain(proj), _on_remote(bare)) == was, "--dry-run changed something"
        assert not _git(proj, "config", "user.email").stdout.strip(), "--dry-run set an identity"
        assert _said("save", proj, "--dryrun")[0] == 2 and _head(proj) == was[0], "a mistyped flag must not save"


def _check_a_push_the_remote_refuses_names_the_commit():
    with _sandbox() as (proj, bare, _tmp):
        _connect(proj, bare)
        remote_was = _on_remote(bare)
        _write(proj, "tuning.txt")
        hook = _refuse_pushes(bare)
        rc, said = _said("save", proj)
        short = _git(proj, "rev-parse", "--short", "HEAD").stdout.strip()
        assert rc == 1 and short and short in said and "not sent" in said.lower(), (rc, said, short)
        assert _on_remote(bare) == remote_was and "tuning.txt" in _tree(proj, "HEAD"), said
        ahead = status(proj).get("ahead")
        assert ahead and ahead[0]["hash"] == _head(proj), ahead
        os.remove(hook)
        rc, said = _said("save", proj)                # the next save sends it, with no new commit
        assert rc == 0 and _on_remote(bare) == _head(proj), (rc, said)
        assert len(_git(proj, "log", "--format=%H").stdout.split()) == 2, "the retry made a commit"


def _check_a_held_git_lock_is_a_refusal():
    with _sandbox() as (proj, bare, _tmp):
        _connect(proj, bare)
        _write(proj, "tuning.txt")
        lock = os.path.join(proj, ".git", "index.lock")
        with open(lock, "w", encoding="utf-8"):
            pass
        before = _head(proj)
        rc, said = _said("save", proj)
        assert rc == 1 and "lock" in said and _head(proj) == before, (rc, said)
        os.remove(lock)
        assert _said("save", proj)[0] == 0, "the lock gone, the save goes"


def _check_an_older_repository_keeps_the_link_and_the_key_out():
    """The seed leaves an existing `.gitignore` alone, so an older project's names neither; `save` holds by itself."""
    with _sandbox() as (proj, bare, _tmp):
        with open(os.path.join(proj, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("# an older project's own\n")
        _git(proj, "add", ".gitignore")
        _git(proj, "commit", "-q", "-m", "their own .gitignore")
        _link(proj)
        _git(proj, "add", "-A")                       # how the link got in before: init's add -A
        _git(proj, "commit", "-q", "-m", "the link came along")
        assert [p for p in _tree(proj, "HEAD") if p.startswith(".claude/")], "the setup did not track the link"
        _connect(proj, bare)
        _write(proj, "tuning.txt")
        _write(proj, ".critic-env", "GEMINI_API_KEY=AQ.x\n")
        _write(proj, ".sessions.log")
        _git(proj, "add", ".sessions.log")            # staged by hand: a commit of the whole index would take it
        rc, said = _said("save", proj)
        assert rc == 0, (rc, said)
        sent = _tree(bare, _on_remote(bare))
        assert "tuning.txt" in sent and ".sessions.log" not in sent and ".critic-env" not in sent, sent
        assert not [p for p in sent if p.startswith(".claude/")], ("a tracked link was not untracked", sent)
        assert os.path.lexists(os.path.join(proj, ".claude", "skills", "autosound-tuning")), "the link left the folder"


def _check_init_does_not_take_the_link():
    with _sandbox() as (proj, _bare, tmp):
        _link(proj)                                   # the seeded .gitignore names it
        _write(proj, "after.txt")
        init(proj)
        assert "after.txt" in _tree(proj, "HEAD") and not [p for p in _tree(proj, "HEAD") if p.startswith(".claude/")], \
            _tree(proj, "HEAD")
        older = os.path.join(tmp, "older")            # an existing .gitignore that does not name it
        _write(older, ".gitignore", "# their own\n")
        _link(older)
        assert init(older)[0]
        assert not [p for p in _tree(older, "HEAD") if p.startswith(".claude/")], _tree(older, "HEAD")


def _check_a_first_save_goes_to_an_empty_remote():
    with _sandbox() as (proj, bare, _tmp):
        assert _git(proj, "remote", "add", "origin", bare).returncode == 0     # connected, never pushed
        assert [c["hash"] for c in status(proj).get("ahead", [])] == [_head(proj)], "the first commit is not waiting"
        _write(proj, "tuning.txt")
        rc, said = _said("save", proj)
        assert rc == 0 and _on_remote(bare) == _head(proj), (rc, said)
        assert status(proj)["ahead"] == [] and _git(proj, "rev-parse", "--abbrev-ref", "@{u}").returncode == 0


def _check_an_identity_is_set_only_to_commit():
    with _sandbox() as (proj, bare, _tmp):
        _connect(proj, bare)
        _write(proj, "tuning.txt")
        _git(proj, "config", "--unset", "user.email")
        _git(proj, "config", "--unset", "user.name")
        rc, said = _said("save", proj)
        assert rc == 0 and _on_remote(bare) == _head(proj), (rc, said)
        assert _git(proj, "config", "user.email").stdout.strip(), "the commit had no identity of this repository's"


def _check_a_remote_that_cannot_be_reached():
    with _sandbox() as (proj, bare, tmp):
        _connect(proj, bare)
        _write(proj, "tuning.txt")
        _git(proj, "remote", "set-url", "origin", os.path.join(tmp, "no-such-remote.git"))
        was = (_head(proj), _porcelain(proj))
        rc, said = _said("save", proj)
        assert rc == 1 and "could not reach" in said and (_head(proj), _porcelain(proj)) == was, (rc, said)
        assert status(proj).get("fetch_error") is None, "status went to the network"
        rc, said = _said("status", proj, "--json", "--fetch")
        assert rc == 0 and json.loads(said).get("fetch_error"), (rc, said)


def _check_status_keeps_what_tcc_reads_and_adds_the_rest():
    with _sandbox() as (proj, bare, tmp):
        st = status(os.path.join(tmp, "project"))
        for key, want in (("repo", True), ("remote", None), ("gh", "absent"), ("init", None), ("offer", None)):
            assert st.get(key) == want, (key, st)
        assert st.get("ahead") == [] and st.get("remote_head") is None, st         # no remote
        _connect(proj, bare)
        remote_was = _on_remote(bare)
        _write(proj, "tuning.txt")
        _write(proj, ".sessions.log")
        _write(proj, "leftover.123-ab.tmp")
        _git(proj, "add", "-f", "leftover.123-ab.tmp")
        rc, said = _said("status", proj, "--json")
        st = json.loads(said)
        changes = st.get("changes") or {}
        assert changes.get("tuning") == ["tuning.txt"], st
        assert sorted(changes.get("housekeeping") or []) == [".sessions.log", "leftover.123-ab.tmp"], st
        assert st.get("ahead") == [] and (st.get("remote_head") or {}).get("hash") == remote_was, st
        assert (st.get("remote_head") or {}).get("time"), st
        # commits not on the remote, newest first: hash, time, first line
        _git(proj, "reset", "-q", "leftover.123-ab.tmp")
        _git(proj, "add", "tuning.txt")
        _git(proj, "commit", "-q", "-m", "first line\n\nthe body")
        ahead = status(proj).get("ahead")
        assert ahead and ahead[0]["hash"] == _head(proj) and ahead[0]["subject"] == "first line" and ahead[0]["time"], ahead
        # the network stays out: a commit on the remote is not seen until something fetches
        _second_copy_pushes(bare, tmp)
        moved = _on_remote(bare)
        assert moved != remote_was
        st = status(proj)
        assert st["remote_head"]["hash"] == remote_was, ("status went to the network", st)
        rc, said = _said("status", proj, "--json", "--fetch")
        st = json.loads(said)
        assert st["remote_head"]["hash"] == moved and st.get("fetched"), st
        # and what `contract.py check` prints is what it was
        assert status_lines(proj) == [], status_lines(proj)


def _check_status_with_no_repository_carries_the_keys_empty():
    with _sandbox() as (_proj, _bare, tmp):
        bare_folder = os.path.join(tmp, "not-a-repo")
        os.makedirs(bare_folder)
        st = status(bare_folder)
        assert st.get("repo") is False and st.get("init"), st
        assert st.get("changes") == {"tuning": [], "housekeeping": []}, st
        assert st.get("ahead") == [] and st.get("remote_head") is None and "fetched" in st, st


def _check_sends_says_who_sends():
    with _sandbox() as (proj, _bare, tmp):
        assert status(proj).get("sends") == "session", status(proj)        # seeded with the rule, in both files
        own = os.path.join(tmp, "own-files")
        _write(own, "CLAUDE.md", "# their own\n")
        _write(own, "AGENTS.md", "# their own too\n")
        assert init(own)[0] and status(own).get("sends") == "person", status(own)
        # either seeded file carries it
        with open(os.path.join(proj, "CLAUDE.md"), encoding="utf-8") as fh:
            rule = [ln for ln in fh.read().splitlines() if "project_repo.py save" in ln]
        assert rule, "CLAUDE.md does not carry the rule"
        os.remove(os.path.join(proj, "CLAUDE.md"))
        assert status(proj).get("sends") == "session", "AGENTS.md alone should say session"


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
            # skill #65: the project says where issues go, in the file a session reads first.
            assert "CLAUDE.md" in tracked and "post_feedback" in open(os.path.join(proj, "CLAUDE.md"), encoding="utf-8").read()
            # #149: and in the file Codex reads, which is not CLAUDE.md.
            assert "AGENTS.md" in tracked and "post_feedback" in open(os.path.join(proj, "AGENTS.md"), encoding="utf-8").read()
            ok2, line2 = init(proj)
            assert ok2 and "a repository already" in line2, line2          # a second run changes nothing
            st2 = status(proj)
            assert st2["repo"] and st2["gh"] == "absent" and st2["offer"] is None and status_lines(proj) == [], st2
            # #149: a repository made before AGENTS.md -- CLAUDE.md committed, no AGENTS.md -- gets it from init, and
            # it is committed; the project's CLAUDE.md stays byte for byte.
            _git(proj, "rm", "-q", "AGENTS.md")
            _git(proj, "commit", "-q", "-m", "a project from before #149")
            claude_was = open(os.path.join(proj, "CLAUDE.md"), "rb").read()
            head_was = _git(proj, "rev-parse", "HEAD").stdout.strip()
            ok4, line4 = init(proj)
            assert ok4 and "first commit made" in line4, line4
            assert _git(proj, "rev-parse", "HEAD~1").stdout.strip() == head_was, "init made more than one commit"
            assert "AGENTS.md" in _git(proj, "ls-files").stdout.split(), "init did not commit AGENTS.md"
            assert _git(proj, "status", "--porcelain").stdout == "", _git(proj, "status", "--porcelain").stdout
            assert open(os.path.join(proj, "CLAUDE.md"), "rb").read() == claude_was, "init rewrote CLAUDE.md"
            # #167: a gh that does not answer in its 30 s is its own state, said in one line -- not "absent", which
            # stopped offering the backup as if gh were not installed.
            globals()["_gh"] = lambda *a: NO_ANSWER
            st3 = status(proj)
            said = status_lines(proj)
            assert st3["gh"] == "no-answer" and st3["offer"] is None and len(said) == 1 \
                and "did not answer" in said[0], (st3, said)
            globals()["_gh"] = lambda *a: None
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
    failures = []
    for check in (_check_save_sends_the_tuning_files_and_only_those, _check_save_deletes_what_was_deleted,
                  _check_a_refusal_changes_nothing, _check_nothing_to_send_is_refused,
                  _check_commits_not_pushed_are_a_push, _check_dry_run_says_and_changes_nothing,
                  _check_a_push_the_remote_refuses_names_the_commit, _check_a_held_git_lock_is_a_refusal,
                  _check_an_older_repository_keeps_the_link_and_the_key_out, _check_init_does_not_take_the_link,
                  _check_a_first_save_goes_to_an_empty_remote, _check_an_identity_is_set_only_to_commit,
                  _check_a_remote_that_cannot_be_reached, _check_status_keeps_what_tcc_reads_and_adds_the_rest,
                  _check_status_with_no_repository_carries_the_keys_empty, _check_sends_says_who_sends):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {str(exc)[:300]}")
    assert not failures, f"{len(failures)} failed:\n" + "\n".join(failures)
    print("selftest[project_repo] OK -- a project becomes a repository with one first commit, the key file kept out "
          "by the seeded .gitignore; with no identity, one for this repository only; a second run is a no-op; no gh, "
          "no GitHub offer; a folder inside another repository is not taken for one; save sends the tuning files only, "
          "refuses with a reason and changes nothing, and names a commit the remote would not take; status splits and lists")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] in (["--selftest"], ["selftest"]):
        return _selftest()
    if len(argv) < 2 or argv[0] not in ("init", "status", "save") or (argv[0] == "save" and set(argv[2:]) - {"--dry-run"}):
        print(__doc__)                   # a mistyped `--dry-run` must not be a real save
        return 2
    if argv[0] == "init":
        ok, line = init(argv[1])
        print(("✓ " if ok else "✗ ") + line)
        return 0 if ok else 1
    if argv[0] == "save":
        ok, line = save(argv[1], dry_run="--dry-run" in argv)
        print(("✓ " if ok else "✗ ") + line)
        return 0 if ok else 1
    st = status(argv[1], fetch="--fetch" in argv)
    if "--json" in argv:
        print(json.dumps(st))
    else:
        print("\n".join(status_lines(argv[1])) or "✓ a repository" + (f", backed up to {st['remote']}" if st["remote"] else ""))
    return 0


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    raise SystemExit(main())
