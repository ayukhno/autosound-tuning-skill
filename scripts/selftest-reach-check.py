#!/usr/bin/env python3
"""Every `_check_*` a module defines is called by it (skill #148) -- checked.

A module's selftest runs its checks through one loop in `_selftest()` that collects every failure (W-9's rule). A check
written and never put in the loop passes for ever, and says nothing: W-8 had two in `state.py` (`001b639`), defined,
green, and run by nothing.

Read by AST, every .py under skills/autosound-tuning/ and the repo's scripts/: a `def _check_*` that nothing else in its
module names is an orphan -- at the module's top level or inside a function, whatever its parameters. A name is a read
of it: a call, the name in a loop's tuple, an attribute (`mod._check_x`, `self._check_x`). A read from inside its own
body (recursion) is not one, and neither is the name in a string, a comment or a docstring, nor a name bound over it.
The production helpers with that prefix (`rew_api._check_address`, `resonalyze_vc`'s ten, `migrate._check_versions`)
are called by their own modules, so they pass. A file that cannot be read as UTF-8, or does not parse, is named too:
what is not read is not passed.

What it does not see: a check that is named and still never runs (a tuple nobody loops over, a branch never taken), and
a test function under another name. A `_check_*` only another module calls is named: give it a read in its own module,
or a name without the prefix.

    scripts/selftest-reach-check.py             # the tree: each orphan and exit 1, or the OK line
    scripts/selftest-reach-check.py --selftest  # an orphan in a throwaway tree, then the same function in the loop

stdlib only.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The folders read, from the repo's root; files are named from there.
SCAN = ("skills/autosound-tuning", "scripts")
PREFIX = "_check_"


def _py_files(root):
    """Every .py under SCAN, as (name from the root with `/`, path)."""
    out = []
    for top in SCAN:
        for folder, dirs, files in os.walk(os.path.join(root, *top.split("/"))):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
            for name in sorted(files):
                if name.endswith(".py"):
                    path = os.path.join(folder, name)
                    out.append((os.path.relpath(path, root).replace(os.sep, "/"), path))
    return out


class _Reads(ast.NodeVisitor):
    """The `_check_*` defs of one module, (name, line), and every name the module reads -- a read inside a function's
    own body of that function's name left out."""

    def __init__(self):
        self.defs, self.reads, self._inside = [], set(), []

    def visit_FunctionDef(self, node):
        if node.name.startswith(PREFIX):
            self.defs.append((node.name, node.lineno))
        for part in node.decorator_list + [node.args] + ([node.returns] if node.returns else []):
            self.visit(part)                     # read where the def stands, not inside its body
        self._inside.append(node.name)
        for stmt in node.body:
            self.visit(stmt)
        self._inside.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _read(self, name, ctx):
        if isinstance(ctx, ast.Load) and name not in self._inside:
            self.reads.add(name)

    def visit_Name(self, node):
        self._read(node.id, node.ctx)

    def visit_Attribute(self, node):
        self._read(node.attr, node.ctx)
        self.generic_visit(node)


def check(root=ROOT):
    """Every complaint, one line each; empty when the tree holds. Also returns how many `_check_*` were read, and in
    how many files: `(problems, checks, files)`."""
    problems, checks, files = [], 0, _py_files(root)
    for rel, path in files:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(f"{rel}: cannot be read ({exc.__class__.__name__}: {exc}) -- its _check_* are not seen; "
                            f"save it as UTF-8, or make it readable")
            continue
        try:
            tree = ast.parse(text, filename=path)
        except SyntaxError as exc:
            problems.append(f"{rel}:{exc.lineno}: does not parse -- {exc.msg}; its _check_* are not seen")
            continue
        reads = _Reads()
        reads.visit(tree)
        checks += len(reads.defs)
        for name, line in reads.defs:
            if name not in reads.reads:
                problems.append(f"{rel}:{line}: {name}() is defined and nothing in its module calls it -- a check "
                                f"that never runs passes for ever: put it in its _selftest()'s loop, or delete it")
    # A floor (group fix 1, item 17): a run that read no file, or no check, looked at nothing, and passed.
    if not files:
        problems.append(f"no .py file read under {' or '.join(s + '/' for s in SCAN)} in {root} -- a check that "
                        f"reads nothing passes for ever: run it in the repository")
    elif not checks:
        problems.append(f"no _check_* read in {len(files)} file(s) under {' or '.join(s + '/' for s in SCAN)} -- the "
                        f"selftests' checks are not where this looks: nothing it could pass was read")
    return problems, checks, len(files)


