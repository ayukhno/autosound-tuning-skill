#!/usr/bin/env python3
"""Every sentence that left SKILL.md went to a file a session reads, or was dropped by name (#145, S2).

  scripts/move-check.py <base> <head>     the sentences of SKILL.md at <base> that are not in it at <head>, each found
                                          in its new home at <head> or named in a commit message of <base>..<head>
  scripts/move-check.py --selftest        the mechanics, in a throwaway git repository

SKILL.md is cut to fit what a session keeps after a context summary, and a cut can lose a rule nobody meant to lose.
So a sentence removed from it between two commits is accounted for only when, normalised -- whitespace, markdown
emphasis and code marks, a link read as its text, a quote's `>` --, it stands in a markdown file of the skill at
<head> (its new home: a file a session can be sent to read), or a commit message of the range names it after a
`dropped:` line:

    dropped:
    - <the sentence whole, or its first words (three at least) and "..."> -- <why, and where its content went>

`dropped: (none)` says the commit dropped nothing. A sentence found only outside the skill -- in a plan, the
CHANGELOG, a test -- has no home a session reads, and is lost. A sentence reworded in SKILL.md is removed too: the
old wording is named after `dropped:`.

Exit codes: 0 every sentence accounted for · 1 a sentence lost · 2 usage (a revision git does not know) · 70 a bug
(the traceback on stderr). stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILL = "skills/autosound-tuning"
SKILL_MD = f"{SKILL}/SKILL.md"
GIT_TIMEOUT_S = 60


class Usage(Exception):
    """A revision git does not know, or no git -- said in one line, exit 2."""


_QUOTE = re.compile(r"^[ \t]*(?:>[ \t]?)+", re.M)          # a quote's `>` at a line's head, nested too
_LINK = re.compile(r"!?\[([^\]\n]*)\]\([^)\n]*\)")          # a link read as its text: its target moves with the file
_UNDERSCORE = re.compile(r"(?<!\w)_+|_+(?!\w)")             # `_emphasis_`, never the `_` inside `v_NNN`


def normalise(text: str) -> str:
    """`text` as the check compares it: a quote's `>` gone, a link read as its text, emphasis and code marks (`*`,
    an underscore at a word's edge, a backtick) gone, either apostrophe one, and every run of white space one space."""
    text = _LINK.sub(r"\1", _QUOTE.sub("", text))
    text = _UNDERSCORE.sub("", text.replace("*", "").replace("`", "")).replace("’", "'")
    return " ".join(text.split())


#: Where a sentence ends: `.`, `!` or `?`, white space, then a capital, a digit or an opening mark -- not after a short
#: abbreviation (`e.g.`, `i.e.`, `etc.`, `vs.`, `cf.`), whose period ends no sentence.
_END = re.compile(r"(?<!\be\.g)(?<!\bi\.e)(?<!\betc)(?<!\bvs)(?<!\bcf)([.!?])\s+(?=[A-Z0-9\u0410-\u042f\u0404\u0406\u0407\u0490«„\"“(\[])")
#: A line that begins a block of its own: a heading, a list item, a table row, a rule.
_BLOCK_HEAD = re.compile(r"^[ \t]*(?:#{1,6}[ \t]|[*+-][ \t]|\d+[.)][ \t]|\||-{3,}[ \t]*$)")


def _blocks(text: str) -> list:
    """The blocks of a markdown document: paragraphs, each list item, each heading, each table cell, each key of the
    frontmatter -- the units a sentence cannot run across."""
    lines = text.split("\n")
    blocks, cur = [], []

    def close():
        if cur:
            blocks.append("\n".join(cur))
            cur.clear()

    front_end = -1
    if lines and lines[0].strip() == "---":
        front_end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), -1)
    for i, line in enumerate(lines):
        if i == 0 and front_end > 0 or i == front_end:
            close()
            continue
        if 0 < i < front_end:                              # a frontmatter key starts a block; the key of a block
            if line[:1].strip():                           # scalar (`description: >-`) is markup, its lines the words
                close()
                if re.match(r"^[\w-]+:[ \t]*[>|][+-]?\d?[ \t]*$", line):
                    continue
            cur.append(line)
            continue
        if not line.strip():
            close()
        elif line.lstrip().startswith("|"):
            close()
            blocks.extend(cell for cell in line.strip().strip("|").split("|"))
        elif _BLOCK_HEAD.match(line):
            close()
            cur.append(re.sub(r"^[ \t]*(?:#{1,6}|[*+-]|\d+[.)])[ \t]+", "", line))
        else:
            cur.append(line)
    close()
    return blocks


