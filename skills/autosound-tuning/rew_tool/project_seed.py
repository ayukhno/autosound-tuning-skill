"""Start a new project from an existing one's system parameters instead of from nothing.

Ported from `autosound-tcc`'s `core/project_seed.py` (2026-08-23) with its classification intact —
that part is theirs and it is the valuable part. It moved here because `project-schema.md` and
`project.py` live here: the code that WRITES `project.json` belongs where the schema is, or the
two drift, and the copy outside the schema drifts silently. Only the loader changed (their
`vendor_loader` became a direct `import project`) plus a CLI, a selftest, and the profile-gap
count below.

**The cost this removes.** A new project asks for the whole car: equipment, drivers per channel,
the naming glossary, the DSP's controls. That is the right question the first time and the wrong
one every time after — the car has not changed. It is wrongest when the tune arrives from
OUTSIDE: whoever wrote that plan has none of our system parameters and never will, so a person
importing it would be retyping their own car to receive somebody else's crossovers (the user, via
the cockpit, 2026-08-23: "each next project demands a full description — and that should not have
to be done"). That import is `resonalyze_vc.py`; this is the other half of the same day's work.

**What "system parameters" means here, and what it deliberately does not.** `project.json` holds
three different kinds of thing (`project-schema.md`), and only one of them describes the car:

* **the system** — `car`, `source`, `dsp`, `amps`, `mic`, `hardware`, `channels`, `glossary`,
  `channel_summary`, `presets`. True of the installation, not of any one tune. This travels.
* **the findings** — `acoustics.flaws` and `_open_questions`. Measured or decided IN a project.
  The cabin's 32 Hz null is a fact about the car and will very likely reappear; the entry that
  records it also carries `evidence` naming measurements that exist only in the project it came
  from. So: offered, off by default, never silent -- and every carried row lands as a
  `hypothesis`, because in the new project nobody has measured it yet.
* **this project's own** — `project_rev` (its own write counter), and most of `paths`, which
  points at a REW file, a baseline set and a ledger version belonging to that project. Only
  `measurements_repo` travels, because it points at the car, not at the tune.

`sources` travels with the facts. Dropping it would leave the new project asserting a driver's Fs
with no record of where the number came from, which is worse than saying it was inherited — and
the seeding itself is appended there as one more source, so the file says what happened to it.

**An allowlist, not a blocklist.** Only the keys and files named here are copied. A project's
`state/`, `process/`, `journal/`, `rew_analitic/`, its ledger snapshots and its `.tcc/` are not
excluded by a rule that has to be kept up to date — they are simply never reached. Whatever the
method adds next stays behind until somebody decides it should travel. That default matters most
to whoever owns the growing schema, which is this repo.

**An inherited profile can be INCOMPLETE, and silence about that reads as settled.** A DSP profile
travels verbatim because it is hardware — but ours has unmeasured fields, and a `null` in a
machine-readable file looks identical to a fact until something tries to check against it. So
`Seeded.profile_open` counts what `dsp_profile.open_questions()` still reports on the copy, and a
caller can say "profile inherited, 2 facts still open" instead of nothing at all.

UI-free on purpose: a window is one caller, and the same act has to be available from a terminal.

    project_seed.py <source> <target> [--findings] [--no-profile] [--note TEXT] [--json]
    project_seed.py --describe <dir>

stdlib only, py3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: Facts about the installation. True whichever tune is running, so they travel whole.
SYSTEM_KEYS = (
    "car", "source", "dsp", "amps", "mic", "hardware",
    "channels", "glossary", "channel_summary", "presets",
)

#: Measured or decided inside a project. Offered separately because the entries reference their
#: own project's evidence -- see the module docstring.
FINDING_KEYS = ("acoustics", "_open_questions")

#: The one path that is about the car rather than about the tune: the measurement corpus for this
#: vehicle. `rew_project`, `baseline_set`, `set0_*` are the other project's own and stay there.
PATHS_THAT_TRAVEL = ("measurements_repo",)

#: Prose. Copied whole because it IS the description the person would otherwise retype, and marked
#: at the top because a reader must not mistake an inherited profile for one written here.
PROSE_FILES = ("autosound_context.md", "preference-profile.md")

#: The DSP's capabilities. Hardware, so it travels verbatim -- and the new project needs it before
#: anything can check whether a filter is even enterable (`resonalyze_vc.py`).
PROFILE_FILE = "dsp_profile.json"

#: Default marker for the prose files. English because this module has no language; a window
#: passes a translated one (autosound-tcc: `i18n.t("npSeedNote")`).
DEFAULT_NOTE = "**Inherited from `{source}` ({when}).** The system profile was copied from that " \
               "project, not written here — check it against this build before relying on it."


@dataclass
class Summary:
    """What a candidate source project IS, in the few words a picker can show."""

    car: str
    dsp: str
    channels: int


@dataclass
class Seeded:
    """What actually happened, in numbers the caller can render in any language.

    Deliberately not pre-rendered sentences: this module is imported by a window that speaks two
    languages, by a CLI that speaks one, and by tests that speak none.
    """

    ok: bool
    written: list = field(default_factory=list)
    channels: int = 0
    amps: int = 0
    flaws: int = 0
    questions: int = 0
    #: Facts the INHERITED DSP profile still does not state (`dsp_profile.open_questions`). Zero
    #: when no profile travelled. A profile is copied verbatim because it is hardware, but ours
    #: has unmeasured fields and a `null` looks like a fact until something checks against it.
    profile_open: int = 0
    #: One technical sentence when `ok` is False -- a path, or what the method's validator said.
    problem: Optional[str] = None


def _read_project(source):
    path = os.path.join(source, "project.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def describe(source):
    """The one-line identity of a project worth seeding from, or None if it is not one.

    Used by a picker to answer "is this a project, and which car is it" before anything is copied.
    Reads the file directly rather than through `Project`: an unreadable or 2.x `project.json` is
    a "no" here, not an exception in a dialog.
    """
    data = _read_project(source)
    if data is None:
        return None
    car = data.get("car") or {}
    dsp = data.get("dsp") or {}
    car_line = " ".join(
        str(car[key]) for key in ("make", "model", "year") if car.get(key) not in (None, "")
    )
    dsp_line = " ".join(
        str(dsp[key]) for key in ("vendor", "model") if dsp.get(key) not in (None, "")
    )
    channels = data.get("channels")
    return Summary(
        car=car_line or os.path.basename(os.path.normpath(source)),
        dsp=dsp_line,
        channels=len(channels) if isinstance(channels, list) else 0,
    )


def dsp_of(source):
    """The source project's DSP as (vendor, model), for prefilling a profile picker.

    The two strings are matched EXACTLY against a consumer's bundled profiles
    (`dsp_profile.find_bundled()`, `project-intake.md §4` — the directory is the caller's, this
    repo ships none today), so handing over the pair a real project already uses is worth more
    than any free typing.
    """
    data = _read_project(source)
    if data is None:
        return None
    dsp = data.get("dsp") or {}
    vendor, model = str(dsp.get("vendor") or "").strip(), str(dsp.get("model") or "").strip()
    return (vendor, model) if vendor and model else None


def _carried_as_hypotheses(acoustics):
    """Every carried flaw lands as `hypothesis`, whatever it was in the source project.

    Not a judgement about the source's rigour -- a judgement about WHERE the row now sits. Its
    `evidence` names captures that exist only in the project it came from, so in the target it is
    by construction unverified: nobody has measured this cabin through this build yet. Carrying a
    status of `confirmed` across that boundary would let one processor's findings arrive in a
    brand-new project as fact, pointing at measurements the project has never taken.

    The asymmetry is deliberate. A row can only be weakened here, never strengthened: `hypothesis`
    is the safe direction, and settling it again is a measurement, which is exactly the work the
    new project exists to do.
    """
    carried = dict(acoustics or {})
    flaws = carried.get("flaws")
    if isinstance(flaws, list):
        carried["flaws"] = [
            {**f, "status": "hypothesis"} if isinstance(f, dict) else f for f in flaws
        ]
    return carried


def _mark(text, note):
    """Put the note where a reader meets it first, without displacing the document's title."""
    lines = text.split("\n")
    if lines and lines[0].startswith("#"):
        return "\n".join([lines[0], "", f"> {note}"] + lines[1:])
    return f"> {note}\n\n{text}"


