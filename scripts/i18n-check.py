#!/usr/bin/env python3
"""`README` and `FAQ` live in four languages — a divergence must not appear silently (checked).

On 2026-09-06 all four `README*.md` were of one date and all four `FAQ*.md` of another: the
translations were in step, and a guard comparing them would have been green. That is exactly
when to write it. What holds them in step today is one author's attention, and the day someone
edits `README.md` and forgets the other three, nothing says so.

Two things can be compared **without knowing the languages**, and both are the ones that matter:

1. **The heading skeleton.** Heading TEXT is translated, so it cannot be compared — but the
   sequence of heading LEVELS can. A section added to one language only changes that sequence,
   which is precisely the failure this guard exists for.
2. **The commands.** A fenced code block is not translated prose: the install command a Polish
   reader runs must be the command an English reader runs. Only `<placeholders>` inside it are
   translated, so those are normalised away before comparing.

**The limit, said out loud so a green run is not read as more than it is:** this guard catches
DIVERGENCE BETWEEN LANGUAGES. It cannot catch all four drifting behind the CODE together — on
2026-09-06 `FAQ*.md` was ten tags old in every language, and no comparison of the four with each
other will ever notice that. That is a content question for a person.

**A translation is allowed to lag** — English is the source and it is mandatory
(`CONTRIBUTING.md`, Language policy). A translation deliberately behind says so in its own first
lines with the words `Translation lags the English original:`; then its divergences are printed
as notes and do not fail the run. Silence is what fails.

Scope: the repository root's documents (`README`, `FAQ`, …). The skill's machine-read references
(`listening-cheat-sheet*`, `test-tracks*`) are deliberately NOT here: they share ids, only their
free text differs, and `rew_tool/listening.py` falls back to English marked `translated: False`
— a coverage report, not an equality check, is what those want (skill issue #24).

Run: `scripts/i18n-check.py` (from anywhere), `--selftest` for the checker's own mechanics.
stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LAG_MARK = "Translation lags the English original:"
LAG_HEAD_LINES = 12
FENCE = re.compile(r"^```([^\n]*)\n(.*?)^```", re.S | re.M)
HEADING = re.compile(r"^(#{1,6}) (.+)$", re.M)
PLACEHOLDER = re.compile(r"<[^<>\n]{1,60}>")


def headings(src: str) -> list[tuple[int, str]]:
    return [(len(m.group(1)), m.group(2).strip()) for m in HEADING.finditer(src)]


def fences(src: str) -> list[tuple[str, str]]:
    """(info string, body) per fenced block, with `<placeholders>` normalised away."""
    out = []
    for info, body in FENCE.findall(src):
        out.append((info.strip(), PLACEHOLDER.sub("<>", body).strip()))
    return out


def groups(root: str) -> dict[str, list[str]]:
    """{base: [translated file, ...]} for every root document that has translations."""
    found: dict[str, list[str]] = {}
    for name in sorted(os.listdir(root)):
        m = re.match(r"^(?P<base>[A-Za-z0-9_-]+)\.(?P<lang>[a-z]{2})\.md$", name)
        if not m:
            continue
        base = m.group("base") + ".md"
        if os.path.isfile(os.path.join(root, base)):
            found.setdefault(base, []).append(name)
    return found


def check_group(root: str, base: str, translations: list[str]) -> tuple[list[str], list[str]]:
    """(failures, notes) for one document and its translations."""
    fails, notes = [], []
    en = open(os.path.join(root, base), encoding="utf-8").read()
    en_h, en_f = headings(en), fences(en)
    for name in translations:
        src = open(os.path.join(root, name), encoding="utf-8").read()
        head = "\n".join(src.splitlines()[:LAG_HEAD_LINES])
        sink = notes if LAG_MARK in head else fails
        h, f = headings(src), fences(src)

        if [lv for lv, _ in h] != [lv for lv, _ in en_h]:
            if len(h) != len(en_h):
                sink.append(f"{name}: {len(h)} headings vs {len(en_h)} in {base} — a section was "
                            f"added or dropped in one language only")
            for i, (a, b) in enumerate(zip(en_h, h)):
                if a[0] != b[0]:
                    sink.append(f"{name}: heading #{i + 1} is level {b[0]} ('{b[1][:40]}') where "
                                f"{base} has level {a[0]} ('{a[1][:40]}') — the outlines differ")
                    break

        if len(f) != len(en_f):
            sink.append(f"{name}: {len(f)} code blocks vs {len(en_f)} in {base} — a command "
                        f"exists for one audience and not another")
        for i, (a, b) in enumerate(zip(en_f, f)):
            if a != b:
                sink.append(f"{name}: code block #{i + 1} is not the same command as in {base} "
                            f"(only <placeholders> may differ): {b[1][:70]!r}")
                break
    return fails, notes


def run(root: str) -> int:
    docs = groups(root)
    if not docs:
        print(f"i18n: no translated documents found in {root} — nothing to compare",
              file=sys.stderr)
        return 1
    fails, notes, langs = [], [], 0
    for base, translations in sorted(docs.items()):
        langs += len(translations)
        f, n = check_group(root, base, translations)
        fails += f
        notes += n
    for n in notes:
        print(f"  note (declared lag): {n}")
    for f in fails:
        print(f)
    if fails:
        print(f"\n{len(fails)} divergence(s) between languages — translate the change, or say the "
              f"lag out loud with '{LAG_MARK}' in the file's first {LAG_HEAD_LINES} lines",
              file=sys.stderr)
        return 1
    print(f"i18n OK — {len(docs)} document(s), {langs} translation(s): same heading skeleton and "
          f"the same commands. Says nothing about all languages lagging the CODE together.")
    return 0


def _selftest() -> int:
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="i18n_check_")
    try:
        def tree(en: str, uk: str):
            root = tempfile.mkdtemp(dir=tmp)
            open(os.path.join(root, "DOC.md"), "w", encoding="utf-8").write(en)
            open(os.path.join(root, "DOC.uk.md"), "w", encoding="utf-8").write(uk)
            return root

        en = ("# Doc\n\n## Install\n\n```sh\npython3 tool.py <path>\n```\n\n### Notes\n\ntext\n")
        uk = ("# Док\n\n## Встановлення\n\n```sh\npython3 tool.py <шлях>\n```\n\n"
              "### Примітки\n\nтекст\n")
        ok = tree(en, uk)
        assert check_group(ok, "DOC.md", ["DOC.uk.md"]) == ([], []), \
            check_group(ok, "DOC.md", ["DOC.uk.md"])
        assert run(ok) == 0

        extra = tree(en + "\n## Extra section\n\nnew\n", uk)
        f, _ = check_group(extra, "DOC.md", ["DOC.uk.md"])
        assert any("headings vs" in c for c in f), f
        assert run(extra) == 1

        other_cmd = tree(en, uk.replace("python3 tool.py <шлях>", "python2 tool.py <шлях>"))
        f, _ = check_group(other_cmd, "DOC.md", ["DOC.uk.md"])
        assert any("not the same command" in c for c in f), f

        dropped_cmd = tree(en, uk.replace("```sh\npython3 tool.py <шлях>\n```\n", ""))
        f, _ = check_group(dropped_cmd, "DOC.md", ["DOC.uk.md"])
        assert any("code blocks vs" in c for c in f), f

        # a lag that says so is a note, and the run stays green
        declared = tree(en + "\n## Extra section\n\nnew\n",
                        uk.replace("# Док\n", f"# Док\n\n> ⏳ **{LAG_MARK}** the Extra section "
                                             f"is not translated yet.\n"))
        f, n = check_group(declared, "DOC.md", ["DOC.uk.md"])
        assert f == [] and n, (f, n)
        assert run(declared) == 0

        # and the repository itself, which is the point of the whole file
        assert run(ROOT) == 0, "the tree must be clean, or the selftest measures a fake"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK — a section added in one language, a changed command and a dropped command "
          "are each named; a translated <placeholder> is not, and a lag that says so is a note, "
          "not a failure")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="check the checker's own rules")
    parser.add_argument("--root", default=ROOT, help="the directory whose documents to compare")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    return run(args.root)


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "skills", "autosound-tuning", "rew_tool"))
    import console
    console.install()
    sys.exit(main())