def sentences(text: str) -> list:
    """The sentences of a markdown document, each normalised, in order, each once; a unit with no word in it (a rule,
    a table's `:---`, a list's `0.`) is not a sentence."""
    out = []
    for block in _blocks(text):
        for part in _END.sub(r"\1\n", normalise(block)).split("\n"):
            part = part.strip()
            if re.search(r"\w\w", part) and part not in out:
                out.append(part)
    return out


#: A `dropped:` line, with an item on it or `(none)`; the items under it, each on a list mark (`- `, `* `); a reason
#: after ` -- `.
_DROPPED = re.compile(r"^dropped:[ \t]*(.*)$", re.I)
_ITEM = re.compile(r"^[-*][ \t]+(.*)$")


def dropped_items(messages: list) -> list:
    """The items listed after `dropped:` in `messages`: [(item text, its commit)], the reason after ` -- ` left out.
    The list runs to a blank line or a line that is neither an item nor an item's indented continuation."""
    items = []
    for sha, message in messages:
        lines = message.split("\n")
        for i, line in enumerate(lines):
            m = _DROPPED.match(line.strip())
            if not m:
                continue
            listed = [m.group(1)] if m.group(1).strip() and m.group(1).strip().lower() not in ("(none)", "none") \
                else []
            for nxt in lines[i + 1:]:
                item = _ITEM.match(nxt)
                if item:
                    listed.append(item.group(1))
                elif nxt[:1] in (" ", "\t") and nxt.strip() and listed:
                    listed[-1] += " " + nxt.strip()
                else:
                    break
            items += [(normalise(text.split(" -- ")[0]), sha) for text in listed]
    return items


_ELLIPSIS = ("...", "…")


def covered(sentence: str, item: str) -> bool:
    """Whether the `dropped:` item names `sentence`: the item is the sentence (or a passage that holds it whole), or
    its first three words or more and an ellipsis."""
    if item.endswith(_ELLIPSIS):
        opening = item.rstrip(".…").rstrip()
        return len(opening.split()) >= 3 and sentence.startswith(opening)
    return bool(item) and (sentence == item or sentence in item)


def _git(repo: str, *args, env=None, stdin=None) -> str:
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                           env=env, input=stdin, timeout=GIT_TIMEOUT_S)
    except FileNotFoundError:
        raise Usage("git is not on PATH") from None
    if r.returncode != 0:
        raise Usage(f"git {' '.join(args[:3])}: {r.stderr.strip() or f'exit {r.returncode}'}")
    return r.stdout


def _commit_of(repo: str, rev: str) -> str:
    try:
        return _git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}").strip()
    except Usage:
        raise Usage(f"'{rev}' is no commit git knows in {repo}") from None


def _file_at(repo: str, sha: str, path: str) -> str | None:
    listed = _git(repo, "ls-tree", sha, "--", path).strip()
    return _git(repo, "show", f"{sha}:{path}") if listed else None


def _homes(repo: str, sha: str) -> dict:
    """Every markdown file under the skill at `sha` -> its normalised text: the files a session can be sent to read."""
    rows = [line.split("\t", 1) for line in _git(repo, "ls-tree", "-r", sha, "--", SKILL).splitlines()]
    blobs = [(meta.split()[2], path) for meta, path in rows if meta.split()[1] == "blob" and path.endswith(".md")]
    if not blobs:
        return {}
    raw = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], capture_output=True, timeout=GIT_TIMEOUT_S,
                         input="".join(f"{blob}\n" for blob, _ in blobs).encode()).stdout
    homes, at = {}, 0
    for _, path in blobs:
        header_end = raw.index(b"\n", at)
        size = int(raw[at:header_end].split()[2])
        homes[path] = normalise(raw[header_end + 1:header_end + 1 + size].decode("utf-8", "replace"))
        at = header_end + 1 + size + 1
    return homes


