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

* **the system**, and it splits in two. `car`, `source`, `amps`, `mic` are true of the
  installation whatever drives it, and always travel. `dsp`, `hardware`, `channels`, `glossary`,
  `channel_summary`, `presets` are bound to the PROCESSOR and travel only while it is the same
  one; on a new processor its output list is not inheritance but a wrong answer, and nothing
  undoes it (there is no `remove-channel`). Which half you get is `copy_profile` — see `seed`.
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

#: Facts about the CAR and its installation: true whichever processor drives them. These travel
#: always -- the drivers are in the same doors whatever is upstream of them.
CAR_KEYS = ("car", "source", "amps", "mic")

#: Facts bound to the PROCESSOR, and the reason `copy_profile=False` had to grow teeth (2026-09-02).
#: `channels` is its output list, `channel_summary` is derived from that list, `glossary.channels`
#: names those same codes, `presets` are its preset slots, and `hardware.controls` is DSP-level by
#: the schema's own words (`project-schema.md`, SCR-017: a vendor with no such remote simply has no
#: entries). Carrying them into a build with a different processor is not inheritance but a wrong
#: answer: 20 Helix channels, a centre, two rears and two virtual tiers arrived in an 8-output DSP
#: with no virtual layer, and nothing undoes it -- there is no `remove-channel`.
DSP_KEYS = ("dsp", "hardware", "channels", "glossary", "channel_summary", "presets")

#: Both halves, for the ordinary case where the processor did not change.
SYSTEM_KEYS = CAR_KEYS + DSP_KEYS

#: Measured or decided inside a project. Offered separately because the entries reference their
#: own project's evidence -- see the module docstring.
FINDING_KEYS = ("acoustics", "_open_questions")

#: The one path that is about the car rather than about the tune: the measurement corpus for this
#: vehicle. `rew_project`, `baseline_set`, `set0_*` are the other project's own and stay there.
PATHS_THAT_TRAVEL = ("measurements_repo",)

#: Prose. Copied whole because it IS the description the person would otherwise retype, and marked
#: at the top because a reader must not mistake an inherited profile for one written here.
PROSE_FILES = ("autosound_context.md",)

