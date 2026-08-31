#!/usr/bin/env python3
"""bind -- the method hands out its own loader, because a copied loader makes policy in silence.

Eighteen scripts in one project tree open with the same three lines: try a pinned copy of
`rew_tool`, else a personal one, take whichever exists, `sys.path.insert(0, ...)`, import. Those
three lines make TWO decisions and announce neither:

  1. WHICH COPY of the method answers the import. If the pinned one is gone the loop takes the
     next and the run continues at another version. Nothing fails, nothing is printed. The pin
     exists precisely so the method holds still under a run; a fallback that works quietly makes
     the pin optional exactly when it matters.
  2. THE METHOD versus THE PROJECT'S OWN modules. Inserting at position 0 puts the method AHEAD
     of the caller's directory, so a project file with the same name is shadowed. Measured in
     `car/passat-b8-2026` on 2026-08-31: `dsp_math.py`, `curve_view.py`, `eq_gate.py` and
     `xover_select.py` exist in BOTH, all four differ, and the method's copies win. That is the
     same failure a session recorded on 2026-08-22 -- a solver running corrected maths while its
     verifiers ran the broken copy, from this exact ordering. Found twice in nine days by two
     sessions, neither knowing about the other, because nothing said which file answered.

Both are one defect: **the loader was copied instead of called.** The rule of this codebase for
that shape is already written down (autosound-hub `SKL-001`, `RELEASE-CHANNEL.md` §9): the shared
carrier is CALLED, not duplicated. So the method provides the loader and signs what it bound.

WHAT IS REFUSED, AND WHAT IS DELIBERATELY NOT DECIDED

`deployment.py` states the principle this module obeys: *disagreement is refused; ORDER is not
judged*. Which candidate a loader should prefer is not knowable from inside one of them. So this
module never silently reorders and never silently substitutes -- it REFUSES and names both sides,
leaving the choice with whoever declared the candidates.

  * the declared (first) candidate is missing        -> refuse, naming it and what else exists
  * a module name exists in BOTH the caller's dir
    and the bound copy                               -> refuse, naming every collision and both paths
  * nothing exists at all                            -> refuse, naming every path tried
  * `expect=` given and the bound copy disagrees     -> refuse, naming both identities

A refusal names the ways out, because a refusal without a path is a dead end, not a guard
(autosound-hub `HUB-KIT-BRIEF.md` §9.9).

WHAT IT RETURNS: the identity of what was bound -- path, realpath, version, sha -- so a run can
write it beside its numbers instead of recovering it later with `readlink`. `provenance.py`
answers this for an artifact days later; `deployment.py` answers it for a machine's copies; this
answers it for the ONE import that just happened, which is the moment neither of those sees.

THE THREE LINES A CALLER STILL NEEDS, and they must hold no policy:

    import os, sys
    for _p in (PINNED, PERSONAL):                     # the candidates YOU declare, in order
        if os.path.isdir(_p): sys.path.insert(0, _p); break
    import bind; INFO = bind.bind(__file__, (PINNED, PERSONAL))

The stub locates and delegates; it decides nothing. `bind()` then re-does the resolution properly,
corrects `sys.path` to what it decided, and refuses if the stub's guess was the wrong copy.
"""
from __future__ import annotations

import os
import sys

#: Written into the record so a reader knows which loader signed it.
BINDER = "autosound-tuning rew_tool/bind.py"


class BindError(RuntimeError):
    """The import cannot be made unambiguous. Never raised for a difference that does not matter."""


