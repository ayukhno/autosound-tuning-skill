#!/usr/bin/env python3
"""readers -- the DSP saved-file readers the method declares, held to their own code (hub #350, CONTRACT.md item 15).

    python3 rew_tool/readers.py              one line a reader: family, file, verbs, models
    python3 rew_tool/readers.py --json       the registry as stored (`knowledge/dsp/readers.json`, `readers.v1`)
    python3 rew_tool/readers.py --selftest   the registry against the code; planted wrong lines must fail

The registry is what a front end turns its buttons on by. `check` holds it to the code both ways, so it cannot drift:

* every reader the verbs dispatch to (`compare_file.READERS`) is listed once, and no other;
* a reader's `pattern` is the one the gate matches for it (`compare_file.READERS`), and the gate
  (`compare_file.reader_for`, which compare-file, attest --from-file and propose --from-file call) gives that reader
  for a file of the pattern under exactly the listed `verbs` (`compare_file.FILE_VERBS`);
* its `models` are the reader's own with a channel layout -- `helix_pct6.models.MODELS`, `mosconi_pr.DEVICE` --
  each named and coded as compare-file's `device` says it, with its `checked_model`;
* `other_models`: a code outside the list is described by the reader as compare-file reports it.
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


def _describe(cf, reader_id, code):
    """compare-file's `device` name, `verified` and `layout` for a model code of a reader, from the reader's code."""
    if reader_id == "helix_pct6":
        d = cf._helix().models.describe(code)
        return d.get("name"), bool(d.get("verified")), d.get("layout")
    if reader_id == "mosconi_pr":
        d = cf._mosconi().describe(code)
        return d.get("name"), bool(d.get("verified")), d.get("layout")
    raise KeyError(reader_id)


def _own_models(cf, reader_id):
    """`[(name, code, checked_model)]`: the models a reader's own code knows the channels of -- a layout. A model it
    names with no layout (Helix Dev 22) is one of the `other_models`: read with the warning, no channel mapped."""
    if reader_id == "helix_pct6":
        models = cf._helix().models
        assert set(models.VERIFIED_NAMES) == {m.name for m in models.MODELS if m.verified}, models.VERIFIED_NAMES
        return [(m.name, m.dev, bool(m.verified)) for m in models.MODELS
                if _describe(cf, reader_id, m.dev)[2] is not None]
    if reader_id == "mosconi_pr":
        mp = cf._mosconi()
        name, verified, _layout = _describe(cf, reader_id, mp.DEVICE["dev"])
        return [(name, mp.DEVICE["dev"], verified)]
    raise KeyError(reader_id)


def _names(pattern, codes):
    """Probe file names for a pattern: the literal one, or `<n>` filled with each code and one code outside them."""
    if "<n>" not in pattern:
        return ["probe" + pattern]
    outside = next(str(n) for n in range(99, 1000) if str(n) not in codes)
    return ["probe" + pattern.replace("<n>", c) for c in list(codes) + [outside]]


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
        out.append("%s: a reader the verbs dispatch to is not listed" % rid)
    for r in readers:
        if not isinstance(r, dict):
            out.append("a reader entry is no object: %r" % (r,))
            continue
        rid = r.get("id")
        if sorted(r) != sorted(_KEYS):
            out.append("%s: keys %s, not %s" % (rid, sorted(r), sorted(_KEYS)))
            continue
        if rid not in cf.READERS:
            out.append("%s: no reader of that id is dispatched to" % rid)
            continue
        module = os.path.join(os.path.dirname(tool), r["module"])
        if os.path.basename(os.path.dirname(module)) != "rew_tool" or not os.path.exists(module) or \
                os.path.splitext(os.path.basename(module))[0] != rid:
            out.append("%s: module %r is not this reader's" % (rid, r["module"]))
        if r["pattern"] != cf.READERS[rid]:
            out.append("%s: pattern %r, the gate's is %r" % (rid, r["pattern"], cf.READERS[rid]))
        strange = [v for v in r["verbs"] if v not in cf.FILE_VERBS]
        if strange:
            out.append("%s: %s no verb that reads a file (%s)" % (rid, strange, list(cf.FILE_VERBS)))
        codes = [str(m.get("code")) for m in r["models"] if isinstance(m, dict)]
        for verb in cf.FILE_VERBS:
            for probe in _names(r["pattern"], codes):
                got = cf.reader_for(probe, verb)
                if (got == rid) != (verb in r["verbs"]):
                    out.append("%s: %s reads %s with %s, the registry says %s" % (
                        rid, verb, probe, got, "it does" if verb in r["verbs"] else "it does not"))
        listed = sorted((m.get("name"), str(m.get("code")), m.get("checked_model")) for m in r["models"]
                        if isinstance(m, dict))
        own = sorted(_own_models(cf, rid))
        if listed != own:
            out.append("%s: models %s, the reader's are %s" % (rid, listed, own))
        for name, code, _checked in own:
            if _describe(cf, rid, code)[2] is None:
                out.append("%s: model %s has no channel layout in the reader" % (rid, code))
        outside = next(str(n) for n in range(77, 1000) if str(n) not in codes)
        name, verified, layout = _describe(cf, rid, outside)
        said = {"read": True, "checked_model": verified, "channels_mapped": layout is not None}
        if r["other_models"] != said or name is not None:
            out.append("%s: other_models %s, the reader says %s for code %s" % (rid, r["other_models"], said, outside))
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
    for what, edit in cases.items():
        assert planted(edit), "a planted line passed: %s" % what


def _selftest():
    failures = []
    for c in (_check_the_tree, _check_planted_lines_fail):
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
    sys.exit(main(sys.argv[1:]))
