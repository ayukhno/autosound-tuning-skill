#!/usr/bin/env python3
"""What a session READS in each phase, in tokens -- and a check that it does not grow (#145, audit I-18).

Each phase is a session of its own after a `/clear` (SKILL.md's Phase Sliding Window), so what a phase reads is paid
again in every phase. Per phase, this counts what the text tells a session to read: SKILL.md; the active phase's file;
the next phase's file -- whole, or to the end of its `## 🎯 Goal-node` section once SKILL.md's Phase Sliding Window
says the next phase is read that far; and the files the phase's own text orders read (the October audit's §3.2 model:
an explicit "read", "alongside", "follow", an entry condition -- a routed `see …` is not counted). Tokens are
characters / 4, the audit's unit. The audit measured ≈ 307K tokens over a full tune on 2026-10-04, 18-54 % more per
phase than four weeks before, and nothing kept the number from growing.

  scripts/reading-cost.py                    the table
  scripts/reading-cost.py --check            exit 1 when a phase reads more than scripts/reading-cost-baseline.json
  scripts/reading-cost.py --write-baseline   today's table into the baseline: a deliberate act, seen in its diff
  scripts/reading-cost.py --selftest         the mechanics, on throwaway trees

A file the model names that is gone fails every mode, naming it: a renamed file read as nothing would pass any budget.
A file renamed or a phase's reading changed is a change to `ORDERED` below, made in the same commit.
Exit codes: 0 done · 1 over the baseline, no baseline, or a file gone · 2 usage · 70 a bug (traceback on stderr).
stdlib only.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILL = os.path.join("skills", "autosound-tuning")
BASELINE = os.path.join("scripts", "reading-cost-baseline.json")

#: The phases in their order, and each one's file under `references/phases/`.
PHASES = ("-1", "0", "1", "2", "3", "4", "5")
PHASE_FILE = {"-1": "phase_-1_intake.md", "0": "phase_0_baseline.md", "1": "phase_1_foundation.md",
              "2": "phase_2_eq.md", "3": "phase_3_control.md", "4": "phase_4_listening.md",
              "5": "phase_5_variations.md"}
_VF, _SHEET = "references/phases/virtual-first.md", "references/phases/capture-session-sheet.md"
_INTAKE, _NAMING = "references/core/project-intake.md", "references/core/naming-and-structure.md"
_REVIEW, _PLAYBOOK = "references/core/review-loop.md", "references/core/analysis-playbook.md"
_DIAG, _CHEAT = "references/core/diagnostic-techniques.md", "references/patterns/listening-cheat-sheet.md"
_TRACKS = "references/patterns/test-tracks.md"
#: What each phase's text orders read besides SKILL.md, its own file and the next phase's: the audit's §3.2 table, by
#: the order that put each file there. A path under the skill is read whole; (path, heading) is that section only.
ORDERED = {
    "-1": [_INTAKE,                                       # "this whole file + Phase 0"
           _VF, _SHEET,                                   # the −1.4 preparation
           "references/tooling/setup-critic-channel.md",  # step 2, the reviewer channel
           _NAMING,                                       # the step-5 gate, §3, §1a
           _REVIEW,                                       # "read it before the first review round"
           "knowledge/dsp/helix-dsp-ultra-s.md"],         # the DSP's file, "LOOK HERE FIRST" (a Helix, as measured)
    "0": [_VF, _SHEET,                                    # "Read … alongside"; the capture recipe
          _NAMING,                                        # "Follow"
          (_INTAKE, "## 3.")],                            # install verification
    "1": [_VF,                                            # "alongside"
          (_INTAKE, "## 3."),                             # the entry gate
          "references/tooling/rew-api-quirks.md",         # "Read … 'Timing'"
          "references/core/filter-types-car-audio.md"],   # "refer to"
    "2": [_VF, _DIAG,                                     # "alongside"; §13, §3, §9 of a file with no index
          _CHEAT,                                         # the listening protocol
          _PLAYBOOK],
    "3": [_VF, _REVIEW,                                   # the verdicts
          _PLAYBOOK,                                      # "method in"
          _TRACKS],
    "4": [_CHEAT, _TRACKS,                                # "read them"
          "references/core/feedback-loop.md",             # the close
          "references/patterns/staging-depth.md",
          _PLAYBOOK],
    "5": ["references/patterns/voicing-by-ear.md",        # "refer to"
          "references/core/preference-profile.md",
          "references/core/preset-strategy.md",
          _DIAG],                                         # one § of it
}
GOAL_NODE = "## 🎯 Goal-node"
#: SKILL.md's section that says how far the next phase is read; naming the Goal-node there turns the partial read on.
WINDOW = "Phase Sliding Window"


class Gone(Exception):
    """Files the model reads that are not there, or a heading it reads to that is not -- each named."""


#: A fenced code block: a `## ` inside one is code, not a heading.
_FENCED = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1", re.S | re.M)


def _masked(text: str) -> str:
    """`text` with its fenced blocks blanked, the length and the line breaks kept: a position is still a position."""
    return _FENCED.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def _span(text: str, heading: str):
    """[start, end) of the section whose heading line starts with `heading`, to the next heading of its level or
    higher; None when no heading line starts so."""
    masked = _masked(text)
    level = len(heading) - len(heading.lstrip("#"))
    head = re.search("^" + re.escape(heading) + "[^\n]*$", masked, re.M)
    if head is None:
        return None
    end = re.compile(r"^#{1,%d} " % level, re.M).search(masked, head.end())
    return head.start(), (end.start() if end else len(text))


def _next_to_goal_node(skill_md: str) -> bool:
    """Whether SKILL.md's Phase Sliding Window names the Goal-node -- the rule that the next phase is read to it."""
    masked = _masked(skill_md)
    head = re.search(r"^(#{1,6}) [^\n]*" + re.escape(WINDOW) + "[^\n]*$", masked, re.M)
    if head is None:
        return False
    end = re.compile(r"^#{1,%d} " % len(head.group(1)), re.M).search(masked, head.end())
    return "Goal-node" in skill_md[head.end():end.start() if end else len(skill_md)]


