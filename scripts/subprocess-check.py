#!/usr/bin/env python3
"""Every child the method starts has an end: a timeout on each production subprocess and download (skill #146; audit
K-5, T-49) -- checked.

A child with no timeout is a run that can wait for ever, and says nothing while it does: a `gh` stuck on a network that
answers nothing, a git on a drive that went away, an engine run that never returns. Before #146, 21 production calls
under the skill had none -- `gh` among them, behind every feedback post and image upload. Each got its timeout where it
is, answered in its caller's own terms; this check keeps a new one from arriving without.

Read by AST, every .py under skills/autosound-tuning/:

  (a) `subprocess.run`, `call`, `check_call`, `check_output` pass a `timeout=` -- `subprocess` under another name and a
      function imported from it alike; a call that hands its arguments over as `**kwargs` is counted as having none;
  (b) a `subprocess.Popen` sits in a function that waits on it with `communicate(timeout=...)`: at least one
      `communicate` there, and every one with a timeout (a keyword, or the second argument);
  (c) a download names its timeout: `urlopen` passes one (a keyword, or the third argument), and `urlretrieve`, which
      takes none, is not called.

Test code is not production, and is not read for (a)-(c): a `_selftest*` function, a `_check_*` function a test
function of the same module names (the loop every `_selftest()` runs its checks through), and anything defined inside
either. ALLOWED names the production (file, function) pairs that start a child with no timeout on purpose, each with its
reason; an entry that matches nothing is a complaint too -- a stale entry would let the next call through unseen.

What it does not see: a child started any other way (`os.system`, `os.spawn*`, `asyncio`), a helper only tests call
that is not named for them (ALLOWED holds the two there are), and a timeout so long it is none.

    scripts/subprocess-check.py             # the tree: each complaint and exit 1, or the OK line
    scripts/subprocess-check.py --selftest  # each rule broken on purpose in a throwaway tree

stdlib only.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The folder read, from the repo's root; files are named from there.
SCAN = "skills/autosound-tuning"

#: (file, function) -> why that function starts a child with no timeout. Rules (a)-(c) pass exactly these.
ALLOWED = {
    ("skills/autosound-tuning/scripts/issue_triage.py", "edit_text_in_editor"):
        "the person's own text editor, open for as long as the person writes: a timeout would close it on them. A "
        "failing editor is caught and said in one line",
    ("skills/autosound-tuning/evals/run_trigger_eval.py", "run_one"):
        "the trigger runs' harness (a maintainer's, by hand): its own deadline loop reads `claude -p` line by line "
        "and kills it at the deadline (`finally: p.kill()`), so no `communicate` is there to carry one",
    ("skills/autosound-tuning/rew_tool/project.py", "_held_elsewhere"):
        "a selftest helper -- another process holding the project's lock: a deadline loop kills the child, and "
        "`wait(60)` bounds its end",
    ("skills/autosound-tuning/rew_tool/state/process.py", "_cli_env"):
        "a selftest helper -- this module's command line as a process of its own, called by its checks only; the "
        "suite's runner bounds each selftest (SELFTEST_TIMEOUT)",
}

#: subprocess's functions that take a `timeout=` of their own.
RUNNERS = ("run", "call", "check_call", "check_output")


def _py_files(root):
    """Every .py under SCAN, as (name from the root with `/`, path)."""
    out = []
    for folder, dirs, files in os.walk(os.path.join(root, *SCAN.split("/"))):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
        for name in sorted(files):
            if name.endswith(".py"):
                path = os.path.join(folder, name)
                out.append((os.path.relpath(path, root).replace(os.sep, "/"), path))
    return out


def _dotted(node):
    """`a.b.c` for a Name/Attribute chain, else None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _names(tree):
    """What this module calls subprocess and urllib.request by: `(modules, functions)`, where `modules` maps a dotted
    name to the module it is (`sp` -> subprocess) and `functions` a bare name to `module.function`."""
    modules = {"subprocess": "subprocess", "urllib.request": "urllib.request"}
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name in ("subprocess", "urllib.request") and a.asname:
                    modules[a.asname] = a.name
        elif isinstance(node, ast.ImportFrom) and not node.level:
            for a in node.names:
                if node.module == "urllib" and a.name == "request":
                    modules[a.asname or "request"] = "urllib.request"
                elif node.module in ("subprocess", "urllib.request"):
                    functions[a.asname or a.name] = f"{node.module}.{a.name}"
    return modules, functions


