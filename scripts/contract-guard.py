#!/usr/bin/env python3
"""Hold the method to its contract (skill #137; PLAN-AUDIT-2026-10 §3 J1).

    scripts/contract-guard.py             # the tree: exit 0, or each break named and exit 1
    scripts/contract-guard.py --selftest  # every rule broken on purpose in a throwaway tree

  1. CONTRACT_VERSION in rew_tool/contract.py is a top-level int literal (not a string, not a bool), and
     CONTRACT.md's title names it.
  2. IMPORTABLE is a top-level dict literal; every module exists; every entry is defined at that module's top level
     (`Class.member` inside the class, or set on `self` in its `__init__`; `Class(...)` lists the `__init__`) as
     the kind of thing it is listed as: an entry without parentheses is a value (an assignment, a class, an
     attribute) and never a def; one with them is a plain function (not async, not a property) or a class. Listed
     parameters are a PREFIX of the real ones, each keeping its kind (a positional-or-keyword one stays so; a
     positional-only or keyword-only one may only widen to positional-or-keyword) and its default, value included;
     every real one past them has a default. An addition passes; a removal, a rename, a lost or changed default or
     a narrower kind does not.
  3. Every `_siblings()` bootstrap is the text this guard holds (BOOTSTRAP) but for its `here =` line, and the
     module it lives in imports `os` and `sys` at its top level.
  4. The probe (audit T-27): each IMPORTABLE module loads by path in a fresh python started in an empty folder with
     PYTHONPATH unset and REW at a dead port; a CALLS function exists, its arguments are a tuple literal, and its
     call raises no ImportError; for CLEAN modules sys.path is untouched by the load.
  5. CLEAN and CALLS name only IMPORTABLE modules, and CONTRACT.md item 9 has one row per IMPORTABLE module, saying
     "guaranteed" for exactly the CLEAN ones.
  6. While CONTRACT_VERSION is N, FROZEN has contract N's table (a bump freezes it in the same commit), and that
     table holds: every module it lists is in IMPORTABLE, and every entry it lists passes rule 2 against the code,
     whatever IMPORTABLE says now.
  7. No function of a CLEAN module imports a sibling by its bare name -- loaded by path, rew_tool/ is not on
     sys.path -- but the command lines CLI_IMPORTS names; and no module of the method calls `_siblings()` at import,
     where a load under the import lock can deadlock against siblings' own lock. The body of a top-level
     `if __name__ == "__main__":` is not import: it runs as a script, outside any import lock.
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
#: The call that reaches a module's lazy sibling imports, and its arguments as a Python tuple literal.
#: dsp_profile's is one crossover family, so `annotate_modellable` runs its loop: called with `{}`, the loop never
#: ran, and a sibling load moved into it went unprobed (J1 review).
CALLS = {"dsp_profile.py": ("annotate_modellable",
                            '({"groups": [{"crossover_filters": {"types": {"LR": {"orders_db_per_oct": [24]}}}}]},)'),
         "rew_api.py": ("get_timing", "('1',)")}

#: Contract N's `IMPORTABLE`, frozen (J1 review). While `CONTRACT_VERSION` is N, every module listed here stays in
#: IMPORTABLE, and every entry here holds against the code by rule 2: a name renamed or removed in the code AND in
#: IMPORTABLE still fails, and so does a module dropped from IMPORTABLE and CONTRACT.md together. IMPORTABLE may grow
#: (a name, a trailing parameter with a default); this table does not move. Contract 1's was generated once from
#: contract.py's IMPORTABLE as committed in dd4312d (unchanged through d8e8cae), and it is not edited by hand. A bump
#: to N+1 adds FROZEN[N+1], generated the same way from the bump's IMPORTABLE, and leaves FROZEN[N] as it is
#: (CONTRACT.md item 12); until it does, the guard fails.
FROZEN = {
    1: {
        "rew_api.py": (
            "BASE_URL", "FINEST_SMOOTHING", "get_measurements()", "get_measurement(mid)",
            "find_measurement_id(name, measurements=None, exact=True)", "get_measurement_by_name(name, exact=True)",
            "rename_measurement(mid, title)", "get_fr(mid, smoothing=None)", "get_group_delay(mid, smoothing=None)",
            "get_impulse_response(mid)", "get_distortion(mid)", "get_filters(mid)", "get_equaliser(mid)",
            "get_equalisers()", "get_crossover_types()", "get_slopes()", "get_target_settings(mid)",
            "get_target_response(mid)", "set_filters(mid, filters)", "is_swept(record)",
            "duplicate_titles(measurements=None)",
        ),
        "state/state.py": (
            "PresetHistory(root, preset, project_dir=None)", "PresetHistory.head()",
            "PresetHistory.load(version=None)", "PresetHistory._path(version)", "SnapshotError",
            "identity_error(path, snap)", "project_channels(project_dir)",
        ),
        "state/process.py": (
            "Process(root)", "Process.load()", "Process.events(limit=None, kinds=None)", "Process.session_closed()",
            "Process.protective_record()", "PHASES", "PHASE_TITLES", "EV_CONFIG_CHANGE", "EV_STEP_DONE",
        ),
        "naming.py": (
            "parse_name(title, glossary=None)", "name_key(parsed)", "Glossary.for_project(project_dir)",
            "Glossary.channel_codes(active_only=False)", "Glossary.resolve_code(code)",
            "Glossary.pairs", "Glossary.joints", "Glossary.sides", "Glossary.combos",
            "generate_name(code, version, method=None, modifier=None, position=None, control=None, params=None)",
            "expected_groups(phase, glossary, version)", "validate_series(titles, expected, glossary=None)",
            "METHODS", "METHOD_SWEEP", "METHOD_RTA", "canonical_title(title)", "canonical_code(code)",
            "explain_name(title, glossary=None)",
        ),
        "dsp_profile.py": (
            "load_profile(path)", "validate_profile(data)", "FIELD_VOCABULARY", "CAPABILITY_CHECKLIST",
            "processing_rate_hz(data)", "bundled_dir()", "list_bundled(dir_=None)",
        ),
        "project.py": (
            "Project(root)", "Project.load()", "Project.save(data)", "Project.parse_impact(impact)",
            "PROJECT_TYPES", "project_type(data)",
        ),
        "dsp_math.py": ("apf1_response(freqs_hz, f0)", "apf2_response(freqs_hz, f0, q)"),
        "resonalyze_vc.py": (
            "load_session(path)",
            "convert(doc, *, profile=None, proj=None, mapping=None, group_id='physical_outputs', source_path=None)",
        ),
        "project_seed.py": (
            "seed(source, target, *, include_findings=False, copy_profile=True, note=DEFAULT_NOTE, today=None, "
            "seat=None, include_fs=True)",
            "describe(source)", "dsp_of(source)",
        ),
        "eq_export.py": (
            "export_eq(profile, eq_rows, *, crossovers=None, fmt=None, group_id='physical_outputs', channel=None)",
        ),
        "protective.py": (
            "legs_of(record, channel)", "should_de_embed(record, channel, *, baseline=None)",
            "matters_at(legs, freq_hz)", "de_embed(freqs_hz, measured, legs)",
        ),
        "listening.py": (
            "characteristics(lang=None)", "tracks(lang=None)", "links(lang=None)", "routes()", "check(lang=None)",
            "languages()", "PATTERNS", "CHEAT_SHEET",
        ),
        "gates/side_effect.py": (
            "FORM_POST_URL", "FORM_FIELD_SENDER", "FORM_FIELD_KIND", "FORM_FIELD_IMPACT", "FORM_FIELD_MESSAGE",
            "FORM_FIELD_VERSIONS", "FORM_LABELS", "FORM_KINDS", "FORM_PERSON_KINDS", "FORM_IMPACTS",
            "FORM_TIMEOUT_S", "form_answers(sender, kind, message, impact='', versions='')",
            "verify_form_reply(status, body)",
            "upload_issue_asset(image_path, dest_name, *, consented=False, message=None, runner=_subprocess_runner, "
            "dry_run=False)",
        ),
        "car_profile.py": (
            "find_prior_projects(dirs, make, model, generation='', body='')",
            "body_slug(make, model, generation='', body='')", "find_bundled_car(make, model, generation='', body='')",
        ),
        "verify.py": ("verdict(name, measurements=None, f_low=20, f_high=20000)",),
    },
}

#: The bare sibling imports a CLEAN module still makes inside a function (rule 7), by (file, function): command-line
#: entry points only, which a front end runs as a process and never calls in-process. Each with what it imports.
CLI_IMPORTS = {
    ("state/state.py", "_variant_cli"): "`variant new --delta` imports apply to apply the delta file",
    ("state/process.py", "_main"): "`capture-import <N>` without titles imports rew_api to read REW's titles",
    ("naming.py", "_main"): "`next-series` imports process (state/ put on sys.path first); `check` imports rew_api",
}

#: The `_siblings()` bootstrap every module that loads a sibling carries, with its `here =` line blanked: that one
#: line differs with the file's folder. The guard holds every copy to THIS text (rule 3), not the copies to each
#: other: the same edit made in all of them is still an edit (J1 review). A deliberate change edits this text and
#: every copy in one commit.
BOOTSTRAP = '''def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here =
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module'''

BOOTSTRAP_HERE = "    here = "
PROBE = r'''
import ast, importlib.util, json, sys
path, call, args = sys.argv[1], sys.argv[2], sys.argv[3]
before = list(sys.path)
spec = importlib.util.spec_from_file_location("contract_probe_target", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
after = list(sys.path)
error = bad_args = None
# Resolved before the call, outside its `except`: a renamed function must not pass as a call that raised, and
# arguments that do not evaluate must not pass as a call that ran.
target = getattr(module, call, None) if call else None
if target is not None and callable(target):
    try:
        values = ast.literal_eval(args)
        if not isinstance(values, tuple):
            raise ValueError(f"{values!r} is not a tuple")
    except Exception as exc:
        bad_args = f"{type(exc).__name__}: {exc}"
    else:
        try:
            target(*values)
        except ImportError as exc:
            error = f"{type(exc).__name__}: {exc}"
        except Exception:
            pass
print(json.dumps({"path_changed": after != before, "import_error": error, "bad_args": bad_args,
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


#: Decorators that make a def an attribute read: `obj.f` is then the value, and `obj.f()` calls that value.
_PROPERTY = ("property", "cached_property", "setter", "getter", "deleter")


def _decorator(node):
    """A decorator's last name: `property`; `functools.cached_property` -> `cached_property`; `x.setter` -> `setter`."""
    return node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", None)


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
        # A value (`BASE_URL`, `Glossary.pairs`, `SnapshotError`) is read, not called: an assignment, a class, or an
        # attribute `__init__` sets. Made a def, the name is still there and a reader gets a function (J1 review).
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False, f"{entry} is listed as a value and is a function -- a caller reading it gets the function"
        return True, ""
    constructor = isinstance(node, ast.ClassDef)
    if constructor:
        node = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
        if node is None:
            # A dataclass or an inherited `__init__`: the parameters are real, but not here to be read.
            return False, f"{name} has no __init__ of its own -- its constructor's parameters cannot be checked"
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False, f"{name} is listed with parameters and is not a function"
    # A caller of `f(...)` gets what f returns: not a coroutine, and not the call of whatever a property returns.
    if isinstance(node, ast.AsyncFunctionDef):
        return False, f"{entry.partition('(')[0]} is async -- a caller gets a coroutine, not what it returns"
    if any(_decorator(d) in _PROPERTY for d in node.decorator_list):
        return False, f"{entry.partition('(')[0]} is a property -- `{entry}` would call the value it returns"
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


