#!/usr/bin/env python3
"""No key leaves a repository: the file that can carry one is ignored, and the tree carries none.

The user's rule (2026-09-08): *if a file with a key can exist, it MUST be ignored, so it never
reaches GitHub.* Prose said "it's gitignored" for months while nothing wrote a `.gitignore`
(HUB-025), and a `.gitignore` is only the second line anyway -- it stops none of `git add -f`, a
copied folder, or a key pasted into a file that IS tracked. So this is a CHECK, in three forms:

  scripts/secret-scan.py [REPO]        the whole repository: a tracked file named like the key
                                       file, a key-shaped string in any tracked text file, and a
                                       key file on disk that git would happily add (not ignored)
  scripts/secret-scan.py --staged      only what is about to be committed -- the pre-commit hook
  scripts/secret-scan.py --install-hook [REPO]
                                       write that hook into REPO/.git/hooks/pre-commit

Exit 1 on any finding, with the file and the fix; 0 when clean. `--selftest` plants each kind of
leak in a throwaway repository and must name every one, then must pass a clean one. The key
shapes are Google's (`AIza…` 39, `AQ.…` 53), Anthropic's and OpenAI's prefixes -- a finding names
the file and line, never the value. stdlib only. Runs in CI through scripts/run-selftests.sh, so a
key committed to this tree fails the build before a tag can carry it.
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

#: Files that exist to carry a key. Exact basenames: `.critic-env.example` is a template and stays.
KEY_FILE_NAMES = (".critic-env", "critic-env")
#: The shapes a real key has. A value is never printed -- the match tells us where, not what.
KEY_SHAPES = re.compile(
    r"AIza[0-9A-Za-z_-]{35}"            # Google, the older shape (39 chars)
    r"|AQ\.[A-Za-z0-9_-]{50}"           # Google, the shape AI Studio issues since 2026 (53 chars)
    r"|sk-ant-[A-Za-z0-9_-]{24,}"       # Anthropic
    r"|sk-proj-[A-Za-z0-9_-]{24,}"      # OpenAI project keys
)
#: An assignment of a key variable with a non-placeholder value is a leak even in a shape this
#: file does not know: the NAME says what the value is.
KEY_ASSIGN = re.compile(r"\b(GEMINI|ANTHROPIC|OPENAI)_API_KEY\s*=\s*[\"']?(?P<v>[A-Za-z0-9_.-]{20,})")
PLACEHOLDER = re.compile(r"^(AQ\.{2,}|AIza\.{2,}|<.*>|\.{3,}|x+|\*+)$")


def _git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r


def _scan_text(text, where):
    """Findings in one text: `(where, line, what)` -- never the value."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if KEY_SHAPES.search(line):
            out.append((where, n, "a key-shaped string"))
            continue
        m = KEY_ASSIGN.search(line)
        if m and not PLACEHOLDER.match(m.group("v")):
            out.append((where, n, f"{m.group(1)}_API_KEY assigned a real-looking value"))
    return out


def scan_repo(repo):
    """The three leaks a repository can carry. Returns [(path, line or None, what, fix)]."""
    findings = []
    tracked = [p for p in _git(repo, "ls-files", "-z").stdout.split("\0") if p]
    for path in tracked:
        if os.path.basename(path) in KEY_FILE_NAMES:
            findings.append((path, None, "a key file is TRACKED",
                             f"git rm --cached '{path}' && add '{os.path.basename(path)}' to .gitignore; "
                             "then ROTATE the key -- it is in the history already"))
    for path in tracked:
        full = os.path.join(repo, path)
        if not os.path.isfile(full) or os.path.getsize(full) > 2_000_000:
            continue
        try:
            with open(full, encoding="utf-8", errors="strict") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue                                   # binary, or gone: not a text leak
        for where, n, what in _scan_text(text, path):
            findings.append((where, n, f"{what} in a tracked file",
                             "remove it, put the key in ~/.config/autosound/critic-env, and ROTATE it"))
    # Key files on disk that git would add: present, untracked, and NOT ignored.
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            if name not in KEY_FILE_NAMES:
                continue
            rel = os.path.relpath(os.path.join(root, name), repo)
            if rel in tracked:
                continue                               # already reported above
            ignored = _git(repo, "check-ignore", "-q", rel, check=False).returncode == 0
            if not ignored:
                findings.append((rel, None, "a key file on disk that git would ADD (not ignored)",
                                 f"add '{name}' to {os.path.join(repo, '.gitignore')} -- or move the "
                                 "key to ~/.config/autosound/critic-env, where no repository reaches"))
    return findings