#: What NEVER travels, and gets no checkbox (the Arbiter, 2026-09-19, hub #185): the tune's PURPOSE
#: (`preference-profile.md`: taste, competition configuration, judging set-up, target curve -- the
#: Passat's file opened by saying the seed described the opposite tune).
#:
#: `hardware.controls` TRAVELS since 2026-09-23 (the Arbiter: «переносити, а там користувач сам підправить
#: або скіл спитає»). The list of controls is the user's (`project.set_hardware_control`), and a copy for the
#: passenger seat in the same car has the same knobs. Each comes marked as carried in from the source, like any
#: inherited fact, so `contract.py check` puts it to him: confirm it here, or change it.
NEVER_TRAVELS = {"preference-profile.md": "the tune's purpose belongs to the project, not to the car"}

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
    #: How many measured flaw rows `--findings` would carry from here (2026-09-02). The checkbox
    #: existed before the number did, so the choice was offered blind: a window could say "carry
    #: the findings?" and neither it nor the person could see whether that meant three rows or
    #: eighteen. `Seeded.flaws` answers the same question AFTER the copy, which is the wrong side
    #: of the decision. Zero is a real answer and reads as one -- the source has none to give.
    flaws: int = 0


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
    #: What `project_repo.init` said: the project is a git repository with a first commit, or why not (hub #199).
    repo: Optional[str] = None


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

    Used by a picker to answer "is this a project, which car is it, and how much is on offer"
    before anything is copied.
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
    flaws = ((data.get("acoustics") or {}).get("flaws")) or []
    return Summary(
        car=car_line or os.path.basename(os.path.normpath(source)),
        dsp=dsp_line,
        channels=len(channels) if isinstance(channels, list) else 0,
        flaws=len(flaws) if isinstance(flaws, list) else 0,
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


#: What a fresh project must never push, seeded as a real file rather than promised in prose.
#: `setup-critic-channel.md` said "it's gitignored" for months with nothing behind it: no
#: `.gitignore` was written by anything, and `project-intake.md` asked the AGENT to make one --
#: an instruction with no carrier, obeyed or not depending on the session. Meanwhile README
#: recommends backing this very folder up to a private GitHub (HUB-025).
#:
#: This is the SECOND line of defence and it is worth saying which: a key belongs outside the
#: project entirely (`~/.config/autosound/critic-env`), because `.gitignore` stops none of
#: `git add -f`, a copied folder, or a backup that is not git at all.
GITIGNORE_LINES = [
    "# Written by project_seed.py. Secrets and machine-local state do not leave this folder.",
    "# The key itself belongs OUTSIDE the project: ~/.config/autosound/critic-env",
    "# (Windows: %APPDATA%\\autosound\\critic-env). See setup-critic-channel.md.",
    ".critic-env",
    "rew_analitic/.critic-env",
    "critic-env",
    ".mcp.json",
    ".tcc/",
    "*.mdat",
]


def write_gitignore(target):
    """Write `.gitignore` into a fresh project. Returns True if it wrote one.

    An existing file is left ALONE and reported as untouched -- a project may already carry
    rules somebody meant, and silently rewriting them would be a worse failure than the one
    this closes."""
    path = os.path.join(target, ".gitignore")
    if os.path.exists(path):
        return False
    os.makedirs(target, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(GITIGNORE_LINES) + "\n")
    return True


def _absolute(path):
    """A path of the source MACHINE: `/…`, `\\\\…`, or a drive (`Z:\\…`). `~/…` is the person's home on any machine and
    travels."""
    return path.startswith(("/", "\\")) or (len(path) > 2 and path[1] == ":")


def _protective_history(source):
    """The source's protective filters as it recorded them, PER CHANNEL from the newest round where each had one --
    history for the import record (hub #185: «протектив там був m/c/r 100 LR24, tw 1000 LR24»), or None.

    Not "the last round": the front may be taken raw in one round and the centre raw in another (the Arbiter,
    2026-09-23), and it used to read only a round still open, which a finished project never has."""
    state_dir = os.path.join(_HERE, "state")
    if state_dir not in sys.path:
        sys.path.insert(0, state_dir)
    try:
        import process as _process
        record = _process.Process(os.path.join(source, "process")).protective_by_channel()
    except Exception:  # noqa: BLE001 -- a source without a process record has no protective history
        return None
    return record or None


def _mark_inherited(obj, source):
    """Mark every `fact()` under `obj` as carried in from `source`, in place (skill #36).

    A channel's bare `fs_hz` is wrapped first: it is the one number a safety gate binds a filter
    to, and a bare value has nowhere to say where it came from. A fact the source had itself
    inherited keeps the project it was first carried from.
    """
    if isinstance(obj, list):
        for item in obj:
            _mark_inherited(item, source)
        return
    if not isinstance(obj, dict):
        return
    if "value" in obj and "source" in obj and "at" in obj:
        if obj.get("origin") != "inherited":
            obj["origin"], obj["inherited_from"] = "inherited", source
        return
    if "code" in obj and "fs_hz" in obj and obj["fs_hz"] is not None and not isinstance(obj["fs_hz"], dict):
        obj["fs_hz"] = {"value": obj["fs_hz"], "source": None, "at": None}
    for value in obj.values():
        _mark_inherited(value, source)


def seed(source, target, *, include_findings=False, copy_profile=True, note=DEFAULT_NOTE,
         today=None, seat=None, include_fs=True):
    """Copy `source`'s system parameters into `target`. Never writes into `source`.

    Refuses rather than merges when `target` already has a `project.json`: seeding is the first
    act of a new project, and quietly overwriting facts somebody has already confirmed is the one
    outcome nobody could want.

    The file is written through `Project.save()` -- so it is validated, written atomically, and
    gets `project_rev` 1 rather than inheriting the source's count of writes it was not part of.

    `copy_profile=False` says **the new build has a different processor**, and that is the whole
    of its meaning: the car still travels -- the same drivers in the same doors -- while `DSP_KEYS`
    stay behind with the profile file, because the source is the wrong authority on all of them.
    Capabilities, outputs and preset slots are then a question for the onboarding interview.

    The flag is named after the file it started with, and until 2026-09-02 that is all it skipped:
    the topology came across anyway, so the one documented path for "same car, new processor" was
    the one path that could not be used (public `skill#18`). Every caller already meant the wider
    thing -- `autosound-tcc`'s window computes it as `dsp_of(source) == (vendor, model)` -- so the
    behaviour was widened to the meaning rather than the name to the behaviour, which would have
    broken that caller for nothing.

    `seat` is the new project's `project_type`, chosen AT the copy (the Arbiter, 2026-09-22: "when we
    copy a project, the seat is exactly what I want to change"). The seat never travels -- another
    seat is why a copy exists -- so without it the copy starts with the seat open and the intake
    asks it; with it, the copy is born knowing what it is. An unknown seat refuses the copy.
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
    import project
    if seat is not None and seat not in project.PROJECT_TYPES:
        return Seeded(False, problem=f"seat {seat!r} is not one of {', '.join(project.PROJECT_TYPES)}")

    when = (today or date.today()).isoformat()
    name = os.path.basename(os.path.normpath(source))
    seeded = {"project_rev": 0}
    for key in (SYSTEM_KEYS if copy_profile else CAR_KEYS):
        if key in data:
            seeded[key] = json.loads(json.dumps(data[key]))
    skipped = [{"what": w, "why": why} for w, why in NEVER_TRAVELS.items()]
    history = {}
    # The user's controls travel, each wrapped as a fact so it can say it was carried in (a bare position from an
    # older file has nowhere to say it); `_mark_inherited` below marks them.
    controls = (seeded.get("hardware") or {}).get("controls") if isinstance(seeded.get("hardware"), dict) else None
    if isinstance(controls, dict):
        for name, pos in list(controls.items()):
            if not (isinstance(pos, dict) and "value" in pos):
                controls[name] = {"value": pos, "source": None, "at": None}
    # The drivers' Fs travel behind their own switch, on by default (the Arbiter: «імпеданс складна штука і
    # міряти його другий раз це подвиг»); off, they are left for this build to measure, and the record says so.
    if not include_fs:
        for row in seeded.get("channels") or []:
            if isinstance(row, dict) and row.get("fs_hz") is not None:
                row["fs_hz"] = None
        skipped.append({"what": "channels[].fs_hz", "why": "left out by the person's choice at the copy"})
    if copy_profile is False:
        skipped.append({"what": ", ".join(DSP_KEYS) + ", dsp_profile.json",
                        "why": "the new build has a different processor"})
    if include_findings:
        for key in FINDING_KEYS:
            if key in data:
                seeded[key] = data[key]
        if "acoustics" in seeded:
            seeded["acoustics"] = _carried_as_hypotheses(seeded["acoustics"])
    else:
        skipped.append({"what": ", ".join(FINDING_KEYS), "why": "the findings box was left off at the copy"})
    paths = data.get("paths")
    if isinstance(paths, dict):
        # An ABSOLUTE path travels only when it resolves on THIS machine (the Arbiter, 2026-09-23): a passenger copy
        # on the same Mac keeps its measurements folder, while a package imported on another MacBook (hub #186),
        # where the path resolves to nothing, keeps it as history -- a path to nothing reads as a place to look.
        travelling = {k: paths[k] for k in PATHS_THAT_TRAVEL
                      if k in paths and isinstance(paths[k], str)
                      and (not _absolute(paths[k]) or os.path.exists(paths[k]))}
        if travelling:
            seeded["paths"] = travelling
        stayed = {k: v for k, v in paths.items() if k not in travelling}
        if stayed:
            history["paths"] = stayed
    protective = _protective_history(source)
    if protective:
        history["protective"] = protective
    # ONE honest line instead of the source's own provenance lines (hub #186): copied forward, the note of
    # one import became a permanent part of the data, and a third generation would carry two of them with
    # no way to tell which import each describes. What came with the source is in `seeded_from`.
    seeded["sources"] = [f"system parameters seeded from project '{name}' on {when} — "
                         "inherited, not re-measured here (the import record is `seeded_from`)"]
    # The sentence above is for a person; these two are for the checks (skill #36). Every fact
    # that came across says so itself, and the project says where from, as a path a check can
    # resolve -- a source deleted two weeks later went unnoticed through four `contract.py check`s.
    _mark_inherited(seeded, source)
    # The IMPORT RECORD (hub #185): where from, when, what was taken, what was left and why, the choices made
    # at the copy, and the source's protective filters, knob positions and paths as HISTORY, never as
    # settings. Without it «no cabin flaws» could not be told from «flaws deliberately not carried».
    seeded["seeded_from"] = {"path": source, "project": name, "at": when,
                             "keys": sorted(k for k in seeded if k not in ("project_rev", "sources")),
                             "skipped": skipped,
                             "chosen": {"findings": bool(include_findings), "fs": bool(include_fs),
                                        "same_processor": bool(copy_profile), "seat": seat},
                             "history": history}
    if seat is not None:
        seeded["project_type"] = seat

    result = Seeded(True)
    try:
        project.Project(target).save(seeded)
    except Exception as exc:                # noqa: BLE001 -- the validator, or a disk that said no
        return Seeded(False, problem=f"{type(exc).__name__}: {exc}")
    result.written.append("project.json")

    os.makedirs(target, exist_ok=True)
    if write_gitignore(target):
        result.written.append(".gitignore")
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
    # hub #199 (TCC-026): the project is a repository in code, not by a line of prose. A git that is missing or
    # fails is said and does not undo the seed: a project is usable without history.
    try:
        import project_repo
        ok_repo, result.repo = project_repo.init(target)
        if ok_repo:
            result.written.append(".git")
    except Exception as exc:  # noqa: BLE001 -- history is an addition, never a reason to fail the seed
        result.repo = f"no repository made: {exc}"
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
                        help="the new build has a DIFFERENT processor: neither dsp_profile.json "
                             "nor anything bound to the old one (channels, glossary, "
                             "channel_summary, presets, hardware controls) is inherited")
    parser.add_argument("--note", default=DEFAULT_NOTE,
                        help="marker put at the top of each inherited prose file; "
                             "{source} and {when} are substituted")
    parser.add_argument("--no-fs", action="store_true",
                        help="leave the drivers' Fs behind: this build measures its own (they travel by "
                             "default, each marked as carried in; hub #185)")
    parser.add_argument("--seat", default=None,
                        help="the new project's seat (project_type: driver, passenger, both, all, "
                             "rear_left, rear_right). The seat never travels; without this the "
                             "copy starts with it open")
    parser.add_argument("--json", action="store_true", help="machine output")
    args = parser.parse_args(argv)

    if args.describe:
        summary = describe(args.source)
        if summary is None:
            print(f"project_seed: no readable project.json in {args.source}", file=sys.stderr)
            return 1
        print(json.dumps(vars(summary), indent=2, ensure_ascii=False) if args.json else
              f"{summary.car} · {summary.dsp or 'DSP not stated'} · "
              f"{summary.channels} channels · "
              + (f"{summary.flaws} flaws on offer (--findings, as hypotheses)"
                 if summary.flaws else "no flaw map to carry"))
        return 0

    if not args.target:
        parser.error("a target directory is required unless --describe is given")

    result = seed(args.source, args.target, include_findings=args.findings,
                  copy_profile=not args.no_profile, note=args.note, seat=args.seat,
                  include_fs=not args.no_fs)
    if args.json:
        print(json.dumps(vars(result), indent=2, ensure_ascii=False))
    elif not result.ok:
        print(f"project_seed: {result.problem}", file=sys.stderr)
    else:
        print(f"seeded {args.target} from {args.source}")
        print(f"  wrote     {', '.join(result.written)}")
        if result.repo:
            print(f"  history   {result.repo}")
        print(f"  carried   {result.channels} channels · {result.amps} amps"
              + (f" · {result.flaws} flaws (as hypotheses) · {result.questions} open questions"
                 if args.findings else ""))
        if PROFILE_FILE in result.written:
            print("  profile   inherited"
                  + (f", {result.profile_open} facts still open" if result.profile_open
                     else ", complete"))
        if args.no_profile:
            print("  processor left behind: no profile, no channels, no glossary, no presets, "
                  "no hardware controls — they belong to the DSP that changed")
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
        "channels": [{"code": "w-L", "role": "woofer", "fs_hz": 38},
                     {"code": "sw", "role": "sub",
                      "fs_hz": {"value": 29, "source": "measured", "at": "2026-07-01",
                                "origin": "inherited", "inherited_from": "/first/build"}}],
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
    os.environ["AUTOSOUND_NO_GH"] = "1"          # a seed makes a repository; the test never reaches GitHub
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
        # The seat never travels: the copy starts with it open, or born with the one chosen AT the
        # copy (2026-09-22) -- and an unknown seat refuses the whole copy.
        assert "project_type" not in got or got["project_type"] is None, got.get("project_type")
        sat = seed(src, os.path.join(tmp, "passenger-copy"), seat="passenger")
        assert sat.ok, sat.problem
        with open(os.path.join(tmp, "passenger-copy", "project.json"), encoding="utf-8") as f:
            assert json.load(f)["project_type"] == "passenger"
        bad = seed(src, os.path.join(tmp, "bad-seat"), seat="front_row")
        assert not bad.ok and "front_row" in bad.problem, bad
        assert not os.path.exists(os.path.join(tmp, "bad-seat", "project.json")), "a refused copy wrote"
        # The file says what happened to it.
        assert any("seeded from project 'old-car' on 2026-08-23" in s for s in got["sources"]), got
        # ...in ONE line: the source's own provenance lines do not pile up from copy to copy (hub #186).
        assert len(got["sources"]) == 1 and "measured 2026-07-01" not in got["sources"], got["sources"]
        # hub #185: the purpose and the control module's state never travel; the import record says what was
        # taken, what was left and why, and keeps the knob positions as HISTORY.
        assert not os.path.exists(os.path.join(dst, "preference-profile.md")), "the tune's purpose travelled"
        rec = got["seeded_from"]
        assert {s["what"] for s in rec["skipped"]} >= {"preference-profile.md"}, rec
        assert "hardware.controls" not in {s["what"] for s in rec["skipped"]}, "controls travel since 2026-09-23"
        assert rec["chosen"] == {"findings": False, "fs": True, "same_processor": True, "seat": None}, rec["chosen"]
        nofs = seed(src, os.path.join(tmp, "no-fs"), include_fs=False)
        assert nofs.ok, nofs.problem
        with open(os.path.join(tmp, "no-fs", "project.json"), encoding="utf-8") as f:
            nf = json.load(f)
        assert all(r.get("fs_hz") is None for r in nf["channels"]), nf["channels"]
        assert any(s["what"] == "channels[].fs_hz" for s in nf["seeded_from"]["skipped"]), nf["seeded_from"]
        # hub #186: an absolute path of the source machine never travels, and the knob positions come only
        # as history in the import record.
        with open(os.path.join(src, "project.json"), encoding="utf-8") as f:
            src_data = json.load(f)
        src_data.setdefault("hardware", {})["controls"] = {"SubRC": {"value": "7/12", "source": "user", "at": None}}
        src_data.setdefault("paths", {})["measurements_repo"] = "/Users/someone/cars/passat"
        with open(os.path.join(src, "project.json"), "w", encoding="utf-8") as f:
            json.dump(src_data, f)
        hx = seed(src, os.path.join(tmp, "history"))
        assert hx.ok, hx.problem
        with open(os.path.join(tmp, "history", "project.json"), encoding="utf-8") as f:
            hd = json.load(f)
        assert "paths" not in hd or "measurements_repo" not in hd["paths"], hd.get("paths")
        hist = hd["seeded_from"]["history"]
        assert hist["paths"]["measurements_repo"] == "/Users/someone/cars/passat", hist
        # ...while an absolute path that resolves HERE travels: a passenger copy on the same machine.
        src_data["paths"]["measurements_repo"] = tmp
        with open(os.path.join(src, "project.json"), "w", encoding="utf-8") as f:
            json.dump(src_data, f)
        assert seed(src, os.path.join(tmp, "same-machine")).ok
        with open(os.path.join(tmp, "same-machine", "project.json"), encoding="utf-8") as f:
            assert json.load(f)["paths"]["measurements_repo"] == tmp
        # The Arbiter, 2026-09-23: the user's controls travel, marked as carried in, so the check asks him.
        sub = hd["hardware"]["controls"]["SubRC"]
        assert sub["value"] == "7/12" and sub["origin"] == "inherited" and sub["inherited_from"] == os.path.abspath(src), sub
        assert "controls" not in hist, hist
        # ...and so does every fact that came across, as a field a check reads (skill #36): the
        # project names its source as a path, and a bare Fs is wrapped so it can say it too.
        assert got["seeded_from"]["path"] == os.path.abspath(src) and got["seeded_from"]["at"] == "2026-08-23"
        # hub #199: the seeded project is a git repository with a first commit, the .gitignore in it.
        import project_repo
        if shutil.which("git"):
            assert project_repo.is_repo(dst), "a seeded project must be a repository (TCC-026)"
            assert ".gitignore" in project_repo._git(dst, "ls-files").stdout.split()
        assert "channels" in got["seeded_from"]["keys"], got["seeded_from"]
        import project as _project
        carried = dict(_project.inherited_facts(got))
        assert carried["channels.w-L.fs_hz"]["value"] == 38 and \
            carried["channels.w-L.fs_hz"]["inherited_from"] == os.path.abspath(src), carried
        assert carried["channels.sw.fs_hz"]["origin"] == "inherited", carried
        assert carried["channels.sw.fs_hz"]["inherited_from"] == "/first/build", \
            "a fact the source had itself inherited keeps where it was first carried from"

        # An allowlist, not a blocklist: the ledger is not excluded by a rule, it is never reached.
        assert not os.path.exists(os.path.join(dst, "state")), "the ledger must not travel"

        # ── the .gitignore is WRITTEN, not promised (HUB-025) ────────────────────────────────
        # `setup-critic-channel.md` claimed "it's gitignored" while nothing wrote one, and README
        # recommends backing this folder up to a private GitHub. This is the carrier that claim
        # never had; the key living outside the project is the first line, this is the second.
        gi_path = os.path.join(dst, ".gitignore")
        assert os.path.isfile(gi_path), "a fresh project must carry a .gitignore"
        assert ".gitignore" in out.written, out.written
        with open(gi_path, encoding="utf-8") as f:
            gi = f.read()
        for rule in (".critic-env", "rew_analitic/.critic-env", ".mcp.json", ".tcc/", "*.mdat"):
            assert any(ln.strip() == rule for ln in gi.splitlines()), (rule, gi)
        # And it says where the key SHOULD live, because a rule with no alternative just moves
        # the problem to wherever the user puts the file next.
        assert "critic-env" in gi and ".config/autosound" in gi, gi

        # An existing .gitignore is left alone: a project may already carry rules somebody meant.
        keep = os.path.join(tmp, "has-own")
        os.makedirs(keep, exist_ok=True)
        with open(os.path.join(keep, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("mine\n")
        assert write_gitignore(keep) is False, "an existing .gitignore must not be rewritten"
        with open(os.path.join(keep, ".gitignore"), encoding="utf-8") as f:
            assert f.read() == "mine\n", "the user's rules survived"

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
        # A different processor: the CAR still travels, everything bound to the old DSP does not
        # (2026-09-02, public `skill#18`). Until then this flag skipped the profile FILE only, so
        # the old output list arrived anyway and "same car, new processor" -- the normal shape of
        # a rebuild -- was the one documented path that could not be used.
        fourth = os.path.join(tmp, "fourth")
        no_p = seed(src, fourth, copy_profile=False, include_findings=True)
        assert PROFILE_FILE not in no_p.written and no_p.profile_open == 0, no_p
        with open(os.path.join(fourth, "project.json"), encoding="utf-8") as fh:
            newdsp = json.load(fh)
        assert newdsp["car"]["model"] == "Passat B8" and len(newdsp["amps"]) == 2, newdsp
        assert not any(k in newdsp for k in DSP_KEYS), \
            [k for k in DSP_KEYS if k in newdsp]
        assert no_p.channels == 0 and no_p.amps == 2, no_p
        # ...and the findings are still reachable on that path. Wanting them WITHOUT the old
        # topology used to mean getting neither: findings travel only with the seeder, and the
        # seeder brought the channels along, so the correct move was to bypass it by hand.
        assert no_p.flaws == 1 and newdsp["acoustics"]["flaws"][0]["status"] == "hypothesis", no_p

        summary = describe(src)
        assert (summary.car, summary.channels) == ("VW Passat B8 2017", 2), summary
        # ...and it says how much `--findings` is offering, BEFORE the choice (2026-09-02). The
        # checkbox shipped before this number did, so a window could ask "carry the findings?"
        # while neither it nor the person could see whether that meant three rows or eighteen.
        # `Seeded.flaws` answers afterwards, which is the wrong side of the decision.
        assert summary.flaws == 1, summary
        assert describe(dst).flaws == 0, "a copy seeded without --findings offers none"
        assert describe(os.path.join(tmp, "third")).flaws == 1, "a copy WITH them offers them on"
        assert dsp_of(src) == ("Audiotec-Fischer", "Helix DSP Ultra S"), dsp_of(src)
        assert describe(os.path.join(tmp, "nowhere")) is None

    print(f"selftest OK -- system travels (2 channels, 2 amps), findings and ledger stay behind, "
          f"only measurements_repo of 4 paths, project_rev 1 not inherited, "
          f"profile carried with {out.profile_open} facts still open, re-seed refused; "
          f"a new processor keeps the car and drops all {len(DSP_KEYS)} DSP-bound keys, "
          f"findings still on offer there")


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