def _modules(dirs):
    """[(path, text, ast)] of every .py under `dirs`, by path."""
    out = []
    for d in dirs:
        for base, _dirs, files in os.walk(d):
            for fn in files:
                if fn.endswith(".py"):
                    path = os.path.join(base, fn)
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                    out.append((path, text, ast.parse(text, filename=path)))
    return sorted(out, key=lambda m: m[0])


def _bootstrap(text, tree):
    """The source of a module's top-level `_siblings` (the last one, as Python binds it) with its `here =` line
    blanked, or None."""
    src = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_siblings":
            src = "\n".join(BOOTSTRAP_HERE.rstrip() if line.startswith(BOOTSTRAP_HERE) else line
                            for line in ast.get_source_segment(text, node).splitlines())
    return src


def _imports_at_top(tree, name):
    """Does the module bind `name` with an `import` in its top-level body (`import os`, `import os.path`)?"""
    return any(isinstance(n, ast.Import) and any((a.asname or a.name.split(".")[0]) == name for a in n.names)
               for n in tree.body)


def _sibling_names(tool):
    """The names a bare `import` of a sibling uses: every .py's stem under rew_tool/, and every folder's name."""
    names = set()
    for _base, dirs, files in os.walk(tool):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        names.update(d for d in dirs if d.isidentifier())
        names.update(fn[:-3] for fn in files if fn.endswith(".py"))
    return names


