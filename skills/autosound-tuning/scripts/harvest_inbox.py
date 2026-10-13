#!/usr/bin/env python3
"""Turn a project's `skill-inbox.md` into a feedback package the maintainer can read.

WHY THIS EXISTS. `skill-inbox.md` was created in every project, recommended by `SKILL.md` and
collected by `feedback-loop.md` — and read by nothing. A file with no reader is not a carrier of
anything: what a tuner wrote into it stayed in that project until the project was forgotten. The
2026-09-09 release review found it named as dead in one document while three others still fed it.
The user's ruling was to keep it and give it a reader. This is the reader.

WHAT IT DOES NOT DO. It never posts anything. It writes a file and prints its path; the Arbiter
reads it and decides whether any of it becomes a public issue. That boundary is the whole safety
model here: a project's notes are written in a car with a person's name, address and habits nearby,
and a script that could publish them would eventually publish them. What this can do instead is
POINT AT what looks personal (`--check` runs only that pass), so the person deciding sees it.

SHAPE. The package follows the template already fixed in `feedback-loop.md` — the same headings, in
the same order, so a maintainer reads every package the same way. Sources, at the project root, their
home (#143, I-21; an older project's in `rew_analitic/` are read too, each with a warning naming the move):
  * `<project>/skill-inbox.md` — the tuner's own notes, section by section;
  * `<project>/tuning-changelog*` — every `Lesson:` line, which is where a lesson
    lands when there was no time to open the inbox.

  harvest_inbox.py <project> [--out FILE] [--check] [--json]
  harvest_inbox.py --selftest

A source that is there and cannot be read (not UTF-8, a permission refused) -- or a folder of them it cannot list or
search -- stops the harvest, named with its repair (W-8 #136's rule): a package without it would be one the person
never sees is short.

Exit codes: 0 done (`--check`: nothing looks personal) · 1 `--check` found something to look at · 2 refused, nothing
written -- no inbox, a source that cannot be read, or a usage error. A refusal is 2, not 1: under `--check` a 1 says
"look before you send", and a refusal must not read as that.
stdlib only.
"""
import argparse
import io
import json
import os
import re
import stat
import sys

INBOX = "skill-inbox.md"
CHANGELOG_GLOB = "tuning-changelog"
#: Where an older project keeps the prose files whose home is the project root (#143, I-21).
OLD_HOME = "rew_analitic"
LESSON = re.compile(r"^\s*[-*]?\s*Lesson:\s*(?P<text>.+?)\s*$", re.I)

# The package's fixed headings (feedback-loop.md). A package that invents its own order costs the
# maintainer a re-read of every one; these are the sections and this is the order.
SECTIONS = ["Setup (equipment classes, no personal data)",
            "What worked",
            "What did NOT work / where the skill erred or was silent",
            "New techniques / know-how",
            "DSP/hardware quirks",
            "This body's cabin anomalies"]

