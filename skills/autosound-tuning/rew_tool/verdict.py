"""The verdict block: at most five lines at the top of a tool's output (skill #70, S-057).

A session calls a tool at a step and has to find the one line that is for it. W-2 made `predict`'s notes
compact (#57 P5); the other tools still printed every table first. The shape was decided by the Arbiter:

    ▶ <the verdict, one line: what this run found>
      · <a number, with its quantity and where it comes from>      (two or three of them)
      · <…>
      → <what to do next: "enter this" / "measure these N" / "nothing to do">

Details come below it, or with `--verbose` where a tool shortens them. A number without its quantity is
not a number here (`name-the-quantity-next-to-the-number`): `-4.1 dB` says nothing until it says
`sum-loss avg over 80-250 Hz`. Five lines is a ceiling the block enforces, not a guideline.

stdlib only.
"""
from __future__ import annotations

MAX_NUMBERS = 3
MAX_LINES = 5


def block(verdict, numbers=(), next_step=None, indent="  "):
    """The block as a list of lines: the verdict, at most three numbers, the next step.

    `numbers` are ready sentences (`"sum-loss avg -1.2 dB over 80-250 Hz (w-L↔m-L, predicted)"`); more than
    three is a caller's mistake and raises, because a silent cut would drop the one a reader needed.
    """
    numbers = [n for n in numbers if n]
    if len(numbers) > MAX_NUMBERS:
        raise ValueError(f"a verdict block carries at most {MAX_NUMBERS} numbers, not {len(numbers)}")
    verdict = " ".join(str(verdict).split())
    if not verdict:
        raise ValueError("a verdict block starts with a verdict")
    lines = [f"{indent}▶ {verdict}"]
    lines += [f"{indent}  · {' '.join(str(n).split())}" for n in numbers]
    if next_step:
        lines.append(f"{indent}  → {' '.join(str(next_step).split())}")
    assert len(lines) <= MAX_LINES
    return lines


def render(verdict, numbers=(), next_step=None, indent="  "):
    """The block as one string, followed by a blank line so the details below read as separate."""
    return "\n".join(block(verdict, numbers, next_step, indent)) + "\n"


def is_block(text):
    """True when `text` opens with a verdict block of at most five lines -- for the tools' selftests."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines or not lines[0].lstrip().startswith("▶"):
        return False
    body = 1
    for ln in lines[1:]:
        if ln.lstrip().startswith(("·", "→")):
            body += 1
        else:
            break
    return body <= MAX_LINES


def _selftest():
    lines = block("TRUSTED -- every measured junction within 1.0 dB",
                  ["worst |mean Δ| 0.7 dB at w-L↔m-L (predicted − measured, 80-250 Hz)"],
                  "go on to Phase 2")
    assert lines[0] == "  ▶ TRUSTED -- every measured junction within 1.0 dB" and len(lines) == 3, lines
    assert lines[-1].startswith("    → "), lines
    assert is_block("\n".join(lines) + "\n\n  table …")
    assert not is_block("  table first\n  ▶ late verdict")
    try:
        block("x", ["1", "2", "3", "4"])
        raise AssertionError("four numbers must be refused, not cut")
    except ValueError:
        pass
    assert len(block("x", ["1", "2", "3"], "next")) == MAX_LINES
    assert block("  a\n  b  ", [None, "n"]) == ["  ▶ a b", "    · n"]
    print("selftest[verdict] OK -- the verdict first, at most three numbers, the next step last; five lines at "
          "most, a fourth number refused rather than cut")
    return 0


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import console
    console.install()
    sys.exit(_selftest())