def _identity(path):
    """(version, sha, ref) of the copy at `path`; each None when it cannot be told.

    `describe()` wants the SKILL FOLDER -- `skills/autosound-tuning` -- which is one level above
    `rew_tool`, not two. Getting that wrong does not fail: it walks up to some other repository
    and answers confidently about the wrong checkout (measured while writing this, 2026-08-31 --
    it returned a sha, just not this copy's). A wrong identity is worse than none, so the level
    is spelled out here rather than derived.

    `ref` is carried because it is the field that says HELD STILL versus DRIFTING: a pinned
    checkout answers `v3.0.33`, a moving one `v3.0.37-6-gc7bf84c`.
    """
    version = sha = ref = None
    try:
        sys.path.insert(0, path)
        import deployment  # noqa: PLC0415 -- resolved from the copy we are identifying, on purpose
        desc = deployment.describe(os.path.dirname(os.path.abspath(path)))
        if isinstance(desc, dict):
            version = desc.get("version") or None
            sha = desc.get("sha") or None
            ref = desc.get("ref") or None
    except Exception:                       # noqa: BLE001 -- "cannot be told" is a valid answer here
        pass
    finally:
        if sys.path and sys.path[0] == path:
            sys.path.pop(0)
    return version, sha, ref


def _modules_in(directory):
    try:
        return {n[:-3] for n in os.listdir(directory)
                if n.endswith(".py") and not n.startswith("_")}
    except OSError:
        return set()


def bind(caller_file, candidates, *, expect=None, allow_shadow=(), fallback=False,
         announce=None):
    """Bind ONE copy of the method for `caller_file`, or refuse and say why.

    `candidates` is ordered and the FIRST is the declared one -- the pin. A later candidate is
    taken only with `fallback=True`, and then it is announced, never assumed.

    `expect` may be a version string or a sha (full or a prefix); a bound copy that disagrees is
    refused. `allow_shadow` names modules the caller KNOWS it overrides on purpose.

    `announce` defaults to on when a substitution or an override happened and off otherwise: a
    line that prints on every run is a line nobody reads.
    """
    caller_dir = os.path.dirname(os.path.abspath(caller_file))
    cands = [os.path.abspath(os.path.expanduser(c)) for c in candidates]
    if not cands:
        raise BindError("bind() needs at least one candidate: the copy this run is pinned to.")
    present = [c for c in cands if os.path.isdir(c)]
    if not present:
        raise BindError(
            "no copy of the method was found. Tried, in the order you declared them:\n"
            + "\n".join(f"  {c}" for c in cands)
            + "\n\nRestore the pin, or declare a candidate that exists. Nothing was imported.")

    declared, chosen = cands[0], present[0]
    substituted = chosen != declared
    if substituted and not fallback:
        raise BindError(
            f"the copy this run is pinned to is GONE:\n  {declared}\n\n"
            f"A copy that would have been taken instead:\n  {chosen}\n\n"
            f"Refusing rather than running at another version. The pin exists so the method holds "
            f"still under a run, and a fallback that works quietly makes it optional exactly when "
            f"it matters.\nWays out: restore the pin; or declare the other copy FIRST if it is "
            f"the one you mean; or pass fallback=True to accept the substitution out loud.")

    shadow = (_modules_in(caller_dir) & _modules_in(chosen)) - set(allow_shadow)
    if shadow:
        raise BindError(
            f"{len(shadow)} module name(s) exist in BOTH your directory and the method, so "
            f"`sys.path` order -- not you -- decides which one runs:\n"
            + "\n".join(f"  {m}.py\n     yours:  {os.path.join(caller_dir, m + '.py')}"
                        f"\n     method: {os.path.join(chosen, m + '.py')}"
                        for m in sorted(shadow))
            + "\n\nThis is not hypothetical: a run once computed with one copy and verified with "
              "the other, from exactly this ordering, and both halves looked fine.\nWays out: "
              "rename yours; or import the method's under its own name; or pass "
              f"allow_shadow=({', '.join(repr(m) for m in sorted(shadow))},) to say you override "
              "them on purpose.")

    version, sha, ref = _identity(chosen)
    if expect:
        ok = (expect in (version, ref)) or (sha and str(sha).startswith(str(expect)))
        if not ok:
            raise BindError(
                f"the bound copy is not the one this run expects.\n  expected: {expect}\n"
                f"  bound:    version={version!r} ref={ref!r} sha={sha!r}\n  at:       {chosen}\n\n"
                f"Ways out: point the pin at the expected checkout, or change `expect` if the "
                f"run is meant to move.")

    # sys.path is corrected to what was DECIDED, not left as the stub guessed it.
    while chosen in sys.path:
        sys.path.remove(chosen)
    sys.path.insert(0, chosen)

    record = {"binder": BINDER, "path": chosen, "realpath": os.path.realpath(chosen),
              "declared": declared, "substituted": substituted, "version": version, "sha": sha, "ref": ref,
              "shadow_allowed": sorted(allow_shadow), "caller": os.path.abspath(caller_file)}
    if announce is None:
        announce = substituted or bool(allow_shadow)
    if announce:
        where = record["realpath"]
        print(f"  method bound: {ref or version or 'identity unknown'} at {where}"
              + ("  [SUBSTITUTED for the pin]" if substituted else "")
              + (f"  [overriding {', '.join(record['shadow_allowed'])}]" if allow_shadow else ""),
              file=sys.stderr)
    return record