# What "looks personal" means here: things that identify a PERSON or a MACHINE rather than a car
# model or a driver. Reported, never removed -- a redaction nobody saw is how a package quietly
# loses the fact that made it worth sending.
PERSONAL = [
    # A KEY first, because this is the one that cannot be taken back. The package is the thing most
    # likely to be pasted into a public issue, and a key pasted once is a key that has left the
    # machine for good. The rule this serves: the key lives OUTSIDE the project
    # (`~/.config/autosound/critic-env`), the wrappers refuse a project file that git would take,
    # the doctor prints only the key's SHAPE — and nothing that leaves here may carry one.
    ("an API key (AI Studio, current shape)", re.compile(r"\bAQ\.[A-Za-z0-9_\-]{20,}")),
    ("an API key (AI Studio, older shape)", re.compile(r"\bAIza[A-Za-z0-9_\-]{30,}")),
    ("an API key (OpenAI shape)", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("an API key (Anthropic shape)", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("a named key assignment", re.compile(r"(?i)\b[A-Z_]*(?:API_KEY|TOKEN|SECRET)\s*=\s*\S+")),
    ("a bearer token", re.compile(r"(?i)\bauthorization:\s*bearer\s+\S+")),
    ("an e-mail address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("a home path", re.compile(r"(/Users/|/home/|C:\\\\Users\\\\)[^\s/\\\\]+")),
    ("a plate-like token", re.compile(r"\b[A-ZА-ЯІЇЄ]{2}\s?\d{4}\s?[A-ZА-ЯІЇЄ]{2}\b")),
    ("a phone number", re.compile(r"(?<!\d)\+?\d[\d ()-]{8,}\d(?!\d)")),
    ("a coordinate pair", re.compile(r"\b-?\d{1,3}\.\d{4,},\s*-?\d{1,3}\.\d{4,}\b")),
]


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.realpath(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "rew_tool"))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


def _read(path):
    """`(text, None)`, or `(None, "<path> <reason> -- <repair>")` for a file that is there and cannot be read: not
    UTF-8, or refused (group fix 1, I3; W-8 #136). The repair of a refusal is its cause's, `project_io.repair_for` --
    a permission on POSIX, what holds the file on Windows. It was None, and the file was read as absent."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            return fh.read(), None
    except UnicodeDecodeError:
        return None, f"{path} is not UTF-8 -- save it as UTF-8 and run this again"
    except OSError as exc:
        return None, f"{path} cannot be opened ({exc}) -- {_siblings().load('project_io.py').repair_for(exc)}"


def inbox_sections(text):
    """`## heading` -> its body, in the order the file has them. Empty bodies are dropped."""
    out = {}
    current = None
    for line in (text or "").splitlines():
        head = re.match(r"^##\s+(.*?)\s*$", line)
        if head:
            current = head.group(1)
            out.setdefault(current, [])
        elif current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items() if "\n".join(v).strip()}


def _moved(project, path):
    """The warning for a prose file read from `rew_analitic/`: it names the file and its home, the project root. Where
    the root holds a file of that name already, the copy is merged into it and deleted -- "move it" there invites the
    `mv` that writes over the root's notes (group fix 1, I3), as `process.py`'s `handoff` says of a changelog copy."""
    home = os.path.join(project, os.path.basename(path))
    if os.path.exists(home):
        return f"{path} is read from {OLD_HOME}/, and the project root holds {home}, its home — merge what it adds " \
               f"there and delete the copy"
    return f"{path} is read from {OLD_HOME}/: its home is the project root — move it to {home}"


def _is_file(path):
    """True when `path` is a file, False when it is not there or is no file, None when that cannot be told -- the folder
    it is in may not be searched (R56). `os.path.isfile` read the last as absent, and the file went unsaid; a caller
    takes a None as a file, so that `_read` names what refused it."""
    try:
        return stat.S_ISREG(os.stat(path).st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return None


def _inboxes(project):
    """`(paths, warnings)`: the project root's `skill-inbox.md`, then an older project's in `rew_analitic/` with the
    line naming the move -- both, when both are there: an older project's root inbox is often the intake's rules header
    alone, its lessons in the copy, and reading the root's only came back empty. One that cannot be told from absent
    -- its folder may not be searched -- is listed too, and `_read` says what refused it (R56)."""
    paths, warnings = [], []
    for folder in (project, os.path.join(project, OLD_HOME)):
        path = os.path.join(folder, INBOX)
        if _is_file(path) is not False:
            paths.append(path)
            if folder != project:
                warnings.append(_moved(project, path))
    return paths, warnings


def _changelogs(project):
    """`(paths, warnings, unreadable)`: every `tuning-changelog*` at the project root, then those an older project keeps
    in `rew_analitic/`, each of these with the line naming the move -- and the line naming each folder that is there
    and cannot be listed, with its repair: it was skipped unsaid, its lessons with it (R56). A folder that is not there
    has nothing to say."""
    paths, warnings, unreadable = [], [], []
    for folder in (project, os.path.join(project, OLD_HOME)):
        try:
            entries = os.listdir(folder)
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError as exc:
            unreadable.append(f"{folder} cannot be listed ({exc}) -- "
                              f"{_siblings().load('project_io.py').repair_for(exc)}")
            continue
        names = sorted(n for n in entries if n.startswith(CHANGELOG_GLOB) and _is_file(os.path.join(folder, n))
                       is not False)
        paths += [os.path.join(folder, n) for n in names]
        if folder != project:
            warnings += [_moved(project, os.path.join(folder, n)) for n in names]
    return paths, warnings, unreadable


def _lessons(project):
    """`(lessons, unreadable)`: every `Lesson:` line from the project's changelogs, in file order, and the line naming
    each changelog that cannot be read, or folder that cannot be listed, with its repair (`_read`, `_changelogs`)."""
    paths, _warnings, unreadable = _changelogs(project)
    found = []
    for path in paths:
        text, why = _read(path)
        if why:
            unreadable.append(why)
        for line in (text or "").splitlines():
            m = LESSON.match(line)
            if m:
                found.append(m.group("text"))
    return found, unreadable


def lessons(project):
    """Every `Lesson:` line from the project's changelog, in file order. A changelog that cannot be read raises
    `ValueError` naming it and its repair: it was read as one with no lessons."""
    found, unreadable = _lessons(project)
    if unreadable:
        raise ValueError("; ".join(unreadable))
    return found


def personal_hits(text):
    """[(what, the matched text)] — reported so a human decides, never edited out."""
    hits = []
    for what, rx in PERSONAL:
        for m in rx.finditer(text or ""):
            hits.append((what, m.group().strip()))
    return hits


def build(project, skill_version="unknown"):
    """The package as text, plus what a reader must look at before sending it -- and, in `unreadable`, the line naming
    each source that is there and cannot be read: a package built without it is not one to send (`_main` refuses)."""
    inbox_paths, warnings = _inboxes(project)
    read = [_read(path) for path in inbox_paths]
    texts = [text for text, _why in read if text is not None]
    found_lessons, unreadable = _lessons(project)
    unreadable = [why for _text, why in read if why] + unreadable
    warnings = warnings + _changelogs(project)[1]
    # Both inboxes add up, the root's first: a heading in both carries both bodies.
    sections = {}
    for text in texts:
        for name, body in inbox_sections(text).items():
            sections[name] = f"{sections[name]}\n\n{body}" if name in sections else body
    body = [f"# Feedback: <car/body> · <DSP> · <date> · skill {skill_version}", ""]
    for name in SECTIONS:
        body.append(f"## {name}")
        match = next((v for k, v in sections.items() if k.lower().startswith(name.split(" (")[0].lower())), "")
        body.append(match if match else "_(nothing recorded)_")
        body.append("")
    if found_lessons:
        body += ["## Lessons picked up from the changelog", ""]
        body += [f"- {line}" for line in found_lessons] + [""]
    text = "\n".join(body)
    return text, {
        "inbox_found": bool(texts),
        "sections_with_content": sorted(sections),
        "lessons": found_lessons,
        "personal": personal_hits(text),
        "warnings": warnings,
        "unreadable": unreadable,
    }


def _main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("project", nargs="?")
    p.add_argument("--out", default=None, help="where to write the package (default: <project>/feedback-package.md)")
    p.add_argument("--check", action="store_true", help="only report what looks personal; write nothing")
    p.add_argument("--json", action="store_true")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.project:
        p.error("a project directory is required (or --selftest)")
    text, report = build(args.project)
    unreadable = report.pop("unreadable")
    if unreadable:
        # Before "no inbox": a root inbox that cannot be read is no missing one (group fix 1, I3).
        for line in unreadable:
            print(f"error: {line}", file=sys.stderr)
        return 2
    if not report["inbox_found"]:
        print(f"error: no {INBOX} at {args.project} (nor in {OLD_HOME}/) — its home, where the intake creates it; "
              f"nothing to harvest", file=sys.stderr)
        return 2
    for line in report["warnings"]:
        print(f"warning: {line}", file=sys.stderr)
    if args.json:
        print(json.dumps({**report, "package": text}, ensure_ascii=False, indent=2))
        return 0
    for what, hit in report["personal"]:
        print(f"LOOKS PERSONAL — {what}: {hit}", file=sys.stderr)
    if args.check:
        print(f"{len(report['personal'])} thing(s) to look at before this is sent anywhere")
        return 1 if report["personal"] else 0
    out = args.out or os.path.join(args.project, "feedback-package.md")
    io.open(out, "w", encoding="utf-8").write(text)
    print(f"package written: {out}")
    print(f"  sections with content: {len(report['sections_with_content'])}"
          f" · lessons from the changelog: {len(report['lessons'])}"
          f" · looks personal: {len(report['personal'])}")
    print("  NOTHING was posted. Read it, decide what is public, then open the issue yourself.")
    return 0


def _run(argv):
    """`_main(argv)` in this process: `(exit code, stdout, stderr)`."""
    import contextlib
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = _main(argv)
        except SystemExit as stop:
            code = stop.code
    return code, out.getvalue(), err.getvalue()


def _project(top, name, inbox_in=None, changelog_in=None):
    """A project folder under `top` with the inbox and a changelog written into the folders named (`""` the root,
    `"rew_analitic"` the old home, None none)."""
    proj = os.path.join(top, name)
    os.makedirs(os.path.join(proj, "rew_analitic"))
    if inbox_in is not None:
        io.open(os.path.join(proj, inbox_in, "skill-inbox.md"), "w", encoding="utf-8").write(
            "# Inbox\n\n## What worked\nLR24 at 80 Hz held the joint.\n")
    if changelog_in is not None:
        io.open(os.path.join(proj, changelog_in, "tuning-changelog.md"), "w", encoding="utf-8").write(
            "- Lesson: the tripod moves the answer\n")
    return proj


def _check_the_inbox_at_the_root():
    """#143, I-21: the project root is the home of `skill-inbox.md` and `tuning-changelog`, and they are harvested
    there, nothing said. It read `rew_analitic/` only: an inbox at the root, where the intake makes it, was "none"."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="harvest_inbox_root_")
    failures = []
    try:
        proj = _project(top, "car", inbox_in="", changelog_in="")
        code, out, err = _run([proj, "--json"])
        report = json.loads(out) if code == 0 else {}
        if code != 0 or not report.get("inbox_found") or "LR24 at 80 Hz" not in report.get("package", "") \
                or report.get("lessons") != ["the tripod moves the answer"] or report.get("warnings") != [] \
                or err.strip():
            failures.append(f"exit {code}, {report or out!r}, said {err.strip()!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the inbox at the project root:"] + failures)


def _check_the_old_home_is_read_and_said():
    """#143, I-21: an older project's inbox and changelog in `rew_analitic/` are harvested, each with one warning line
    naming the file and where to move it -- the project root; a root file wins over its copy there, unsaid."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="harvest_inbox_old_home_")
    failures = []
    try:
        proj = _project(top, "car", inbox_in="rew_analitic", changelog_in="rew_analitic")
        code, out, err = _run([proj, "--json"])
        report = json.loads(out) if code == 0 else {}
        if code != 0 or not report.get("inbox_found") or "LR24 at 80 Hz" not in report.get("package", "") \
                or report.get("lessons") != ["the tripod moves the answer"]:
            failures.append(f"not harvested: exit {code}, {report or out!r}")
        said = [ln for ln in err.splitlines() if ln.startswith("warning: ")]
        for name in ("skill-inbox.md", "tuning-changelog.md"):
            old, home = os.path.join(proj, "rew_analitic", name), os.path.join(proj, name)
            if len([ln for ln in said if old in ln and home in ln]) != 1:
                failures.append(f"{name}: no one line naming {old} and {home}: {said!r}")
        if len(said) != 2 or report.get("warnings") != [ln[len("warning: "):] for ln in said]:
            failures.append(f"the warnings: said {said!r}, the report's {report.get('warnings')!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the old home, rew_analitic/:"] + failures)


def _check_both_inboxes_are_harvested():
    """#143, I-21 (fix 2): where both folders hold an inbox or a changelog, both are harvested -- the root's first,
    then the `rew_analitic/` copy with its move warning; sections and `Lesson:` lines add up. The root's won silently,
    and an older project's harvest came back empty: its root inbox is the intake's rules header, its lessons are in
    `rew_analitic/skill-inbox.md`."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="harvest_inbox_both_")
    failures = []
    try:
        proj = _project(top, "car")
        old = os.path.join(proj, "rew_analitic")
        io.open(os.path.join(proj, "skill-inbox.md"), "w", encoding="utf-8").write(
            "# Skill inbox\n\nRules: one line per lesson, 📚 and why.\n\n## What worked\n\n## DSP/hardware quirks\n")
        io.open(os.path.join(old, "skill-inbox.md"), "w", encoding="utf-8").write(
            "# Skill inbox\n\n## What worked\nTHE OLD LESSON: LR24 at 80 Hz held the joint.\n")
        io.open(os.path.join(proj, "tuning-changelog.md"), "w", encoding="utf-8").write("- Lesson: the root's\n")
        io.open(os.path.join(old, "tuning-changelog.md"), "w", encoding="utf-8").write("- Lesson: the copy's\n")
        code, out, err = _run([proj, "--json"])
        report = json.loads(out) if code == 0 else {}
        if code != 0 or "THE OLD LESSON" not in report.get("package", "") \
                or report.get("lessons") != ["the root's", "the copy's"]:
            failures.append(f"the old layout: exit {code}, {report or out!r}")
        said = [ln for ln in err.splitlines() if ln.startswith("warning: ")]
        for name in ("skill-inbox.md", "tuning-changelog.md"):
            if len([ln for ln in said if os.path.join(old, name) in ln and os.path.join(proj, name) in ln]) != 1:
                failures.append(f"{name}: no one line naming the copy and its home: {said!r}")
        if len(said) != 2:
            failures.append(f"{len(said)} warning line(s), not 2: {said!r}")
        # Both with something to say under one heading: the root's first, then the copy's.
        io.open(os.path.join(proj, "skill-inbox.md"), "w", encoding="utf-8").write(
            "## What worked\nTHE ROOT'S LESSON\n")
        code, out, err = _run([proj, "--json"])
        package = json.loads(out).get("package", "") if code == 0 else ""
        at = [package.find(s) for s in ("THE ROOT'S LESSON", "THE OLD LESSON")]
        if code != 0 or -1 in at or at != sorted(at) or package.count("## What worked") != 1:
            failures.append(f"one heading in both: exit {code}, {package!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["both folders:"] + failures)


def _check_no_inbox_names_the_root():
    """#143, I-21: with no inbox at the root nor in `rew_analitic/`, today's refusal (exit 2, nothing written) names the
    project root, the inbox's home -- it named `rew_analitic/`."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="harvest_inbox_none_")
    failures = []
    try:
        proj = _project(top, "car", changelog_in="")
        code, out, err = _run([proj])
        if code != 2 or f"error: no skill-inbox.md at {proj}" not in err \
                or os.path.exists(os.path.join(proj, "feedback-package.md")):
            failures.append(f"exit {code}, said {err.strip()!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["no inbox:"] + failures)


def _check_a_file_that_cannot_be_read_stops_the_harvest():
    """Group fix 1, I3 (W-8 #136's rule): an inbox or a changelog that is there and cannot be read -- not UTF-8, a
    permission refused -- stops the harvest: one `error: <file> <reason> -- <repair>` line each, exit 2 (the module's
    refusal, as for no inbox; 1 is `--check`'s "something to look at"), nothing written, nothing on stdout. It was read
    as absent and left out of the package unsaid -- a root inbox that could not be read was "no inbox", a changelog's
    lessons simply missing."""
    import shutil
    import stat
    import tempfile
    top = tempfile.mkdtemp(prefix="harvest_inbox_unreadable_")
    failures = []
    try:
        cases = [("the root's inbox", "", "skill-inbox.md"), ("the copy's inbox", "rew_analitic", "skill-inbox.md"),
                 ("a changelog", "", "tuning-changelog.md"), ("the copy's changelog", "rew_analitic", "tuning-changelog.md")]
        for n, (label, folder, name) in enumerate(cases):
            proj = _project(top, f"car{n}", inbox_in="", changelog_in="")
            bad = os.path.join(proj, folder, name)
            with open(bad, "wb") as fh:
                fh.write(b"## What worked\n\xff\xfe a note in another encoding\n")
            for argv in ([proj], [proj, "--json"], [proj, "--check"]):
                code, out, err = _run(argv)
                said = [ln for ln in err.splitlines() if ln.startswith("error: ")]
                if code != 2 or out.strip() or os.path.exists(os.path.join(proj, "feedback-package.md")) \
                        or [ln for ln in said if bad in ln] != [f"error: {bad} is not UTF-8 -- save it as UTF-8 and "
                                                                f"run this again"]:
                    failures.append(f"{label}, not UTF-8, {argv[1:]}: exit {code}, out {out.strip()[:80]!r}, "
                                    f"said {err.strip()!r}")
        if os.name == "posix" and os.geteuid() != 0:
            proj = _project(top, "car-locked", inbox_in="", changelog_in="")
            locked = os.path.join(proj, "skill-inbox.md")
            os.chmod(locked, 0)
            try:
                code, out, err = _run([proj])
            finally:
                os.chmod(locked, stat.S_IRUSR | stat.S_IWUSR)
            said = [ln for ln in err.splitlines() if ln.startswith(f"error: {locked} cannot be opened (")]
            if code != 2 or len(said) != 1 or "give it access" not in said[0] \
                    or os.path.exists(os.path.join(proj, "feedback-package.md")):
                failures.append(f"a root inbox this user may not read: exit {code}, said {err.strip()!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a file the harvest cannot read:"] + failures)


def _check_a_folder_that_cannot_be_read_is_said():
    """R56 (group fix 1's leftover, the class of I3): a folder the harvest cannot list or search is said, not skipped.
    `_changelogs` skipped a folder it could not list (`except OSError: continue`), and `_inboxes` asked `isfile`, which
    reads a file in a folder it may not search as absent: an older project's `rew_analitic/` with its mode wrong left
    its inbox and its lessons out of the package, unsaid. Each is one `error: <what> ... -- <repair>` line, exit 2, as
    a file that cannot be read. A folder that is not there is still nothing to say. POSIX only, and not as root (a mode
    is no refusal to root)."""
    if os.name != "posix" or os.geteuid() == 0:
        return
    import shutil
    import stat
    import tempfile
    top = tempfile.mkdtemp(prefix="harvest_inbox_folder_")
    failures = []
    try:
        # A folder this user may neither list nor search (mode 0), and one it may list but not search (r--).
        for label, mode, want in (("rew_analitic/ unlistable", 0, ("rew_analitic cannot be listed (",
                                                                   "skill-inbox.md cannot be opened (")),
                                  ("rew_analitic/ unsearchable", stat.S_IRUSR,
                                   ("tuning-changelog.md cannot be opened (", "skill-inbox.md cannot be opened ("))):
            proj = _project(top, label.split()[1], inbox_in="rew_analitic", changelog_in="rew_analitic")
            io.open(os.path.join(proj, "skill-inbox.md"), "w", encoding="utf-8").write("## What worked\nthe root's\n")
            old = os.path.join(proj, "rew_analitic")
            os.chmod(old, mode)
            try:
                code, out, err = _run([proj])
            finally:
                os.chmod(old, stat.S_IRWXU)
            said = [ln for ln in err.splitlines() if ln.startswith("error: ")]
            missing = [w for w in want if not any(w in ln and "give it access" in ln for ln in said)]
            if code != 2 or missing or out.strip() or os.path.exists(os.path.join(proj, "feedback-package.md")):
                failures.append(f"{label}: exit {code}, not said {missing}, said {err.strip()!r}")
        # The project root itself, unsearchable: its inbox is not "no inbox".
        proj = _project(top, "root", inbox_in="", changelog_in="")
        os.chmod(proj, stat.S_IRUSR)
        try:
            code, out, err = _run([proj])
        finally:
            os.chmod(proj, stat.S_IRWXU)
        said = [ln for ln in err.splitlines() if ln.startswith("error: ")]
        if code != 2 or not any("skill-inbox.md cannot be opened (" in ln for ln in said) \
                or any(f"no {INBOX}" in ln for ln in said):
            failures.append(f"the root unsearchable: exit {code}, said {err.strip()!r}")
        # No rew_analitic/ at all: nothing to say, the root's inbox harvested.
        proj = os.path.join(top, "fresh")
        os.makedirs(proj)
        io.open(os.path.join(proj, "skill-inbox.md"), "w", encoding="utf-8").write("## What worked\nthe root's\n")
        code, out, err = _run([proj, "--json"])
        if code != 0 or err.strip():
            failures.append(f"no rew_analitic/: exit {code}, said {err.strip()!r}")
    finally:
        for folder, _dirs, _files in os.walk(top):
            os.chmod(folder, stat.S_IRWXU)
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a folder the harvest cannot read:"] + failures)


def _check_a_copy_beside_the_roots_is_merged_not_moved():
    """Group fix 1, I3: a `rew_analitic/` inbox or changelog whose name the project root holds already is told to be
    merged into the root's and deleted -- "move it to <root>/<name>" there invites the `mv` that writes over the root's
    notes. As `process.py`'s `handoff` says of a changelog copy. "Move it" stays for a copy the root has no file of."""
    import shutil
    import tempfile
    top = tempfile.mkdtemp(prefix="harvest_inbox_merge_")
    failures = []
    try:
        proj = _project(top, "car", inbox_in="", changelog_in="")
        old = os.path.join(proj, "rew_analitic")
        for name in ("skill-inbox.md", "tuning-changelog.md"):
            io.open(os.path.join(old, name), "w", encoding="utf-8").write("## What worked\n- Lesson: the copy's\n")
        code, out, err = _run([proj, "--json"])
        said = [ln for ln in err.splitlines() if ln.startswith("warning: ")]
        for name in ("skill-inbox.md", "tuning-changelog.md"):
            copy, home = os.path.join(old, name), os.path.join(proj, name)
            mine = [ln for ln in said if copy in ln]
            if code != 0 or len(mine) != 1 or home not in mine[0] or "merge what it adds there and delete the copy" \
                    not in mine[0] or "move it" in mine[0]:
                failures.append(f"{name}, the root's beside it: exit {code}, said {mine or said!r}")
        os.remove(os.path.join(proj, "tuning-changelog.md"))
        code, out, err = _run([proj, "--json"])
        copy = os.path.join(old, "tuning-changelog.md")
        mine = [ln for ln in err.splitlines() if ln.startswith("warning: ") and copy in ln]
        if code != 0 or len(mine) != 1 or f"move it to {os.path.join(proj, 'tuning-changelog.md')}" not in mine[0]:
            failures.append(f"a changelog copy, none at the root: exit {code}, said {mine!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a copy in rew_analitic/ beside the root's:"] + failures)


def _selftest():
    import shutil
    import tempfile
    failures = []
    for check in (_check_the_inbox_at_the_root, _check_the_old_home_is_read_and_said, _check_both_inboxes_are_harvested,
                  _check_no_inbox_names_the_root, _check_a_file_that_cannot_be_read_stops_the_harvest,
                  _check_a_copy_beside_the_roots_is_merged_not_moved, _check_a_folder_that_cannot_be_read_is_said):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    tmp = tempfile.mkdtemp(prefix="harvest_inbox_")
    try:
        proj = os.path.join(tmp, "car")
        os.makedirs(os.path.join(proj, "rew_analitic"))
        io.open(os.path.join(proj, INBOX), "w", encoding="utf-8").write(
            "# Inbox\n\n## What worked\nLR24 at 80 Hz held the joint.\n\n"
            "## DSP/hardware quirks\nThe Phase control is one APF2.\n")
        io.open(os.path.join(proj, "tuning-changelog.md"), "w",
                encoding="utf-8").write("- Lesson: never sweep a tweeter bare\nnoise\n"
                                        "Lesson: the tripod moves the answer\n")
        text, report = build(proj)
        assert report["inbox_found"], report
        assert "LR24 at 80 Hz" in text, text
        assert "The Phase control is one APF2" in text, text
        assert report["lessons"] == ["never sweep a tweeter bare",
                                     "the tripod moves the answer"], report["lessons"]
        # every fixed heading is present even when the project said nothing under it
        for name in SECTIONS:
            assert f"## {name}" in text, name
        assert text.count("_(nothing recorded)_") == len(SECTIONS) - 2, text

        # a project with no inbox is a refusal, not an empty package
        bare = os.path.join(tmp, "bare")
        os.makedirs(bare)
        assert build(bare)[1]["inbox_found"] is False

        # what looks personal is NAMED, and naming it is all this does
        hits = personal_hits("write to bob@example.com from /Users/bob/car, +38 050 123 4567")
        kinds = {what for what, _ in hits}
        assert "an e-mail address" in kinds and "a home path" in kinds, hits
        assert "a phone number" in kinds, hits

        # A KEY is the one that cannot be taken back once a package is pasted in public.
        for sample, expect in [
                ("GEMINI_API_KEY=AQ." + "x" * 53, "an API key (AI Studio, current shape)"),
                ("key AIza" + "y" * 35, "an API key (AI Studio, older shape)"),
                ("sk-" + "z" * 40, "an API key (OpenAI shape)"),
                ("Authorization: Bearer abc123def456", "a bearer token"),
                ("OPENAI_API_KEY=whatever", "a named key assignment")]:
            found = {what for what, _ in personal_hits(sample)}
            assert expect in found, (sample[:24], found)
        assert personal_hits("LR24 at 80 Hz, 3.15 kHz, +4 dB") == [], \
            personal_hits("LR24 at 80 Hz, 3.15 kHz, +4 dB")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK — inbox sections and changelog `Lesson:` lines land in the fixed package "
          "shape, read at the project root and, added after them, an older project's in rew_analitic/ "
          "with a warning naming the move (a merge where the root holds the file), a missing inbox and a source "
          "or a folder that cannot be read are refused rather than answered with an empty or a short package, and "
          "an API KEY in any of the four shapes, an e-mail, a home path and a phone are NAMED "
          "while ordinary tuning numbers are not — a key that leaves the machine once has left "
          "it for good")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
