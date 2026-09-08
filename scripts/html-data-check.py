#!/usr/bin/env python3
"""A file's name is DATA — in our HTML tools it must never become markup (HUB-040, checked).

The curve visualizer takes a curve from three places the page does not control:

1. the **name** of the dropped file (`f.name`),
2. a `# NTT: Name - …` line inside the file's **body**,
3. the `#curve=…` **link fragment** — a URL one person can send another.

All three become `ds.label`, and every panel prints that label: the crosshair readout, the
comparison table, the deviation report, the curve card. Until 2026-09-09 they printed it
into `innerHTML`, with `cleanLabel()` in the middle — a function that strips the trailing
`(loaded)` / `(+1.0 dB)` bookkeeping and nothing else. It looked like a sanitiser and was
not one, so a curve named `<img src=x onerror=alert(1)>` executed.

The rule that replaced it, and that this file keeps:

> **Our own markup is the string; anything from outside goes in through `esc()`.**
> A helper whose name does not say "escaped" is not allowed to be the last thing a foreign
> value passes through.

Three checks, each of them a thing a future edit can quietly undo:

1. **No foreign value is concatenated into markup.** A line that builds HTML (writes
   `innerHTML`/`outerHTML`, or carries a tag inside a string literal) may not mention a
   file-derived value unless it is inside `esc(...)` / `labelHtml(...)`.
2. **`cleanLabel()` is used ONLY by `labelHtml()`.** That is what makes the look-alike
   harmless: everything that wants the cleaned name gets it escaped, or not at all.
3. **A file with an `innerHTML` sink defines the escape helper.** A copy of the page that
   lost `esc()` in a merge would otherwise pass checks 1 and 2 by having nothing to find.

The limit, named: this is a lint on the DIRECT form — the concatenation you can see on one
line — not dataflow. A foreign value laundered through a local variable two functions away
is not caught here; check 2 is what makes that path narrow, because the only clean-up
helper the page has hands back escaped text.

Run: `scripts/html-data-check.py` (from anywhere), `--selftest` for the checker's own
mechanics. The end-to-end proof is a browser: drop a file called
`<img src=x onerror=alert(1)>.txt` and look at the card. stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# What "came from outside the page" looks like in this code, and why each one is foreign.
FOREIGN = [
    (re.compile(r"\bcleanLabel\s*\("), "cleanLabel() strips brackets, not markup"),
    (re.compile(r"\brawName\b"), "rawName is the dropped file's name"),
    (re.compile(r"\b_rawName\b"), "_rawName is the dropped file's name"),
    (re.compile(r"\.label\b"), "a dataset label is built from the file's name"),
    # a bare `label` in this page is a CURVE label; `<label`, `</label` and `data-label` are
    # markup of our own, and so is `</label>`; the lookbehind is what keeps those out.
    (re.compile(r"(?<![<\w/-])label\b"), "a curve label is built from the file's name"),
    (re.compile(r"\bparams\.get\s*\("), "a URL parameter comes from whoever sent the link"),
    (re.compile(r"\blocation\.(hash|search)\b"), "the URL comes from whoever sent the link"),
    (re.compile(r"\b\w*[fF]ile\.name\b|\bf\.name\b"), "a File object's name is the user's file name"),
    (re.compile(r"\b(target|reader)\.result\b"), "a FileReader result is the file's bytes"),
    (re.compile(r"\blocalStorage\.getItem\s*\("), "restored state carries the labels it stored"),
]
# The two wrappers that make a foreign value safe to paste into markup. Anything inside
# them is removed before the line is searched, so `esc(f.name)` reads as own markup.
WRAPPERS = ("esc", "labelHtml", "encodeURIComponent")
# A line builds markup if it writes into an HTML sink, or if a string literal in it opens
# or closes a tag. `=>` and `>=` are NOT tags — that is why the tag test needs the quote.
SINKS = re.compile(r"\b(innerHTML|outerHTML|insertAdjacentHTML|document\.write)\b")
TAG_IN_STRING = re.compile(r"""['"]\s*</?[a-zA-Z][^'"]*>|['"]>['"]|>['"]\s*\+""")
# Two kinds of line are not hand-written markup and are excluded from check 1: the vendored
# minified Chart.js bundle and our own one-line data literals (curve points, the i18n
# tables). Both are single lines of thousands of characters; a line a person wrote is not.
# The count of excluded lines is printed, so the exclusion is visible rather than silent.
MACHINE_LINE = 1500
bad_note: list[str] = []


def _strip_wrapped(line: str) -> str:
    """Remove every `esc(...)` / `labelHtml(...)` call, innermost first, parens balanced."""
    out = line
    for _ in range(40):                       # a line with 40 nested escapes is not real
        hit = None
        for name in WRAPPERS:
            for m in re.finditer(r"\b%s\s*\(" % name, out):
                depth, i = 1, m.end()
                while i < len(out) and depth:
                    if out[i] == "(":
                        depth += 1
                    elif out[i] == ")":
                        depth -= 1
                    i += 1
                if depth == 0 and (hit is None or m.start() < hit[0]):
                    hit = (m.start(), i)
        if hit is None:
            return out
        out = out[:hit[0]] + "''" + out[hit[1]:]
    return out