def check(repo: str, base: str, head: str) -> tuple:
    """(ok, lines): each sentence of SKILL.md at `base` that is not in it at `head`, and where it is accounted for."""
    base_sha, head_sha = _commit_of(repo, base), _commit_of(repo, head)
    before = _file_at(repo, base_sha, SKILL_MD)
    if before is None:
        raise Usage(f"{SKILL_MD} is not in {base} -- nothing to compare from")
    after = normalise(_file_at(repo, head_sha, SKILL_MD) or "")
    gone = [s for s in sentences(before) if s not in after]
    homes = _homes(repo, head_sha)                     # SKILL.md among them: what left it is not in it
    log = _git(repo, "log", "--format=%h%x00%B%x01", f"{base_sha}..{head_sha}")
    messages = [tuple(entry.strip("\n").split("\x00", 1)) for entry in log.split("\x01") if "\x00" in entry]
    items = dropped_items(messages)
    lines, lost = [], 0
    for s in gone:
        where = [path for path, text in homes.items() if s in text]
        named = next((sha for item, sha in items if covered(s, item)), None)
        if where:
            lines.append(f"  moved    {where[0]}{f' (+{len(where) - 1})' if len(where) > 1 else ''}: {_short(s)}")
        elif named:
            lines.append(f"  dropped  {named}: {_short(s)}")
        else:
            lost += 1
            lines.append(f"  LOST     {s}")
    head_line = (f"move-check: {base}..{head}, {SKILL_MD} -- {len(gone)} sentence(s) left it; a home is a markdown "
                 f"file under {SKILL}/ at {head}")
    if lost:
        return False, [head_line] + lines + [
            f"move-check: {lost} sentence(s) LOST -- each one goes to a file of the skill a session reads, or is named "
            f"after `dropped:` in a commit message of the range (the sentence, or its first words and \"...\")"]
    return True, [head_line] + lines + [f"move-check OK -- {len(gone)} sentence(s) accounted for"]