def _phases(names: list) -> str:
    return ("phase " if len(names) == 1 else "phases ") + ", ".join(names)


def _read(root: str, rel: str) -> str | None:
    path = os.path.join(root, SKILL, rel)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def table(root: str) -> dict:
    """{"unit", "next_phase", "phases": {phase: {"tokens", "chars", "files": {label: chars}}}, "full_tune_tokens"} --
    or `Gone`, naming every file the model reads that is not there."""
    skill_md = _read(root, "SKILL.md")
    to_goal = skill_md is not None and _next_to_goal_node(skill_md)
    gone, phases = {}, {}
    for i, phase in enumerate(PHASES):
        items = [("SKILL.md", None, "SKILL.md"), (f"references/phases/{PHASE_FILE[phase]}", None, None)]
        if i + 1 < len(PHASES):
            rel = f"references/phases/{PHASE_FILE[PHASES[i + 1]]}"
            items.append((rel, GOAL_NODE, f"{rel} (to its Goal-node)") if to_goal else (rel, None, f"{rel} (next)"))
        for item in ORDERED[phase]:
            rel, heading = (item, None) if isinstance(item, str) else item
            items.append((rel, heading, f"{rel} § {heading}" if heading else rel))
        files = {}
        for rel, heading, label in items:
            text = _read(root, rel)
            if text is None:
                gone.setdefault(f"{rel} is gone", []).append(phase)
                continue
            if heading is None:
                files[label or rel] = len(text)
                continue
            span = _span(text, heading)
            if span is None:
                why = ("SKILL.md's Phase Sliding Window reads the next phase to it" if heading == GOAL_NODE
                       else "the model reads that section")
                gone.setdefault(f"{rel} has no `{heading}` heading, and {why}", []).append(phase)
                continue
            files[label] = span[1] if heading == GOAL_NODE else span[1] - span[0]
        chars = sum(files.values())
        phases[phase] = {"tokens": (chars + 2) // 4, "chars": chars, "files": files}
    if gone:
        raise Gone("\n".join(f"{what} (read in {_phases(names)}) -- a file renamed or moved is a change to the "
                             f"model in scripts/reading-cost.py, made in the same commit" for what, names in gone.items()))
    return {"unit": "tokens = characters / 4", "next_phase": "to its Goal-node" if to_goal else "whole",
            "phases": phases, "full_tune_tokens": sum(p["tokens"] for p in phases.values())}


def _k(tokens: int) -> str:
    return f"{tokens / 1000:.1f}K"


def render(tab: dict) -> list:
    """The table as lines: one per phase, its total and what makes it up, then a full tune."""
    out = [f"What a session reads per phase, in tokens ({tab['unit']}; the audit's §3.2 model); the next phase "
           f"{'to its Goal-node' if tab['next_phase'] != 'whole' else 'whole'}"]
    for phase, row in tab["phases"].items():
        parts = " · ".join(f"{label.replace('references/', '')} {_k((n + 2) // 4)}" for label, n in row["files"].items())
        out.append(f"  phase {phase:>2}  {_k(row['tokens']):>6}  {parts}")
    out.append(f"  a full tune, phases −1…5: {_k(tab['full_tune_tokens'])} tokens")
    return out


def check(root: str, baseline: str) -> tuple:
    """(ok, lines): each phase against the baseline -- not ok when one reads more than it did, or the baseline is
    missing, unreadable or of other phases."""
    tab = table(root)
    again = "write it again with --write-baseline"
    try:
        with open(baseline, encoding="utf-8") as fh:
            base = json.load(fh)
    except FileNotFoundError:
        return False, [f"no baseline at {baseline}: write one with --write-baseline"]
    except ValueError as exc:
        return False, [f"{baseline} is not JSON ({exc}): {again}"]
    known = base.get("phases") if isinstance(base, dict) else None
    if not isinstance(known, dict):
        return False, [f"{baseline} holds no phases: {again}"]
    ok, lines = True, []
    for phase, now in tab["phases"].items():
        was = known.get(phase)
        if not (isinstance(was, dict) and isinstance(was.get("chars"), int) and isinstance(was.get("files"), dict)):
            ok = False
            lines.append(f"phase {phase} is not in the baseline: {again}")
            continue
        if now["chars"] <= was["chars"]:
            lines.append(f"phase {phase:>2}  {_k(now['tokens']):>6}  ≤ {_k(was.get('tokens', 0))}")
            continue
        ok = False
        grew = [f"{label} +{n - was['files'].get(label, 0)}" for label, n in now["files"].items()
                if n > was["files"].get(label, 0)]
        lines.append(f"phase {phase} reads {_k(now['tokens'])} tokens, over its baseline {_k(was.get('tokens', 0))} "
                     f"(+{now['chars'] - was['chars']:,} characters; grew: {', '.join(grew)})")
    for phase in known:
        if phase not in tab["phases"]:
            ok = False
            lines.append(f"phase {phase} of the baseline is no phase of the model: {again}")
    if not ok:
        lines.append("A growth that is meant: write the baseline again, scripts/reading-cost.py --write-baseline, and "
                     "its diff is what a reviewer reads.")
    return ok, lines


def write_baseline(root: str, baseline: str) -> dict:
    """Today's table into `baseline` -- nothing written when a file the model reads is gone."""
    tab = table(root)
    os.makedirs(os.path.dirname(baseline) or ".", exist_ok=True)
    with open(baseline, "w", encoding="utf-8") as fh:
        json.dump({"what": "scripts/reading-cost.py's baseline: what a session reads per phase (#145); --check fails "
                           "a phase that reads more, and --write-baseline writes this file",
                   **tab}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return tab


# --------------------------------------------------------------------------------------------------- selftest
@contextlib.contextmanager
def _scratch():
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="reading_cost_")
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_GOAL_PART = "# P\n\nOne path.\n\n" + GOAL_NODE + "\n\nThe goal.\n\n```\n## not a heading\n```\n\n"
_RUNBOOK = "## Step-by-Step Runbook\n\n" + "step\n" * 40
_WINDOW_WHOLE = ("## 🧭 Phase Sliding Window\n\nLoad ONLY the active phase's reference file + the next adjacent one.\n\n"
                 "## 📁 Reference Map\n\n| x | each phase file opens with its Goal-node |\n")
_WINDOW_GOAL = ("## 🧭 Phase Sliding Window\n\nLoad ONLY the active phase's reference file + the next one to its "
                "`## 🎯 Goal-node`.\n\n## 📁 Reference Map\n\n| x | y |\n")
_INTAKE_TEXT = "# I\n\n## 0. Quickstart\n\n" + "q\n" * 30 + "## 3. Install verification\n\nverify\n\n## 4. DSP\n\nd\n"


def _model_files() -> list:
    """Every file the model reads but SKILL.md and the phase files, once."""
    out = []
    for items in ORDERED.values():
        for item in items:
            rel = item if isinstance(item, str) else item[0]
            if rel not in out:
                out.append(rel)
    return out


def _tree(tmp: str, window: str = _WINDOW_WHOLE, drop: str | None = None) -> str:
    """A skill whose every file has a size of its own: SKILL.md (its Phase Sliding Window `window`), the phase files
    (a Goal-node part, then a runbook), project-intake.md with sections, and each other file of the model -- the
    n-th one n*10 characters long. `drop` leaves that file out."""
    import tempfile
    root = tempfile.mkdtemp(dir=tmp)
    files = {"SKILL.md": "---\nname: s\n---\n\n# S\n\n" + window}
    for i, phase in enumerate(PHASES):
        files[f"references/phases/{PHASE_FILE[phase]}"] = _GOAL_PART + _RUNBOOK + "x" * (i + 1)
    for n, rel in enumerate(_model_files(), 1):
        files[rel] = _INTAKE_TEXT if rel == _INTAKE else "y" * (n * 10)
    for rel, text in files.items():
        if rel == drop:
            continue
        path = os.path.join(root, SKILL, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return root


def _run(*argv) -> tuple:
    """`main(argv)` -> (exit code, what it printed on stdout and stderr together)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = main(list(argv))
    return rc, out.getvalue()


def _size(root: str, rel: str) -> int:
    with open(os.path.join(root, SKILL, rel), encoding="utf-8") as fh:
        return len(fh.read())


def _check_counts():
    """A phase reads SKILL.md, its own file, the next phase's whole (today's rule), and what it orders -- a section
    when the model says so; tokens are characters / 4; phase 5 has no next phase."""
    with _scratch() as tmp:
        root = _tree(tmp)
        tab = table(root)
        assert tab["next_phase"] == "whole", tab["next_phase"]
        intake_3 = len("## 3. Install verification\n\nverify\n\n")
        want = (_size(root, "SKILL.md") + _size(root, "references/phases/phase_0_baseline.md")
                + _size(root, "references/phases/phase_1_foundation.md") + _size(root, _VF) + _size(root, _SHEET)
                + _size(root, _NAMING) + intake_3)
        zero = tab["phases"]["0"]
        assert zero["chars"] == want, (zero["chars"], want, zero["files"])
        assert zero["files"][f"{_INTAKE} § ## 3."] == intake_3, zero["files"]
        assert zero["tokens"] == (want + 2) // 4, zero
        five = tab["phases"]["5"]["files"]
        assert list(five)[:2] == ["SKILL.md", "references/phases/phase_5_variations.md"], five
        assert not any("phase_" in label for label in list(five)[2:]), five
        assert tab["full_tune_tokens"] == sum(p["tokens"] for p in tab["phases"].values()), tab


def _check_goal_node():
    """Once SKILL.md's Phase Sliding Window names the Goal-node, the next phase is read to the end of its Goal-node
    section (a `##` inside a fenced block does not end it) -- and a Goal-node said elsewhere in SKILL.md does not
    turn it on. A next phase with no Goal-node heading is named."""
    with _scratch() as tmp:
        root = _tree(tmp, window=_WINDOW_GOAL)
        tab = table(root)
        assert tab["next_phase"] == "to its Goal-node", tab["next_phase"]
        label = "references/phases/phase_1_foundation.md (to its Goal-node)"
        assert tab["phases"]["0"]["files"][label] == len(_GOAL_PART), tab["phases"]["0"]["files"]
        whole = table(_tree(tmp))                       # _WINDOW_WHOLE says Goal-node in the Map, not the window
        assert whole["next_phase"] == "whole" and whole["phases"]["0"]["chars"] > tab["phases"]["0"]["chars"]

        root = _tree(tmp, window=_WINDOW_GOAL)
        with open(os.path.join(root, SKILL, "references/phases/phase_2_eq.md"), "w", encoding="utf-8") as fh:
            fh.write("# P\n\n## Goal\n\ntext\n")
        rc, out = _run("--root", root)
        assert rc == 1 and "references/phases/phase_2_eq.md" in out and GOAL_NODE in out and "phase 1" in out, out


def _check_baseline():
    """--write-baseline then --check passes; one character more in a file fails each phase that reads it, naming the
    file; less passes; no baseline, and a baseline of other phases, fail."""
    with _scratch() as tmp:
        root = _tree(tmp)
        rc, out = _run("--root", root, "--write-baseline")
        assert rc == 0 and os.path.isfile(os.path.join(root, BASELINE)), out
        rc, out = _run("--root", root, "--check")
        assert rc == 0 and out.rstrip().splitlines()[-1].startswith("reading-cost OK"), out

        path = os.path.join(root, SKILL, _CHEAT)          # read in phases 2 and 4
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("z")
        rc, out = _run("--root", root, "--check")
        assert rc == 1, out
        over = [ln for ln in out.splitlines() if " over its baseline" in ln]
        assert [ln.split()[1] for ln in over] == ["2", "4"], out
        assert all(f"{_CHEAT} +1" in ln for ln in over), over
        assert "--write-baseline" in out, out

        with open(path, "w", encoding="utf-8") as fh:
            fh.write("z")
        rc, out = _run("--root", root, "--check")
        assert rc == 0, out

        with open(os.path.join(root, BASELINE), encoding="utf-8") as fh:
            base = json.load(fh)
        del base["phases"]["5"]
        with open(os.path.join(root, BASELINE), "w", encoding="utf-8") as fh:
            json.dump(base, fh)
        rc, out = _run("--root", root, "--check")
        assert rc == 1 and "phase 5" in out and "not in the baseline" in out, out

        os.remove(os.path.join(root, BASELINE))
        rc, out = _run("--root", root, "--check")
        assert rc == 1 and "no baseline" in out and "--write-baseline" in out, out


def _check_gone():
    """A file the model reads that is gone fails the table, the check and the baseline's writing, naming it and the
    phases that read it -- and writes no baseline."""
    with _scratch() as tmp:
        root = _tree(tmp, drop=_PLAYBOOK)                 # read in phases 2, 3 and 4
        for mode in ((), ("--check",), ("--write-baseline",)):
            rc, out = _run("--root", root, *mode)
            assert rc == 1 and f"{_PLAYBOOK} is gone" in out and "phases 2, 3, 4" in out, (mode, out)
        assert not os.path.exists(os.path.join(root, BASELINE)), "a baseline written over a gone file"


def _selftest() -> int:
    failures = []
    for check_ in (_check_counts, _check_goal_node, _check_baseline, _check_gone):
        try:
            check_()
        except AssertionError as exc:
            failures.append(f"{check_.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    print("selftest OK -- a phase reads SKILL.md, its file, the next phase's (whole, or to its Goal-node once the "
          "Phase Sliding Window says so -- not when another section does) and what it orders, a section where the "
          "model says so; a baseline written and checked passes, one character more fails each phase that reads "
          "it, naming the file, and less passes; no baseline, a baseline of other phases, a file gone and a next "
          "phase with no Goal-node are each named")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="exit 1 when a phase reads more than its baseline")
    mode.add_argument("--write-baseline", action="store_true", help="write today's table as the baseline")
    mode.add_argument("--selftest", action="store_true", help="the mechanics, on throwaway trees")
    parser.add_argument("--root", default=ROOT, help="the repository root (default: this script's)")
    parser.add_argument("--baseline", help=f"the baseline file (default: <root>/{BASELINE})")
    args = parser.parse_args(argv)
    if args.selftest:
        try:
            return _selftest()
        except AssertionError as exc:                      # a check that said no: 1, as the repo's checks end
            print(f"selftest FAILED --\n{exc}", file=sys.stderr)
            return 1
    baseline = args.baseline or os.path.join(args.root, BASELINE)
    shown = os.path.relpath(baseline, args.root) if baseline.startswith(args.root) else baseline
    try:
        if args.write_baseline:
            tab = write_baseline(args.root, baseline)
            print("\n".join(render(tab)))
            print(f"reading-cost: the baseline written, {shown} -- a full tune {_k(tab['full_tune_tokens'])} tokens")
            return 0
        if args.check:
            ok, lines = check(args.root, baseline)
            print("\n".join(lines))
            if not ok:
                print(f"reading-cost: FAILED against {shown}", file=sys.stderr)
                return 1
            print(f"reading-cost OK -- no phase reads more than its baseline ({shown})")
            return 0
        print("\n".join(render(table(args.root))))
        return 0
    except Gone as exc:
        print(f"reading-cost: what the model reads is not all there --\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, SKILL, "rew_tool"))
    import console
    console.install()
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                  # a bug: the traceback, and 70
        traceback.print_exc()
        sys.exit(70)
