"""`python3 -m helix_pct6 read|diff|check|models|selftest ...` -- JSON on stdout. Writes no file, ever.

    read  FILE [--summary]                   everything the file says (or a short per-channel table)
    diff  LEFT RIGHT [--ignore-save-metadata] differences by category
    check FILE EXPECTED.json                 one file against expected values (see compare.check)
    models                                   which models are checked, and the warning shown with every result
    selftest                                 the package's tests (tests/test_helix_pct6.py); last line OK on a pass

Runs as `python3 -m helix_pct6` from rew_tool, or by its path (`python3 .../helix_pct6/__main__.py`), as
scripts/selftests.txt runs it: the block below lets the relative imports resolve then.

Exit codes: 0 done, 2 the file could not be read (the error's kind on stderr), 3 the input changed while read;
selftest: 0 when the tests passed (or every one was skipped, said SKIPPED), 1 when one failed.
"""

import argparse
import json
import os
import sys

if not __package__:
    # Run by its path: Python put this folder on sys.path and gave the module no package. The package's parent goes
    # there instead, so `from .x import ...` resolves against `helix_pct6`, the same package `-m` loads.
    _HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
    sys.path.insert(0, os.path.dirname(_HERE))
    __package__ = "helix_pct6"

from . import CREDIT, MODELS, WARNING, __version__
from .compare import check, differences
from .container import Pct6Error, file_unchanged, read_pct6
from .inventory import interpret


_SHORT = {"Linkwitz": "LR", "Butterworth": "BW", "Bessel": "BE", "Chebyshev": "CH", "Self-define": "SD"}


def _summary(inv: dict) -> str:
    d = inv["device"]
    lines = [WARNING, "",
             "model: %s (Dev %s, %s), PC-Tool %s, saved %s" % (d["name"] or "unknown", d["dev"],
                                                              "checked" if d["verified"] else "NOT CHECKED",
                                                              d["pc_tool_version"], d["saved"]),
             "file: md5 %s" % inv["file"]["input_md5"], ""]
    for note in inv["notes"]:
        lines.append("note: " + note)
    lines.append("%-12s %-22s %8s %9s %5s %5s  %s" % ("channel", "name", "gain dB", "delay ms", "pol", "mute", "crossover"))
    for c in inv["channels"]:
        if c["kind"] != "output":
            continue
        t = c["timing"][0]["delay"]["display_ms"] if c["timing"] else None
        xo = []
        for side in ("high_pass", "low_pass"):
            x = c.get(side)
            if not x:
                continue
            if x.get("state") == "configured":
                xo.append("%s %g Hz %s%g" % (side[0].upper() + "P", x["frequency_hz"], _SHORT.get(x["family"], "?"),
                                              x["slope_db_oct"]))
            else:
                xo.append("%sP %s" % (side[0].upper(), x.get("state")))
        level = c["level"]["value"]
        lines.append("%-12s %-22s %8s %9s %5s %5s  %s" % (
            c["label"] or "OC %s" % c["index"], (c["name"] or "")[:22],
            "-inf" if c["level"]["state"] == "zero_amplitude" else ("" if level is None else "%.1f" % level),
            "" if t is None else "%.2f" % t, c["polarity"] or "", {True: "ON", False: "", None: "?"}[c.get("mute_on")],
            ", ".join(xo)))
    lines += ["", CREDIT]
    return "\n".join(lines)


def selftest() -> int:
    """Run the package's tests. The last line says OK only when they passed and at least one ran: a run where every
    test was skipped says SKIPPED (the selftest runner's NOT RUN), a failure or no test found says FAILED."""
    import unittest
    tests = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    suite = unittest.defaultTestLoader.discover(tests, pattern="test_*.py", top_level_dir=tests)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    sys.stdout.flush()
    # Only a test's own skip is counted: a class or module skipped as a whole is one placeholder that is not a test.
    skipped = sum(1 for test, _ in result.skipped if isinstance(test, unittest.TestCase))
    ran = result.testsRun - skipped
    counts = "%d tests: %d ran, %d skipped" % (result.testsRun, ran, skipped) + (" (fixture absent)" if skipped else "")
    if not result.wasSuccessful() or result.testsRun == 0:
        print("helix_pct6 selftest FAILED -- %s, %d failures, %d errors"
              % (counts, len(result.failures), len(result.errors)))
        return 1
    if ran <= 0:
        print("helix_pct6 selftest SKIPPED -- every test skipped: " + counts)
        return 0
    print("helix_pct6 selftest OK -- " + counts)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="helix_pct6", description=__doc__.split("\n")[0])
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    rd = sub.add_parser("read")
    rd.add_argument("file")
    rd.add_argument("--summary", action="store_true")
    df = sub.add_parser("diff")
    df.add_argument("left")
    df.add_argument("right")
    df.add_argument("--ignore-save-metadata", action="store_true")
    ck = sub.add_parser("check")
    ck.add_argument("file")
    ck.add_argument("expected")
    sub.add_parser("models")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command == "models":
        print(json.dumps({"warning": WARNING, "credit": CREDIT,
                          "models": [m.__dict__ for m in MODELS]}, indent=2, ensure_ascii=False))
        return 0
    try:
        paths = [args.left, args.right] if args.command == "diff" else [args.file]
        docs = [read_pct6(p) for p in paths]
    except Pct6Error as exc:
        print("error (%s): %s" % (exc.kind, exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print("error (file): %s" % exc, file=sys.stderr)
        return 2
    if args.command == "read":
        inv = interpret(docs[0])
        text = _summary(inv) if args.summary else json.dumps(inv, indent=1, ensure_ascii=False)
    elif args.command == "diff":
        text = json.dumps(differences(docs[0], docs[1], args.ignore_save_metadata), indent=1, ensure_ascii=False)
    else:
        with open(args.expected, encoding="utf-8") as handle:
            expected = json.load(handle)
        text = json.dumps({"warning": WARNING, "results": check(docs[0], expected)}, indent=1, ensure_ascii=False)
    if not all(file_unchanged(d) for d in docs):
        print("error: an input file changed while it was read", file=sys.stderr)
        return 3
    print(text)
    return 0


if __name__ == "__main__":
    # skill #21: a code page must not destroy a result. `console` is rew_tool's, one folder up: on the path when run
    # by path (the block at the top) and under `-m` from rew_tool; put there for any other way in.
    _TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _TOOL not in sys.path:
        sys.path.insert(0, _TOOL)
    import console
    console.install()
    sys.exit(main())