def scan_staged(repo):
    """What is about to be committed: added key files, and key-shaped strings in the staged diff."""
    findings = []
    names = _git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").stdout.split("\0")
    for path in [p for p in names if p]:
        if os.path.basename(path) in KEY_FILE_NAMES:
            findings.append((path, None, "a key file is STAGED",
                             f"git rm --cached '{path}' and add '{os.path.basename(path)}' to .gitignore"))
    diff = _git(repo, "diff", "--cached", "--unified=0", "--no-color").stdout
    current = "?"
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[4:].removeprefix("b/")
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for _, _, what in _scan_text(line[1:], current):
            findings.append((current, None, f"{what} in the staged diff",
                             "unstage it; the key belongs in ~/.config/autosound/critic-env"))
    return findings


def render(findings):
    lines = []
    for path, n, what, fix in findings:
        at = f"{path}:{n}" if n else path
        lines.append(f"  ✗ {at}: {what}\n      fix: {fix}")
    return "\n".join(lines)


HOOK = """#!/usr/bin/env bash
# pre-commit: no key leaves this repository. Written by scripts/secret-scan.py --install-hook.
# A key-shaped string or a key file in the staged change refuses the commit and says where.
command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "{scan}" --staged "$(git rev-parse --show-toplevel)"
"""


