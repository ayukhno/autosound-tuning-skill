#!/usr/bin/env python3
"""What `rew-tool-docs.md` says about each module, checked against the module.

Two claims are checkable without running anything, and both have been wrong in this file:

* **What it needs to run.** The file opened with "uses standard library only — no external
  dependencies" while 21 of 54 modules import numpy and four of those also scipy. A reader who
  believes that line installs on a bare python and meets an ImportError at the first useful step.
  Per-module claims are checked against the module's actual imports, and a module whose entry says
  nothing is reported so the claim can be added rather than guessed at.
* **The flags in its own command line.** A flag written inside a module's own backticked command
  must exist in that module. Flags named in prose ABOUT another tool are left alone — an entry may
  legitimately mention `analyze-joints --process` while describing something else.

  tool-docs-check.py            # report
  tool-docs-check.py --selftest

stdlib only (and this one is checked by its own rule).
"""
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SKILL = os.path.join(REPO, "skills", "autosound-tuning")
DOC = os.path.join(SKILL, "references", "tooling", "rew-tool-docs.md")

ENTRY = re.compile(r"^\* \*\*`(rew_tool/[\w/]+\.py)`\*\*(.*)$", re.M)
IMPORT = re.compile(r"^\s*(?:import|from)\s+(numpy|scipy)\b", re.M)
# A module's own imports are not the whole answer: `predict.py` imports numpy and reaches scipy
# THROUGH `dsp_math`. What a reader needs is what must be INSTALLED, so local imports are followed.
# Imports at ANY level count, here and through the local modules this one pulls in. The question a
# dependency line answers is "will this run on my python", and a lazy import inside the function
# that does the work is still something that has to be installed. `dsp_math` reaches scipy exactly
# that way, and its "numpy + scipy" is right.
LOCAL = re.compile(r"^\s*(?:from\s+([a-z_][\w.]*)\s+import|import\s+([a-z_][\w.]*))", re.M)
BACKTICK = re.compile(r"`([^`]+)`")
FLAG = re.compile(r"(--[a-z][\w-]*)")


MODULE_DIRS = [os.path.join(SKILL, "rew_tool"), os.path.join(SKILL, "rew_tool", "state"),
               os.path.join(SKILL, "rew_tool", "gates")]


def _local_path(name):
    for d in MODULE_DIRS:
        cand = os.path.join(d, name.split(".")[0] + ".py")
        if os.path.isfile(cand):
            return cand
    return None


def _needs(path, seen):
    """Every third-party package this module needs, its own and its neighbours'."""
    if path in seen:
        return set()
    seen.add(path)
    src = io.open(path, encoding="utf-8", errors="replace").read()
    found = set(IMPORT.findall(src))
    for a, b in LOCAL.findall(src):
        nxt = _local_path(a or b)
        if nxt:
            found |= _needs(nxt, seen)
    return found


def deps_of(module_rel):
    """('numpy + scipy' | 'numpy' | 'stdlib only') — what must be INSTALLED to run it."""
    path = os.path.join(SKILL, module_rel)
    if not os.path.isfile(path):
        return None
    found = _needs(path, set())
    if "scipy" in found:
        return "numpy + scipy"
    if "numpy" in found:
        return "numpy"
    return "stdlib only"


def claim_in(body):
    """What the entry SAYS it needs, or None."""
    low = body.lower()
    if "numpy + scipy" in low or ("numpy" in low and "scipy" in low):
        return "numpy + scipy"
    if "scipy" in low:
        return "numpy + scipy"          # scipy without numpy is not a thing here
    if "numpy" in low:
        return "numpy"
    if "stdlib" in low:
        return "stdlib only"
    return None


def entries(text=None):
    text = io.open(DOC, encoding="utf-8").read() if text is None else text
    return ENTRY.findall(text)


def check(text=None):
    """(problems, missing) — a wrong claim is a problem; an absent one is a gap."""
    problems, missing = [], []
    for module, body in entries(text):
        real = deps_of(module)
        if real is None:
            problems.append(f"{module}: named in the index, no such file")
            continue
        said = claim_in(body)
        if said is None:
            missing.append(module)
        elif said != real:
            problems.append(f"{module}: the entry says {said!r}, the imports say {real!r}")
        name = os.path.basename(module)
        src = io.open(os.path.join(SKILL, module), encoding="utf-8", errors="replace").read()
        for token in BACKTICK.findall(body):
            token = token.strip()
            if not (token.startswith(name) or token.startswith(module)):
                continue                      # prose about another tool keeps its own flags
            for flag in FLAG.findall(token):
                if flag not in src:
                    problems.append(f"{module}: its own command line names {flag}, "
                                    f"which is not in the module")
    return problems, missing


def fill():
    """Write the true dependency word into every entry that carries none."""
    text = io.open(DOC, encoding="utf-8").read()
    _, missing = check(text)
    for module in missing:
        real = deps_of(module)
        for line in text.splitlines():
            m = ENTRY.match(line)
            if m and m.group(1) == module:
                text = text.replace(line, line.rstrip() + f" **Needs: {real}.**", 1)
                break
    io.open(DOC, "w", encoding="utf-8").write(text)
    return len(missing)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fill", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.fill:
        n = fill()
        print(f"{n} entr(ies) given their true dependency line")
        return 0
    problems, missing = check()
    for p in problems:
        print(p)
    print(f"\n{len(entries())} module entries · {len(problems)} wrong · "
          f"{len(missing)} without a dependency line"
          + (f" ({', '.join(os.path.basename(m) for m in missing[:6])}…)" if missing else ""))
    return 1 if problems else 0


def selftest():
    # the real tree: the reader of this rule is the file it guards
    assert deps_of("rew_tool/predict.py") == "numpy + scipy", deps_of("rew_tool/predict.py")
    assert deps_of("rew_tool/naming.py") == "stdlib only", deps_of("rew_tool/naming.py")
    # transitive: it imports numpy itself and reaches scipy through `protective`/`dsp_math`
    assert deps_of("rew_tool/resonalyze_ir.py") == "numpy + scipy", deps_of("rew_tool/resonalyze_ir.py")
    assert deps_of("rew_tool/no_such.py") is None
    assert claim_in("… stdlib only. `--selftest`") == "stdlib only"
    assert claim_in("… numpy + scipy.") == "numpy + scipy"
    assert claim_in("… nothing said …") is None
    # a wrong claim is caught, and a flag from prose about another tool is not
    fake = ("* **`rew_tool/naming.py`** — the names. numpy. `naming.py --nope`\n"
            "* **`rew_tool/predict.py`** — reads `analyze-joints --process` too. numpy + scipy.\n")
    problems, missing = check(fake)
    assert any("the entry says 'numpy', the imports say 'stdlib only'" in p for p in problems), problems
    assert any("--nope" in p for p in problems), problems
    assert not any("predict.py" in p for p in problems), problems
    assert missing == [], missing
    print("selftest OK — a dependency claim is read off the module's own imports (a wrong one is "
          "named, an absent one counted), and a flag is checked only inside the module's OWN "
          "command line, so prose about a neighbouring tool is left alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
