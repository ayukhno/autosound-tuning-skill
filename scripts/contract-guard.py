#!/usr/bin/env python3
"""Hold the method to its contract (skill #137; PLAN-AUDIT-2026-10 §3 J1).

    scripts/contract-guard.py             # the tree: exit 0, or each break named and exit 1
    scripts/contract-guard.py --selftest  # every rule broken on purpose in a throwaway tree

  1. CONTRACT_VERSION in rew_tool/contract.py is a top-level int literal, and CONTRACT.md's title names it.
  2. IMPORTABLE is a top-level dict literal; every module exists; every entry is defined at that module's top level
     (`Class.member` inside the class, or set on `self` in its `__init__`; `Class(...)` lists the `__init__`);
     listed parameters are a PREFIX of the real ones, each keeping its kind (a positional-or-keyword one stays so;
     a positional-only or keyword-only one may only widen to positional-or-keyword) and its default, value
     included; every real one past them has a default. An addition passes; a removal, a rename, a lost or changed
     default or a narrower kind does not.
  3. Every `_siblings()` bootstrap is the canonical text; only its `here =` line may differ.
  4. The probe (audit T-27): each IMPORTABLE module loads by path in a fresh python started in an empty folder with
     PYTHONPATH unset and REW at a dead port; a CALLS function exists and its call raises no ImportError; for CLEAN
     modules sys.path is untouched by the load.
  5. CLEAN and CALLS name only IMPORTABLE modules, and CONTRACT.md item 9 has one row per IMPORTABLE module, saying
     "guaranteed" for exactly the CLEAN ones.
"""
import ast
import json
import os
import re
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
# Resolved before the call, outside its `except`: a renamed function must not pass as a call that raised.
target = getattr(module, call, None) if call else None
if target is not None and callable(target):
    try:
        target(*eval(args))
    except ImportError as exc:
        error = f"{type(exc).__name__}: {exc}"
    except Exception:
        pass
print(json.dumps({"path_changed": after != before, "import_error": error,
                  "missing_call": bool(call) and not callable(target)}))