def _short(sentence: str, width: int = 100) -> str:
    return sentence if len(sentence) <= width else sentence[:width - 1] + "…"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base", nargs="?", help="the commit SKILL.md is compared from")
    parser.add_argument("head", nargs="?", help="the commit it is compared to, whose files are the homes")
    parser.add_argument("--selftest", action="store_true", help="the mechanics, in a throwaway git repository")
    parser.add_argument("--repo", default=ROOT, help="the repository (default: this script's)")
    args = parser.parse_args(argv)
    if args.selftest:
        try:
            return _selftest()
        except AssertionError as exc:
            print(f"selftest FAILED --\n{exc}", file=sys.stderr)
            return 1
    if not (args.base and args.head):
        parser.print_usage(sys.stderr)
        print("move-check: give two commits, <base> <head>", file=sys.stderr)
        return 2
    try:
        ok, lines = check(args.repo, args.base, args.head)
    except Usage as exc:
        print(f"move-check: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0 if ok else 1


# --------------------------------------------------------------------------------------------------- selftest
_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def _repo(path: str) -> str:
    """A fresh repository at `path`, read with no global or system git configuration."""
    os.makedirs(path)
    _git(path, "init", "-q", "-b", "main", env=_ENV)
    return path


def _commit(repo: str, files: dict, message: str) -> str:
    """Write `files` (path -> text, None removes it) and commit them with `message`; the new commit's sha."""
    for rel, text in files.items():
        path = os.path.join(repo, rel)
        if text is None:
            os.remove(path)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    _git(repo, "add", "-A", env=_ENV)
    _git(repo, "commit", "-q", "-F", "-", env=_ENV, stdin=message)
    return _git(repo, "rev-parse", "HEAD", env=_ENV).strip()


def _run(*argv) -> tuple:
    import contextlib
    import io
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = main(list(argv))
    return rc, out.getvalue()


_A = "The stop has one order, and it is written once."
_B = "Every agreed change is banked through **apply.propose**, never by hand."
_C = "A capture the list should not have is skipped with its reason."
_SKILL = ("---\nname: s\ndescription: >-\n  Tune a car audio DSP\n  from scratch.\n---\n\n# S\n\n## Rules\n\n"
          f"* **{_A}** {_B}\n* {_C}\n")


def _base(tmp: str, name: str = "repo") -> tuple:
    """A repository of its own under `tmp` (`name`), holding SKILL.md and one reference: (repo, the base commit)."""
    repo = _repo(os.path.join(tmp, name))
    sha = _commit(repo, {SKILL_MD: _SKILL, f"{SKILL}/references/core/x.md": "# X\n\ntext\n"}, "base")
    return repo, sha


def _check_normalise():
    """Whitespace, emphasis, code marks, a link's target and a quote's `>` do not change a sentence; a word in
    `v_NNN` keeps its underscore; either apostrophe reads as one."""
    assert normalise("**Bank** every\n  change via `apply.propose`  [here](references/x.md).") == \
        "Bank every change via apply.propose here.", normalise("**Bank** every\n  change via `apply.propose`.")
    assert normalise("> one\n> two _three_ v_NNN it’s") == "one two three v_NNN it's", normalise("> one\n> two")


def _check_sentences():
    """A sentence ends at `.`, `!` or `?` before a capital; `e.g.` ends none; a bullet, a heading, a table cell and
    a frontmatter key begin a new one; a unit with no word is not a sentence."""
    text = ("---\nname: s\ndescription: >-\n  Tune a DSP (e.g. Helix) from\n  scratch. Resume it.\n---\n\n"
            "# Title\n\n* **One rule.** Its reason, e.g. a story.\n* Two rule\n  wrapped.\n\n| a cell | Read when. |\n"
            "| :--- | :--- |\n\n0. Step zero.\n")
    got = sentences(text)
    for want in ("Tune a DSP (e.g. Helix) from scratch.", "Resume it.", "One rule.", "Its reason, e.g. a story.",
                 "Two rule wrapped.", "a cell", "Read when.", "Step zero.", "Title", "name: s"):
        assert want in got, (want, got)
    assert not any(s in ("---", ":---", "0.") for s in got), got


def _check_moved():
    """A sentence moved to a markdown file of the skill -- rewrapped, its bold and a link changed -- is accounted for,
    and the home is named; a sentence kept in SKILL.md is not counted as removed."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        repo, base = _base(tmp)
        head = _commit(repo, {SKILL_MD: _SKILL.replace(f" {_B}", ""),
                              f"{SKILL}/references/core/x.md": "# X\n\nEvery agreed change is banked\nthrough "
                              "[apply.propose](../../x.md), never by hand.\n"}, "move B\n\ndropped: (none)\n")
        rc, out = _run("--repo", repo, base, head)
        assert rc == 0, out
        assert "references/core/x.md" in out and "1 sentence(s) left" in out, out
        assert out.rstrip().splitlines()[-1].startswith("move-check OK"), out


def _check_lost():
    """A sentence removed and found nowhere is named, exit 1 -- and so is one found only outside the skill (a plan),
    or only in a file that is not markdown."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        repo, base = _base(tmp)
        head = _commit(repo, {SKILL_MD: _SKILL.replace(f"* {_C}\n", "")}, "cut C\n\ndropped: (none)\n")
        rc, out = _run("--repo", repo, base, head)
        assert rc == 1 and "LOST" in out and _C in out, out
        head = _commit(repo, {"docs/plan.md": f"# Plan\n\n{_C}\n", f"{SKILL}/rew_tool/x.py": f"# {_C}\n"}, "plan")
        rc, out = _run("--repo", repo, base, head)
        assert rc == 1 and _C in out, out


def _check_dropped_by_name():
    """A sentence named after `dropped:` -- whole, or by three words or more and an ellipsis, a reason after ` -- ` --
    is accounted for; two words and an ellipsis name nothing."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cut = {SKILL_MD: _SKILL.replace(f"* {_C}\n", "")}
        for n, listed in enumerate((f"- {_C} -- said in the sheet's Block 0", "- A capture the list... -- in Block 0",
                                    f"- {_C[:20]}…", f"* {_C}", f"- A passage. {_C} And more. -- all three")):
            repo, base = _base(tmp, f"r{n}")
            head = _commit(repo, cut, f"cut C\n\nWhy.\n\ndropped:\n{listed}\n\nCo-Authored-By: t <t@t>\n")
            rc, out = _run("--repo", repo, base, head)
            assert rc == 0 and "dropped" in out, (listed, out)
        # two words name nothing; another sentence, or a piece of this one, is not this one; a line with no list
        # mark is not an item
        for n, listed in enumerate(("- A capture... -- two words", "- A capture the list should not have.",
                                    "- the list should not have is skipped", _C)):
            repo, base = _base(tmp, f"s{n}")
            head = _commit(repo, cut, f"cut C\n\ndropped:\n{listed}\n")
            rc, out = _run("--repo", repo, base, head)
            assert rc == 1 and _C in out, (listed, out)


def _check_range():
    """A `dropped:` list counts in any commit of <base>..<head>, and not in one before <base>; the reworded wording
    of a sentence is a removal too."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(os.path.join(tmp, "one"))
        _commit(repo, {"pre.txt": "x"}, f"before\n\ndropped:\n- {_C}\n")
        base = _commit(repo, {SKILL_MD: _SKILL}, "base")
        mid = _commit(repo, {SKILL_MD: _SKILL.replace(_C, "A capture the list should not have: skip it.")},
                      f"reword C\n\ndropped:\n- {_C} -- reworded\n")
        head = _commit(repo, {"y.txt": "y"}, "other\n\ndropped: (none)\n")
        rc, out = _run("--repo", repo, base, head)
        assert rc == 0, out
        rc, out = _run("--repo", repo, mid, head)
        assert rc == 0 and "0 sentence(s) left" in out, out
        repo2 = _repo(os.path.join(tmp, "two"))
        _commit(repo2, {"pre.txt": "x"}, f"before\n\ndropped:\n- {_C}\n")
        base2 = _commit(repo2, {SKILL_MD: _SKILL}, "base")
        head2 = _commit(repo2, {SKILL_MD: _SKILL.replace(f"* {_C}\n", "")}, "cut\n\ndropped: (none)\n")
        rc, out = _run("--repo", repo2, base2, head2)
        assert rc == 1 and _C in out, out


def _check_usage():
    """A revision git does not know is a usage error, exit 2, naming it; no revisions at all is usage too."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        repo, base = _base(tmp)
        rc, out = _run("--repo", repo, base, "nosuchrev")
        assert rc == 2 and "nosuchrev" in out, out
        rc, out = _run("--repo", repo)
        assert rc == 2, out


def _selftest() -> int:
    failures = []
    for check in (_check_normalise, _check_sentences, _check_moved, _check_lost, _check_dropped_by_name,
                  _check_range, _check_usage):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    print("selftest OK -- a sentence moved to a markdown file of the skill (rewrapped, its bold, code marks, a link's "
          "target or a quote's mark changed) is found and its home named; one removed and found nowhere, or only in a "
          "plan outside the skill or a file that is not markdown, is LOST and named, exit 1; one named after "
          "`dropped:` -- whole, in a passage, or by three words or more and an ellipsis, in any commit of the range -- "
          "passes, while two words, another sentence, a piece of it, a line with no list mark or a list before the "
          "range name nothing; a reworded sentence is a removal; a sentence ends before a capital but not after "
          "e.g.; a revision git does not know is usage, exit 2")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        sys.exit(70)
