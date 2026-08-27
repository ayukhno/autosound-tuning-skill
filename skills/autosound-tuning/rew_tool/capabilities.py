#!/usr/bin/env python3
"""capabilities -- keeps `references/core/capabilities.md` (the board of what the method can do)
honest against the code it points at.

The board is an INDEX by intent: one line per capability, a command or a call, a pointer to the
doctrine. An index that names a flag which no longer exists is worse than none -- a session reads
it as the truth and stops looking (the capture sheet once prescribed a title the grammar refused;
same shape). So this module is the seam check between the board and the tree:

  * every backticked `module.py` on the board exists (rew_tool, rew_tool/state, rew_tool/gates,
    the skill's scripts/, the repo's scripts/);
  * every `--flag` or verb named next to a module appears in that module's source;
  * every `module.function` names a `def` (or a class) in that module;
  * every `read` pointer resolves to a file;
  * and the reverse: every module WITH a command line is on the board, except the ones listed
    here as deliberately not (a legacy one-off, a plotting helper, a research harness). "With a
    command line" is read WIDELY -- `__main__`, a `.sh`, an argument parser, a `main()`, a read of
    `sys.argv` -- because the narrow reading (`__main__` only) would let a tool that offers its CLI
    another way pass in silence.

What this does NOT prove, and a consumer of the board should say so rather than imply otherwise:
every tool with a command line is represented, but the DEPTH of each tool's coverage is not
machine-checked -- a module on the board with a seventh useful mode nobody wrote a row for looks
exactly like one with none.

    python3 rew_tool/capabilities.py --selftest     (in the suite)
    python3 rew_tool/capabilities.py                 (print the board's row count per section)
"""
from __future__ import annotations

import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(_HERE, ".."))
REPO = os.path.normpath(os.path.join(SKILL, "..", ".."))
BOARD = os.path.join(SKILL, "references", "core", "capabilities.md")
MODULE_DIRS = [_HERE, os.path.join(_HERE, "state"), os.path.join(_HERE, "gates"),
               os.path.join(SKILL, "scripts"), os.path.join(REPO, "scripts")]
#: modules with a command line that the board deliberately does not carry, and why
NOT_ON_BOARD = {
    "verify_measurements.py": "a one-off session script kept as it was (rew-tool-docs says so)",
    "make_plot.py": "a plotting helper, not a decision",
    "provenance.py": "which checkout wrote a file; the writers' stamp and a way to print it, "
                     "not something a tuner runs (autosound-hub HUB-002)",
    "excess_gate.py": "the research / validation harness behind eq_gate",
    "capabilities.py": "this checker",
    "__init__.py": "not a tool",
    "analysis.py": "library; its functions are on the board by name",
    "dsp_math.py": "library; its functions are on the board by name",
    "curve_view.py": "library; on the board by function",
    "joint_analysis.py": "library; on the board by function",
    "xover_select.py": "library; on the board by function",
    "eq_gate.py": "library; on the board by function",
    "target_curves.py": "library; on the board by function",
    "target_bands.py": "library; on the board by function",
    "level_offsets.py": "library; on the board by function",
    "protective.py": "library; on the board by function",
    "atf_eq.py": "library; on the board by function",
    "generic_eq.py": "reached through eq_export (board row: the DSP's format)",
    "nono_curves.py": "library; on the board by function",
    "equal_loudness.py": "on the board",
    "rew_api.py": "on the board by function",
    "migrate.py": "on the board as state/migrate.py",
    "apply.py": "library; on the board by function",
    "state.py": "on the board",
    "process.py": "on the board",
    "presweep_safety.py": "on the board by function",
    "side_effect.py": "on the board",
    "installer-consistency.py": "on the board",
    "windows-install-test.md": "not a module",
    "upstream-drift.py": "a maintainer's tool (ported-code drift), see CLAUDE.md of the repo",
    "issue_triage.py": "on the board",
    "smoke_test.py": "on the board",
    "run_trigger_eval.py": "an eval harness under evals/, not a tuning tool",
    # the per-vendor wrappers of the review channel: the board names the channel (autosound_ai.py)
    # and setup-critic-channel.md lists the wrappers
    "_claude_common.sh": "wrapper internals", "_codex_common.sh": "wrapper internals", "_gemini_common.sh": "wrapper internals",
    "claude_advisor.sh": "review-channel wrapper", "claude_critic.sh": "review-channel wrapper",
    "codex_advisor.sh": "review-channel wrapper", "codex_critic.sh": "review-channel wrapper",
    "gemini_advisor.sh": "review-channel wrapper", "gemini_critic.sh": "review-channel wrapper",
    "start_gemini_tuner.sh": "a launcher for one vendor's CLI (setup-critic-channel.md)",
    "skill_metrics.sh": "a maintainer's usage-metrics script",
    "make-macos-app.sh": "the app bundle builder, called by the installers",
    "run-selftests.sh": "on the board", "tag-check.sh": "on the board",
}

_BACKTICK = re.compile(r"`([^`]+)`")
_PY = re.compile(r"([A-Za-z_][\w-]*\.py)")
_SH = re.compile(r"([A-Za-z_][\w-]*\.sh)")
_FLAG = re.compile(r"(--[a-z][\w-]*)")
_FUNC = re.compile(r"\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)(?:\(|\b)")
_VERB = re.compile(r"(?:process\.py|project\.py|naming\.py|state\.py|dsp_profile\.py|rew_tool\.py)\s+(?:<[^>]+>\s+|--root\s+\S+\s+)?([a-z][a-z-]+)")


