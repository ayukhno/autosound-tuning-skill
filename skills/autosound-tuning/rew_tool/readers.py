#!/usr/bin/env python3
"""readers -- the DSP saved-file readers the method declares, held to their own code (hub #350, CONTRACT.md item 15).

    python3 rew_tool/readers.py              one line a reader: family, file, verbs, models
    python3 rew_tool/readers.py --json       the registry as stored (`knowledge/dsp/readers.json`, `readers.v1`)
    python3 rew_tool/readers.py --selftest   the registry against the code; planted wrong lines must fail

The registry is what a front end turns its buttons on by. `check` holds it to the code both ways, so it cannot drift:

* every reader the gate dispatches from (`compare_file.READERS`, which `reader_for` reads) is listed once, no other,
  and a name no pattern matches is read by no verb;
* a reader's `pattern` is the gate's, its `family` and `model_code` its own code's (`VENDOR` / `DEVICE["vendor"]`,
  `MODEL_CODE`), and every shipped test file (`TESTDATA`) goes through the gate under exactly the listed `verbs` and is
  read by the real reader as a model the registry lists;
* its `models` are the ones its `describe` gives a channel layout, named and coded as compare-file's `device` says;
* `other_models` is what reading one gives: a shipped file made to name a code outside the list, compared through
  compare-file's real path (`_probe_other`). Types exactly: codes strings, flags booleans.
"""

import json
import os
import sys

CONTRACT = "readers.v1"
REGISTRY = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "knowledge", "dsp",
                        "readers.json")
_KEYS = ("id", "family", "module", "pattern", "verbs", "model_code", "models", "other_models")


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.realpath(__file__))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


def load(path=REGISTRY):
    """The registry as stored."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: The shipped test files, by reader: each runs through the gate and its real reader (`check`).
TESTDATA = {"helix_pct6": os.path.join("testdata", "helix-pct6", "*.pct6"),
            "mosconi_pr": os.path.join("testdata", "mosconi-pr", "*.PR15")}


def _module(cf, reader_id):
    """The reader's own code: `helix_pct6.models`, `mosconi_pr`."""
    return {"helix_pct6": lambda: cf._helix().models, "mosconi_pr": cf._mosconi}[reader_id]()


def _own_models(cf, reader_id):
    """`[(name, code, checked_model)]`: the models the reader's code knows the channel layout of, as its `describe`
    says them. A model it names with no layout (Helix Dev 22) is one of the `other_models`."""
    own = _module(cf, reader_id)
    if reader_id == "helix_pct6":
        assert set(own.VERIFIED_NAMES) == {m.name for m in own.MODELS if m.verified}, own.VERIFIED_NAMES
        codes = [m.dev for m in own.MODELS]
    else:
        codes = list(own.MODELS)
    out = []
    for code in codes:
        d = own.describe(code)
        if d.get("layout") is not None:
            out.append((d["name"], d["dev"], d["verified"]))
    return out


def _shipped(cf, reader_id):
    """`[(path, model code)]`: every shipped test file of the reader, read by its real reader through compare-file's
    own read; a file it does not read is `(path, None)`."""
    import glob
    tool = os.path.dirname(os.path.realpath(__file__))
    out = []
    for path in sorted(glob.glob(os.path.join(tool, TESTDATA[reader_id]))):
        if reader_id == "helix_pct6":
            code, doc = cf.read_doc(path)
            out.append((path, doc.dev if code == cf.EXIT_COMPARED else None))
        else:
            code, reading = cf.read_pr(path)
            out.append((path, reading["device"]["dev"] if code == cf.EXIT_COMPARED else None))
    return out