def _test_functions(tree):
    """The names of this module's test functions: `_selftest*`, and every `_check_*` a test function names."""
    defs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(node.name, []).append(node)
    tests = {name for name in defs if name.startswith("_selftest")}
    while True:
        named = {n.id for name in tests for d in defs.get(name, ()) for n in ast.walk(d)
                 if isinstance(n, ast.Name) and n.id.startswith("_check_") and n.id in defs}
        if named <= tests:
            return tests
        tests |= named


def _is_none(node):
    return isinstance(node, ast.Constant) and node.value is None


def _has_kw(call, name, position):
    """True when `call` passes `name` -- by keyword, or as positional argument number `position` (1-based) -- as
    something other than `None`, which is no timeout."""
    if any(k.arg == name and not _is_none(k.value) for k in call.keywords):
        return True
    return (position is not None and len(call.args) >= position and not _is_none(call.args[position - 1])
            and not any(isinstance(a, ast.Starred) for a in call.args[:position]))


class _Scan(ast.NodeVisitor):
    """The calls of one module that start a child or a download, with the function each sits in (`Class.method`,
    `outer.inner`, `<module>`), test code left out."""

    def __init__(self, modules, functions, tests):
        self.modules, self.functions, self.tests = modules, functions, tests
        self.stack = []
        self.found = []           # (line, what, function)
        self.popens = {}          # function -> [line of each Popen]
        self.communicates = {}    # function -> [has a timeout, ...]

    def _scoped(self, outside, name, body):
        for n in outside:
            self.visit(n)
        self.stack.append(name)
        for n in body:
            self.visit(n)
        self.stack.pop()

    def visit_FunctionDef(self, node):
        returns = [node.returns] if node.returns is not None else []
        self._scoped(node.decorator_list + [node.args] + returns, node.name, node.body)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._scoped(node.decorator_list + node.bases + node.keywords, node.name, node.body)

    def _target(self, func):
        """`subprocess.run`, `urllib.request.urlopen` ... for a call's function, or None."""
        if isinstance(func, ast.Name):
            return self.functions.get(func.id)
        if isinstance(func, ast.Attribute):
            module = self.modules.get(_dotted(func.value) or "")
            return f"{module}.{func.attr}" if module else None
        return None

    def visit_Call(self, node):
        if not any(name in self.tests for name in self.stack):
            where = ".".join(self.stack) or "<module>"
            target = self._target(node.func)
            if target and target.startswith("subprocess."):
                fn = target.split(".", 1)[1]
                if fn in RUNNERS and not _has_kw(node, "timeout", None):
                    self.found.append((node.lineno, f"{target} in {where}() has no timeout=", where))
                elif fn == "Popen":
                    self.popens.setdefault(where, []).append(node.lineno)
            elif target == "urllib.request.urlopen" and not _has_kw(node, "timeout", 3):
                self.found.append((node.lineno, f"urlopen in {where}() has no timeout", where))
            elif target == "urllib.request.urlretrieve":
                self.found.append((node.lineno, f"urlretrieve in {where}() -- it takes no timeout: urlopen(..., "
                                                f"timeout=N) and write the file", where))
            if isinstance(node.func, ast.Attribute) and node.func.attr == "communicate":
                self.communicates.setdefault(where, []).append(_has_kw(node, "timeout", 2))
        self.generic_visit(node)

    def problems(self):
        out = list(self.found)
        for where, lines in self.popens.items():
            waits = self.communicates.get(where, [])
            if not waits or not all(waits):
                why = "no communicate(timeout=...) waits on it" if not waits else "a communicate() there has no timeout"
                out += [(line, f"subprocess.Popen in {where}(): {why}", where) for line in lines]
        return out