def _profile_open_count(path):
    """How many facts the copied profile still does not state. Never fatal: a profile we cannot
    read is reported as unknown by the caller's own checker later, and refusing the whole seeding
    over it would throw away the ten things that did copy."""
    try:
        import dsp_profile
        return len(dsp_profile.open_questions(dsp_profile.load_profile(path)))
    except Exception:                                  # noqa: BLE001 -- unreadable or foreign
        return 0


def seed(source, target, *, include_findings=False, copy_profile=True, note=DEFAULT_NOTE,
         today=None):
    """Copy `source`'s system parameters into `target`. Never writes into `source`.

    Refuses rather than merges when `target` already has a `project.json`: seeding is the first
    act of a new project, and quietly overwriting facts somebody has already confirmed is the one
    outcome nobody could want.

    The file is written through `Project.save()` -- so it is validated, written atomically, and
    gets `project_rev` 1 rather than inheriting the source's count of writes it was not part of.

    `copy_profile=False` is for the one case where the source is the wrong authority on it: the
    person picked a DIFFERENT DSP for the new build. Everything else about the car still travels
    -- the same drivers in the same doors, on a new processor -- but its capabilities are then a
    question for the onboarding interview, not a file to inherit.
    """
    source = os.path.abspath(os.path.expanduser(str(source)))
    target = os.path.abspath(os.path.expanduser(str(target)))
    if source == target:
        return Seeded(False, problem="the source and the new project are the same folder")
    data = _read_project(source)
    if data is None:
        return Seeded(False, problem=f"no readable project.json in {source}")
    if os.path.isfile(os.path.join(target, "project.json")):
        return Seeded(False, problem=f"{target} already has a project.json")

    when = (today or date.today()).isoformat()
    name = os.path.basename(os.path.normpath(source))
    seeded = {"project_rev": 0}
    for key in SYSTEM_KEYS:
        if key in data:
            seeded[key] = data[key]
    if include_findings:
        for key in FINDING_KEYS:
            if key in data:
                seeded[key] = data[key]
        if "acoustics" in seeded:
            seeded["acoustics"] = _carried_as_hypotheses(seeded["acoustics"])
    paths = data.get("paths")
    if isinstance(paths, dict):
        travelling = {k: paths[k] for k in PATHS_THAT_TRAVEL if k in paths}
        if travelling:
            seeded["paths"] = travelling
    sources = data.get("sources")
    seeded["sources"] = (list(sources) if isinstance(sources, list) else []) + [
        f"system parameters seeded from project '{name}' on {when} — "
        "inherited, not re-measured here"
    ]

    result = Seeded(True)
    try:
        import project
        project.Project(target).save(seeded)
    except Exception as exc:                # noqa: BLE001 -- the validator, or a disk that said no
        return Seeded(False, problem=f"{type(exc).__name__}: {exc}")
    result.written.append("project.json")

    os.makedirs(target, exist_ok=True)
    profile = os.path.join(source, PROFILE_FILE)
    if copy_profile and os.path.isfile(profile):
        shutil.copy2(profile, os.path.join(target, PROFILE_FILE))
        result.written.append(PROFILE_FILE)
        result.profile_open = _profile_open_count(os.path.join(target, PROFILE_FILE))

    marker = note.format(source=name, when=when)
    for prose_name in PROSE_FILES:
        prose = os.path.join(source, prose_name)
        if not os.path.isfile(prose):
            continue
        try:
            with open(prose, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        with open(os.path.join(target, prose_name), "w", encoding="utf-8") as f:
            f.write(_mark(text, marker))
        result.written.append(prose_name)

    channels = seeded.get("channels")
    amps = seeded.get("amps")
    result.channels = len(channels) if isinstance(channels, list) else 0
    result.amps = len(amps) if isinstance(amps, list) else 0
    flaws = ((seeded.get("acoustics") or {}).get("flaws")) if include_findings else None
    result.flaws = len(flaws) if isinstance(flaws, list) else 0
    questions = seeded.get("_open_questions") if include_findings else None
    result.questions = len(questions) if isinstance(questions, list) else 0
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="project_seed.py",
        description="Start a new project from an existing one's system parameters.")
    parser.add_argument("source", help="the project to inherit from")
    parser.add_argument("target", nargs="?", help="the new project directory")
    parser.add_argument("--describe", action="store_true",
                        help="just say what SOURCE is, and copy nothing")
    parser.add_argument("--findings", action="store_true",
                        help="also carry acoustics.flaws and _open_questions; every carried flaw "
                             "lands as a hypothesis, because its evidence points at the source "
                             "project's measurements, not at this one's")
    parser.add_argument("--no-profile", action="store_true",
                        help="do not inherit dsp_profile.json (the new build has a DIFFERENT DSP)")
    parser.add_argument("--note", default=DEFAULT_NOTE,
                        help="marker put at the top of each inherited prose file; "
                             "{source} and {when} are substituted")
    parser.add_argument("--json", action="store_true", help="machine output")
    args = parser.parse_args(argv)

    if args.describe:
        summary = describe(args.source)
        if summary is None:
            print(f"project_seed: no readable project.json in {args.source}", file=sys.stderr)
            return 1
        print(json.dumps(vars(summary), indent=2, ensure_ascii=False) if args.json else
              f"{summary.car} · {summary.dsp or 'DSP not stated'} · "
              f"{summary.channels} channels")
        return 0

    if not args.target:
        parser.error("a target directory is required unless --describe is given")

    result = seed(args.source, args.target, include_findings=args.findings,
                  copy_profile=not args.no_profile, note=args.note)
    if args.json:
        print(json.dumps(vars(result), indent=2, ensure_ascii=False))
    elif not result.ok:
        print(f"project_seed: {result.problem}", file=sys.stderr)
    else:
        print(f"seeded {args.target} from {args.source}")
        print(f"  wrote     {', '.join(result.written)}")
        print(f"  carried   {result.channels} channels · {result.amps} amps"
              + (f" · {result.flaws} flaws (as hypotheses) · {result.questions} open questions"
                 if args.findings else ""))
        if PROFILE_FILE in result.written:
            print(f"  profile   inherited"
                  + (f", {result.profile_open} facts still open" if result.profile_open
                     else ", complete"))
        if not args.findings:
            print("  findings  left behind (--findings to carry them; their evidence names "
                  "measurements that live in the source project)")
    return 0 if result.ok else 1


