#!/usr/bin/env python3
"""Has this CABIN been described before? — the car-side twin of `dsp_profile.find_bundled`.

`project-intake.md:172` asks one question about two libraries: "first check whether there's already
a profile in `knowledge/dsp/` (and `knowledge/cars/` for this body)". Only half of it was backed by
code. For the processor there is a tool, it returns a clean "no" (`bundled_exact_match: null`), and
a consumer can put the answer in front of the person. For the body there was prose, so the check
happened when a session remembered to go looking — and on a real intake it did, then decided
silently what to do with what it found, and the material went unused for two days until the person
asked directly whether any existed (reported as `ayukhno/autosound-tuning-skill#19`).

**The point is not automation.** It is that "there is prior material for this cabin, here is how
much, do you want it carried as hypotheses?" becomes a question the person is ASKED, instead of a
judgement an agent makes quietly.

⛔ **EXACT match or nothing, and a near miss is never named.** A platform sibling is a different
car: the same shell can carry different doors, different glass and a different floor, and its
numbers do not transfer. The scope rule is `SKILL.md → knowledge/cars`, and the failure it guards
against is not a wrong file being read but a wrong file being *mentioned* — "we have something for
the Passat B7, want it?" is already the damage, because the answer is going to be yes. So this
module offers no suggestions, no fuzzy fallback and no "did you mean": `list_bundled` exists for a
person browsing the library, not for softening a `None`.

The library is markdown on purpose — `knowledge/cars/<body-slug>.md` is read by a person and by a
session, not parsed for numbers, and PART B of one is a checklist of things to VERIFY rather than
facts to cite. So this returns where the file is and what it calls itself, not its contents.

    car_profile.py --find "VW" "Passat" "B8" "sedan"
    car_profile.py --prior "VW" "Passat" "B8" "sedan" <project-dir> [<project-dir>...]
    car_profile.py --list

stdlib only, py3.9+.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

#: The method's own cabin library. Absolute, resolved from this module rather than from the
#: caller's cwd -- the same reason `dsp_profile.bundled_dir()` is.
BUNDLED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "knowledge", "cars")

#: Not a body. The template is the thing you copy to describe a new one, and a lookup that returns
#: it has answered "yes, we know this car" about a file full of placeholders.
NOT_A_BODY = ("_TEMPLATE",)


def bundled_dir():
    """The library's absolute path."""
    return os.path.normpath(BUNDLED_DIR)


def body_slug(make, model, generation="", body=""):
    """`("VW", "Passat", "B8", "sedan")` -> `vw-passat-b8-sedan`.

    **Four parts, because the car has four** (the owner, 2026-09-03). `model` is the nameplate --
    Passat. `generation` is the model range -- B8 -- and it is precisely **the span of years over
    which the acoustics count as the same**, which is why it, and not the year, is what classifies.
    `body` is a separate story again: sedan, wagon, hatch, and it changes the cabin outright.

    ⛔ **The year does not classify at all.** It is a detail of one car, not a property of the
    class: two builds of the same generation and body are the same cabin whether they left the
    line in 2017 or 2018, and the same year in a different shell is a different cabin. So `year`
    is absent from the slug on purpose -- it is recorded in the project because it describes THAT
    car, and it is never asked whether two cabins match.

    Built rather than searched for, which is the naming rule's whole purpose (`SKILL.md:108`: the
    path comes from the answer, never from a `find`). That also makes the refusals fall out of the
    arithmetic instead of needing rules of their own: a wagon slugs differently from a sedan and so
    does not match it, and a body nobody named slugs short and matches nothing.

    The parts are joined, so the older three-argument form still lands on the same slug: a project
    that recorded `model = "Passat B8"` with no separate generation slugs identically to one that
    split them. That is deliberate -- the split describes the car better without invalidating what
    was written before it.
    """
    joined = " ".join(str(p or "").strip() for p in (make, model, generation, body))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", joined.lower())).strip("-")


def title_of(path):
    """The file's own first heading, so a consumer shows what the LIBRARY calls this car.

    Read from the file rather than composed from the caller's three strings: the answer to "is this
    the same car?" must come from the thing being matched, not from the question.
    """
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return ""


def find_bundled_car(make, model, generation="", body="", dir_=None):
    """The library's entry for EXACTLY this body, or `None` — which is itself the answer.

    `None` means "nobody has described this cabin here", and that is what a session needs to hear
    before it starts an intake from scratch. It never means "close enough exists": see the module
    docstring for why a near miss is not reported at all.

    Returns `{"slug", "path", "title"}`.
    """
    slug = body_slug(make, model, generation, body)
    if not slug or slug.upper() in NOT_A_BODY:
        return None
    path = os.path.join(dir_ or bundled_dir(), f"{slug}.md")
    if not os.path.isfile(path):
        return None
    return {"slug": slug, "path": path, "title": title_of(path)}


