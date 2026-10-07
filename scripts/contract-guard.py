#!/usr/bin/env python3
"""Hold the method to its contract (skill #137; PLAN-AUDIT-2026-10 §3 J1).

    scripts/contract-guard.py             # the tree: exit 0, or each break named and exit 1
    scripts/contract-guard.py --selftest  # every rule broken on purpose in a throwaway tree

  1. CONTRACT_VERSION in rew_tool/contract.py is a top-level int literal, and CONTRACT.md's title names it.
  2. IMPORTABLE is a top-level dict literal; every module exists; every entry is defined at that module's top level
     (`Class.member` inside the class, or set on `self` in its `__init__`; `Class(...)` lists the `__init__`);
     listed parameters are a PREFIX of the real ones and every real one past them has a default -- an addition
     passes, a removal or a rename does not.
  3. Every `_siblings()` bootstrap is the canonical text; only its `here =` line may differ.
  4. The probe (audit T-27): each IMPORTABLE module loads by path in a fresh python started in an empty folder with
     PYTHONPATH unset and REW at a dead port; a lazy-import call raises no ImportError; for CLEAN modules sys.path
     is untouched by the load.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "skills", "autosound-tuning", "rew_tool")
SCRIPTS = os.path.join(ROOT, "skills", "autosound-tuning", "scripts")

#: Modules that load by path without touching sys.path -- CONTRACT.md item 9 says "guaranteed" for exactly these.
#: The rest are J1b's (W-10). Filled from what the probe reported (2026-10-07), not from a guess: the other six
#: (project, resonalyze_vc, project_seed, eq_export, protective, verify) each put rew_tool/ on sys.path at import.
CLEAN = ("rew_api.py", "state/state.py", "state/process.py", "naming.py", "dsp_profile.py", "dsp_math.py",
         "listening.py", "gates/side_effect.py", "car_profile.py")
#: The call that reaches a module's lazy sibling imports, and its arguments as a Python literal.
CALLS = {"dsp_profile.py": ("annotate_modellable", "({},)"), "rew_api.py": ("get_timing", "('1',)")}

BOOTSTRAP_HERE = "    here = "
PROBE = r'''
import importlib.util, json, sys
path, call, args = sys.argv[1], sys.argv[2], sys.argv[3]
before = list(sys.path)
spec = importlib.util.spec_from_file_location("contract_probe_target", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
after = list(sys.path)
error = None
if call:
    try:
        getattr(module, call)(*eval(args))
    except ImportError as exc:
        error = f"{type(exc).__name__}: {exc}"
    except Exception:
        pass
print(json.dumps({"path_changed": after != before, "import_error": error}))
'''


def _module_ast(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return node.value
    return None


def _params(args):
    names = [a.arg for a in args.posonlyargs + args.args] + [a.arg for a in args.kwonlyargs]
    n_pos = len(args.posonlyargs) + len(args.args)
    defaults = [None] * (n_pos - len(args.defaults)) + list(args.defaults) + list(args.kw_defaults)
    return names, defaults


def _defined(tree, entry):
    """(ok, why) for one IMPORTABLE entry against a module's ast."""
    name, _, sig = entry.partition("(")
    owner, _, attr = name.partition(".")
    scope = tree.body
    if attr:
        cls = next((n for n in scope if isinstance(n, ast.ClassDef) and n.name == owner), None)
        if cls is None:
            return False, f"class {owner} is not defined"
        scope, name = cls.body, attr
    node = None
    for n in scope:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name:
            node = n
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(getattr(t, "id", None) == name for t in targets):
                node = n
    if node is None and attr:
        # An attribute every instance carries is set in `__init__` (`self.pairs = ...`): TCC reads
        # `Glossary.pairs` as a name all the same.
        init = next((n for n in scope if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
        for n in ast.walk(init) if init is not None else ():
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if any(isinstance(t, ast.Attribute) and t.attr == name and getattr(t.value, "id", None) == "self"
                       for t in targets):
                    node = n
    if node is None:
        return False, f"{entry.partition('(')[0]} is not defined"
    if not sig:
        return True, ""
    constructor = isinstance(node, ast.ClassDef)
    if constructor:
        node = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
        if node is None:
            return True, ""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False, f"{name} is listed with parameters and is not a function"
    listed, _ = _params(ast.parse(f"def _x({sig.rstrip(')')}): pass").body[0].args)
    real, real_defaults = _params(node.args)
    # `Class.method(...)` and `Class(...)` (its `__init__`) list what a caller passes: `self` / `cls` is not one.
    if (attr or constructor) and real[:1] in (["self"], ["cls"]):
        real, real_defaults = real[1:], real_defaults[1:]
    if real[:len(listed)] != listed:
        return False, f"{name}({', '.join(real)}) does not begin with ({', '.join(listed)})"
    extra = [p for p, d in zip(real[len(listed):], real_defaults[len(listed):]) if d is None]
    if extra:
        return False, f"{name} has new required parameters {extra} -- a contract break"
    return True, ""


def _bootstraps(dirs):
    """{path: source of its `_siblings` with the `here =` line blanked}."""
    out = {}
    for d in dirs:
        for base, _dirs, files in os.walk(d):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(base, fn)
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                tree = ast.parse(text)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == "_siblings":
                        src = ast.get_source_segment(text, node)
                        out[path] = "\n".join(line if not line.startswith(BOOTSTRAP_HERE) else BOOTSTRAP_HERE
                                              for line in src.splitlines())
    return out


def check(tool, scripts, clean=CLEAN, calls=CALLS):
    problems = []
    contract_path = os.path.join(tool, "contract.py")
    tree = _module_ast(contract_path)
    cv = _literal(tree, "CONTRACT_VERSION")
    if not (isinstance(cv, ast.Constant) and type(cv.value) is int):
        problems.append("contract.py: CONTRACT_VERSION is not a top-level int literal (TCC reads it with ast)")
    else:
        md = os.path.join(tool, "CONTRACT.md")
        title = open(md, encoding="utf-8").readline().strip() if os.path.isfile(md) else ""
        if title != f"# Contract {cv.value}":
            problems.append(f"CONTRACT.md's title is {title!r}, not '# Contract {cv.value}'")
    imp = _literal(tree, "IMPORTABLE")
    try:
        importable = ast.literal_eval(imp) if imp is not None else None
    except ValueError:
        importable = None
    if not isinstance(importable, dict):
        problems.append("contract.py: IMPORTABLE is not a top-level dict literal")
        importable = {}
    for rel, entries in importable.items():
        path = os.path.join(tool, *rel.split("/"))
        if not os.path.isfile(path):
            problems.append(f"IMPORTABLE lists {rel}, which is not in rew_tool/")
            continue
        mod_tree = _module_ast(path)
        for entry in entries:
            ok, why = _defined(mod_tree, entry)
            if not ok:
                problems.append(f"{rel}: {why}")
    boot = _bootstraps([tool, scripts])
    if len(set(boot.values())) > 1:
        first = sorted(boot)[0]
        for path, src in sorted(boot.items()):
            if src != boot[first]:
                problems.append(f"{os.path.relpath(path, tool)}: _siblings() differs from {os.path.relpath(first, tool)}")
    # REW at a dead port (T-30): `get_timing('1')` is a probe call, and a guard run by hand must never reach a REW that
    # is open on the machine.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["REW_API_URL"] = "http://127.0.0.1:1"
    for rel in importable:
        path = os.path.join(tool, *rel.split("/"))
        if not os.path.isfile(path):
            continue
        call, args = calls.get(rel, ("", "()"))
        with tempfile.TemporaryDirectory(prefix="contract_probe_") as empty:   # a fresh empty folder, removed after
            r = subprocess.run([sys.executable, "-c", PROBE, path, call, args], cwd=empty, env=env,
                               capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            problems.append(f"{rel}: does not load by path from an empty folder -- {r.stderr.strip().splitlines()[-1:]}")
            continue
        seen = json.loads(r.stdout.strip().splitlines()[-1])
        if seen["import_error"]:
            problems.append(f"{rel}: {call}() fails a sibling import when loaded by path -- {seen['import_error']}")
        if rel in clean and seen["path_changed"]:
            problems.append(f"{rel}: listed CLEAN, and loading it changed sys.path")
    return problems


#: The `_siblings()` bootstrap the throwaway tree's modules carry: the method's text, `here` filled per file.
_SELFTEST_BOOT = '''
def _siblings():
    """`rew_tool/siblings.py`, by its path."""
    import hashlib
    import importlib.util
    here = {here}
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module = sys.modules.setdefault(name, module)
    return module
'''


def _selftest():
    """Every rule broken on purpose in a throwaway tree, each break named by the rule that holds it."""
    import shutil
    with tempfile.TemporaryDirectory(prefix="contract_guard_") as root:
        tool, scripts = os.path.join(root, "rew_tool"), os.path.join(root, "scripts")
        os.makedirs(os.path.join(tool, "sub"))
        os.makedirs(scripts)
        shutil.copy(os.path.join(TOOL, "siblings.py"), os.path.join(tool, "siblings.py"))
        boot = _SELFTEST_BOOT.format
        files = {
            "rew_tool/contract.py": (
                'CONTRACT_VERSION = 1\n'
                'IMPORTABLE = {\n'
                '    "m.py": ("X", "f(a, b=1)", "g(a, *, k=None)", "C(a)", "C.meth(x)", "C.make(y)", "C.st(z)",\n'
                '             "C.attr", "lazy()"),\n'
                '    "sub/n.py": ("Y", "h()"),\n'
                '}\n'),
            "rew_tool/CONTRACT.md": "# Contract 1\n\nThe throwaway tree's promises.\n",
            "rew_tool/m.py": (
                'import os\nimport sys\n\nX = 1\n'
                + boot(here="os.path.dirname(os.path.realpath(__file__))") + '\n\n'
                'def f(a, b=1, added=2):\n    return a\n\n\n'
                'def g(a, *, k=None):\n    return a\n\n\n'
                'class C:\n'
                '    def __init__(self, a):\n        self.attr = a\n\n'
                '    def meth(self, x):\n        return x\n\n'
                '    @classmethod\n    def make(cls, y):\n        return cls(y)\n\n'
                '    @staticmethod\n    def st(z):\n        return z\n\n\n'
                'def lazy():\n'
                '    if os.environ.get("REW_API_URL") != "http://127.0.0.1:1":\n'
                '        raise ImportError("the probe reached REW at " + str(os.environ.get("REW_API_URL")))\n'
                '    return _siblings().load("sub/n.py").Y\n'),
            "rew_tool/sub/n.py": (
                'import os\nimport sys\n\nY = 2\n'
                + boot(here="os.path.dirname(os.path.dirname(os.path.realpath(__file__)))") + '\n\n'
                'def h():\n    return Y\n'),
            # The form a script outside rew_tool/ takes: another `here =` line, the same bootstrap.
            "scripts/tool.py": (
                'import os\nimport sys\n'
                + boot(here='os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "rew_tool")')),
        }
        for rel, text in files.items():
            with open(os.path.join(root, *rel.split("/")), "w", encoding="utf-8") as f:
                f.write(text)
        clean, calls = ("m.py",), {"m.py": ("lazy", "()")}

        def run():
            return check(tool, scripts, clean=clean, calls=calls)

        good = run()
        assert good == [], f"the good tree: {good}"

        failures = []

        def broken(label, rel, old, new, phrase):
            path = os.path.join(root, *rel.split("/"))
            text = files[rel]
            assert text.count(old) == 1, f"{label}: {old!r} is not once in {rel}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(text.replace(old, new))
            try:
                got = run()
            finally:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            if not any(phrase in p for p in got):
                failures.append(f"{label}: no problem says {phrase!r} -- {got}")

        broken("CONTRACT_VERSION = 1 + 0", "rew_tool/contract.py", "CONTRACT_VERSION = 1\n",
               "CONTRACT_VERSION = 1 + 0\n", "CONTRACT_VERSION is not a top-level int literal")
        broken("CONTRACT.md titled '# Contract 2'", "rew_tool/CONTRACT.md", "# Contract 1", "# Contract 2",
               "CONTRACT.md's title is '# Contract 2', not '# Contract 1'")
        broken("IMPORTABLE is not a literal", "rew_tool/contract.py", 'IMPORTABLE = {\n',
               'IMPORTABLE = {"m.py": ("X",)} or {\n', "IMPORTABLE is not a top-level dict literal")
        broken("an absent function", "rew_tool/contract.py", '"lazy()"', '"lazy()", "absent(a)"',
               "m.py: absent is not defined")
        broken("a parameter renamed", "rew_tool/m.py", "def f(a, b=1, added=2):", "def f(a, bee=1, added=2):",
               "m.py: f(a, bee, added) does not begin with (a, b)")
        broken("a new required parameter", "rew_tool/m.py", "def f(a, b=1, added=2):",
               "def f(a, b=1, added=2, *, needed):", "m.py: f has new required parameters ['needed']")
        broken("a constructor's parameter renamed", "rew_tool/m.py", "def __init__(self, a):\n        self.attr = a",
               "def __init__(self, b):\n        self.attr = b", "m.py: C(b) does not begin with (a)")
        broken("an attribute __init__ no longer sets", "rew_tool/m.py", "self.attr = a", "self.other = a",
               "m.py: C.attr is not defined")
        broken("a constant listed as a function", "rew_tool/contract.py", '"m.py": ("X",', '"m.py": ("X(a)",',
               "m.py: X is listed with parameters and is not a function")
        broken("a module that is not there", "rew_tool/contract.py", '    "sub/n.py"',
               '    "gone.py": ("Z",),\n    "sub/n.py"', "IMPORTABLE lists gone.py, which is not in rew_tool/")
        broken("a _siblings copy with one changed line", "rew_tool/sub/n.py",
               "module = sys.modules.setdefault(name, module)", "sys.modules[name] = module",
               "sub/n.py: _siblings() differs from m.py")
        broken("a module that fails at load", "rew_tool/sub/n.py", "Y = 2\n", "Y = 2\nraise RuntimeError('boom')\n",
               "sub/n.py: does not load by path from an empty folder")
        broken("a CLEAN module that edits sys.path", "rew_tool/m.py", "X = 1\n", 'X = 1\nsys.path.insert(0, ".")\n',
               "m.py: listed CLEAN, and loading it changed sys.path")
        broken("a bare import in the called function", "rew_tool/m.py", 'return _siblings().load("sub/n.py").Y',
               "import nowhere_module\n    return nowhere_module",
               "m.py: lazy() fails a sibling import when loaded by path -- ModuleNotFoundError: "
               "No module named 'nowhere_module'")
        # The probe's own environment: PYTHONPATH is not inherited (a module the caller's path holds stays out of
        # reach), REW is at the dead port whatever the caller's REW_API_URL, and both hold for the bare import too.
        with open(os.path.join(root, "nowhere_module.py"), "w", encoding="utf-8") as f:
            f.write("")
        saved = {k: os.environ.get(k) for k in ("PYTHONPATH", "REW_API_URL")}
        os.environ["PYTHONPATH"], os.environ["REW_API_URL"] = root, "http://127.0.0.1:4735"
        try:
            env_good = run()
            if env_good:
                failures.append(f"the caller's REW_API_URL reached the probe: {env_good}")
            broken("a bare import that only the caller's PYTHONPATH resolves", "rew_tool/m.py",
                   'return _siblings().load("sub/n.py").Y', "import nowhere_module\n    return nowhere_module",
                   "No module named 'nowhere_module'")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        assert not failures, "\n".join(failures)
    print("contract-guard selftest OK -- named: a CONTRACT_VERSION that is no literal, a CONTRACT.md title that is "
          "not it, an IMPORTABLE that is no literal, an absent name, a renamed or a new required parameter (a "
          "constructor's too), an attribute __init__ no longer sets, a constant listed as a function, a module not "
          "there, a _siblings copy with one changed line, a module that fails at load, a CLEAN module that edits "
          "sys.path, a bare import in a probe call; the probe ignores the caller's PYTHONPATH and REW_API_URL")


def main(argv):
    if argv[1:] == ["--selftest"]:
        _selftest()
        return 0
    problems = check(TOOL, SCRIPTS)
    for p in problems:
        print(f"[contract] {p}")
    print(f"contract-guard: {len(problems)} problem(s)" if problems else "contract-guard OK -- contract 1 holds")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