def _runs_as_script(test):
    """Is an `if`'s test `__name__ == "__main__"` (either way round)?"""
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
        return False
    sides = (test.left, test.comparators[0])
    return (any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
            and any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides))


class _Scopes(ast.NodeVisitor):
    """Where a module's imports and `_siblings()` calls run (rule 7): inside a function, when it is called; or at
    import -- the module's body, a class body, a decorator, a default value. The body of a top-level
    `if __name__ == "__main__":` is neither: it runs as a script, outside any import lock."""

    def __init__(self):
        self.stack = []          # ("class" | "def", name), from the module down
        self.imports = []        # (the outermost function, `f` or `Class.f`; line; the top name imported)
        self.at_import = []      # lines of a `_siblings()` call that runs at import
        self.as_script = 0       # inside the body of `if __name__ == "__main__":`

    def visit_If(self, node):
        if self.stack or not _runs_as_script(node.test):
            self.generic_visit(node)
            return
        self.visit(node.test)
        self.as_script += 1
        for n in node.body:
            self.visit(n)
        self.as_script -= 1
        for n in node.orelse:    # the `else:` runs on import
            self.visit(n)

    def _function(self):
        names = []
        for kind, name in self.stack:
            names.append(name)
            if kind == "def":
                return ".".join(names)
        return None

    def visit_ClassDef(self, node):
        for n in node.decorator_list + node.bases + node.keywords:
            self.visit(n)
        self.stack.append(("class", node.name))
        for n in node.body:
            self.visit(n)
        self.stack.pop()

    def _def(self, node, name, body):
        # A decorator, a default value and an annotation run where the def runs; only the body waits for a call.
        for n in getattr(node, "decorator_list", ()):
            self.visit(n)
        self.visit(node.args)
        if getattr(node, "returns", None) is not None:
            self.visit(node.returns)
        self.stack.append(("def", name))
        for n in body:
            self.visit(n)
        self.stack.pop()

    def visit_FunctionDef(self, node):
        self._def(node, node.name, node.body)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self._def(node, "<lambda>", [node.body])

    def visit_Import(self, node):
        function = self._function()
        if function:
            self.imports += [(function, node.lineno, a.name.split(".")[0]) for a in node.names]

    def visit_ImportFrom(self, node):
        function = self._function()
        if function and node.level == 0 and node.module:
            self.imports.append((function, node.lineno, node.module.split(".")[0]))

    def visit_Call(self, node):
        if self._function() is None and not self.as_script and getattr(node.func, "id", None) == "_siblings":
            self.at_import.append(node.lineno)
        self.generic_visit(node)