def _probe_other(cf, reader_id, outside):
    """`{read, checked_model, channels_mapped}` for a model of the family outside the registry: a shipped file made to
    name the code `outside`, compared through compare-file's real path with a one-row version. Mosconi: a temp copy of
    the shipped `.PR15` named `.PR<outside>`, through the gate (`compare_journal`). Helix: the shipped `.pct6` read by
    `read_doc` and its `Dev` set to `outside` on the parsed root in memory, then `compare_doc` -- no `.pct6` is
    written: the method has no encoder."""
    import glob
    import shutil
    import tempfile
    tool = os.path.dirname(os.path.realpath(__file__))
    sample = sorted(glob.glob(os.path.join(tool, TESTDATA[reader_id])))[0]
    journal = ({"channels": {"probe": {"gain_db": 0.0}}}, {"probe": {"code": "probe", "slot": "1"}}, {})
    if reader_id == "helix_pct6":
        code, doc = cf.read_doc(sample)
        if code == cf.EXIT_COMPARED:
            doc.root.set("Dev", outside)
            code, result = cf.compare_doc(journal, doc, "probe.pct6")
    else:
        top = tempfile.mkdtemp(prefix="readers_probe_")
        try:
            path = os.path.join(top, "probe.PR" + outside)
            shutil.copyfile(sample, path)
            if cf.reader_for(path) != reader_id:
                return {"read": False, "checked_model": False, "channels_mapped": False}
            code, result = cf.compare_journal(journal, path)
        finally:
            shutil.rmtree(top, ignore_errors=True)
    if code != cf.EXIT_COMPARED:
        return {"read": False, "checked_model": False, "channels_mapped": False}
    return {"read": True, "checked_model": result["checked_model"], "channels_mapped": result["device"]["layout"] is not None}


def _bool(value):
    return value is True or value is False


def check(registry):
    """Every way the registry and the code disagree, one string each; `[]` when they agree."""
    cf = _siblings().load("state/compare_file.py")
    tool = os.path.dirname(os.path.realpath(__file__))
    out = []
    if registry.get("contract") != CONTRACT:
        out.append("contract is %r, not %r" % (registry.get("contract"), CONTRACT))
    readers = registry.get("readers") if isinstance(registry.get("readers"), list) else []
    ids = [r.get("id") for r in readers if isinstance(r, dict)]
    for rid in sorted(set(ids)):
        if ids.count(rid) > 1:
            out.append("%s is listed %d times" % (rid, ids.count(rid)))
    for rid in sorted(set(cf.READERS) - set(ids)):
        out.append("%s: a reader the gate dispatches to is not listed" % rid)
    outside_all = "probe.no-reader-reads-this"
    for verb in cf.FILE_VERBS:
        if cf.reader_for(outside_all, verb) is not None:
            out.append("%s reads %s, a name no pattern matches" % (verb, outside_all))
    for r in readers:
        if not isinstance(r, dict):
            out.append("a reader entry is no object: %r" % (r,))
            continue
        rid = r.get("id")
        if sorted(r) != sorted(_KEYS):
            out.append("%s: keys %s, not %s" % (rid, sorted(r), sorted(_KEYS)))
            continue
        if rid not in cf.READERS or rid not in TESTDATA:
            out.append("%s: no reader of that id is dispatched to" % rid)
            continue
        own = _module(cf, rid)
        module = os.path.join(os.path.dirname(tool), r["module"])
        if os.path.basename(os.path.dirname(module)) != "rew_tool" or not os.path.exists(module) or \
                os.path.splitext(os.path.basename(module))[0] != rid:
            out.append("%s: module %r is not this reader's" % (rid, r["module"]))
        family = own.VENDOR if rid == "helix_pct6" else own.DEVICE["vendor"]
        if r["family"] != family:
            out.append("%s: family %r, the reader's is %r" % (rid, r["family"], family))
        if r["model_code"] != own.MODEL_CODE:
            out.append("%s: model_code %r, the reader's is %r" % (rid, r["model_code"], own.MODEL_CODE))
        if r["pattern"] != cf.READERS[rid]:
            out.append("%s: pattern %r, the gate's is %r" % (rid, r["pattern"], cf.READERS[rid]))
        verbs = r["verbs"] if isinstance(r["verbs"], list) else []
        strange = [v for v in verbs if v not in cf.FILE_VERBS]
        if strange or not isinstance(r["verbs"], list):
            out.append("%s: %s no verb that reads a file (%s)" % (rid, strange or r["verbs"], list(cf.FILE_VERBS)))
        for verb in sorted({v for v in verbs if isinstance(v, str) and verbs.count(v) > 1}):
            out.append("%s: the verb %r is listed %d times" % (rid, verb, verbs.count(verb)))
        models = [m for m in r["models"] if isinstance(m, dict)] if isinstance(r["models"], list) else []
        if not isinstance(r["models"], list) or len(models) != len(r["models"]):
            out.append("%s: models %r hold an entry that is no object" % (rid, r["models"]))
        for m in models:
            if not (isinstance(m.get("name"), str) and isinstance(m.get("code"), str) and _bool(m.get("checked_model"))
                    and sorted(m) == ["checked_model", "code", "name"]):
                out.append("%s: model %r is not {name: str, code: str, checked_model: bool}" % (rid, m))
        codes = [m.get("code") for m in models]
        shipped = _shipped(cf, rid)
        if not shipped:
            out.append("%s: no shipped test file to read (%s)" % (rid, TESTDATA[rid]))
        for path, code in shipped:
            name = os.path.basename(path)
            for verb in cf.FILE_VERBS:
                got = cf.reader_for(path, verb)
                if (got == rid) != (verb in verbs):
                    out.append("%s: %s reads %s with %s, the registry says %s" % (
                        rid, verb, name, got, "it does" if verb in verbs else "it does not"))
            if code is None:
                out.append("%s: its reader does not read the shipped %s" % (rid, name))
            elif code not in codes:
                out.append("%s: the shipped %s is model %s, not one the registry lists" % (rid, name, code))
        listed = sorted((m.get("name"), m.get("code"), m.get("checked_model")) for m in models)
        mine = sorted(_own_models(cf, rid))
        if listed != mine:
            out.append("%s: models %s, the reader's are %s" % (rid, listed, mine))
        outside = next(str(n) for n in range(77, 1000) if str(n) not in codes and own.describe(str(n))["name"] is None)
        said = _probe_other(cf, rid, outside)
        other = r["other_models"] if isinstance(r["other_models"], dict) else {}
        if other != said or not all(_bool(v) for v in other.values()):
            out.append("%s: other_models %s; read with model %s, the reader gives %s" % (rid, r["other_models"],
                                                                                         outside, said))
    return out


