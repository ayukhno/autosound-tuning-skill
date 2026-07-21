#!/usr/bin/env python3
"""smoke_test.py — post-install / post-pull health check for the autosound-tuning skill.

Run this after `git clone`, `git pull`, a plugin update, or on a fresh machine (Windows/macOS/Linux)
to confirm the DETERMINISTIC tooling works here — the issue-#5 multi-slot state integrity, the
apply-change gate, and the side-effect / pre-sweep gates. Offline + stdlib-only, so it's safe to run
anywhere; the reviewer channel (CLI / API key) is reported as INFO and never fails the smoke.

    python skills/autosound-tuning/scripts/smoke_test.py     # exit 0 = healthy, 1 = a check broke

Set SMOKE_VERBOSE=1 for full tracebacks on failure.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import traceback

# Windows consoles often default to cp1252, which can't encode the ✓/✗ markers below — same fix
# already used in autosound_ai.py / issue_triage.py.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)                              # …/skills/autosound-tuning
for _p in (os.path.join(SKILL, "rew_tool"),
           os.path.join(SKILL, "rew_tool", "state"),
           os.path.join(SKILL, "rew_tool", "gates")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_results = []


def _quiet(fn):
    """Run fn with its (verbose) stdout+stderr swallowed — the smoke test prints its own ✓/✗."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn()


def check(name, fn):
    try:
        fn()
        _results.append((True, name))
        print(f"  ✓ {name}")
    except Exception as e:                                 # noqa: BLE001 — a smoke test reports, never crashes
        _results.append((False, name))
        print(f"  ✗ {name} — {e}")
        if os.environ.get("SMOKE_VERBOSE"):
            traceback.print_exc()


def _state_selftest():
    import state
    assert _quiet(state._selftest) == 0, "state.py selftest returned non-zero"


def _apply_selftest():
    import apply
    assert _quiet(apply._selftest) == 0, "apply.py selftest returned non-zero"


def _issue5_scenario():
    """The real issue-#5 incident, end-to-end: active slot = SQ-Comp-Ref, a change aimed at the
    ResoNix slot must be REFUSED (you can't compute filters off a neighbour slot's baseline)."""
    import apply
    import state
    root = tempfile.mkdtemp(prefix="autosound_smoke_")
    state.PresetHistory(root, "SQ_Comp_Ref").snapshot(state._sample_state(), note="emma")
    reso = state.PresetHistory(root, "ResoNix")
    reso.snapshot(state._sample_state(), note="reso")
    reg = state.Registry(root)
    reg.set_active("SQ_Comp_Ref")
    banner = reg.render()
    assert "ACTIVE SLOT IN THE DSP:** `SQ_Comp_Ref`" in banner, "active-slot banner missing/wrong"
    try:
        apply.propose(reso, {"tw-L": {"gain_db": -8.0}}, registry=reg)   # aimed at the NON-active slot
        raise AssertionError("gate did NOT refuse a cross-slot proposal")
    except ValueError as e:
        assert "SLOT MISMATCH" in str(e), f"unexpected refusal reason: {e}"


def _gates_selftest():
    import side_effect
    if hasattr(side_effect, "_selftest"):
        _quiet(side_effect._selftest)
    import presweep_safety
    if hasattr(presweep_safety, "_selftest"):
        _quiet(presweep_safety._selftest)


def _rew_tool_selftest():
    """get_fr's phase-present (sweep) vs phase-absent (RTA) branch + the FR
    analysis magnitude-only path. The RTA branch used to KeyError silently
    because no test drove it (rew-api-quirks.md 'Timing') — cover it here so a
    post-pull smoke catches a regression even with no live measurement."""
    import rew_api
    import analysis
    _quiet(rew_api._selftest)
    _quiet(analysis._selftest)


def main():
    print("=== autosound-tuning smoke test ===")
    print(f"python {sys.version.split()[0]} · {sys.platform} · skill={SKILL}")

    print("\n[core tooling — deterministic, offline]")
    check("state.py selftest (versioned hard-params state)", _state_selftest)
    check("apply.py selftest (apply-change gate)", _apply_selftest)
    check("issue #5 (active=SQ-Comp-Ref → propose to ResoNix REFUSED)", _issue5_scenario)
    check("gates selftest (side_effect + presweep_safety)", _gates_selftest)
    check("rew_tool selftest (get_fr RTA/sweep phase branch + FR analysis)", _rew_tool_selftest)

    # reviewer channel — INFO only; machine/project-dependent, never fails the smoke.
    print("\n[reviewer channel — informational]")
    cli = shutil.which("agy") or shutil.which("gemini")
    api = next((k for k in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")
                if os.environ.get(k)), None)
    print(f"  · local CLI : {cli or 'none (agy/gemini not on PATH → Clipboard Mode)'}")
    print(f"  · API key   : {api or 'none (Clipboard Mode fallback)'}")
    if sys.platform == "win32":
        wr = [w for w in ("gemini_critic.cmd", "gemini_advisor.cmd")
              if os.path.isfile(os.path.join(HERE, w))]
        print(f"  · win .cmd wrappers: {', '.join(wr) or 'MISSING ✗'}")

    failed = [n for ok, n in _results if not ok]
    print("\n" + ("=== PASS — core tooling healthy ✓ ===" if not failed
                  else f"=== FAIL — {len(failed)} check(s) broke: {failed} ==="))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