def _check_nothing_read_is_no_pass():
    """A tree where it reads no file, or no `_check_*`, is a complaint, not the OK line (group fix 1, item 17): run
    from somewhere else, or over a tree whose checks were renamed away, it said "each of the 0 _check_* functions in 0
    files ... is called by its module" -- a pass for a check that looked at nothing."""
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="selftest_reach_floor_")
    try:
        problems, checks, files = check(root)
        assert (checks, files) == (0, 0) and len(problems) == 1 and problems[0].startswith("no .py file read under "), \
            problems
        path = os.path.join(root, *SCAN[1].split("/"), "plain.py")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            f.write("def helper():\n    return 1\n")
        problems, checks, files = check(root)
        assert (checks, files) == (0, 1) and len(problems) == 1 and problems[0].startswith("no _check_* read in 1 "), \
            problems
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _selftest():
    failures = []
    for check_ in (_check_nothing_read_is_no_pass,):
        try:
            check_()
        except AssertionError as exc:
            failures.append(f"{check_.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="selftest_reach_")
    tool = f"{SCAN[0]}/rew_tool"
    try:
        def put(rel, text, encoding="utf-8"):
            path = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding=encoding) as f:
                f.write(text)

        def module(loop):
            """A module whose `_selftest()` loops over `loop`, and the cases that hold whatever the loop holds."""
            return ("def _check_a():\n    assert True\n\n\n"
                    "def _check_b():\n    assert True\n\n\n"
                    "def _check_address():\n    return 1\n\n\n"                 # production: called below
                    "def fetch():\n    return _check_address()\n\n\n"
                    "def _check_edge(lo, hi):\n    return lo < hi\n\n\n"          # takes parameters, read below
                    "def gate(x):\n    return _check_edge(0, x)\n\n\n"
                    "class Probe:\n    def _check_self(self):\n        return 1\n\n"
                    "    def run(self):\n        return self._check_self()\n\n\n"
                    "def _selftest():\n    failures = []\n"
                    f"    for check in ({loop}):\n"
                    "        try:\n            check()\n        except AssertionError as exc:\n"
                    "            failures.append(str(exc))\n    assert not failures\n")

        # The orphan: `_check_b` is defined and the loop holds `_check_a` alone -- named, by file and line.
        put(f"{tool}/m.py", module("_check_a,"))
        # The others nothing calls: one nested in a selftest (the trigger harness's form), one that takes a fixture,
        # one only its own body reads (recursion), one only a string, a comment and a docstring name, one a name is
        # bound over, and one in the repo's scripts/.
        put(f"{SCAN[0]}/evals/e.py", "def _selftest():\n    def _check_inner():\n        assert True\n\n"
                                     "    def _check_called():\n        assert True\n\n"
                                     "    for check in (_check_called,):\n        check()\n")
        put(f"{SCAN[0]}/scripts/s.py", "def _check_with_fixture(fx):\n    assert fx\n\n\n"
                                       "def _check_self_only(n=3):\n    return n and _check_self_only(n - 1)\n\n\n"
                                       "def _check_said():\n    '''_check_said'''\n\n\n"
                                       "# _check_said\nNOTE = '_check_said'\n\n\n"
                                       "def _check_bound():\n    pass\n\n\n_check_bound = None\n")
        put("scripts/x.py", "def _check_repo():\n    pass\n")
        # Read, and passed: a module `mod._check_c` reads; a file outside the two folders is not read.
        put(f"{tool}/state/n.py", "import sys\n\n\ndef _check_c():\n    pass\n\n\n"
                                  "def _selftest():\n    sys.modules[__name__]._check_c()\n")
        put("docs/outside.py", "def _check_outside():\n    pass\n")
        # What cannot be read is named, not passed: a file in another code page, and one that does not parse.
        put(f"{tool}/cp1251.py", "# Перевірка\ndef _check_hidden():\n    pass\n", encoding="cp1251")
        put(f"{tool}/broken.py", "def _check_x(:\n    pass\n")
        problems, checks, files = check(root)
        want = [f"{SCAN[0]}/evals/e.py:2: _check_inner() is defined and nothing in its module calls it",
                f"{SCAN[0]}/scripts/s.py:1: _check_with_fixture()",
                f"{SCAN[0]}/scripts/s.py:5: _check_self_only()",
                f"{SCAN[0]}/scripts/s.py:9: _check_said()",
                f"{SCAN[0]}/scripts/s.py:17: _check_bound()",
                f"{tool}/broken.py:1: does not parse",
                f"{tool}/cp1251.py: cannot be read (UnicodeDecodeError",
                f"{tool}/m.py:5: _check_b() is defined and nothing in its module calls it -- a check that never runs "
                f"passes for ever: put it in its _selftest()'s loop, or delete it",
                "scripts/x.py:1: _check_repo()"]
        missing = [w for w in want if not any(p.startswith(w) for p in problems)]
        assert not missing, f"not named: {missing}\ngot:\n" + "\n".join(problems)
        assert len(problems) == len(want), "named beyond the cases:\n" + "\n".join(problems)
        assert files == 7, f"read {files} files, want the 7 under the two folders (docs/ is not read)"
        # The same function in the loop: the module passes.
        put(f"{tool}/m.py", module("_check_a, _check_b"))
        problems, _, _ = check(root)
        assert not any("m.py" in p for p in problems), "\n".join(problems)
        assert checks == 13, f"{checks} _check_* read, want 13 (none from the two files it could not read)"
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("selftest-reach-check selftest OK -- named: a _check_ the loop does not hold (by file and line), one nested "
          "in a selftest, one that takes a fixture, one only its own body reads, one only a string, a comment or its "
          "docstring names, one a name is bound over, one in the repo's scripts/, a file not UTF-8 and one that does "
          "not parse; passed: the same function once in the loop, production helpers their module calls (with "
          "parameters too, and a method), a read through an attribute; a file outside the two folders is not read")
    return 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return _selftest()
    if argv[1:]:
        print("usage: selftest-reach-check.py [--selftest]", file=sys.stderr)
        return 2
    problems, checks, files = check()
    for p in problems:
        print(p)
    if problems:
        print(f"selftest-reach-check: {len(problems)} complaint(s)")
        return 1
    print(f"selftest-reach-check OK -- each of the {checks} _check_* functions in {files} files under "
          f"{' and '.join(s + '/' for s in SCAN)} is called by its module")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