def _check_the_tree():
    problems = check(load())
    assert not problems, "\n".join(problems)


def _check_planted_lines_fail():
    """Each wrong line is caught: a verb the gate does not have, a verb dropped, an extension, a model, a code, a
    reader listed twice or not at all, a reader the code does not have."""
    import copy
    tree = load()

    def planted(edit):
        reg = copy.deepcopy(tree)
        edit(reg)
        return check(reg)
    mosconi = next(i for i, r in enumerate(tree["readers"]) if r["id"] == "mosconi_pr")
    helix = next(i for i, r in enumerate(tree["readers"]) if r["id"] == "helix_pct6")
    cases = {
        "a verb that is none": lambda g: g["readers"][mosconi]["verbs"].append("export --to-file"),
        "a verb dropped": lambda g: g["readers"][mosconi]["verbs"].remove("propose --from-file"),
        "an extension": lambda g: g["readers"][mosconi].update(pattern=".PRX"),
        "the other extension": lambda g: g["readers"][helix].update(pattern=".pct7"),
        "a model added": lambda g: g["readers"][helix]["models"].append(
            {"name": "HELIX DSP PRO MK3", "code": "23", "checked_model": True}),
        "a model's code": lambda g: g["readers"][mosconi]["models"][0].update(code="16"),
        "a model's check": lambda g: g["readers"][mosconi]["models"][0].update(checked_model=True),
        "other models refused": lambda g: g["readers"][helix]["other_models"].update(read=False),
        "listed twice": lambda g: g["readers"].append(copy.deepcopy(g["readers"][helix])),
        "not listed": lambda g: g["readers"].pop(mosconi),
        "a reader the code does not have": lambda g: g["readers"].append(dict(g["readers"][helix], id="musway_m6")),
        "a key missing": lambda g: g["readers"][helix].pop("family"),
    }
    cases.update({
        "a model entry that is no object": lambda g: g["readers"][helix]["models"].append("HELIX DSP PRO MK3"),
        "a verb twice": lambda g: g["readers"][mosconi]["verbs"].append("compare-file"),
        "a family": lambda g: g["readers"][mosconi].update(family="Gladen"),
        "a model_code": lambda g: g["readers"][helix].update(model_code="extension"),
        "a code that is no string": lambda g: g["readers"][mosconi]["models"][0].update(code=15),
        "a checked_model that is no bool": lambda g: g["readers"][helix]["models"][0].update(checked_model=1),
        "other models' flag no bool": lambda g: g["readers"][helix]["other_models"].update(checked_model=0),
    })
    for what, edit in cases.items():
        assert planted(edit), "a planted line passed: %s" % what


