#!/usr/bin/env python3
"""Nothing in `rew_tool` may depend on the console's code page — issue #21, checked.

The bug was one `⚠` printed one line before `self._write(state)`: on a cp1252 console the print
raised, and the post-sweep gate's finished verdicts were lost. The fix is `rew_tool/console.py`,
and a fix that lives only in the copy of the tree it was written in is the fix that comes back.
Three things have to stay true, and each of them is a thing a future edit can quietly undo:

1. **Every entry point installs the fold.** A module with a `__main__` block prints; a module
   that prints without `console.install()` can raise where it meant to inform.
2. **Every text `open()` names its encoding.** Windows' default is the locale's ANSI page, so an
   unqualified `open()` reads UTF-8 project files as cp1252. `process.py:1147` did exactly that
   inside an `except (OSError, ValueError)`, and `UnicodeDecodeError` IS a `ValueError`: the
   profile was readable and the run behaved as if there were none. Silence, not a crash.
3. **Every subprocess that reads text names UTF-8.** `text=True` decodes the child through
   the parent's locale, so two of our own processes on a Windows machine talk cp1252 on one end
   and UTF-8 on the other — and the mismatch arrives as mangled evidence rather than an error.
4. **Every printable non-ASCII character has an ASCII sense.** `console.GLYPHS` decides what
   `→` becomes; a character with no entry falls through to `?`, and a report of question marks
   is the same lost information the crash was.

Run: `scripts/encoding-check.py` (from anywhere), `--selftest` for the checker's own mechanics.
stdlib only.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "skills", "autosound-tuning", "rew_tool")

TEXT_OPENERS = {"open"}


def _load_console(tool_dir):
    path = os.path.join(tool_dir, "console.py")
    spec = importlib.util.spec_from_file_location("_encoding_check_console", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path} — the fold table is the checker's input")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mode_is_binary(call: ast.Call) -> bool:
    for node in list(call.args[1:2]) + [kw.value for kw in call.keywords if kw.arg == "mode"]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "b" in node.value:
            return True
    return False


def check_file(path: str, console) -> list[str]:
    """Every complaint this file earns, as `line: what`. Empty list is a pass."""
    src = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, os.path.dirname(TOOL))
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as exc:
        return [f"{exc.lineno}: does not parse — {exc.msg}"]

    bad = []
    is_console = os.path.basename(path) == "console.py"

    # -- 1. entry point without the fold installed
    has_main = any(
        isinstance(node, ast.If) and ast.dump(node.test).find("__main__") >= 0
        for node in ast.walk(tree)
    )
    installs = "install()" in src if is_console else "console.install()" in src
    if has_main and not installs:
        bad.append("0: has a __main__ block but never calls console.install() — a print in this "
                   "module can still raise on a non-UTF-8 console")

    for node in ast.walk(tree):
        # -- 2. text open() with no encoding
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in TEXT_OPENERS:
            named = {kw.arg for kw in node.keywords}
            if "encoding" not in named and not _mode_is_binary(node):
                bad.append(f"{node.lineno}: open() with no encoding= — reads/writes in the "
                           f"machine's ANSI code page, not UTF-8")

        # -- 4. a subprocess pipe that decodes in the machine's page
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in ("run", "check_output", "Popen", "call") \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
            named = {kw.arg: kw.value for kw in node.keywords}
            textual = any(
                isinstance(named.get(key), ast.Constant) and named[key].value is True
                for key in ("text", "universal_newlines", "capture_output")
            )
            if textual and "encoding" not in named:
                bad.append(f"{node.lineno}: subprocess reading text with no encoding= — decodes "
                           f"the child in the machine's page, not UTF-8")

        # -- 3. a character in a printable string with no ASCII sense
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and not is_console:
            for ch in node.value:
                if ch.isascii() or ch in ("\n", "\t"):
                    continue
                if console.fold_char(ch) == "?":
                    bad.append(f"{node.lineno}: U+{ord(ch):04X} {ch!r} has no entry in "
                               f"console.GLYPHS — it prints as '?' wherever the page lacks it")
    return [f"{rel}:{line}" for line in bad]


def run(tool_dir: str) -> int:
    console = _load_console(tool_dir)
    files = sorted(
        os.path.join(root, name)
        for root, _dirs, names in os.walk(tool_dir)
        for name in names if name.endswith(".py")
    )
    problems = []
    for path in files:
        problems.extend(check_file(path, console))
    if problems:
        print(f"encoding-check: {len(problems)} problem(s) in {len(files)} files")
        for line in problems:
            print(f"  {line}")
        return 1
    print(f"encoding-check OK — {len(files)} modules: every entry point folds, every text open() "
          f"and subprocess pipe names UTF-8, every printed glyph has an ASCII sense")
    return 0


def _selftest() -> int:
    """Break each rule on purpose and watch the checker name it.

    A check nobody has made fail is not a check yet (CLAUDE.md). These three fakes are the three
    ways issue #21 can come back.
    """
    import shutil
    import tempfile

    console = _load_console(TOOL)
    tmp = tempfile.mkdtemp(prefix="encoding_check_")
    try:
        shutil.copy(os.path.join(TOOL, "console.py"), tmp)

        clean = os.path.join(tmp, "clean.py")
        open(clean, "w", encoding="utf-8").write(
            'import console\n'
            'def main():\n'
            '    with open("x", encoding="utf-8") as fh:\n'
            '        print("→ 45° ─ ok", fh)\n'
            'if __name__ == "__main__":\n'
            '    console.install()\n'
        )
        assert check_file(clean, console) == [], check_file(clean, console)

        no_install = os.path.join(tmp, "no_install.py")
        open(no_install, "w", encoding="utf-8").write(
            'def main():\n    print("hi")\nif __name__ == "__main__":\n    main()\n'
        )
        assert any("console.install()" in c for c in check_file(no_install, console))

        bare_open = os.path.join(tmp, "bare_open.py")
        open(bare_open, "w", encoding="utf-8").write('d = open("p.json").read()\n')
        assert any("no encoding=" in c for c in check_file(bare_open, console))
        binary_ok = os.path.join(tmp, "binary.py")
        open(binary_ok, "w", encoding="utf-8").write('d = open("p.bin", "rb").read()\n')
        assert check_file(binary_ok, console) == [], "a binary open has no encoding to name"

        piped = os.path.join(tmp, "piped.py")
        open(piped, "w", encoding="utf-8").write(
            'import subprocess\nsubprocess.run(["git"], capture_output=True, text=True)\n'
        )
        assert any("no encoding=" in c for c in check_file(piped, console)), check_file(piped, console)
        piped_bytes = os.path.join(tmp, "piped_bytes.py")
        open(piped_bytes, "w", encoding="utf-8").write(
            'import subprocess\nsubprocess.run(["git"], stdout=subprocess.PIPE)\n'
        )
        assert check_file(piped_bytes, console) == [], "bytes out of a pipe decode nothing"

        new_glyph = os.path.join(tmp, "glyph.py")
        open(new_glyph, "w", encoding="utf-8").write('print("done ☃ now")\n')
        found = check_file(new_glyph, console)
        assert any("U+2603" in c for c in found), found

        # and the tree itself, which is the point of the whole file
        assert run(TOOL) == 0, "the tree must be clean, or the selftest is measuring a fake"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK — a missing install(), a bare open(), an undeclared subprocess pipe "
          "and an unmapped glyph are each named; a binary open, a bytes pipe and a clean module "
          "are not")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="check the checker's own rules")
    parser.add_argument("--tool", default=TOOL, help="the rew_tool directory to scan")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    return run(args.tool)


if __name__ == "__main__":
    sys.path.insert(0, TOOL)
    import console
    console.install()
    sys.exit(main())
