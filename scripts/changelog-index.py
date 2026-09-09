#!/usr/bin/env python3
"""The CHANGELOG needs an ENTRANCE — one table, generated, never typed (autosound-hub HUB-043).

A reader opens this file with one question: *what changes for me if I upgrade?* The answer is in
there — every note carries an **Upgrading** line when there is something to know — but on
2026-09-06 finding it meant reading 3 297 lines / 292 KB across 72 version sections, some of them
90 lines long. The doctrine of what a version number means stays in `CHANGELOG.md` (it is about how
to write a note, and it lives there correctly); what was missing was the way in.

So: a table of every version — number, date, the one-line summary the heading already carries, and
whether that section has an Upgrading note — generated from the headings themselves, between
`<!-- changelog-index:start -->` and `<!-- changelog-index:end -->`. Generated and not written,
because an index maintained by hand is a second source of truth about which versions exist, and it
is wrong the first time someone forgets it. `--check` is the version the test suite runs: it
regenerates and compares, so a new version note without an index row fails.

Versions up to v3.0.20 live in `docs/changelog/archive-v1.0.0-v3.0.20.md`; the table spans BOTH
files, so a version is looked up in one place no matter which file holds it.

The limit, named: the links are GitHub's own heading anchors, computed here by GitHub's documented
rule (lowercase, drop everything that is not a word character, space or hyphen, spaces to hyphens).
`--check` proves every anchor comes from a heading that exists in the file it points at; it cannot
prove GitHub renders that anchor the same way, because that is not knowable offline.

The Upgrading flag reads the note's OPENING LINE, not a fixed string: `**Upgrading:** ...` and
`**Upgrading — ...**` are both a note, quoted with `> ` or not, because that line is human prose and
tying a release's flag to one punctuation mark is tying it to nothing. A line that opens with
`**Upgrading` in any THIRD form is not guessed at — the run REFUSES and names the line. Silence would
print `—` in the table, and `—` is what "nothing to know" looks like: the one warning that audience
gets would be lost exactly where it is needed (autosound-hub TCC-009, on v3.0.47).

Run: `scripts/changelog-index.py` (writes), `--check` (fails on a stale table), `--selftest`.
stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIVE = "CHANGELOG.md"
ARCHIVE = os.path.join("docs", "changelog", "archive-v1.0.0-v3.0.20.md")
START = "<!-- changelog-index:start -->"
END = "<!-- changelog-index:end -->"
# `## [v3.0.46] — 2026-09-06 · one line about what changed`
VERSION_HEAD = re.compile(r"^## \[(?P<ver>[^\]]+)\](?:\s*[—-]\s*(?P<date>\d{4}-\d{2}-\d{2}))?"
                          r"(?:\s*·\s*(?P<summary>.+))?$")
# `> **Upgrading:** ...`, `**Upgrading:** ...`, `> **Upgrading — a sentence.**` — all one note.
UPGRADING_NOTE = re.compile(r"^\s*(?:>\s*)?\*\*Upgrading\s*[:—–-]")
# anything that STARTS a line with the word is meant as the note; mid-sentence mentions are prose.
UPGRADING_OPENS = re.compile(r"^\s*(?:>\s*)?\*\*Upgrading")


def anchor(heading_line: str) -> str:
    """GitHub's heading anchor for a `## ...` line."""
    text = heading_line.lstrip("#").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return text.replace(" ", "-")


def versions(root: str, rel: str) -> list[dict]:
    """Every version section of one file, in file order, with its Upgrading flag."""
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        return []
    lines = open(path, encoding="utf-8").read().splitlines()
    found = []
    for i, line in enumerate(lines):
        m = VERSION_HEAD.match(line)
        if not m:
            continue
        if found:
            found[-1]["body_end"] = i
        found.append({"ver": m.group("ver"), "date": m.group("date") or "",
                      "summary": (m.group("summary") or "").strip(),
                      "anchor": anchor(line), "file": rel, "body_start": i + 1,
                      "body_end": len(lines)})
    for v in found:
        body = lines[v["body_start"]:v["body_end"]]
        v["upgrading"] = any(UPGRADING_NOTE.match(ln) for ln in body)
        v["odd"] = [(v["body_start"] + k + 1, ln.strip()) for k, ln in enumerate(body)
                    if UPGRADING_OPENS.match(ln) and not UPGRADING_NOTE.match(ln)]
    return found