def _check_planted_code_fails():
    """The code changed under a registry that stays: each is caught by reading, not by a constant -- the Mosconi reader
    refusing another model again, the Helix path refusing an unknown Dev, a pattern wrong in both the gate's table and
    the registry, a reader the gate dispatches to that the registry does not list."""
    cf = _siblings().load("state/compare_file.py")
    mp, tree = cf._mosconi(), load()
    real_read, real_doc, real_readers = mp.read_pr, cf.compare_doc, dict(cf.READERS)

    def refuse_other(path):
        if model_of_probe(path) != mp.DEVICE["dev"]:
            raise mp.PrError("model", "only .PR15 is read")
        return real_read(path)

    def model_of_probe(path):
        return mp.model_of(path)

    def refuse_unknown_dev(journal, doc, name, inv=None):
        if cf._helix().models.lookup(doc.dev) is None:
            return cf.EXIT_UNREADABLE, cf.refusal(cf._helix().WARNING, name, "model", "an unknown Dev")
        return real_doc(journal, doc, name, inv=inv)
    wrong_both = dict(tree, readers=[dict(r, pattern=".pct") if r["id"] == "helix_pct6" else r for r in tree["readers"]])
    cases = (("the Mosconi reader refuses another model", lambda: setattr(mp, "read_pr", refuse_other), tree),
             ("the Helix path refuses an unknown Dev", lambda: setattr(cf, "compare_doc", refuse_unknown_dev), tree),
             ("a pattern wrong in both", lambda: cf.READERS.update(helix_pct6=".pct"), wrong_both),
             ("a reader the gate has and the registry does not", lambda: cf.READERS.update(musway_m6=".m6v"), tree))
    try:
        for what, patch, registry in cases:
            patch()
            try:
                assert check(registry), "planted code passed: %s" % what
            finally:
                mp.read_pr, cf.compare_doc = real_read, real_doc
                cf.READERS.clear()
                cf.READERS.update(real_readers)
    finally:
        mp.read_pr, cf.compare_doc = real_read, real_doc
        cf.READERS.clear()
        cf.READERS.update(real_readers)


def _selftest():
    failures = []
    for c in (_check_the_tree, _check_planted_lines_fail, _check_planted_code_fails):
        try:
            c()
        except Exception as exc:  # noqa: BLE001 -- every failure is reported
            failures.append("%s: %s: %s" % (c.__name__, type(exc).__name__, exc))
    for line in failures:
        print("FAIL " + line)
    if failures:
        return 1
    print("readers selftest OK -- %s holds against the readers' code, and every planted wrong line fails"
          % os.path.relpath(REGISTRY, os.path.dirname(os.path.dirname(os.path.dirname(REGISTRY)))))
    return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()
    registry = load()
    if "--json" in argv:
        print(json.dumps(registry, indent=2, ensure_ascii=False))
        return 0
    for r in registry["readers"]:
        print("%s %s (%s): %s; models %s; other models %s" % (
            r["family"], r["pattern"], r["module"], ", ".join(r["verbs"]),
            ", ".join("%s (%s)" % (m["name"], m["code"]) for m in r["models"]),
            "read, not checked" if r["other_models"]["read"] else "refused"))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    sys.exit(main(sys.argv[1:]))
