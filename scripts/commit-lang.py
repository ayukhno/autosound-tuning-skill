#!/usr/bin/env python3
"""A commit message reaches GitHub in English: no Cyrillic in it, checked when the commit is made.

The user's rule (2026-09-13): everything written to the project's GitHub is in English, except the
language versions of the skill. A commit subject is the most public of those places without looking
like one -- GitHub shows it as the title of the CI run the push starts -- and the Actions lists of
this repository and of the companion app carried Ukrainian titles for weeks before anyone looked.
The rule went into a memory file and into `CLAUDE.md` that morning; a rule that lives only in prose
is the one that already failed (`CLAUDE.md`, on deployments), so this is the CHECK behind it:

  scripts/commit-lang.py MSGFILE            the commit-msg hook: exit 1 if the message has Cyrillic,
                                            naming each line
  scripts/commit-lang.py --install-hook [REPO]
                                            write that hook into REPO/.git/hooks/commit-msg

The whole message is checked, not only the subject: the body lands on the commit page and in any PR
built from it. A commit that edits a translation is described in English too -- name the file and
line instead of quoting the text. Not checked: git's own comment lines (`#` followed by a space, a
tab or nothing -- an issue reference such as `#19: ...` IS checked, because with `-m` git keeps it
as the subject) and everything below the scissors line `git commit -v` adds. `git commit
--no-verify` skips every hook; that is git's door, not one this file can close.

`--selftest` commits through git in a throwaway repository: an English message passes; a Cyrillic
subject, a Cyrillic body line and a `#19:` subject are each refused and named, and none of them
lands; git's template comments and the diff under the scissors are ignored; a foreign hook is never
overwritten. stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

#: Cyrillic and Cyrillic Supplement -- the script this project's non-English text is written in.
CYRILLIC = re.compile("[Ѐ-ԯ]")
#: What git strips when it cleans a message up: `#` followed by whitespace or the end of the line.
GIT_COMMENT = re.compile(r"^#(\s|$)")
SCISSORS = "------------------------ >8 ------------------------"


def _git(repo, *args, env=None, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r


def findings(message):
    """`[(line number, line)]` for every line git keeps that has Cyrillic in it."""
    out = []
    for n, line in enumerate(message.splitlines(), 1):
        if GIT_COMMENT.match(line):
            if SCISSORS in line:
                break                                  # below it is the diff `commit -v` shows
            continue
        if CYRILLIC.search(line):
            out.append((n, line))
    return out


def render(found):
    lines = ["commit-lang: the commit message is not in English -- everything that reaches GitHub is"]
    for n, line in found:
        lines.append(f"  x line {n}: {line if len(line) <= 72 else line[:69] + '...'}")
    lines.append("  the subject becomes the title of the CI run; describe a translation change in English")
    lines.append("  and name the file and line instead of quoting it")
    return "\n".join(lines)


HOOK = """#!/usr/bin/env bash
# commit-msg: what reaches GitHub is in English. Written by scripts/commit-lang.py --install-hook.
# A line with Cyrillic in the message refuses the commit and says which line.
command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "{check}" "$1"
"""


def install_hook(repo, env=None):
    """The commit-msg hook into `repo`, refusing to overwrite a hook that is not ours."""
    top = _git(repo, "rev-parse", "--show-toplevel", env=env).stdout.strip()
    hooks = _git(repo, "rev-parse", "--git-path", "hooks", env=env).stdout.strip()
    if not os.path.isabs(hooks):
        hooks = os.path.join(top, hooks)
    os.makedirs(hooks, exist_ok=True)
    path = os.path.join(hooks, "commit-msg")
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            if "commit-lang.py" not in fh.read():
                raise SystemExit(f"{path} exists and is not ours -- chain it by hand: "
                                 f'python3 {os.path.abspath(__file__)} "$1"')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HOOK.format(check=os.path.abspath(__file__)))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _selftest():
    # A throwaway repository with no global or system config: a hooksPath or commit signing set on
    # this machine must neither redirect the hook we install nor break the commits we make.
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    # The real subject from this repository's Actions list, 2026-09-11 ("Zbir 11.09: ... published").
    uk = "Збір 11.09: v3.0.49 опубліковано"

    # 1. Which lines count.
    assert findings("Add the award photo\n\nThird place, Frankfurt.\n") == []
    assert [n for n, _ in findings(f"{uk}\n")] == [1]
    assert [n for n, _ in findings(f"English subject\n\nbody\n{uk}\n")] == [4]
    assert [n for n, _ in findings(f"#19: {uk}\n")] == [1], "an issue reference is a subject, not a comment"
    template = (f"English subject\n# Please enter the commit message for your changes.\n#\tmodified:   {uk}.md\n"
                f"#\n# {SCISSORS}\ndiff --git a/x b/x\n+{uk}\n")
    assert findings(template) == [], findings(template)

    # 2. Through git itself: the hook installs, passes English, refuses each Cyrillic shape.
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init", "-q", "-b", "main", tmp], check=True, env=env)
        hook = install_hook(tmp, env=env)
        with open(hook, encoding="utf-8") as fh:
            assert os.access(hook, os.X_OK) and "commit-lang.py" in fh.read()

        def commit(msg):
            with open(os.path.join(tmp, "f.txt"), "a", encoding="utf-8") as fh:
                fh.write("x\n")
            _git(tmp, "add", "f.txt", env=env)
            r = _git(tmp, "commit", "-q", "-m", msg, env=env, check=False)
            return r.returncode, r.stdout + r.stderr

        rc, out = commit("Add the German EMMA Final photo\n\nThird place, Frankfurt.")
        assert rc == 0, out
        for msg, line in ((uk, "line 1"), (f"English subject\n\nbody\n{uk}", "line 4"), (f"#19: {uk}", "line 1")):
            rc, out = commit(msg)
            assert rc != 0 and line in out and "not in English" in out, (msg, rc, out)
        count = _git(tmp, "rev-list", "--count", "HEAD", env=env).stdout.strip()
        assert count == "1", f"a refused commit landed: {count} commits"

        # 3. A hook that is not ours is not overwritten.
        with open(hook, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        try:
            install_hook(tmp, env=env)
        except SystemExit as e:
            assert "not ours" in str(e)
        else:
            raise AssertionError("overwrote a hook that is not ours")
    print("selftest[commit-lang] OK -- an English message commits; a Cyrillic subject, a Cyrillic body "
          "line and a '#19:' subject are each refused by git with the line named, and none lands; git's "
          "comments and the diff under the scissors are ignored; a foreign hook is never overwritten")
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")      # a cp1252 console prints '?', it does not raise
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("msgfile", nargs="?", help="the message file git hands the commit-msg hook")
    ap.add_argument("--install-hook", nargs="?", const=REPO, metavar="REPO",
                    help="write the commit-msg hook into REPO (default: this repository)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.install_hook:
        print(f"installed {install_hook(os.path.abspath(args.install_hook))}")
        return 0
    if not args.msgfile:
        ap.error("MSGFILE is required -- git passes it to the commit-msg hook")
    with open(args.msgfile, encoding="utf-8", errors="replace") as fh:
        found = findings(fh.read())
    if found:
        print(render(found))
        return 1
    print("commit-lang: English -- the message carries no Cyrillic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
