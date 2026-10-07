#!/usr/bin/env python3
"""Every file the method owns is written through `rew_tool/project_io.py` (skill #135; audit T-8) -- checked.

`project_io.atomic_write_text` / `atomic_write_json` write a temp file whose name no other writer uses, fsync it and
move it over the file in one `os.replace`. Before #135, eleven writers named their temp `<file>.tmp` -- one name for
every writer of that file, so a second writer truncated the first one's temp and moved it into place -- and four more
wrote in place. Two rules keep that from coming back:

  (a) no string constant ending in `.tmp` outside `rew_tool/project_io.py`: a fixed temp name IS the defect. ALLOWED
      holds the (file, literal) pairs that are not a temp name, each with its reason. This file is not read for (a).
  (b) no call to `os.replace` or `os.rename` outside `project_io.py` but the moves MOVES names by (file, function):
      whole files moved aside or installed, not a temp moved over a file the method owns.

An ALLOWED or MOVES entry that matches nothing is a complaint too: a stale entry would let the next fixed temp name,
or the next move, through unseen.

Read by AST, every .py under skills/autosound-tuning/ and the repo's scripts/: a comment is not a constant, and `os`
under another name (`import os as _os`, `from os import replace`) is still `os`. What it does not see: a temp name
built without a `.tmp` literal, and a move by `shutil.move` or `pathlib`.

    scripts/atomic-write-check.py             # the tree: each complaint and exit 1, or the OK line
    scripts/atomic-write-check.py --selftest  # each rule broken on purpose in a throwaway tree

stdlib only.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The folders read, from the repo's root. Files are named from there too: `scripts/x.py` is the repo's, and the
#: skill's own scripts are `skills/autosound-tuning/scripts/x.py`.
SCAN = ("skills/autosound-tuning", "scripts")
PROJECT_IO = "skills/autosound-tuning/rew_tool/project_io.py"
SELF = "scripts/atomic-write-check.py"

#: (file, literal) -> why the literal is not a temp name. Rule (a) passes exactly these.
ALLOWED = {
    ("skills/autosound-tuning/rew_tool/project_seed.py", "*.tmp"):
        "the `.gitignore` line a new project gets, so that a temp a crash left is never committed: a pattern, "
        "not a temp name",
    ("skills/autosound-tuning/rew_tool/state/process.py", "process-state.json.tmp"):
        "its selftest plants the temp name the writer used before #135, as another writer's file, and checks the "
        "writer leaves it alone",
}

#: (file, function) -> why its move is not a temp moved over a file the method owns. Rule (b) passes exactly these.
MOVES = {
    ("skills/autosound-tuning/rew_tool/state/state.py", "migrate_line"):
        "the ledger's one move to the per-project layout: the per-preset folders, registry.json and seals.json go "
        "to legacy/ whole, kept and not rewritten",
    ("skills/autosound-tuning/rew_tool/intake.py", "_set_aside"):
        "a profile of another processor moved aside under a new name, never deleted",
    ("skills/autosound-tuning/scripts/upkeep.py", "update_gh_release"):
        "the gh binary, checked against its release's checksums, installed over the old one: a program, not a file "
        "the method owns",
}


MOVERS = ("replace", "rename")


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


def _os_names(tree):
    """The names `os` goes by in this module, and the names `os.replace` / `os.rename` go by on their own."""
    module, movers = {"os"}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "os" or a.name.startswith("os."):
                    module.add(a.asname or "os")
        elif isinstance(node, ast.ImportFrom) and node.module == "os" and not node.level:
            for a in node.names:
                if a.name in MOVERS:
                    movers[a.asname or a.name] = a.name
    return module, movers


class _Scan(ast.NodeVisitor):
    """The `.tmp` literals of one module, and its moves with the function each sits in (`Class.method` for a method,
    `outer.inner` for a nested def, `<module>` at the top)."""

    def __init__(self, module_names, movers):
        self.module_names, self.movers = module_names, movers
        self.stack, self.literals, self.moves = [], [], []

    def _scoped(self, outside, name, body):
        for n in outside:                    # decorators, defaults and bases run where the def or the class is
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

    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value.lower().endswith(".tmp"):
            self.literals.append((node.lineno, node.value))

    def visit_Call(self, node):
        f, mover = node.func, None
        if isinstance(f, ast.Attribute) and f.attr in MOVERS and isinstance(f.value, ast.Name) \
                and f.value.id in self.module_names:
            mover = f.attr
        elif isinstance(f, ast.Name) and f.id in self.movers:
            mover = self.movers[f.id]
        if mover:
            self.moves.append((node.lineno, mover, ".".join(self.stack) or "<module>"))
        self.generic_visit(node)


def check(root=ROOT, allowed=ALLOWED, moves=MOVES):
    """Every complaint, one line each; empty when the tree holds."""
    problems, allowed_seen, moves_seen = [], set(), set()
    for rel, path in _py_files(root):
        if rel == PROJECT_IO:
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        try:
            tree = ast.parse(text, filename=path)
        except SyntaxError as exc:
            problems.append(f"{rel}:{exc.lineno}: does not parse -- {exc.msg}")
            continue
        scan = _Scan(*_os_names(tree))
        scan.visit(tree)
        found = []
        for line, value in ([] if rel == SELF else scan.literals):
            if (rel, value) in allowed:
                allowed_seen.add((rel, value))
            else:
                found.append((line, f"{value!r} -- a fixed temp name, which two writers of one file share: write "
                                    f"through project_io (atomic_write_text / atomic_write_json), or name the "
                                    f"literal in ALLOWED with its reason"))
        for line, mover, function in scan.moves:
            if (rel, function) in moves:
                moves_seen.add((rel, function))
            else:
                found.append((line, f"os.{mover} in {function}() -- a temp moved over a file goes through "
                                    f"project_io; a whole file moved aside or installed is named in MOVES with its "
                                    f"reason"))
        problems += [f"{rel}:{line}: {what}" for line, what in sorted(found)]
    for rel, value in sorted(set(allowed) - allowed_seen):
        problems.append(f"ALLOWED names {rel} {value!r}, which that file no longer holds -- drop the entry")
    for rel, function in sorted(set(moves) - moves_seen):
        problems.append(f"MOVES names {function}() in {rel}, which moves nothing there any more -- drop the entry")
    return problems


def _selftest():
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="atomic_write_check_")
    tool = "skills/autosound-tuning/rew_tool"
    try:
        def put(rel, text):
            path = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

        # The two violations: a fixed temp name, and a move nobody listed.
        put(f"{tool}/fixed.py", 'def save(path, text):\n    tmp = path + ".tmp"\n    return tmp, text\n')
        put(f"{tool}/mover.py", "import os\n\n\ndef swap(a, b):\n    os.replace(a, b)\n")
        # The allowed move, and a listed literal in its own file.
        put(f"{tool}/state/aside.py", "import os\n\n\nclass Keep:\n    def set_aside(self, a, b):\n"
                                      "        os.replace(a, b)\n")
        put(f"{tool}/seed.py", 'IGNORE = ["*.mdat", "*.tmp"]\n')
        # Not a constant, not this rule's business, or the writer itself: none of these is a complaint.
        put(f"{tool}/quiet.py", 'import os\n# the old writer did `tmp = path + ".tmp"`\n'
                                'NAME = "x.tmp.json"\n\n\ndef f(s):\n    return s.replace("a", "b")\n')
        put(PROJECT_IO, 'import os\n\n\ndef w(p):\n    os.replace(p + ".tmp", p)\n')
        put(SELF, 'SUFFIX = ".tmp"\n')
        # `os` under another name is still `os`, in the repo's scripts/ as in the skill.
        put("scripts/tool.py", "import os as _os\n\n\ndef go(a, b):\n    _os.rename(a, b)\n")
        put("skills/autosound-tuning/scripts/helper.py", "from os import replace as mv\n\n\ndef go(a, b):\n"
                                                         "    mv(a, b)\n")
        # A listed literal in a file it is not listed for, and a listed function's name in another file.
        put(f"{tool}/other.py", 'IGNORE = "*.tmp"\n\n\ndef set_aside(a, b):\n    import os\n    os.replace(a, b)\n')
        allowed = {(f"{tool}/seed.py", "*.tmp"): "a pattern",
                   (f"{tool}/seed.py", "gone.tmp"): "stale: the file no longer holds it"}
        moves = {(f"{tool}/state/aside.py", "Keep.set_aside"): "a whole file moved aside",
                 (f"{tool}/mover.py", "unswap"): "stale: no such move"}
        got = check(root, allowed, moves)
        want = [f"{tool}/fixed.py:2: '.tmp'",
                f"{tool}/mover.py:5: os.replace in swap()",
                f"{tool}/other.py:1: '*.tmp'",
                f"{tool}/other.py:6: os.replace in set_aside()",
                "scripts/tool.py:5: os.rename in go()",
                "skills/autosound-tuning/scripts/helper.py:5: os.replace in go()",
                f"ALLOWED names {tool}/seed.py 'gone.tmp'",
                f"MOVES names unswap() in {tool}/mover.py"]
        missing = [w for w in want if not any(line.startswith(w) for line in got)]
        assert not missing, f"not named: {missing}\ngot:\n" + "\n".join(got)
        assert len(got) == len(want), "named beyond the cases:\n" + "\n".join(got)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("atomic-write-check selftest OK -- named: a .tmp literal, an unlisted os.replace, os.rename under an alias, "
          "a replace imported from os, a listed literal or function name in another file, a stale ALLOWED or MOVES "
          "entry; passed: a listed move, a listed literal, a comment, a str.replace, project_io itself, this file")
    return 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return _selftest()
    if argv[1:]:
        print("usage: atomic-write-check.py [--selftest]", file=sys.stderr)
        return 2
    problems = check()
    for p in problems:
        print(p)
    if problems:
        print(f"atomic-write-check: {len(problems)} complaint(s)")
        return 1
    print("atomic-write-check OK -- every write goes through project_io")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