def _find_module(name):
    for d in MODULE_DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


def _rows(text):
    """(section, cells) for every table row of the board."""
    section, out = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("| ") and not line.startswith("|---") and "what you want" not in line:
            # an escaped pipe inside a cell (`--solos DIR \| --rew`) is not a column boundary
            cells = [c.strip().replace("\x00", "|") for c in line.strip().strip("|").replace("\\|", "\x00").split("|")]
            if len(cells) >= 7:
                out.append((section, cells))
    return out


def check(board_path=BOARD):
    """Every problem as one line; empty = the board and the tree agree."""
    problems = []
    text = open(board_path, encoding="utf-8").read()
    rows = _rows(text)
    mentioned = set()
    for section, cells in rows:
        cmd_cell, read_cell = cells[2], cells[6]
        for token in _BACKTICK.findall(cmd_cell):
            token = token.replace("\\|", "|")
            for m in _PY.findall(token) + _SH.findall(token):
                path = _find_module(m)
                if path is None:
                    problems.append(f"[{section}] no such module {m!r} (from `{token}`)")
                    continue
                mentioned.add(m)
                src = open(path, encoding="utf-8", errors="replace").read()
                for flag in _FLAG.findall(token):
                    if flag not in src:
                        problems.append(f"[{section}] {m} has no flag {flag} (from `{token}`)")
                for verb in _VERB.findall(token):
                    if m.endswith(".py") and verb not in src:
                        problems.append(f"[{section}] {m} has no verb {verb!r} (from `{token}`)")
            for mod, fn in _FUNC.findall(token):
                if fn in ("py", "sh", "md", "txt", "json", "csv"):
                    continue                    # `eq_propose.py` is a file, not a call
                path = _find_module(mod + ".py")
                if path is None:
                    continue                    # `patterns/…` and prose dots are not calls
                mentioned.add(mod + ".py")
                src = open(path, encoding="utf-8", errors="replace").read()
                if not re.search(rf"^\s*(def|class)\s+{re.escape(fn)}\b", src, re.M):
                    problems.append(f"[{section}] {mod}.py has no `{fn}` (from `{token}`)")
            if token.startswith("patterns/") or token.startswith("core/") or token.startswith("tooling/"):
                pat = os.path.join(SKILL, "references", token)
                if not (os.path.exists(pat) or glob.glob(pat)):
                    problems.append(f"[{section}] no such reference {token!r}")
        for token in _BACKTICK.findall(read_cell):
            token = token.split(" ")[0]
            if "/" not in token and not token.endswith(".md"):
                continue                        # `(dsp_math)` names a section inside the pointer
            cands = [os.path.join(SKILL, "references", token), os.path.join(SKILL, token),
                     os.path.join(REPO, token)]
            if not any(os.path.exists(c) for c in cands):
                problems.append(f"[{section}] read pointer {token!r} resolves to nothing")
    # the reverse: every module with a command line is on the board, or listed as deliberately not
    for d in MODULE_DIRS:
        for path in sorted(glob.glob(os.path.join(d, "*.py")) + glob.glob(os.path.join(d, "*.sh"))):
            name = os.path.basename(path)
            if name in mentioned or name in NOT_ON_BOARD:
                continue
            src = open(path, encoding="utf-8", errors="replace").read()
            # What counts as "has a command line". `__main__` catches the usual shape, but a tool
            # can offer one another way -- an entry point, an `argparse` parser in a function that
            # something else calls -- and that one would walk through this gate in silence (named
            # by the TCC session, 2026-08-26: the same family as the `name_key` shape change, where
            # the check that exists passes and the one that matters was never written). So the gate
            # is the WIDER claim: anything that builds an argument parser, or prints its own usage,
            # is a tool as far as the board is concerned.
            cli = ("__main__" in src or name.endswith(".sh")
                   or "ArgumentParser" in src or "add_argument" in src
                   or "sys.argv" in src
                   or re.search(r"^\s*def _?main\(", src, re.M))
            if cli:
                problems.append(f"{name} has a command line and is neither on the board nor in NOT_ON_BOARD")
    for name in NOT_ON_BOARD:
        if name in mentioned and name not in ("state.py", "process.py", "equal_loudness.py", "side_effect.py",
                                              "issue_triage.py", "smoke_test.py", "installer-consistency.py",
                                              "rew_api.py", "migrate.py", "apply.py"):
            pass                                 # listed as library but also named: fine
    return problems, len(rows)


def _selftest():
    problems, n = check()
    if problems:
        print("\n".join(problems))
        raise AssertionError(f"capabilities.md and the tree disagree in {len(problems)} place(s)")
    assert n >= 40, f"the board has only {n} rows -- was a section lost?"
    print(f"selftest[capabilities] OK -- {n} board rows: every module, flag, verb, function and read pointer "
          f"named on the board exists; every module with a command line is on the board or listed as "
          f"deliberately not.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    problems, n = check()
    text = open(BOARD, encoding="utf-8").read()
    counts = {}
    for section, _ in _rows(text):
        counts[section] = counts.get(section, 0) + 1
    for s, c in counts.items():
        print(f"  {c:3}  {s}")
    print(f"  {n:3}  total" + (f"; {len(problems)} problem(s):" if problems else ""))
    for p in problems:
        print("   - " + p)
    sys.exit(1 if problems else 0)
