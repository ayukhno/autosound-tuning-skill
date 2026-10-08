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

stdlib only.
"""
import argparse
import io
import json
import os
import re
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


def _read(path):
    try:
        return io.open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return None


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
    """The warning for a prose file read from `rew_analitic/`: it names the file and its home, the project root."""
    return f"{path} is read from {OLD_HOME}/: its home is the project root — move it to " \
           f"{os.path.join(project, os.path.basename(path))}"


def _inbox(project):
    """`(path, warnings)`: the project root's `skill-inbox.md`, else an older project's in `rew_analitic/` with the
    line naming the move; `(None, [])` when there is neither."""
    for folder in (project, os.path.join(project, OLD_HOME)):
        path = os.path.join(folder, INBOX)
        if os.path.isfile(path):
            return path, ([] if folder == project else [_moved(project, path)])
    return None, []


def _changelogs(project):
    """`(paths, warnings)`: every `tuning-changelog*` at the project root; with none there, those an older project
    keeps in `rew_analitic/`, each with the line naming the move."""
    for folder in (project, os.path.join(project, OLD_HOME)):
        try:
            names = sorted(n for n in os.listdir(folder)
                           if n.startswith(CHANGELOG_GLOB) and os.path.isfile(os.path.join(folder, n)))
        except OSError:
            continue
        if names:
            paths = [os.path.join(folder, n) for n in names]
            return paths, ([] if folder == project else [_moved(project, p) for p in paths])
    return [], []


def lessons(project):
    """Every `Lesson:` line from the project's changelog, in file order."""
    found = []
    for path in _changelogs(project)[0]:
        for line in (_read(path) or "").splitlines():
            m = LESSON.match(line)
            if m:
                found.append(m.group("text"))
    return found


def personal_hits(text):
    """[(what, the matched text)] — reported so a human decides, never edited out."""
    hits = []
    for what, rx in PERSONAL:
        for m in rx.finditer(text or ""):
            hits.append((what, m.group().strip()))
    return hits


def build(project, skill_version="unknown"):
    """The package as text, plus what a reader must look at before sending it."""
    inbox_path, warnings = _inbox(project)
    inbox_text = _read(inbox_path) if inbox_path else None
    warnings = warnings + _changelogs(project)[1]
    sections = inbox_sections(inbox_text)
    found_lessons = lessons(project)
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
        "inbox_found": inbox_text is not None,
        "sections_with_content": sorted(sections),
        "lessons": found_lessons,
        "personal": personal_hits(text),
        "warnings": warnings,
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
        both = _project(top, "both", inbox_in="", changelog_in="")
        io.open(os.path.join(both, "rew_analitic", "skill-inbox.md"), "w", encoding="utf-8").write(
            "## What worked\nTHE OLD COPY\n")
        code, out, err = _run([both, "--json"])
        report = json.loads(out) if code == 0 else {}
        if code != 0 or "THE OLD COPY" in report.get("package", "THE OLD COPY") or report.get("warnings") != []:
            failures.append(f"the root's beside a copy: exit {code}, {report or out!r}, said {err.strip()!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the old home, rew_analitic/:"] + failures)


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


def _selftest():
    import shutil
    import tempfile
    failures = []
    for check in (_check_the_inbox_at_the_root, _check_the_old_home_is_read_and_said, _check_no_inbox_names_the_root):
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
          "shape, read at the project root (an older project's in rew_analitic/ with a warning naming "
          "the move), a missing inbox is refused rather than answered with an empty package, and an "
          "an API KEY in any of the four shapes, an e-mail, a home path and a phone are NAMED "
          "while ordinary tuning numbers are not — a key that leaves the machine once has left "
          "it for good")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