# ── selftest ───────────────────────────────────────────────────────────────────
def _source_project(root):
    """A project with one of each kind of key, so the split can be observed rather than assumed."""
    os.makedirs(root, exist_ok=True)
    import project
    project.Project(root).save({
        "car": {"make": "VW", "model": "Passat B8", "year": 2017},
        "dsp": {"vendor": "Audiotec-Fischer", "model": "Helix DSP Ultra S"},
        "amps": [{"name": "A"}, {"name": "B"}],
        "channels": [{"code": "w-L", "role": "woofer"}, {"code": "sw", "role": "sub"}],
        "glossary": {"channels": [{"code": "w-L"}]},
        # A real flaw row, because `Project.save()` validates them: a cabin null is interference,
        # so `leave`, and `evidence` names a capture that exists only in THIS project -- which is
        # the whole reason findings do not travel by default.
        "acoustics": {"flaws": [{
            "kind": "cabin_null", "f_hz": 32, "level_db": -11.0, "action": "leave",
            "why": "cabin null, interference rather than minimum-phase",
            "evidence": ["w-L_2 (sw)"],
        }]},
        "_open_questions": ["is the left door lagging?"],
        "paths": {"measurements_repo": "~/corpus", "rew_project": "~/this-tune.rewp",
                  "baseline_set": "set0"},
        "sources": ["measured 2026-07-01"],
    })
    with open(os.path.join(root, "autosound_context.md"), "w", encoding="utf-8") as f:
        f.write("# The car\n\nTwo doors, treated.\n")
    with open(os.path.join(root, PROFILE_FILE), "w", encoding="utf-8") as f:
        # Deliberately INCOMPLETE, the way a real one is: it declares crossover legs and EQ but
        # states no `crossover_filters` for them, and carries an explicit null. A profile that is
        # complete for what it declares would make `profile_open` zero and the assertion below
        # would pass without measuring anything.
        json.dump({"dsp_profile": {
            "name": "Helix DSP Ultra S", "vendor": "Audiotec-Fischer", "dsp_processing_rate_hz": 96000,
            "delay": {"step_ms": 0.01, "max_ms": None},
            "polarity": {"scope": ["per driver output"]},
            "groups": [{"id": "physical_outputs", "label": "Outputs", "max_count": 12,
                        "fields": ["hp", "lp", "gain_db", "ta_ms", "polarity"]}],
        }}, f)
    # A ledger and a scratch dir that must NOT travel -- the allowlist should never reach them.
    os.makedirs(os.path.join(root, "state", "SQ"), exist_ok=True)
    with open(os.path.join(root, "state", "SQ", "v_001.json"), "w", encoding="utf-8") as f:
        f.write("{}")
    return root


