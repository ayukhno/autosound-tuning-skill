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
the same order, so a maintainer reads every package the same way. Sources:
  * `<project>/rew_analitic/skill-inbox.md` — the tuner's own notes, section by section;
  * `<project>/rew_analitic/tuning-changelog*` — every `Lesson:` line, which is where a lesson
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

INBOX = os.path.join("rew_analitic", "skill-inbox.md")
CHANGELOG_GLOB = "tuning-changelog"
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


def lessons(project):
    """Every `Lesson:` line from the project's changelog, in file order."""
    found = []
    root = os.path.join(project, "rew_analitic")
    if not os.path.isdir(root):
        return found
    for name in sorted(os.listdir(root)):
        if not name.startswith(CHANGELOG_GLOB):
            continue
        for line in (_read(os.path.join(root, name)) or "").splitlines():
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
    inbox_text = _read(os.path.join(project, INBOX))
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
        print(f"error: no {INBOX} in {args.project} — the intake creates it; "
              f"nothing to harvest", file=sys.stderr)
        return 2
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


def _selftest():
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="harvest_inbox_")
    try:
        proj = os.path.join(tmp, "car")
        os.makedirs(os.path.join(proj, "rew_analitic"))
        io.open(os.path.join(proj, INBOX), "w", encoding="utf-8").write(
            "# Inbox\n\n## What worked\nLR24 at 80 Hz held the joint.\n\n"
            "## DSP/hardware quirks\nThe Phase control is one APF2.\n")
        io.open(os.path.join(proj, "rew_analitic", "tuning-changelog.md"), "w",
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
        assert personal_hits("LR24 at 80 Hz, 3.15 kHz, +4 dB") == [], \
            personal_hits("LR24 at 80 Hz, 3.15 kHz, +4 dB")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest OK — inbox sections and changelog `Lesson:` lines land in the fixed package "
          "shape, a missing inbox is refused rather than answered with an empty package, and an "
          "e-mail / home path / phone are NAMED while ordinary tuning numbers are not")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