def list_bundled(dir_=None):
    """Every cabin the library describes, as `(slug, path, title)`, slug-sorted.

    For a person browsing, and for a selftest. NOT for turning a `None` from `find_bundled_car`
    into a suggestion -- naming a sibling is the mistake this library's scope rule exists to stop.
    """
    out = []
    for path in sorted(glob.glob(os.path.join(dir_ or bundled_dir(), "*.md"))):
        slug = os.path.splitext(os.path.basename(path))[0]
        if slug.upper() in NOT_A_BODY:
            continue
        out.append((slug, path, title_of(path)))
    return out


def car_identity(project_dir):
    """What body a project SAYS it is: `{"slug", "car", "why"}` — `slug` is None when it cannot say.

    Three outcomes, and the third is the point. A project can be **this body**, can be **another
    body**, or can be **unable to say** — because `project.json` records `make`/`model`/`year` and
    a body only if somebody wrote one. Collapsing the third into "no" is the original failure of
    `#19` in a new place: material exists, nothing says so, and the silence reads as an answer.

    Old projects slug from their combined `model` ("Passat B8"), so they still match — but with no
    `body` recorded there is nothing to tell a sedan from a wagon, and this refuses rather than
    guessing. A wrong "yes" here hands another cabin's flaw map to a build it does not describe.
    """
    path = os.path.join(project_dir, "project.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"slug": None, "car": "", "why": "not a readable project"}
    if not isinstance(data, dict):
        return {"slug": None, "car": "", "why": "not a readable project"}
    car = data.get("car") or {}
    make, model = car.get("make") or "", car.get("model") or ""
    generation, body = car.get("generation") or "", car.get("body") or ""
    # The identity line is make/model/generation/body — the year is deliberately NOT in it. It
    # describes one car, never the class, and putting it here would suggest it takes part.
    line = " ".join(str(v) for v in (make, model, generation, body) if v)
    if not (make and model):
        return {"slug": None, "car": line, "why": "no car recorded"}
    if not body:
        return {"slug": None, "car": line,
                "why": "no body recorded — sedan and wagon cannot be told apart, so no match is claimed"}
    return {"slug": body_slug(make, model, generation, body), "car": line, "why": ""}


def find_prior_projects(dirs, make, model, generation="", body=""):
    """Previous projects on the SAME body, and the ones that could not say — `(matches, unknown)`.

    The second place `project-intake.md:172` asks about, and the half that had no command: the
    library answers "has this cabin been described", this answers "have WE built on it before".
    A previous build of the same shell carries a measured flaw map, and on the live intake that
    material sat unused for two days because nothing put it in front of the person (`#19`).

    Each match carries how much is on offer -- the row count and the measurements its `evidence`
    names -- because that is the question the person is answering: those captures live THERE, so
    the rows travel as hypotheses, never as facts (`project_seed`, `--findings`).

    `unknown` is returned separately and must be shown, not dropped: a project that does not record
    its body is not a project on another body. Reporting it as "none" is how the answer goes quiet.
    """
    want = body_slug(make, model, generation, body)
    matches, unknown = [], []
    for d in dirs:
        d = os.path.abspath(os.path.expanduser(str(d)))
        ident = car_identity(d)
        if ident["slug"] is None:
            if ident["why"] != "not a readable project":
                unknown.append({"path": d, "car": ident["car"], "why": ident["why"]})
            continue
        if not want or ident["slug"] != want:
            continue
        flaws = _flaw_rows(d)
        evidence = sorted({str(e) for row in flaws
                           for e in (row.get("evidence") or []) if e})
        matches.append({"path": d, "car": ident["car"], "slug": ident["slug"],
                        "flaws": len(flaws), "evidence": evidence})
    return matches, unknown


def _flaw_rows(project_dir):
    try:
        with open(os.path.join(project_dir, "project.json"), encoding="utf-8") as f:
            rows = ((json.load(f).get("acoustics") or {}).get("flaws")) or []
    except (OSError, ValueError, AttributeError):
        return []
    return [r for r in rows if isinstance(r, dict)]


def _main(argv):
    if len(argv) > 1 and argv[1] == "--list":
        for slug, path, title in list_bundled():
            print(f"{slug:<28} {title}")
        return 0
    if len(argv) > 1 and argv[1] == "--find":
        parts = argv[2:6]
        if len(parts) != 4:
            print('usage: --find "<make>" "<model>" "<generation>" "<body>"\n'
                  '  four parts, because the car has four: Passat is the MODEL, B8 the GENERATION\n'
                  '  (it carries the years), sedan the BODY. Three arguments would slug short and\n'
                  '  answer "not in the library" about a car that is in it.', file=sys.stderr)
            return 2
        found = find_bundled_car(*parts)
        if found is None:
            print("no exact match — this body is not in the library")
            return 0
        print(f"{found['slug']}\n{found['title']}\n{found['path']}")
        return 0
    if len(argv) > 1 and argv[1] == "--prior":
        parts, dirs = argv[2:6], argv[6:]
        if len(parts) != 4 or not dirs:
            print('usage: --prior "<make>" "<model>" "<generation>" "<body>" <dir> [<dir>...]',
                  file=sys.stderr)
            return 2
        matches, unknown = find_prior_projects(dirs, *parts)
        for m in matches:
            print(f"{m['path']}\n  {m['car']} · {m['flaws']} measured flaw rows on offer")
            if m["evidence"]:
                print(f"  evidence names captures that live THERE: {', '.join(m['evidence'][:6])}"
                      + (" …" if len(m["evidence"]) > 6 else ""))
        for u in unknown:
            print(f"{u['path']}\n  ⚠️ {u['why']}" + (f" ({u['car']})" if u["car"] else ""))
        if not matches and not unknown:
            print("no previous project on this body — which is the answer")
        return 0
    print(__doc__.strip().splitlines()[-4].strip(), file=sys.stderr)
    return 2


def _selftest():
    import tempfile

    lib = tempfile.mkdtemp(prefix="autosound_cars_")
    with open(os.path.join(lib, "vw-passat-b8-sedan.md"), "w", encoding="utf-8") as f:
        f.write("# VW Passat B8 sedan — a SINGLE-BUILD CASE STUDY\n\nbody\n")
    with open(os.path.join(lib, "_TEMPLATE.md"), "w", encoding="utf-8") as f:
        f.write("# <Make> <Model> <body>\n")

    assert body_slug("VW", "Passat", "B8 sedan") == "vw-passat-b8-sedan"
    assert body_slug(" vw ", "PASSAT", "b8   sedan") == "vw-passat-b8-sedan", "case and spacing"

    hit = find_bundled_car("VW", "Passat", "B8 sedan", dir_=lib)
    assert hit and hit["slug"] == "vw-passat-b8-sedan", hit
    assert hit["title"].startswith("VW Passat B8 sedan"), hit
    # The title comes off the FILE. Composing it from the caller's own three strings would make
    # the answer to "is this the same car?" a restatement of the question.
    assert "CASE STUDY" in hit["title"], hit

    # -- everything that is NOT this body must come back None, and come back SILENTLY ------------
    # A wagon is not a sedan, a B7 is not a B8, and an unnamed body is not a body. None of these
    # may be softened into a suggestion: naming a sibling is the damage, because the answer to
    # "we have something for the Passat B7, want it?" is going to be yes.
    for miss in (("VW", "Passat", "B8 wagon"),      # different body on the same platform
                 ("VW", "Passat", "B7 sedan"),      # different generation
                 ("VW", "Passat", ""),              # body not named at all
                 ("VW", "Passat", "B8"),            # generation without the body
                 ("", "", ""),                      # nothing asked
                 ("Skoda", "Superb", "B8 sedan")):  # same platform, different car
        assert find_bundled_car(*miss, dir_=lib) is None, miss

    # The template is not a car. A lookup that returns it has answered "yes, we know this cabin"
    # about a file of placeholders -- and it is reachable, because `_TEMPLATE` slugs to `template`
    # only if something strips the underscore, so the guard is on the NAME, not on the slug.
    assert find_bundled_car("", "", "_TEMPLATE", dir_=lib) is None
    assert [s for s, _, _ in list_bundled(dir_=lib)] == ["vw-passat-b8-sedan"], list_bundled(lib)

    # -- and the shipped library answers for the one body it describes --------------------------
    # `dsp_profile`'s own history is the reason this assertion is here: `find_bundled` took a
    # directory argument for months while no library shipped, so every consumer built a private
    # one and the same processor ended up described four times. A lookup with nothing to look in
    # passes its tests and fails its users.
    assert os.path.isdir(bundled_dir()), bundled_dir()
    assert find_bundled_car("VW", "Passat", "B8 sedan") is not None, "the shipped library moved"

    # -- four parts, because the car has four (the owner, 2026-09-03) ---------------------------
    # `model` is the nameplate, `generation` the model range (it carries the years), `body` a
    # separate story again -- and the body outranks the year: same year in another shell is
    # another cabin, same shell across two years is one.
    assert body_slug("VW", "Passat", "B8", "sedan") == "vw-passat-b8-sedan"
    assert find_bundled_car("VW", "Passat", "B8", "sedan", dir_=lib) is not None
    # The split does not invalidate what was written before it: the parts are joined, so a project
    # that kept "Passat B8" in one field lands on the same slug as one that split them.
    assert body_slug("VW", "Passat B8", "", "sedan") == body_slug("VW", "Passat", "B8", "sedan")
    # ...and the body still decides. A wagon of the same generation is a different cabin.
    assert find_bundled_car("VW", "Passat", "B8", "wagon", dir_=lib) is None

    # -- the second place: a previous PROJECT on the same body (#19) -----------------------------
    projects = tempfile.mkdtemp(prefix="autosound_projects_")

    def _project(name, car, flaws=()):
        d = os.path.join(projects, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as fh:
            json.dump({"car": car, "acoustics": {"flaws": list(flaws)}}, fh)
        return d

    same = _project("passat-helix", {"make": "VW", "model": "Passat", "generation": "B8",
                                     "body": "sedan", "year": 2018},
                    [{"f_hz": 32, "evidence": ["w-L_2 (sw)"]},
                     {"f_hz": 63, "evidence": ["w-L_2 (sw)", "m-R_4 (sw)"]}])
    wagon = _project("passat-wagon", {"make": "VW", "model": "Passat", "generation": "B8",
                                      "body": "wagon"})
    old = _project("passat-old", {"make": "VW", "model": "Passat B8", "year": 2019})
    _project("not-a-project", {})
    with open(os.path.join(projects, "not-a-project", "project.json"), "w") as fh:
        fh.write("{ broken")

    matches, unknown = find_prior_projects(
        [same, wagon, old, os.path.join(projects, "not-a-project"), os.path.join(projects, "gone")],
        "VW", "Passat", "B8", "sedan")

    assert [m["path"] for m in matches] == [same], matches
    # The YEAR takes no part. A second build of the same generation and body from another year is
    # the same cabin -- the generation IS the span of years over which the acoustics count as one
    # (the owner, 2026-09-03), so a match must not depend on the year agreeing.
    other_year = _project("passat-2020", {"make": "VW", "model": "Passat", "generation": "B8",
                                          "body": "sedan", "year": 2020})
    both, _ = find_prior_projects([same, other_year], "VW", "Passat", "B8", "sedan")
    assert [m["path"] for m in both] == [same, other_year], both
    assert all("2018" not in m["car"] and "2020" not in m["car"] for m in both), both
    assert matches[0]["flaws"] == 2, matches
    # What is on offer is the row count AND where its evidence points: those captures live in the
    # OTHER project, which is why the rows travel as hypotheses and never as facts.
    assert matches[0]["evidence"] == ["m-R_4 (sw)", "w-L_2 (sw)"], matches[0]
    # A wagon is not a sedan -- silently, with no "did you mean".
    assert wagon not in [m["path"] for m in matches]
    # ...but a project that cannot SAY its body is a third answer, not a "no". Dropping it into
    # the "no" pile is `#19` happening again one layer down: material exists, nothing says so.
    assert [u["path"] for u in unknown] == [old], unknown
    assert "no body recorded" in unknown[0]["why"], unknown
    # Unreadable and missing directories are not projects at all and stay out of both lists.
    assert len(matches) + len(unknown) == 2, (matches, unknown)
    # Asking about nothing matches nothing, rather than matching everything.
    assert find_prior_projects([same], "", "", "", "")[0] == []

    print(f"selftest OK -- exact body matched off the shipped library and off a fixture; six near "
          f"misses (wagon, B7, unnamed body, generation-only, empty, platform sibling) all None "
          f"and unsuggested; the template is not a car. Four-part slug (model/generation/body) "
          f"agrees with the old combined form; prior projects: 1 match with 2 rows and its "
          f"evidence, a wagon skipped, a body-less project reported as UNKNOWN not as no, "
          f"two years of one generation matched as one cabin. "
          f"library={bundled_dir()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        raise SystemExit(_selftest())
    raise SystemExit(_main(sys.argv))