def refuse_odd(root: str) -> int:
    """1, having named every Upgrading heading the flag cannot read; 0 when there are none."""
    bad = [(v, lineno, text) for v in versions(root, LIVE) + versions(root, ARCHIVE)
           for lineno, text in v["odd"]]
    if not bad:
        return 0
    for v, lineno, text in bad:
        print(f"{v['file']}:{lineno}: {v['ver']} opens an Upgrading note in a form the index "
              f"cannot read — {text}", file=sys.stderr)
    print("A note opens with `**Upgrading:**` or `**Upgrading — ...`, at the start of its line, "
          "quoted with `> ` or not. Guessing here would print `—` in the table, and `—` is what "
          "\"nothing to know\" reads as — so the run stops instead.", file=sys.stderr)
    return 1


def render(root: str) -> str:
    rows = versions(root, LIVE) + versions(root, ARCHIVE)
    out = [START,
           "## Index — every version, newest first",
           "",
           "Generated by `scripts/changelog-index.py` (the test suite fails on a stale table — do "
           "not edit by hand).",
           "**Upgrading** marks a section that carries a note about what changes for a consumer; "
           "versions up to v3.0.20 are in "
           "[`docs/changelog/archive-v1.0.0-v3.0.20.md`](docs/changelog/archive-v1.0.0-v3.0.20.md).",
           "",
           "| Version | Date | What changed | Upgrading |",
           "| :--- | :--- | :--- | :---: |"]
    for v in rows:
        href = ("#" + v["anchor"]) if v["file"] == LIVE else \
            (ARCHIVE.replace(os.sep, "/") + "#" + v["anchor"])
        summary = v["summary"].replace("|", "\\|") or "—"
        out.append(f"| [{v['ver']}]({href}) | {v['date'] or '—'} | {summary} | "
                   f"{'yes' if v['upgrading'] else '—'} |")
    out += ["", f"{len(rows)} versions.", END]
    return "\n".join(out) + "\n"


def _splice(src: str, block: str) -> str:
    """Replace whatever stands between the markers (inclusive) with `block`."""
    i, j = src.find(START), src.find(END)
    if i < 0 or j < 0:
        raise SystemExit(f"{LIVE}: the markers {START} / {END} are not both there — the index has "
                         f"nowhere to go")
    tail = src[j + len(END):]
    if tail.startswith("\n"):
        tail = tail[1:]                  # `block` already ends with its own newline
    return src[:i] + block + tail


def write(root: str) -> int:
    if refuse_odd(root):
        return 1
    path = os.path.join(root, LIVE)
    src = open(path, encoding="utf-8").read()
    new = _splice(src, render(root))
    if new == src:
        print("index already current — nothing written")
        return 0
    open(path, "w", encoding="utf-8").write(new)
    print(f"index written into {LIVE}")
    return 0


def check(root: str) -> int:
    if refuse_odd(root):
        return 1
    path = os.path.join(root, LIVE)
    src = open(path, encoding="utf-8").read()
    want = render(root)
    i, j = src.find(START), src.find(END)
    if i < 0 or j < 0:
        print(f"{LIVE}: no index block — run scripts/changelog-index.py", file=sys.stderr)
        return 1
    have = src[i:j + len(END)] + "\n"
    if have != want:
        heads = len(versions(root, LIVE)) + len(versions(root, ARCHIVE))
        rows = len([ln for ln in have.splitlines() if ln.startswith("| [")])
        print(f"{LIVE}: the index is stale — {rows} row(s) for {heads} version heading(s). "
              f"Run scripts/changelog-index.py", file=sys.stderr)
        return 1
    # every anchor must come from a heading that really is in the file it points at
    for v in versions(root, LIVE) + versions(root, ARCHIVE):
        body = open(os.path.join(root, v["file"]), encoding="utf-8").read()
        if f"[{v['ver']}]" not in body:
            print(f"{v['file']}: index row {v['ver']} points at a heading that is not there",
                  file=sys.stderr)
            return 1
    n = len([ln for ln in want.splitlines() if ln.startswith("| [")])
    print(f"changelog index OK — {n} versions in the table, one row per heading across "
          f"{LIVE} + the archive")
    return 0