def install_hook(repo):
    """The pre-commit hook into `repo`, refusing to overwrite a hook that is not ours."""
    top = _git(repo, "rev-parse", "--show-toplevel").stdout.strip()
    hooks = _git(repo, "rev-parse", "--git-path", "hooks").stdout.strip()
    if not os.path.isabs(hooks):
        hooks = os.path.join(top, hooks)
    os.makedirs(hooks, exist_ok=True)
    path = os.path.join(hooks, "pre-commit")
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            if "secret-scan.py" not in fh.read():
                raise SystemExit(f"{path} exists and is not ours -- chain it by hand: "
                                 f"python3 {os.path.abspath(__file__)} --staged")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HOOK.format(scan=os.path.abspath(__file__)))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _selftest():
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    fake_google = "AQ." + "x" * 50
    fake_old = "AIza" + "y" * 35
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init", "-q", "-b", "main", tmp], check=True, env=env)
        # 1. A clean repository: a template with placeholders and prose is not a leak.
        with open(os.path.join(tmp, ".critic-env.example"), "w", encoding="utf-8") as fh:
            fh.write("# GEMINI_API_KEY=AQ....\nGEMINI_CRITIC_MODEL=gemini-pro-latest\n")
        with open(os.path.join(tmp, "notes.md"), "w", encoding="utf-8") as fh:
            fh.write("the key shape is AQ. + 53 chars; the old one AIza + 39\n")
        subprocess.run(["git", "-C", tmp, "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", tmp, "commit", "-q", "-m", "clean"], check=True, env=env)
        assert scan_repo(tmp) == [], scan_repo(tmp)
        # 2. Each leak, named: a tracked key file; a key-shaped string in a tracked file; a real
        #    assignment under the variable's name; an unignored key file on disk.
        with open(os.path.join(tmp, ".critic-env"), "w", encoding="utf-8") as fh:
            fh.write(f"GEMINI_API_KEY={fake_google}\n")
        with open(os.path.join(tmp, "lib.py"), "w", encoding="utf-8") as fh:
            fh.write(f'KEY = "{fake_old}"\n')
        # Built at run time, in pieces: written literally, this line would be the scanner's own
        # first finding -- the pre-commit hook refused the commit that introduced it (2026-09-08).
        with open(os.path.join(tmp, "conf.txt"), "w", encoding="utf-8") as fh:
            fh.write("ANTHROPIC" + "_API_KEY=" + "abcdefghijklmnopqrstuvwxyz0123456789" + "\n")
        subprocess.run(["git", "-C", tmp, "add", "-A"], check=True, env=env)
        staged = scan_staged(tmp)
        kinds = {(p, w.split(" in ")[0]) for p, _, w, _ in staged}
        assert (".critic-env", "a key file is STAGED") in kinds, staged
        assert ("lib.py", "a key-shaped string") in kinds, staged
        assert ("conf.txt", "ANTHROPIC_API_KEY assigned a real-looking value") in kinds, staged
        assert not any(fake_google in str(f) or fake_old in str(f) for f in staged), "a value was printed"
        subprocess.run(["git", "-C", tmp, "commit", "-q", "-m", "leaks"], check=True, env=env)
        found = scan_repo(tmp)
        whats = {(p, w) for p, _, w, _ in found}
        assert (".critic-env", "a key file is TRACKED") in whats, found
        assert any(p == "lib.py" and "key-shaped" in w for p, w in whats), found
        assert any(p == "conf.txt" and "ANTHROPIC" in w for p, w in whats), found
        assert not any(fake_google in str(f) or fake_old in str(f) for f in found), "a value was printed"
        # 3. The key file untracked and NOT ignored is a finding; ignored, it is not.
        subprocess.run(["git", "-C", tmp, "rm", "-q", "--cached", ".critic-env", "lib.py", "conf.txt"], check=True, env=env)
        subprocess.run(["git", "-C", tmp, "commit", "-q", "-m", "untracked again"], check=True, env=env)
        os.remove(os.path.join(tmp, "lib.py")); os.remove(os.path.join(tmp, "conf.txt"))
        found = scan_repo(tmp)
        assert [w for _, _, w, _ in found] == ["a key file on disk that git would ADD (not ignored)"], found
        with open(os.path.join(tmp, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write(".critic-env\n")
        assert scan_repo(tmp) == [], scan_repo(tmp)
        # 4. The hook installs, is ours, and refuses a staged key with exit 1 -- through git itself.
        hook = install_hook(tmp)
        assert os.access(hook, os.X_OK) and "secret-scan.py" in open(hook, encoding="utf-8").read()
        with open(os.path.join(tmp, "oops.py"), "w", encoding="utf-8") as fh:
            fh.write(f'k = "{fake_google}"\n')
        subprocess.run(["git", "-C", tmp, "add", "oops.py"], check=True, env=env)
        r = subprocess.run(["git", "-C", tmp, "commit", "-q", "-m", "leak"], capture_output=True, text=True, env=env)
        assert r.returncode != 0 and "oops.py" in (r.stdout + r.stderr) and fake_google not in (r.stdout + r.stderr), r
        # ...and an existing foreign hook is not overwritten.
        with open(hook, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        try:
            install_hook(tmp)
        except SystemExit as e:
            assert "not ours" in str(e)
        else:
            raise AssertionError("overwrote a hook that is not ours")
    print("selftest[secret-scan] OK -- a template and prose pass; a tracked key file, a key-shaped string, "
          "a named key assignment and an unignored key file are each named without printing a value; "
          "an ignored key file passes; the pre-commit hook refuses a staged key through git and never "
          "overwrites a foreign hook")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("repo", nargs="?", default=REPO, help="repository to scan (default: this one)")
    ap.add_argument("--staged", action="store_true", help="only the staged change (the pre-commit hook)")
    ap.add_argument("--install-hook", action="store_true", help="write the pre-commit hook into REPO")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    repo = os.path.abspath(args.repo)
    if args.install_hook:
        print(f"installed {install_hook(repo)}")
        return 0
    findings = scan_staged(repo) if args.staged else scan_repo(repo)
    if findings:
        print(f"secret-scan: {len(findings)} finding(s) in {repo}{' (staged)' if args.staged else ''}:")
        print(render(findings))
        return 1
    print(f"secret-scan: clean -- {'the staged change' if args.staged else repo} carries no key and no key file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