'''


def _module_ast(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return node.value
    return None


#: How a caller may pass a parameter, as a problem names it.
_KINDS = {"posonly": "positional-only", "pos": "positional-or-keyword", "kwonly": "keyword-only"}
#: What each listed kind may become: a caller who passes it by position still can (positional-only widened), and
#: one who passes it by keyword still can (keyword-only widened). A positional-or-keyword one stays as it is.
_WIDER = {"posonly": ("posonly", "pos"), "pos": ("pos",), "kwonly": ("kwonly", "pos")}


def _params(args):
    """[(name, kind, the default's source or None)] of an `ast.arguments`: positional-only, positional-or-keyword,
    then keyword-only."""
    pos = [(a.arg, "posonly") for a in args.posonlyargs] + [(a.arg, "pos") for a in args.args]
    defaults = [None] * (len(pos) - len(args.defaults)) + [ast.unparse(d) for d in args.defaults]
    kw = [(a.arg, "kwonly") for a in args.kwonlyargs]
    kw_defaults = [None if d is None else ast.unparse(d) for d in args.kw_defaults]
    return [(n, k, d) for (n, k), d in zip(pos + kw, defaults + kw_defaults)]


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
            # A dataclass or an inherited `__init__`: the parameters are real, but not here to be read.
            return False, f"{name} has no __init__ of its own -- its constructor's parameters cannot be checked"
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False, f"{name} is listed with parameters and is not a function"
    # One closing parenthesis, not every one: a default may end in its own (`kinds=()`).
    if not sig.endswith(")"):
        return False, f"{entry!r} does not end with ')'"
    try:
        listed = _params(ast.parse(f"def _x({sig[:-1]}): pass").body[0].args)
    except SyntaxError:
        return False, f"{entry!r} does not parse as a signature"
    real = _params(node.args)
    # `Class.method(...)` and `Class(...)` (its `__init__`) list what a caller passes: `self` / `cls` is not one.
    if (attr or constructor) and [p[0] for p in real[:1]] in (["self"], ["cls"]):
        real = real[1:]
    names, real_names = [p[0] for p in listed], [p[0] for p in real]
    if real_names[:len(names)] != names:
        return False, f"{name}({', '.join(real_names)}) does not begin with ({', '.join(names)})"
    # Each listed parameter as a caller passes it (R18): its kind, and its default with the same value.
    for (p, kind, default), (_, real_kind, real_default) in zip(listed, real):
        if real_kind not in _WIDER[kind]:
            return False, f"{name}: {p} became {_KINDS[real_kind]} -- the contract lists it {_KINDS[kind]}"
        if default is not None and real_default is None:
            return False, f"{name}: {p} lost its default -- the contract lists {p}={default}"
        if default is not None and real_default != default:
            return False, f"{name}: {p}'s default is {real_default}, the contract lists {p}={default}"
    extra = [p for p, _, d in real[len(listed):] if d is None]
    if extra:
        return False, f"{name} has new required parameters {extra} -- a contract break"
    return True, ""


#: A row of CONTRACT.md item 9's table: `| `<module>` | <status> |`.
_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]*?)\s*\|\s*$")


def _item9(md):
    """{module: status} from the table under CONTRACT.md's `## 9.` heading, or None when there is no such heading."""
    rows, inside = None, False
    with open(md, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## "):
                inside = line.startswith("## 9.")
                if inside:
                    rows = {}
                continue
            m = _ROW.match(line.rstrip("\n")) if inside else None
            if m:
                rows[m.group(1)] = m.group(2)
    return rows


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
    # What the probe holds and what CONTRACT.md promises name the same modules as IMPORTABLE: a module renamed
    # there and left here would leave a promise that nothing checks.
    for table, rels in (("CLEAN", clean), ("CALLS", calls)):
        for rel in rels:
            if rel not in importable:
                problems.append(f"{table} lists {rel}, which IMPORTABLE does not list")
    md = os.path.join(tool, "CONTRACT.md")
    rows = _item9(md) if os.path.isfile(md) else None
    if rows is None:
        problems.append("CONTRACT.md has no item 9 table (a `## 9.` heading, a `| `<module>` | <status> |` row for "
                        "each IMPORTABLE module)")
    else:
        for rel in importable:
            if rel not in rows:
                problems.append(f"CONTRACT.md item 9 has no row for {rel}, which IMPORTABLE lists")
        for rel, status in rows.items():
            if rel not in importable:
                problems.append(f"CONTRACT.md item 9 has a row for {rel}, which IMPORTABLE does not list")
            elif status == "guaranteed" and rel not in clean:
                problems.append(f"CONTRACT.md item 9 says guaranteed for {rel}, which CLEAN does not hold")
            elif status != "guaranteed" and rel in clean:
                problems.append(f"CONTRACT.md item 9 does not say guaranteed for {rel}, which CLEAN holds")
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
        if seen["missing_call"]:
            problems.append(f"{rel}: CALLS names {call}(), which the module does not define -- its lazy imports "
                            f"went unprobed")
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
                '    "m.py": ("X", "f(a, b=1)", "g(a, *, k=None)", "w(*, k=None)", "t(x=())", "C(a)", "C.meth(x)",\n'
                '             "C.make(y)", "C.st(z)", "C.attr", "lazy()"),\n'
                '    "sub/n.py": ("Y", "h()"),\n'
                '}\n'),
            "rew_tool/CONTRACT.md": (
                "# Contract 1\n\nThe throwaway tree's promises.\n\n## 9. The modules TCC imports\n\n"
                "| module | loads by path without touching `sys.path` |\n|---|---|\n"
                "| `m.py` | guaranteed |\n| `sub/n.py` | W-10 (J1b) |\n"),
            "rew_tool/m.py": (
                'import os\nimport sys\n\nX = 1\n'
                + boot(here="os.path.dirname(os.path.realpath(__file__))") + '\n\n'
                'def f(a, b=1, added=2):\n    return a\n\n\n'
                'def g(a, *, k=None):\n    return a\n\n\n'
                'def w(*, k=None):\n    return k\n\n\n'
                'def t(x=()):\n    return x\n\n\n'
                'class C:\n'
                '    def __init__(self, a):\n        self.attr = a\n\n'
                '    def meth(self, x):\n        return x\n\n'
                '    @classmethod\n    def make(cls, y):\n        return cls(y)\n\n'
                '    @staticmethod\n    def st(z):\n        return z\n\n\n'
                'class D:\n    """No `__init__` of its own."""\n\n\n'
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

        def edited(label, rel, old, new):
            path = os.path.join(root, *rel.split("/"))
            text = files[rel]
            assert text.count(old) == 1, f"{label}: {old!r} is not once in {rel}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(text.replace(old, new))
            try:
                return run()
            finally:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)

        def broken(label, rel, old, new, phrase):
            got = edited(label, rel, old, new)
            if not any(phrase in p for p in got):
                failures.append(f"{label}: no problem says {phrase!r} -- {got}")

        def allowed(label, rel, old, new):
            got = edited(label, rel, old, new)
            if got:
                failures.append(f"{label}: breaks no caller, and the guard refused it -- {got}")

        def named(label, phrase, clean_=clean, calls_=calls):
            got = check(tool, scripts, clean=clean_, calls=calls_)
            if not any(phrase in p for p in got):
                failures.append(f"{label}: no problem says {phrase!r} -- {got}")

        named("a CALLS function the module does not define", "m.py: CALLS names gone(), which the module does not "
              "define -- its lazy imports went unprobed", calls_={"m.py": ("gone", "()")})
        # The tables that say what the probe promises agree with IMPORTABLE, and CONTRACT.md item 9 with CLEAN.
        named("CLEAN lists a module IMPORTABLE does not", "CLEAN lists zz.py, which IMPORTABLE does not list",
              clean_=("m.py", "zz.py"))
        named("CALLS lists a module IMPORTABLE does not", "CALLS lists zz.py, which IMPORTABLE does not list",
              calls_={"m.py": ("lazy", "()"), "zz.py": ("f", "()")})
        broken("item 9 says guaranteed for a module CLEAN does not hold", "rew_tool/CONTRACT.md",
               "| `sub/n.py` | W-10 (J1b) |", "| `sub/n.py` | guaranteed |",
               "CONTRACT.md item 9 says guaranteed for sub/n.py, which CLEAN does not hold")
        broken("item 9 does not say guaranteed for a CLEAN module", "rew_tool/CONTRACT.md", "| `m.py` | guaranteed |",
               "| `m.py` | W-10 (J1b) |", "CONTRACT.md item 9 does not say guaranteed for m.py, which CLEAN holds")
        broken("item 9 has no row for a listed module", "rew_tool/CONTRACT.md", "| `sub/n.py` | W-10 (J1b) |\n", "",
               "CONTRACT.md item 9 has no row for sub/n.py, which IMPORTABLE lists")
        broken("item 9 has a row for a module IMPORTABLE does not list", "rew_tool/CONTRACT.md",
               "| `sub/n.py` | W-10 (J1b) |\n", "| `sub/n.py` | W-10 (J1b) |\n| `zz.py` | W-10 (J1b) |\n",
               "CONTRACT.md item 9 has a row for zz.py, which IMPORTABLE does not list")
        broken("CONTRACT.md without item 9", "rew_tool/CONTRACT.md", "## 9. The modules", "## Nine. The modules",
               "CONTRACT.md has no item 9 table")

        # The verdict line names the contract the tree holds, read from the literal: a bumped tree says its number.
        import contextlib
        import io

        def put(rel, text):
            with open(os.path.join(root, *rel.split("/")), "w", encoding="utf-8") as f:
                f.write(text)

        def verdict():
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = main(["contract-guard.py"], tool, scripts, clean, calls)
            return rc, out.getvalue().strip().splitlines()[-1]

        said = verdict()
        if said != (0, "contract-guard OK -- contract 1 holds"):
            failures.append(f"the verdict on the good tree: {said}")
        put("rew_tool/contract.py", files["rew_tool/contract.py"].replace("CONTRACT_VERSION = 1\n",
                                                                          "CONTRACT_VERSION = 2\n"))
        try:
            said = verdict()                                 # 2 in the literal, 1 in the title: one problem
            if said != (1, "contract-guard: 1 problem(s)"):
                failures.append(f"the verdict on a tree with one problem: {said}")
            put("rew_tool/CONTRACT.md", files["rew_tool/CONTRACT.md"].replace("# Contract 1", "# Contract 2"))
            said = verdict()
            if said != (0, "contract-guard OK -- contract 2 holds"):
                failures.append(f"the verdict on a contract 2 tree: {said}")
        finally:
            put("rew_tool/contract.py", files["rew_tool/contract.py"])
            put("rew_tool/CONTRACT.md", files["rew_tool/CONTRACT.md"])

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
        # A listed parameter keeps its kind and its default, value included (R18): a caller passes it as listed.
        broken("a listed default removed", "rew_tool/m.py", "def f(a, b=1, added=2):", "def f(a, b, added=2):",
               "m.py: f: b lost its default -- the contract lists b=1")
        broken("a listed default changed", "rew_tool/m.py", "def f(a, b=1, added=2):", "def f(a, b=2, added=2):",
               "m.py: f: b's default is 2, the contract lists b=1")
        broken("a positional parameter made keyword-only", "rew_tool/m.py", "def f(a, b=1, added=2):",
               "def f(a, *, b=1, added=2):", "m.py: f: b became keyword-only -- the contract lists it "
               "positional-or-keyword")
        broken("a positional parameter made positional-only", "rew_tool/m.py", "def f(a, b=1, added=2):",
               "def f(a, /, b=1, added=2):", "m.py: f: a became positional-only -- the contract lists it "
               "positional-or-keyword")
        broken("a keyword-only parameter made positional-only", "rew_tool/m.py", "def w(*, k=None):",
               "def w(k=None, /):", "m.py: w: k became positional-only -- the contract lists it keyword-only")
        allowed("a keyword-only parameter widened to positional-or-keyword", "rew_tool/m.py", "def g(a, *, k=None):",
                "def g(a, k=None):")
        allowed("a default given to a parameter the contract lists without one", "rew_tool/m.py",
                "def meth(self, x):", "def meth(self, x=0):")
        broken("a constructor's parameter renamed", "rew_tool/m.py", "def __init__(self, a):\n        self.attr = a",
               "def __init__(self, b):\n        self.attr = b", "m.py: C(b) does not begin with (a)")
        broken("an attribute __init__ no longer sets", "rew_tool/m.py", "self.attr = a", "self.other = a",
               "m.py: C.attr is not defined")
        broken("a class listed with parameters and no __init__ of its own", "rew_tool/contract.py", '"C.st(z)"',
               '"C.st(z)", "D(x)"', "m.py: D has no __init__ of its own -- its constructor's parameters cannot "
               "be checked")
        broken("a constant listed as a function", "rew_tool/contract.py", '"m.py": ("X",', '"m.py": ("X(a)",',
               "m.py: X is listed with parameters and is not a function")
        broken("an entry that does not parse", "rew_tool/contract.py", '"t(x=())"', '"t(x=()"',
               "m.py: 't(x=()' does not parse as a signature")
        broken("an entry without its closing parenthesis", "rew_tool/contract.py", '"t(x=())"', '"t(x"',
               "m.py: 't(x' does not end with ')'")
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
          "constructor's too), a listed default removed or changed, a parameter made keyword-only or "
          "positional-only (a widened one passes), an attribute __init__ no longer sets, a class with no __init__ "
          "of its own, a constant listed as a function, an entry that does not parse, a module not there, CLEAN or "
          "CALLS naming a module IMPORTABLE does not, CONTRACT.md item 9 out of step with IMPORTABLE or CLEAN, a "
          "_siblings copy with one changed line, a module that fails at load, a CLEAN module that edits sys.path, a "
          "bare import in a probe call, a probe call that is not there; the probe ignores the caller's PYTHONPATH "
          "and REW_API_URL; the verdict names the contract the tree holds")


def main(argv, tool=TOOL, scripts=SCRIPTS, clean=CLEAN, calls=CALLS):
    if argv[1:] == ["--selftest"]:
        _selftest()
        return 0
    problems = check(tool, scripts, clean=clean, calls=calls)
    for p in problems:
        print(f"[contract] {p}")
    if problems:
        print(f"contract-guard: {len(problems)} problem(s)")
        return 1
    # No problem means the literal is an int: the line names the contract this tree holds.
    version = _literal(_module_ast(os.path.join(tool, "contract.py")), "CONTRACT_VERSION").value
    print(f"contract-guard OK -- contract {version} holds")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