def check(root=ROOT, allowed=ALLOWED):
    """Every complaint, one line each; empty when the tree holds."""
    problems, seen = [], set()
    for rel, path in _py_files(root):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            # Named, as selftest-reach-check names it (group fix 1, item 16): it raised out of check(), a traceback.
            problems.append(f"{rel}: cannot be read ({exc.__class__.__name__}: {exc}) -- the children it starts are "
                            f"not seen; save it as UTF-8, or make it readable")
            continue
        try:
            tree = ast.parse(text, filename=path)
        except SyntaxError as exc:
            problems.append(f"{rel}:{exc.lineno}: does not parse -- {exc.msg}")
            continue
        scan = _Scan(*_names(tree), _test_functions(tree))
        scan.visit(tree)
        found = []
        for line, what, where in scan.problems():
            if (rel, where) in allowed:
                seen.add((rel, where))
            else:
                found.append((line, f"{what} -- give it its timeout and answer one in the caller's own terms, or "
                                    f"name ({rel!r}, {where!r}) in ALLOWED with its reason"))
        problems += [f"{rel}:{line}: {what}" for line, what in sorted(found)]
    for rel, where in sorted(set(allowed) - seen):
        problems.append(f"ALLOWED names {where}() in {rel}, which starts no child without a timeout any more -- drop "
                        f"the entry")
    return problems