def check(tool, scripts, clean=CLEAN, calls=CALLS, frozen=FROZEN, cli_imports=CLI_IMPORTS):
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
        # Rule 6 needs a table to hold: a bump freezes its own in the same commit, or the new number holds nothing.
        if cv.value not in frozen:
            problems.append(f"contract {cv.value} has no frozen table: a bump freezes its IMPORTABLE as FROZEN"
                            f"[{cv.value}] in scripts/contract-guard.py, in the same commit (CONTRACT.md item 12)")
    imp = _literal(tree, "IMPORTABLE")
    try:
        importable = ast.literal_eval(imp) if imp is not None else None
    except ValueError:
        importable = None
    parsed = isinstance(importable, dict)
    if not parsed:
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
    # Rule 6: the contract the literal names is frozen. Its modules stay in IMPORTABLE, and each of its names still
    # holds against the code, whatever IMPORTABLE says now -- an entry IMPORTABLE lists word for word was held above.
    version = cv.value if isinstance(cv, ast.Constant) and type(cv.value) is int else None
    for rel, entries in (frozen.get(version, {}) if parsed else {}).items():
        if rel not in importable:
            problems.append(f"contract {version} froze {rel}, and IMPORTABLE no longer lists it -- it stays listed "
                            f"until CONTRACT_VERSION moves (CONTRACT.md item 12)")
        path = os.path.join(tool, *rel.split("/"))
        if not os.path.isfile(path):
            continue                                     # named: not listed, or listed and not in rew_tool/
        mod_tree = _module_ast(path)
        for entry in entries:
            if entry in importable.get(rel, ()):
                continue
            ok, why = _defined(mod_tree, entry)
            if not ok:
                problems.append(f"contract {version} froze {rel}'s {entry}: {why} -- a break moves CONTRACT_VERSION "
                                f"(CONTRACT.md item 12)")
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
    # Rules 3 and 7, one walk over the method's modules.
    siblings = _sibling_names(tool)
    for path, text, mod_tree in _modules([tool, scripts]):
        where = os.path.relpath(path, tool).replace(os.sep, "/")
        src = _bootstrap(text, mod_tree)
        if src is not None:
            if src != BOOTSTRAP:
                got, want = src.splitlines(), BOOTSTRAP.splitlines()
                i = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
                line, line_ = (got[i] if i < len(got) else "<none>"), (want[i] if i < len(want) else "<none>")
                problems.append(f"{where}: _siblings() is not the bootstrap this guard holds (BOOTSTRAP) -- its line "
                                f"{i + 1} is {line.strip()!r}, the guard's {line_.strip()!r}")
            for name in ("os", "sys"):
                if not _imports_at_top(mod_tree, name):
                    problems.append(f"{where} defines _siblings() and does not import {name} at its top level -- the "
                                    f"bootstrap reads {name} when it is called")
        scopes = _Scopes()
        scopes.visit(mod_tree)
        for line in scopes.at_import:
            problems.append(f"{where}: _siblings() runs at module level (line {line}) -- a load at import can "
                            f"deadlock against siblings' lock; load inside the function that needs it")
        if where in clean:
            for function, line, name in scopes.imports:
                if name in siblings and (where, function) not in cli_imports:
                    problems.append(f"{where}: {function}() imports {name} inside a function (line {line}) -- loaded "
                                    f"by path, rew_tool/ is not on sys.path and the call fails; load it through "
                                    f"_siblings().load(), or name a command line in CLI_IMPORTS")
    # REW at a dead port (T-30): `get_timing('1')` is a probe call, and a guard run by hand must never reach a REW that
    # is open on the machine.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["REW_API_URL"] = "http://127.0.0.1:1"
    env["PYTHONIOENCODING"] = "utf-8"                    # both ends of the pipe in UTF-8, whatever the code page
    for rel in importable:
        path = os.path.join(tool, *rel.split("/"))
        if not os.path.isfile(path):
            continue
        call, args = calls.get(rel, ("", "()"))
        with tempfile.TemporaryDirectory(prefix="contract_probe_") as empty:   # a fresh empty folder, removed after
            r = subprocess.run([sys.executable, "-c", PROBE, path, call, args], cwd=empty, env=env,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        if r.returncode != 0:
            problems.append(f"{rel}: does not load by path from an empty folder -- {r.stderr.strip().splitlines()[-1:]}")
            continue
        seen = json.loads(r.stdout.strip().splitlines()[-1])
        if seen["missing_call"]:
            problems.append(f"{rel}: CALLS names {call}(), which the module does not define -- its lazy imports "
                            f"went unprobed")
        if seen["bad_args"]:
            problems.append(f"{rel}: CALLS gives {call}() the arguments {args!r}, which are not a tuple literal -- "
                            f"{seen['bad_args']}; the call went unprobed")
        if seen["import_error"]:
            problems.append(f"{rel}: {call}() fails a sibling import when loaded by path -- {seen['import_error']}")
        if rel in clean and seen["path_changed"]:
            problems.append(f"{rel}: listed CLEAN, and loading it changed sys.path")
    return problems


def _boot(here):
    """BOOTSTRAP with its `here =` line filled: the text a module of the throwaway tree carries."""
    blank = "\n" + BOOTSTRAP_HERE.rstrip() + "\n"
    assert BOOTSTRAP.count(blank) == 1, "BOOTSTRAP has no blank `here =` line to fill"
    return "\n\n" + BOOTSTRAP.replace(blank, f"\n{BOOTSTRAP_HERE}{here}\n") + "\n"


def _selftest():
    """Every rule broken on purpose in a throwaway tree, each break named by the rule that holds it."""
    import shutil
    with tempfile.TemporaryDirectory(prefix="contract_guard_") as root:
        tool, scripts = os.path.join(root, "rew_tool"), os.path.join(root, "scripts")
        os.makedirs(os.path.join(tool, "sub"))
        os.makedirs(scripts)
        shutil.copy(os.path.join(TOOL, "siblings.py"), os.path.join(tool, "siblings.py"))
        boot = _boot
        files = {
            "rew_tool/contract.py": (
                'CONTRACT_VERSION = 1\n'
                'IMPORTABLE = {\n'
                '    "m.py": ("X", "f(a, b=1)", "g(a, *, k=None)", "w(*, k=None)", "t(x=())", "C(a)", "C.meth(x)",\n'
                '             "C.make(y)", "C.st(z)", "C.attr", "D", "lazy()"),\n'
                '    "sub/n.py": ("Y", "h()"),\n'
                '}\n'),
            "rew_tool/CONTRACT.md": (
                "# Contract 1\n\nThe throwaway tree's promises.\n\n## 9. The modules TCC imports\n\n"
                "| module | loads by path without touching `sys.path` |\n|---|---|\n"
                "| `m.py` | guaranteed |\n| `sub/n.py` | W-10 (J1b) |\n"),
            "rew_tool/m.py": (
                'import os\nimport sys\n\nX = 1\n'
                + boot("os.path.dirname(os.path.realpath(__file__))") + '\n\n'
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
                '    return _siblings().load("sub/n.py").Y\n\n\n'
                # A command line the tree's CLI table names: its bare sibling import is allowed (rule 7).
                'def _main(argv):\n    import n\n    return n.Y\n'),
            "rew_tool/sub/n.py": (
                'import os\nimport sys\n\nY = 2\n'
                + boot("os.path.dirname(os.path.dirname(os.path.realpath(__file__)))") + '\n\n'
                'def h():\n    return Y\n'),
            # The form a script outside rew_tool/ takes: another `here =` line, the same bootstrap.
            "scripts/tool.py": (
                'import os\nimport sys\n'
                + boot('os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "rew_tool")')),
        }
        for rel, text in files.items():
            with open(os.path.join(root, *rel.split("/")), "w", encoding="utf-8") as f:
                f.write(text)
        clean, calls = ("m.py",), {"m.py": ("lazy", "()")}
        # The tree's contract 1, frozen, and its command line.
        frozen = {1: {"m.py": ("X", "f(a, b=1)", "C.attr", "lazy()"), "sub/n.py": ("Y", "h()")}}
        cli = {("m.py", "_main"): "the throwaway tree's command line"}

        def run():
            return check(tool, scripts, clean=clean, calls=calls, frozen=frozen, cli_imports=cli)

        good = run()
        assert good == [], f"the good tree: {good}"

        failures = []

        def edited(label, rel, old, new, also=()):
            # `also`: more (rel, old, new) edits made with this one, in order; each must find its text once.
            texts = {}
            for r, o, n in ((rel, old, new),) + tuple(also):
                text = texts.get(r, files[r])
                assert text.count(o) == 1, f"{label}: {o!r} is not once in {r}"
                texts[r] = text.replace(o, n)
            try:
                for r, text in texts.items():
                    with open(os.path.join(root, *r.split("/")), "w", encoding="utf-8") as f:
                        f.write(text)
                return run()
            finally:
                for r in texts:
                    with open(os.path.join(root, *r.split("/")), "w", encoding="utf-8") as f:
                        f.write(files[r])

        def broken(label, rel, old, new, phrase, also=()):
            got = edited(label, rel, old, new, also)
            if not any(phrase in p for p in got):
                failures.append(f"{label}: no problem says {phrase!r} -- {got}")

        def allowed(label, rel, old, new, also=()):
            got = edited(label, rel, old, new, also)
            if got:
                failures.append(f"{label}: breaks no caller, and the guard refused it -- {got}")

        def named(label, phrase, clean_=clean, calls_=calls, cli_=cli):
            got = check(tool, scripts, clean=clean_, calls=calls_, frozen=frozen, cli_imports=cli_)
            if not any(phrase in p for p in got):
                failures.append(f"{label}: no problem says {phrase!r} -- {got}")

        # Contract 1's table, frozen (J1 review): a rename or a removal made in IMPORTABLE too is still one, and a
        # module dropped from IMPORTABLE and item 9 together is still gone; IMPORTABLE may grow.
        broken("a frozen function renamed in the code and in IMPORTABLE", "rew_tool/m.py", "def f(a, b=1, added=2):",
               "def eff(a, b=1, added=2):", "contract 1 froze m.py's f(a, b=1): f is not defined",
               also=(("rew_tool/contract.py", '"f(a, b=1)"', '"eff(a, b=1)"'),))
        broken("a frozen value removed from the code and from IMPORTABLE", "rew_tool/m.py", "X = 1\n", "",
               "contract 1 froze m.py's X: X is not defined", also=(("rew_tool/contract.py", '("X", ', '('),))
        broken("a frozen module dropped from IMPORTABLE and from item 9", "rew_tool/contract.py",
               '    "sub/n.py": ("Y", "h()"),\n', "", "contract 1 froze sub/n.py, and IMPORTABLE no longer lists it",
               also=(("rew_tool/CONTRACT.md", "| `sub/n.py` | W-10 (J1b) |\n", ""),))
        allowed("a frozen entry listed with a new trailing parameter that has a default", "rew_tool/contract.py",
                '"f(a, b=1)"', '"f(a, b=1, added=2)"')
        # A bump freezes its own table in the same commit: a number with none would hold nothing (J1 review).
        broken("a bump without its frozen table", "rew_tool/contract.py", "CONTRACT_VERSION = 1\n",
               "CONTRACT_VERSION = 2\n", "contract 2 has no frozen table",
               also=(("rew_tool/CONTRACT.md", "# Contract 1", "# Contract 2"),))
        # The KIND of thing an entry names (J1 review): a value stays a value, a function a plain function.
        broken("a value made a function", "rew_tool/m.py", "X = 1\n", "def X():\n    return 1\n",
               "m.py: X is listed as a value and is a function")
        broken("an attribute made a method", "rew_tool/m.py", "    def meth(self, x):\n",
               "    def attr(self):\n        return 1\n\n    def meth(self, x):\n",
               "m.py: C.attr is listed as a value and is a function")
        broken("a class listed as a value made a function", "rew_tool/m.py", "class D:\n", "def D():\n",
               "m.py: D is listed as a value and is a function")
        broken("a function made async", "rew_tool/m.py", "def f(a, b=1, added=2):", "async def f(a, b=1, added=2):",
               "m.py: f is async")
        prop = "    @property\n    def meth(self):\n        return 1\n\n"
        for deco, before in (("property", ""), ("functools.cached_property", ""), ("meth.setter", prop),
                             ("meth.getter", prop), ("meth.deleter", prop)):
            broken(f"a method made @{deco}", "rew_tool/m.py", "    def meth(self, x):\n",
                   f"{before}    @{deco}\n    def meth(self, x):\n", "m.py: C.meth is a property",
                   also=(("rew_tool/m.py", "import os\n", "import functools\nimport os\n"),))
        # The bootstrap is the text the guard holds, and the module it lives in imports what it reads (J1 review).
        same = ("module = sys.modules.setdefault(name, module)", "sys.modules[name] = module")
        broken("the same edit in every _siblings() copy", "rew_tool/m.py", *same,
               "m.py: _siblings() is not the bootstrap this guard holds",
               also=(("rew_tool/sub/n.py",) + same, ("scripts/tool.py",) + same))
        broken("a module with _siblings() and no top-level import sys", "rew_tool/m.py", "import os\nimport sys\n",
               "import os\n", "m.py defines _siblings() and does not import sys at its top level")
        broken("a module with _siblings() and no top-level import os", "rew_tool/m.py", "import os\nimport sys\n",
               "import sys\n", "m.py defines _siblings() and does not import os at its top level")
        broken("a module with _siblings() that imports sys inside a function only", "rew_tool/m.py",
               "import os\nimport sys\n", "import os\n",
               "m.py defines _siblings() and does not import sys at its top level",
               also=(("rew_tool/m.py", "def lazy():\n", "def lazy():\n    import sys\n"),))
        allowed("a module with _siblings() that imports os.path (it binds os)", "rew_tool/m.py",
                "import os\nimport sys\n", "import os.path\nimport sys\n")
        # No bare sibling import inside a function of a CLEAN module but its named command line, and no
        # `_siblings()` at import anywhere (J1 review).
        broken("a bare sibling import inside a function of a CLEAN module", "rew_tool/m.py",
               "def g(a, *, k=None):\n    return a\n", "def g(a, *, k=None):\n    import n\n    return a\n",
               "m.py: g() imports n inside a function")
        broken("a `from` sibling import inside a function of a CLEAN module", "rew_tool/m.py",
               "def g(a, *, k=None):\n    return a\n", "def g(a, *, k=None):\n    from n import Y\n    return Y\n",
               "m.py: g() imports n inside a function")
        broken("a sibling folder imported inside a method of a CLEAN module", "rew_tool/m.py",
               "    def meth(self, x):\n        return x\n",
               "    def meth(self, x):\n        import sub.n\n        return x\n",
               "m.py: C.meth() imports sub inside a function")
        named("a command line named for another file", "m.py: _main() imports n inside a function",
              cli_={("sub/n.py", "_main"): "another file's command line"})
        allowed("a bare sibling import inside a function of a module that is not CLEAN", "rew_tool/sub/n.py",
                "def h():\n    return Y\n", "def h():\n    import m\n    return Y\n")
        allowed("a stdlib import inside a function of a CLEAN module", "rew_tool/m.py",
                "def g(a, *, k=None):\n    return a\n", "def g(a, *, k=None):\n    import json\n    return a\n")
        broken("_siblings() at module level", "rew_tool/sub/n.py", "def h():\n    return Y\n",
               'def h():\n    return Y\n\n\nM = _siblings().load("m.py")\n',
               "sub/n.py: _siblings() runs at module level")
        broken("_siblings() at module level in a script", "scripts/tool.py", "    return module\n",
               "    return module\n\n\nSIB = _siblings()\n", "scripts/tool.py: _siblings() runs at module level")
        broken("_siblings() in a class body", "rew_tool/m.py", 'class D:\n    """No `__init__` of its own."""\n',
               'class D:\n    """No `__init__` of its own."""\n    S = _siblings()\n',
               "m.py: _siblings() runs at module level")
        broken("_siblings() in a default value", "rew_tool/m.py", "def _main(argv):\n",
               "def _main(argv=_siblings()):\n", "m.py: _siblings() runs at module level")
        # A script's `if __name__ == "__main__":` block runs outside any import lock: a load there is not at import.
        # Its `else:`, and a test that is not that one, still run on import (J1 review, round 2).
        script = "def _main(argv):\n    import n\n    return n.Y\n"
        allowed("_siblings() in the `if __name__ == \"__main__\":` block", "rew_tool/m.py", script,
                script + '\n\nif __name__ == "__main__":\n    _siblings().load("sub/n.py")\n')
        broken("_siblings() in the else of that block", "rew_tool/m.py", script,
               script + '\n\nif __name__ == "__main__":\n    pass\nelse:\n    _siblings()\n',
               "m.py: _siblings() runs at module level")
        broken("_siblings() under `if __name__ != \"__main__\":`", "rew_tool/m.py", script,
               script + '\n\nif __name__ != "__main__":\n    _siblings()\n', "m.py: _siblings() runs at module level")
        # The probe's arguments evaluate before the call, outside its `except` (J1 review).
        named("a CALLS literal that does not evaluate", "m.py: CALLS gives lazy() the arguments '(', which are not "
              "a tuple literal", calls_={"m.py": ("lazy", "(")})
        named("a CALLS literal that is not a tuple", "m.py: CALLS gives lazy() the arguments '5', which are not a "
              "tuple literal", calls_={"m.py": ("lazy", "5")})
        # The literal's TYPE, not only its form (J1 review): a string or a bool is not the int TCC reads.
        broken("CONTRACT_VERSION = '1'", "rew_tool/contract.py", "CONTRACT_VERSION = 1\n", 'CONTRACT_VERSION = "1"\n',
               "CONTRACT_VERSION is not a top-level int literal")
        broken("CONTRACT_VERSION = True", "rew_tool/contract.py", "CONTRACT_VERSION = 1\n", "CONTRACT_VERSION = True\n",
               "CONTRACT_VERSION is not a top-level int literal")

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

        def verdict(frozen_=frozen):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = main(["contract-guard.py"], tool, scripts, clean, calls, frozen_, cli)
            return rc, out.getvalue().strip().splitlines()[-1]

        said = verdict()
        if said != (0, "contract-guard OK -- contract 1 holds"):
            failures.append(f"the verdict on the good tree: {said}")
        put("rew_tool/contract.py", files["rew_tool/contract.py"].replace("CONTRACT_VERSION = 1\n",
                                                                          "CONTRACT_VERSION = 2\n"))
        bumped = {**frozen, 2: frozen[1]}                    # the bump froze its table, as it must
        try:
            said = verdict(bumped)                           # 2 in the literal, 1 in the title: one problem
            if said != (1, "contract-guard: 1 problem(s)"):
                failures.append(f"the verdict on a tree with one problem: {said}")
            put("rew_tool/CONTRACT.md", files["rew_tool/CONTRACT.md"].replace("# Contract 1", "# Contract 2"))
            said = verdict(bumped)
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
               "sub/n.py: _siblings() is not the bootstrap this guard holds")
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
    print("contract-guard selftest OK -- named: a CONTRACT_VERSION that is no literal, a string or a bool, a "
          "CONTRACT.md title that is not it, an IMPORTABLE that is no literal, an absent name, a renamed or a new "
          "required parameter (a constructor's too), a listed default removed or changed, a parameter made "
          "keyword-only or positional-only (a widened one passes), an attribute __init__ no longer sets, a class "
          "with no __init__ of its own, a constant listed as a function, a value made a function, a function made "
          "async or a property, an entry that does not parse, a module not there, a frozen name renamed or removed "
          "with its entry and a frozen module dropped (a frozen entry may grow), a bump without its frozen table, "
          "CLEAN or CALLS naming a module "
          "IMPORTABLE does not, CONTRACT.md item 9 out of step with IMPORTABLE or CLEAN, a _siblings copy that is "
          "not the guard's text (one copy or all of them), a module with _siblings and no top-level os or sys, a "
          "bare sibling import inside a function of a CLEAN module (its named command line passes), _siblings() "
          "run at import (a script's `__main__` block passes), a module that fails at load, a CLEAN module that "
          "edits sys.path, a bare import in a probe "
          "call, a probe call that is not there, probe arguments that are not a tuple literal; the probe ignores "
          "the caller's PYTHONPATH and REW_API_URL; the verdict names the contract the tree holds")


def main(argv, tool=TOOL, scripts=SCRIPTS, clean=CLEAN, calls=CALLS, frozen=FROZEN, cli_imports=CLI_IMPORTS):
    if argv[1:] == ["--selftest"]:
        _selftest()
        return 0
    problems = check(tool, scripts, clean=clean, calls=calls, frozen=frozen, cli_imports=cli_imports)
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