def _selftest() -> int:
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="changelog_index_")
    try:
        os.makedirs(os.path.join(tmp, os.path.dirname(ARCHIVE)))
        live = os.path.join(tmp, LIVE)
        open(live, "w", encoding="utf-8").write(
            f"# Changelog\n\n{START}\n{END}\n\n"
            "## [v9.9.3] — 2026-09-11 · the dash form\n\n"
            "> **Upgrading — a sentence, and not a colon in sight.**\n\ntext\n\n"
            "## [v9.9.2] — 2026-09-10 · the unquoted form\n\n"
            "**Upgrading:** no `> ` in front of this one.\n\ntext\n\n"
            "## [v9.9.1] — 2026-09-09 · a thing changed\n\n> **Upgrading:** read this.\n\n"
            "> prose that only MENTIONS **Upgrading** mid-sentence is not a note.\n\n"
            "## [v9.9.0] — 2026-09-08 · another thing\n\nno note here\n")
        open(os.path.join(tmp, ARCHIVE), "w", encoding="utf-8").write(
            "# archive\n\n## [v1.0.0] — 2026-06-13\n\nold\n")

        assert check(tmp) == 1, "an empty block must be caught as stale"
        assert write(tmp) == 0
        assert check(tmp) == 0, "a freshly written index must pass"
        src = open(live, encoding="utf-8").read()
        assert "| [v9.9.1](#v991--2026-09-09--a-thing-changed) | 2026-09-09 |" in src, src
        assert src.count("| yes |") == 3, "colon, dash and unquoted are one note; a mention is not"
        assert ARCHIVE.replace(os.sep, "/") + "#v100--2026-06-13" in src, "archive link missing"
        assert "5 versions." in src

        # a new version note without regenerating the index fails
        with open(live, "a", encoding="utf-8") as fh:
            fh.write("\n## [v9.9.4] — 2026-09-12 · newest\n\nbody\n")
        assert check(tmp) == 1, "a version added after the index must fail the check"
        assert write(tmp) == 0 and check(tmp) == 0

        # a THIRD form is refused by name, not silently flagged `—`
        with open(live, "a", encoding="utf-8") as fh:
            fh.write("\n## [v9.9.5] — 2026-09-13 · an unreadable heading\n\n"
                     "> **Upgrading** four things change.\n\nbody\n")
        before = open(live, encoding="utf-8").read()
        assert write(tmp) == 1, "an Upgrading heading in an unknown form must stop the run"
        assert open(live, encoding="utf-8").read() == before, "a refused run must write nothing"
        assert check(tmp) == 1, "and --check must refuse it too, not call the tree clean"

        # put it in a form the flag reads, and the same section flows through
        open(live, "w", encoding="utf-8").write(
            before.replace("> **Upgrading** four", "> **Upgrading — four"))
        assert write(tmp) == 0 and check(tmp) == 0
        assert open(live, encoding="utf-8").read().count("| yes |") == 4

        # and the repository itself, which is the point of the whole file
        assert check(ROOT) == 0, "the tree must be clean, or the selftest measures a fake"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK — an empty index, a stale one and a version added after it are each caught; "
          "the Upgrading flag reads the colon, dash and unquoted forms but not a mid-sentence "
          "mention, a fourth form is refused by name instead of flagged `—`, and an archived "
          "version links into the archive")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the table is stale")
    parser.add_argument("--selftest", action="store_true", help="check the checker's own mechanics")
    parser.add_argument("--root", default=ROOT, help="the repository root")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    return check(args.root) if args.check else write(args.root)


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "skills", "autosound-tuning", "rew_tool"))
    import console
    console.install()
    sys.exit(main())