def _selftest():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src = _source_project(os.path.join(tmp, "old-car"))
        dst = os.path.join(tmp, "new-car")
        out = seed(src, dst, today=date(2026, 8, 23))
        assert out.ok, out.problem

        with open(os.path.join(dst, "project.json"), encoding="utf-8") as f:
            got = json.load(f)

        # The system travels...
        assert got["car"]["model"] == "Passat B8" and len(got["channels"]) == 2, got
        assert out.channels == 2 and out.amps == 2, out
        # ...the findings do NOT, by default. Their `evidence` names measurements that exist only
        # in the source project, so copying them ships dangling proof.
        assert "acoustics" not in got and "_open_questions" not in got, got
        assert out.flaws == 0 and out.questions == 0, out
        # ...and of `paths`, only the one that points at the CAR rather than at the tune.
        assert got["paths"] == {"measurements_repo": "~/corpus"}, got["paths"]
        # The write counter is this project's own, not the source's.
        assert got["project_rev"] == 1, got["project_rev"]
        # The file says what happened to it.
        assert any("seeded from project 'old-car' on 2026-08-23" in s for s in got["sources"]), got
        assert "measured 2026-07-01" in got["sources"], got

        # An allowlist, not a blocklist: the ledger is not excluded by a rule, it is never reached.
        assert not os.path.exists(os.path.join(dst, "state")), "the ledger must not travel"

        # Prose is marked, and the mark goes UNDER the title rather than displacing it.
        with open(os.path.join(dst, "autosound_context.md"), encoding="utf-8") as f:
            prose = f.read()
        assert prose.startswith("# The car\n\n> **Inherited from `old-car`"), prose[:80]
        assert "Two doors, treated." in prose

        # An inherited profile can be INCOMPLETE, and a null looks like a fact until something
        # checks it. The count is what lets a caller say so instead of staying quiet.
        import dsp_profile
        gaps = dsp_profile.open_questions(
            dsp_profile.load_profile(os.path.join(dst, PROFILE_FILE)))
        assert PROFILE_FILE in out.written, out
        assert out.profile_open == len(gaps) > 0, (out.profile_open, gaps)
        # It counts the gaps of the COPY, which is what the new project will actually be checked
        # against -- not a number remembered from the source.
        assert "delay.max_ms" in gaps and any("crossover_filters" in g for g in gaps), gaps

        # Refuses rather than merges: a second seeding into a live project would overwrite facts
        # somebody has already confirmed.
        again = seed(src, dst)
        assert not again.ok and "already has a project.json" in again.problem, again
        assert seed(src, src).problem.startswith("the source and the new project"), "same folder"
        assert not seed(os.path.join(tmp, "nowhere"), os.path.join(tmp, "x")).ok

        # --findings carries them, and counts them, so the choice is visible either way.
        with_f = seed(src, os.path.join(tmp, "third"), include_findings=True)
        assert with_f.flaws == 1 and with_f.questions == 1, with_f
        # ...and they arrive as HYPOTHESES, whatever they were at home (2026-09-02). The source
        # row here is a plain confirmed one -- no `status` key at all, which is how every map
        # written before the field existed reads. Carried verbatim it would have banked another
        # build's finding in a brand-new project as fact, its evidence naming captures this
        # project has never taken. Read off DISK, because that is where the next session reads it.
        with open(os.path.join(tmp, "third", "project.json"), encoding="utf-8") as fh:
            carried = json.load(fh)["acoustics"]["flaws"]
        assert [f["status"] for f in carried] == ["hypothesis"], carried
        with open(os.path.join(src, "project.json"), encoding="utf-8") as fh:
            assert "status" not in json.load(fh)["acoustics"]["flaws"][0], "source was mutated"
        # A different DSP: everything about the car still travels, its capabilities do not.
        no_p = seed(src, os.path.join(tmp, "fourth"), copy_profile=False)
        assert PROFILE_FILE not in no_p.written and no_p.profile_open == 0, no_p
        assert no_p.channels == 2, "the car still travels when the processor changes"

        summary = describe(src)
        assert (summary.car, summary.channels) == ("VW Passat B8 2017", 2), summary
        assert dsp_of(src) == ("Audiotec-Fischer", "Helix DSP Ultra S"), dsp_of(src)
        assert describe(os.path.join(tmp, "nowhere")) is None

    print(f"selftest OK -- system travels (2 channels, 2 amps), findings and ledger stay behind, "
          f"only measurements_repo of 4 paths, project_rev 1 not inherited, "
          f"profile carried with {out.profile_open} facts still open, re-seed refused")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