def builds_markup(line: str) -> bool:
    return bool(SINKS.search(line) or TAG_IN_STRING.search(line))


def check_file(path: str) -> list[str]:
    """Every complaint this file earns, as `line: what`. Empty list is a pass."""
    src = open(path, encoding="utf-8").read()
    lines = src.splitlines()
    bad = []

    # -- 1. a foreign value pasted straight into markup
    machine = 0
    for n, line in enumerate(lines, 1):
        if len(line) > MACHINE_LINE:
            machine += 1
            continue
        if not builds_markup(line):
            continue
        naked = _strip_wrapped(line)
        for pattern, why in FOREIGN:
            m = pattern.search(naked)
            if m:
                bad.append(f"{n}: {m.group(0)!r} goes into markup unescaped — {why}; "
                           f"wrap it in esc() or labelHtml()")

    # -- 2. the look-alike cleaner is reachable only through the escaping one
    for n, line in enumerate(lines, 1):
        if len(line) > MACHINE_LINE or re.search(r"^\s*(//|\*)", line):
            continue
        if "function cleanLabel" in line:
            continue
        if re.search(r"\bcleanLabel\s*\(", line) and "function labelHtml" not in line:
            bad.append(f"{n}: cleanLabel() called outside labelHtml() — it removes the "
                       f"trailing '(loaded)' bookkeeping, NOT markup; call labelHtml()")

    # -- 3. a page with an HTML sink must carry the escape helper itself
    if SINKS.search(src) and not re.search(r"\bfunction\s+esc\s*\(", src):
        bad.append("0: writes innerHTML but defines no esc() — foreign text has nowhere "
                   "safe to go through")
    if machine:
        bad_note.append(f"{os.path.basename(path)}: {machine} machine-written line(s) "
                        f"(minified bundle / data literal) excluded from the markup check")
    return bad


def html_files(root: str) -> list[str]:
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__"}]
        found += [os.path.join(base, f) for f in files if f.endswith(".html")]
    return sorted(found)


def run(root: str) -> int:
    bad_note.clear()
    files = html_files(root)
    total = 0
    for path in files:
        bad = check_file(path)
        rel = os.path.relpath(path, root)
        if bad:
            total += len(bad)
            for c in bad:
                print(f"{rel}:{c}")
    if total:
        print(f"\n{total} place(s) where data from outside the page could become markup",
              file=sys.stderr)
        return 1
    sinks = sum(len(SINKS.findall(open(f, encoding='utf-8').read())) for f in files)
    for note in bad_note:
        print(f"  note: {note}")
    print(f"html-data OK — {len(files)} file(s), {sinks} HTML sink(s), every file-derived "
          f"value escaped")
    return 0


def _selftest() -> int:
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="html_data_check_")
    try:
        def write(name, body):
            p = os.path.join(tmp, name)
            open(p, "w", encoding="utf-8").write(body)
            return p

        clean = write("clean.html", """<script>
    function esc(v) { return String(v).replace(/</g, '&lt;'); }
    function cleanLabel(l) { return l; }
    function labelHtml(l) { return esc(cleanLabel(l)); }
    function draw(ds, f) {
        box.innerHTML = '<b>' + labelHtml(ds.label) + '</b>' + '<i>' + esc(f.name) + '</i>';
    }
    ds.label = strip(ds.label);                       // bookkeeping, not markup
</script>""")
        assert check_file(clean) == [], check_file(clean)

        raw = write("raw.html", """<script>
    function esc(v) { return v; }
    box.innerHTML = '<b>' + ds.label + '</b>';
</script>""")
        assert any("goes into markup unescaped" in c for c in check_file(raw)), check_file(raw)

        lookalike = write("lookalike.html", """<script>
    function esc(v) { return v; }
    function cleanLabel(l) { return l; }
    const lbl = cleanLabel(ds.label);
    box.innerHTML = '<b>' + lbl + '</b>';
</script>""")
        assert any("outside labelHtml()" in c for c in check_file(lookalike)), check_file(lookalike)

        no_esc = write("no_esc.html", """<script>
    box.innerHTML = '<b>hello</b>';
</script>""")
        assert any("defines no esc()" in c for c in check_file(no_esc)), check_file(no_esc)

        # things that must NOT be mistaken for markup or for foreign data
        quiet = write("quiet.html", """<script>
    const bigger = (a, b) => a.x >= b.x;
    if (d._rawName === name) return;                  // a comparison, not a sink
    el.textContent = f.name;                          // text is text
    localStorage.getItem(LS);
</script>""")
        assert check_file(quiet) == [], check_file(quiet)

        # and the tree itself, which is the point of the whole file
        assert run(ROOT) == 0, "the tree must be clean, or the selftest measures a fake"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK — a raw label in markup, a cleanLabel() outside labelHtml() and a "
          "page without esc() are each named; an arrow function, a textContent write and a "
          "wrapped value are not")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="check the checker's own rules")
    parser.add_argument("--root", default=ROOT, help="the directory tree to scan")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    return run(args.root)


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "skills", "autosound-tuning", "rew_tool"))
    import console
    console.install()
    sys.exit(main())