def _selftest():
    import json, shutil, tempfile
    root = tempfile.mkdtemp()
    try:
        pin = os.path.join(root, "pin"); alt = os.path.join(root, "alt")
        caller = os.path.join(root, "proj")
        for d in (pin, alt, caller):
            os.makedirs(d)
        open(os.path.join(pin, "rew_api.py"), "w").close()
        open(os.path.join(alt, "rew_api.py"), "w").close()
        me = os.path.join(caller, "run.py")
        open(me, "w").close()
        gone = os.path.join(root, "not-here")

        # 1. the declared copy exists -> bound, quietly, and sys.path leads with it
        rec = bind(me, (pin, alt))
        assert rec["path"] == pin and rec["substituted"] is False, rec
        assert sys.path[0] == pin, sys.path[:2]
        # 2. the pin is gone -> REFUSED, and the refusal names the pin and the stand-in
        try:
            bind(me, (gone, alt))
        except BindError as e:
            assert gone in str(e) and alt in str(e) and "pinned" in str(e), str(e)
        else:
            raise AssertionError("a missing pin fell through to the next candidate")
        # 3. ...unless the substitution is asked for OUT LOUD
        rec = bind(me, (gone, alt), fallback=True)
        assert rec["path"] == alt and rec["substituted"] is True
        # 4. a name in both places -> REFUSED, both paths named
        open(os.path.join(caller, "dsp_math.py"), "w").close()
        open(os.path.join(pin, "dsp_math.py"), "w").close()
        try:
            bind(me, (pin, alt))
        except BindError as e:
            assert "dsp_math.py" in str(e) and caller in str(e) and pin in str(e), str(e)
        else:
            raise AssertionError("a shadowed module was bound without a word")
        # 5. ...unless the caller says it overrides it on purpose
        rec = bind(me, (pin, alt), allow_shadow=("dsp_math",))
        assert rec["shadow_allowed"] == ["dsp_math"]
        # 6. nothing exists at all -> refused, every path tried is named
        try:
            bind(me, (gone,))
        except BindError as e:
            assert gone in str(e) and "Nothing was imported" in str(e)
        else:
            raise AssertionError("bound something out of nowhere")
        # 7. an expectation that cannot be met is refused, not warned about
        try:
            bind(me, (pin, alt), allow_shadow=("dsp_math",), expect="v9.9.9")
        except BindError as e:
            assert "v9.9.9" in str(e)
        else:
            raise AssertionError("a copy that is not the expected one was accepted")
        # 8. the record is writable beside a run's numbers
        json.dumps(rec)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("selftest[bind] OK -- a missing pin refuses instead of falling through, a name that "
          "exists in both places refuses instead of letting sys.path decide, both refusals name "
          "the ways out, fallback and override are possible only OUT LOUD, and what was bound "
          "comes back as a record a run can write down.")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv or "selftest" in sys.argv[1:2] else
             (print(__doc__.split("\n\n")[0]) or 0))