def _check_a_file_it_cannot_read_is_named():
    """A `.py` under the skill that is not UTF-8 -- one saved in cp1251 -- is a named complaint, as selftest-reach-check
    names one (group fix 1, item 16): `open(...).read()` raised `UnicodeDecodeError` out of `check()`, a traceback
    where the run's verdict belonged. The other files are still read: a child with no timeout beside it is named."""
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="subprocess_check_cp1251_")
    try:
        tool = os.path.join(root, *f"{SCAN}/rew_tool".split("/"))
        os.makedirs(tool)
        with open(os.path.join(tool, "x.py"), "wb") as f:
            f.write("# Перевірка\nimport subprocess\nsubprocess.run(['git'])\n".encode("cp1251"))
        with open(os.path.join(tool, "y.py"), "w", encoding="utf-8") as f:
            f.write("import subprocess\n\n\ndef head():\n    subprocess.run(['git'])\n")
        try:
            got = check(root, {})
        except Exception as exc:  # noqa: BLE001 -- a traceback is the failure under test
            got = [f"raised {type(exc).__name__}: {exc}"]
        assert len(got) == 2 and got[0].startswith(f"{SCAN}/rew_tool/x.py: cannot be read (UnicodeDecodeError") \
            and "save it as UTF-8" in got[0] and got[1].startswith(f"{SCAN}/rew_tool/y.py:5: subprocess.run in head()"), \
            got
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _selftest():
    failures = []
    for check_ in (_check_a_file_it_cannot_read_is_named,):
        try:
            check_()
        except AssertionError as exc:
            failures.append(f"{check_.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="subprocess_check_")
    tool = f"{SCAN}/rew_tool"
    try:
        def put(rel, text):
            path = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

        # (a): a run with no timeout, subprocess under another name, a function imported from it, arguments as **kw.
        put(f"{tool}/bare.py", "import subprocess\n\n\ndef head(root):\n"
                               "    return subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'])\n")
        put(f"{tool}/alias.py", "import subprocess as sp\n\n\nclass Git:\n    def out(self):\n"
                                "        return sp.check_output(['git', 'status'])\n")
        put(f"{tool}/state/imported.py", "from subprocess import run as go\n\n\ndef f(kw):\n    go(['x'], **kw)\n")
        # (b): a Popen nobody waits on with a timeout, and one with two waits, one of them without.
        put(f"{SCAN}/scripts/clip.py", "import subprocess\n\n\ndef copy(text):\n"
                                       "    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)\n"
                                       "    p.communicate(text.encode())\n\n\n"
                                       "def copy_twice(text):\n"
                                       "    p = subprocess.Popen(['xclip'], stdin=subprocess.PIPE)\n"
                                       "    p.communicate(text.encode(), 10)\n    p.communicate(timeout=None)\n"
                                       "    q = subprocess.Popen(['xsel'])\n    q.communicate()\n")
        # (c): a download with no timeout, and urlretrieve, which takes none.
        put(f"{SCAN}/scripts/fetch.py", "import urllib.request\nfrom urllib import request as rq\n"
                                        "from urllib.request import urlretrieve\n\n\n"
                                        "def get(url):\n    return urllib.request.urlopen(url).read()\n\n\n"
                                        "def keep(url, path):\n    urlretrieve(url, path)\n\n\n"
                                        "def other(url):\n    return rq.urlopen(url, None)\n")
        # The same calls held: a timeout by keyword or by position, a communicate that has one, test code of every
        # kind, a listed function, a call that is not subprocess's or urllib's, and a file outside the skill.
        put(f"{tool}/held.py", "import subprocess\nimport urllib.request\n\n\n"
                               "def head(root):\n"
                               "    return subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'], timeout=10)\n\n\n"
                               "def copy(text):\n    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)\n"
                               "    p.communicate(text.encode(), timeout=10)\n\n\n"
                               "def get(url, data=None):\n    urllib.request.urlopen(url, data, 20)\n"
                               "    return urllib.request.urlopen(url, timeout=20)\n\n\n"
                               "def run(cmd):\n    return cmd\n\n\n"
                               "def via(x):\n    return run(['git']), x.run(['git'])\n\n\n"
                               "def _check_held_by_its_test():\n    subprocess.run(['git'])\n\n\n"
                               "def _check_nested_one():\n    subprocess.run(['git'])\n\n\n"
                               "def _check_by_another_check():\n    _check_nested_one()\n\n\n"
                               "def _check_unnamed():\n    subprocess.run(['gh'])\n\n\n"
                               "def _selftest():\n    def git(*a):\n        return subprocess.run(['git', *a])\n"
                               "    for check in (_check_held_by_its_test, _check_by_another_check):\n"
                               "        check()\n    urllib.request.urlretrieve('x', 'y')\n    return git()\n")
        put(f"{SCAN}/scripts/editor.py", "import subprocess\n\n\ndef edit(path):\n"
                                         "    subprocess.run(['vi', path], check=True)\n")
        put("scripts/outside.py", "import subprocess\n\n\ndef f():\n    subprocess.run(['git'])\n")
        allowed = {(f"{SCAN}/scripts/editor.py", "edit"): "the person's editor",
                   (f"{SCAN}/scripts/editor.py", "gone"): "stale: nothing there any more"}
        got = check(root, allowed)
        want = [f"{tool}/alias.py:6: subprocess.check_output in Git.out() has no timeout=",
                f"{tool}/bare.py:5: subprocess.run in head() has no timeout=",
                f"{tool}/held.py:40: subprocess.run in _check_unnamed() has no timeout=",
                f"{tool}/state/imported.py:5: subprocess.run in f() has no timeout=",
                f"{SCAN}/scripts/clip.py:5: subprocess.Popen in copy(): a communicate() there has no timeout",
                f"{SCAN}/scripts/clip.py:10: subprocess.Popen in copy_twice(): a communicate() there has no timeout",
                f"{SCAN}/scripts/clip.py:13: subprocess.Popen in copy_twice(): a communicate() there has no timeout",
                f"{SCAN}/scripts/fetch.py:7: urlopen in get() has no timeout",
                f"{SCAN}/scripts/fetch.py:11: urlretrieve in keep()",
                f"{SCAN}/scripts/fetch.py:15: urlopen in other() has no timeout",
                f"ALLOWED names gone() in {SCAN}/scripts/editor.py"]
        missing = [w for w in want if not any(line.startswith(w) for line in got)]
        assert not missing, f"not named: {missing}\ngot:\n" + "\n".join(got)
        assert len(got) == len(want), "named beyond the cases:\n" + "\n".join(got)
        # A Popen with no communicate at all is its own sentence.
        put(f"{SCAN}/scripts/clip.py", "import subprocess\n\n\ndef spawn():\n    subprocess.Popen(['sleep', '9'])\n")
        got = [line for line in check(root, allowed) if "clip.py" in line]
        assert got and got[0].startswith(f"{SCAN}/scripts/clip.py:5: subprocess.Popen in spawn(): no "
                                         f"communicate(timeout=...) waits on it"), got
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("subprocess-check selftest OK -- named: a run with no timeout (subprocess under another name, a function "
          "imported from it, arguments as **kw, a _check_ no test names), a Popen no timed communicate waits on, a "
          "download with no timeout and urlretrieve, a stale ALLOWED entry; passed: a timeout by keyword or position, "
          "a timed communicate, test code (_selftest, what it nests, the _check_ it names and those they name), a "
          "listed function, a run that is not subprocess's, a file outside the skill")
    return 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return _selftest()
    if argv[1:]:
        print("usage: subprocess-check.py [--selftest]", file=sys.stderr)
        return 2
    problems = check()
    for p in problems:
        print(p)
    if problems:
        print(f"subprocess-check: {len(problems)} complaint(s)")
        return 1
    print(f"subprocess-check OK -- every production subprocess and download under {SCAN}/ has its timeout, but the "
          f"{len(ALLOWED)} functions ALLOWED names ({len(_py_files(ROOT))} files read)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
